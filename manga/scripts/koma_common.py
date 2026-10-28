"""コマ切り出し・はめ込みで共通に使う処理。"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

INK_LEVEL = 160        # これより暗い画素を「線」とみなす（0=黒, 255=白）
INFO_NAME = "コマ情報.json"
MASK_DIR = "マスク"
ADOPT_DIR = "採用"


def load_gray(path):
    """画像を白背景のグレースケール配列で読む（透明部分は白にする）。"""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return np.asarray(im.convert("L"))


def ring(mask, width):
    """マスクの外周から内側に width 画素ぶんの枠線部分（紙の端の辺には付けない）。"""
    inner = ndimage.binary_erosion(mask, iterations=max(1, width), border_value=1)
    return mask & ~inner


def save_info(folder, info):
    (Path(folder) / INFO_NAME).write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def load_info(folder):
    return json.loads((Path(folder) / INFO_NAME).read_text(encoding="utf-8"))
