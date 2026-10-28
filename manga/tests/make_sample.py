"""テスト・お試し用のネーム画像（棒人間のラフ）を作る。

python manga/tests/make_sample.py  → manga/sample/p1.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 1700
M, G = 80, 30  # 紙の余白、コマの間のすき間

# 読み順どおりに並べたコマ（x0, y0, x1, y1）
PANELS = [
    (M, M, W - M, 520),                    # 1 上段・横長
    (640, 520 + G, W - M, 1180),           # 2 中段・右の縦長
    (M, 520 + G, 640 - G, 850),            # 3 中段・左上
    (M, 850 + G, 640 - G, 1180),           # 4 中段・左下
    (620, 1180 + G, W - M, H - M),         # 5 下段・右
    (M, 1180 + G, 620 - G, H - M),         # 6 下段・左
]


def stick(draw, x, y, s, label, font):
    """棒人間を1人描く（x, y は頭の中心、s は大きさ）。"""
    draw.ellipse((x - s, y - s, x + s, y + s), outline="black", width=3)
    draw.line((x, y + s, x, y + 4 * s), fill="black", width=3)
    draw.line((x - 2 * s, y + 2 * s, x + 2 * s, y + 2 * s), fill="black", width=3)
    draw.line((x, y + 4 * s, x - 1.5 * s, y + 6.5 * s), fill="black", width=3)
    draw.line((x, y + 4 * s, x + 1.5 * s, y + 6.5 * s), fill="black", width=3)
    draw.text((x + 2 * s, y - 2 * s), label, fill="black", font=font)


def make(path, panels=PANELS, size=(W, H), line=6):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=36)
    except TypeError:
        font = ImageFont.load_default()
    for x0, y0, x1, y1 in panels:
        d.rectangle((x0, y0, x1, y1), outline="black", width=line)
        s = max(12, min((y1 - y0) // 14, (x1 - x0) // 24))
        stick(d, (x0 + x1) // 2 + s * 3, y0 + (y1 - y0) // 3, s, "A", font)
        if x1 - x0 > 400:
            stick(d, (x0 + x1) // 2 - s * 4, y0 + (y1 - y0) // 3, s, "B", font)
    d.text((W // 2, H - M // 2), "1", fill="black", font=font)  # ノンブル（ページ番号）
    im.save(path)
    return path


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "sample" / "p1.png"
    make(out)
    print(out)
    sys.exit(0)
