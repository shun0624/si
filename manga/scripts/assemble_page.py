"""ComfyUI で描いたコマを、ネームのページにはめ込んで仮組みする。

使い方: python assemble_page.py <ネーム画像 または「<ファイル名>_コマ」フォルダ> [...]

「採用」フォルダに入れた画像のうち、名前が「<ファイル名>_c01」などで始まるものを
そのコマに使う（同じコマに複数あるときは一番新しいもの）。
まだ描いていないコマはラフのまま残す。結果は「<ファイル名>_仮組み.png」に保存する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image, ImageOps

from koma_common import ADOPT_DIR, MASK_DIR, load_info, ring

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def resolve_folder(path):
    path = Path(path)
    if path.is_dir():
        return path
    return path.with_name(f"{path.stem}_コマ")


def adopted_image(folder, pid):
    files = [f for f in (folder / ADOPT_DIR).glob("*")
             if f.suffix.lower() in IMAGE_EXT and f.stem.lower().startswith(pid.lower())]
    return max(files, key=lambda f: f.stat().st_mtime) if files else None


def assemble(path):
    folder = resolve_folder(path)
    if not (folder / "コマ情報.json").exists():
        print(f"[{Path(path).name}] 先にコマ切り出しツールでコマに分けてください。")
        return None
    info = load_info(folder)
    page_path = folder.parent / info["page"]
    w, h = info["size"]
    if page_path.exists():
        page = Image.open(page_path).convert("RGB")
    else:
        page = Image.new("RGB", (w, h), "white")

    done, todo = [], []
    for p in info["panels"]:
        src = adopted_image(folder, p["id"])
        if not src:
            todo.append(p["id"])
            continue
        cx0, cy0, cx1, cy1 = p["crop"]
        size = (cx1 - cx0, cy1 - cy0)
        art = ImageOps.fit(Image.open(src).convert("RGB"), size, Image.LANCZOS)
        mask = np.asarray(Image.open(folder / MASK_DIR / f"{p['id']}.png")) > 127
        page.paste(art, (cx0, cy0), Image.fromarray((mask * 255).astype(np.uint8)))
        frame = ring(mask, p["line"])
        black = Image.new("RGB", size, "black")
        page.paste(black, (cx0, cy0), Image.fromarray((frame * 255).astype(np.uint8)))
        done.append(p["id"])

    out = folder.parent / f"{Path(info['page']).stem}_仮組み.png"
    page.save(out)
    print(f"[{info['page']}] {len(done)}/{len(info['panels'])}コマをはめ込みました → {out}")
    if todo:
        print("  まだのコマ: " + "、".join(todo))
    return out


def main():
    if len(sys.argv) < 2:
        print("ネームの画像（または「〇〇_コマ」フォルダ）を、このツールのアイコンの上に"
              "ドラッグ＆ドロップしてください。")
        return 1
    ok = 0
    for path in sys.argv[1:]:
        try:
            ok += assemble(path) is not None
        except Exception as e:
            print(f"[{Path(path).name}] はめ込みに失敗しました: {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
