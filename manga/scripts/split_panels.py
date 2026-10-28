"""ネーム（コマ割りしたラフ）の画像をコマごとに切り出す。

使い方: python split_panels.py p1.png [p2.png ...] [--comfy ComfyUIのフォルダ]

ネーム画像と同じ場所に「<ファイル名>_コマ」フォルダを作り、次のものを保存する。
  <ファイル名>_c01.png …  ComfyUI に渡すラフ（枠線と枠の外は消してある）
  確認用.png            …  どこをコマと判定したか番号付きで示したページ
  マスク/               …  はめ込み用のコマの形
  採用/                 …  ComfyUI で描いた中から選んだ画像を入れる場所
  コマ情報.json          …  はめ込みツールが使う位置情報
--comfy を付けると、ラフを ComfyUI の input フォルダにもコピーする。
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from koma_common import ADOPT_DIR, INK_LEVEL, MASK_DIR, load_gray, save_info

MIN_AREA = 0.01   # ページ面積に対するコマの最小の大きさ
PAD = 0.04        # 切り出すときにコマの周りに足す余白（コマの長辺に対する割合）
COLORS = [(230, 60, 60), (40, 140, 230), (40, 170, 90), (230, 150, 20),
          (150, 70, 200), (20, 170, 170), (200, 60, 140), (120, 120, 120)]


def frame_width(gray, mask, box):
    """コマの上下左右の中央で、枠線の太さ（暗い画素が続く長さ）を測る。"""
    x0, y0, x1, y1 = box
    ink = gray < INK_LEVEL
    runs = []
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    probes = [
        [(cy, x) for x in range(x0, x1)],
        [(cy, x) for x in range(x1 - 1, x0 - 1, -1)],
        [(y, cx) for y in range(y0, y1)],
        [(y, cx) for y in range(y1 - 1, y0 - 1, -1)],
    ]
    for line in probes:
        pts = [(y, x) for y, x in line if mask[y, x]][:80]
        n = 0
        for y, x in pts:
            if ink[y, x]:
                n += 1
            elif n:
                break
        if n:
            runs.append(n)
    return int(np.clip(np.median(runs) if runs else 3, 1, 40))


def find_panels(gray):
    h, w = gray.shape
    short = min(h, w)
    ink = gray < INK_LEVEL
    # 紙の端にも線を引く（紙の端まで出ているコマ＝タチキリも閉じた形にするため）
    ink[0, :] = ink[-1, :] = ink[:, 0] = ink[:, -1] = True
    # 枠線の小さなすき間をふさぐ
    close = max(1, round(short / 600))
    ink_wide = ndimage.binary_dilation(ink, iterations=close)

    # 余白とコマ間のすき間（紙の端につながる、細い・すかすかした白い部分）を探す
    lab, _ = ndimage.label(~ink_wide)
    e = close + 1
    edge = np.concatenate([lab[e], lab[-e - 1], lab[:, e], lab[:, -e - 1]])
    background = np.zeros((h, w), bool)
    objs = ndimage.find_objects(lab)
    for i in np.unique(edge[edge > 0]):
        ys, xs = objs[i - 1]
        bh, bw = ys.stop - ys.start, xs.stop - xs.start
        comp = lab[ys, xs] == i
        if comp.sum() < 0.6 * bh * bw or min(bh, bw) < 0.06 * short:
            background[ys, xs] |= comp

    # 残りがコマ。枠をはみ出したラフの線などの細いつながりは切り離す
    k = max(15, 4 * close + 9)
    solid = ndimage.binary_opening(~background, structure=np.ones((k, k), bool))
    flab, _ = ndimage.label(solid)
    panels = []
    for i, sl in enumerate(ndimage.find_objects(flab), 1):
        ys, xs = sl
        if ys.stop - ys.start < h * 0.05 or xs.stop - xs.start < w * 0.05:
            continue
        # 最初に太らせた分を戻す（紙の端に接している辺はそのまま）
        mask = ndimage.binary_erosion(flab == i, iterations=close, border_value=1)
        if mask.sum() < MIN_AREA * h * w or not (gray[mask] < INK_LEVEL).any():
            continue
        ys, xs = np.nonzero(mask)
        box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        at_edge = box[0] == 0 or box[1] == 0 or box[2] == w or box[3] == h
        panels.append({"box": box, "mask": mask, "open": at_edge,
                       "line": frame_width(gray, mask, box)})
    return panels


def reading_order(panels, page_w):
    """右から左、上から下の順（日本のマンガの読み順）に並べる。"""
    rows = []
    for p in sorted(panels, key=lambda p: p["box"][1]):
        x0, y0, x1, y1 = p["box"]
        for row in rows:
            overlap = min(y1, row["y1"]) - max(y0, row["y0"])
            if overlap > 0.5 * min(y1 - y0, row["y1"] - row["y0"]):
                row["items"].append(p)
                row["y0"], row["y1"] = min(y0, row["y0"]), max(y1, row["y1"])
                break
        else:
            rows.append({"y0": y0, "y1": y1, "items": [p]})
    step = page_w * 0.03
    ordered = []
    for row in sorted(rows, key=lambda r: r["y0"]):
        ordered += sorted(row["items"], key=lambda p: (-round(p["box"][2] / step), p["box"][1]))
    return ordered


def draw_check(gray, panels, path):
    page = Image.fromarray(gray).convert("RGB")
    overlay = Image.new("RGBA", page.size, (0, 0, 0, 0))
    h, w = gray.shape
    for n, p in enumerate(panels, 1):
        r, g, b = COLORS[(n - 1) % len(COLORS)]
        tint = np.zeros((h, w, 4), np.uint8)
        tint[p["mask"]] = (r, g, b, 60)
        overlay = Image.alpha_composite(overlay, Image.fromarray(tint, "RGBA"))
    page = Image.alpha_composite(page.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(page)
    size = max(24, min(h, w) // 12)
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:
        font = ImageFont.load_default()
    for n, p in enumerate(panels, 1):
        x0, y0, x1, y1 = p["box"]
        color = COLORS[(n - 1) % len(COLORS)]
        draw.rectangle(p["box"], outline=color, width=max(3, size // 10))
        label = str(n) + ("!" if p["open"] else "")
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        draw.text((cx, cy), label, fill=color, font=font, anchor="mm",
                  stroke_width=max(2, size // 12), stroke_fill="white")
    page.convert("RGB").save(path)


def split(image_path, comfy=None):
    image_path = Path(image_path)
    stem = image_path.stem
    gray = load_gray(image_path)
    h, w = gray.shape
    panels = reading_order(find_panels(gray), w)
    if not panels:
        print(f"[{image_path.name}] コマが見つかりませんでした。枠線が閉じているか、"
              "コマとコマの間に白いすき間があるか確認してください。")
        return None

    out = image_path.with_name(f"{stem}_コマ")
    (out / MASK_DIR).mkdir(parents=True, exist_ok=True)
    (out / ADOPT_DIR).mkdir(exist_ok=True)
    input_dir = Path(comfy) / "ComfyUI" / "input" if comfy else None

    info = {"page": image_path.name, "size": [w, h], "panels": []}
    for n, p in enumerate(panels, 1):
        pid = f"{stem}_c{n:02d}"
        x0, y0, x1, y1 = p["box"]
        pad = round(PAD * max(x1 - x0, y1 - y0))
        crop = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
        cx0, cy0, cx1, cy1 = crop
        mask = p["mask"][cy0:cy1, cx0:cx1]
        # 枠線を消し、枠の外を白にしたラフ（AIが枠線まで描かないように）
        inner = ndimage.binary_erosion(mask, iterations=p["line"] + 2, border_value=1)
        rough = np.full(mask.shape, 255, np.uint8)
        rough[inner] = gray[cy0:cy1, cx0:cx1][inner]
        Image.fromarray(rough).convert("RGB").save(out / f"{pid}.png")
        Image.fromarray((mask * 255).astype(np.uint8)).save(out / MASK_DIR / f"{pid}.png")
        if input_dir and input_dir.is_dir():
            shutil.copyfile(out / f"{pid}.png", input_dir / f"{pid}.png")
        info["panels"].append({"id": pid, "box": list(p["box"]), "crop": list(crop),
                               "line": p["line"], "open": p["open"]})
    save_info(out, info)
    draw_check(gray, panels, out / "確認用.png")

    print(f"[{image_path.name}] {len(panels)}コマに分けました → {out}")
    if any(p["open"] for p in panels):
        print("  ※「!」付きのコマは紙の端まで出ているコマ（タチキリ）として扱いました。")
    if input_dir and input_dir.is_dir():
        print("  ComfyUI の「Load Image」の一覧にもコピーしました。")
    return out


def main():
    ap = argparse.ArgumentParser(description="ネーム画像をコマごとに切り出す")
    ap.add_argument("images", nargs="*")
    ap.add_argument("--comfy", help="ComfyUI_windows_portable のフォルダ")
    args = ap.parse_args()
    if not args.images:
        print("ネームの画像ファイルを、このツールのアイコンの上にドラッグ＆ドロップしてください。")
        return 1
    ok = 0
    for path in args.images:
        try:
            ok += split(path, args.comfy) is not None
        except Exception as e:  # 1枚失敗しても残りは続ける
            print(f"[{Path(path).name}] 読み込めませんでした: {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
