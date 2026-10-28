"""コマ切り出し・はめ込みのテスト。 python manga/tests/test_panels.py"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import numpy as np
from PIL import Image, ImageDraw

import assemble_page
import make_sample
import split_panels
from koma_common import load_info


def near(a, b, tol=12):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def test_split_and_assemble(tmp):
    page = make_sample.make(tmp / "p1.png")
    # ラフの線がコマの間のすき間をまたいでいても、別のコマとして分けられる
    im = Image.open(page)
    ImageDraw.Draw(im).line((560, 700, 700, 720), fill="black", width=3)
    im.save(page)
    out = split_panels.split(page)
    info = load_info(out)
    boxes = [p["box"] for p in info["panels"]]
    assert len(boxes) == len(make_sample.PANELS), boxes
    for got, want in zip(boxes, make_sample.PANELS):
        assert near(got, (want[0], want[1], want[2] + 1, want[3] + 1)), (got, want)
    assert all(not p["open"] for p in info["panels"])
    assert all(4 <= p["line"] <= 8 for p in info["panels"]), [p["line"] for p in info["panels"]]

    # 切り出したラフには枠線が残っていない（端の列がすべて白）
    rough = np.asarray(Image.open(out / "p1_c01.png").convert("L"))
    assert rough[:, :20].min() == 255 and rough[:, -20:].min() == 255
    assert rough.min() < 50  # 棒人間は残っている

    # 2コマだけ「採用」に入れてはめ込む
    for pid, color in (("p1_c01", (255, 0, 0)), ("p1_c03", (0, 0, 255))):
        x0, y0, x1, y1 = next(p["crop"] for p in info["panels"] if p["id"] == pid)
        Image.new("RGB", (1216, 832), color).save(out / "採用" / f"manga_{pid}_00001_.png")
        Image.new("RGB", (1216, 832), color).save(out / "採用" / f"{pid}_00002_.png")
    result = assemble_page.assemble(page)
    img = np.asarray(Image.open(result).convert("RGB"))
    x0, y0, x1, y1 = make_sample.PANELS[0]
    assert tuple(img[(y0 + y1) // 2, (x0 + x1) // 2]) == (255, 0, 0)
    assert tuple(img[y0 + 2, (x0 + x1) // 2]) == (0, 0, 0)        # 枠線は黒
    assert tuple(img[y0 - 10, (x0 + x1) // 2]) == (255, 255, 255)  # 枠の外は白のまま
    x0, y0, x1, y1 = make_sample.PANELS[2]
    assert tuple(img[(y0 + y1) // 2, (x0 + x1) // 2]) == (0, 0, 255)
    x0, y0, x1, y1 = make_sample.PANELS[1]
    assert tuple(img[(y0 + y1) // 2, x0 + 20]) == (255, 255, 255)  # 未採用のコマはラフのまま


def test_tachikiri(tmp):
    # 右上のコマが紙の端まで出ている（タチキリ）ページ
    panels = [(600, 0, 1200, 600), (80, 80, 570, 600), (80, 630, 1120, 1620)]
    page = make_sample.make(tmp / "p2.png", panels=panels)
    info = load_info(split_panels.split(page))
    assert len(info["panels"]) == 3
    first = info["panels"][0]
    assert first["open"] and near(first["box"], (600, 0, 1200, 603), 15), first


def test_no_panels(tmp):
    Image.new("RGB", (800, 1000), "white").save(tmp / "blank.png")
    assert split_panels.split(tmp / "blank.png") is None


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        for name, fn in list(globals().items()):
            if name.startswith("test_"):
                sub = Path(d) / name
                sub.mkdir()
                fn(sub)
                print("OK", name)
