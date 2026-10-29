#!/usr/bin/env python3
"""10インチラック用 1U キーストーン パッチパネル（10口）を3Dプリント用STLで出力する。

使い方:
    pip install manifold3d trimesh
    python rack/patch_panel.py            # rack/stl/ に全部出力

寸法を変えたいときは、下の「設定」の数字を書き換えて実行し直す。
"""

import os
import manifold3d as m3d
import trimesh

# ===== 設定（単位: mm） =====
PORTS = 10            # 口数
PITCH = 19.5          # ポートの間隔
KEY_W = 14.9          # キーストーン穴の幅
KEY_H = 16.6          # キーストーン穴の高さ
PLATE_T = 2.0         # 正面板の厚さ（キーストーンのツメが掛かる厚さ）

PANEL_W = 254.0       # 10インチ
PANEL_H = 43.6        # 1U(44.45) から少し小さく
RAIL_PITCH = 236.5    # 左右の取付穴の中心間隔
HOLE_D = 6.5          # 取付穴の直径（M6ネジ用）
SLOT_LEN = 4.0        # 取付穴を横長にする量（位置ずれ吸収）
HOLE_Y = (6.0, 37.6)  # 取付穴の高さ（パネル上端から）

LIP_T = 2.0           # 裏の補強リブの厚さ
LIP_D = 12.0          # 裏の補強リブの奥行き
LIP_HALF = 102.0      # 補強リブの左右の範囲（中心から）。ラックの柱に当たらない幅

SPLICE_HOLE = 3.4     # 分割版の連結ネジ穴（M3）
# ============================


def box(x0, y0, z0, x1, y1, z1):
    """x:左右 y:上下(上が0, 下へ+) z:奥行き(正面0, 奥へ+)"""
    return m3d.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_z(x, y, d, z0, z1):
    return m3d.Manifold.cylinder(z1 - z0, d / 2, d / 2, 48).translate([x, y, z0])


def slot(x, y, d, length, z0, z1):
    s = cyl_z(x - length / 2, y, d, z0, z1) + cyl_z(x + length / 2, y, d, z0, z1)
    return s + box(x - length / 2, y - d / 2, z0, x + length / 2, y + d / 2, z1)


def port_xs():
    return [(i - (PORTS - 1) / 2) * PITCH for i in range(PORTS)]


def panel():
    hw = PANEL_W / 2
    body = box(-hw, 0, 0, hw, PANEL_H, PLATE_T)
    # 裏の補強リブ（上下）
    body += box(-LIP_HALF, 0, 0, LIP_HALF, LIP_T, LIP_D)
    body += box(-LIP_HALF, PANEL_H - LIP_T, 0, LIP_HALF, PANEL_H, LIP_D)
    # キーストーン穴
    cy = PANEL_H / 2
    for x in port_xs():
        body -= box(x - KEY_W / 2, cy - KEY_H / 2, -1, x + KEY_W / 2, cy + KEY_H / 2, LIP_D + 1)
    # 取付穴
    for sx in (-RAIL_PITCH / 2, RAIL_PITCH / 2):
        for hy in HOLE_Y:
            body -= slot(sx, hy, HOLE_D, SLOT_LEN, -1, PLATE_T + 1)
    return body


def splice_holes():
    # 中央（5番と6番の間）をまたぐ連結穴。リブの内側の高さに2段
    return [(dx, y) for dx in (-6.0, 6.0) for y in (PANEL_H * 0.5 - 13.5, PANEL_H * 0.5 + 13.5)]


def split_halves(p):
    hw = PANEL_W / 2 + 1
    for x, y in splice_holes():
        p -= cyl_z(x, y, SPLICE_HOLE, -1, LIP_D + 1)
    left = p ^ box(-hw, -1, -1, 0, PANEL_H + 1, LIP_D + 1)
    right = p ^ box(0, -1, -1, hw, PANEL_H + 1, LIP_D + 1)
    return left, right


def splice_plate():
    """裏から当てる連結バー。上下で同じ形なので2個印刷して使う。"""
    y0 = LIP_T + 0.5
    y1 = PANEL_H / 2 - KEY_H / 2 - 2.5   # キーストーン本体に当たらない高さまで
    bar = box(-12, y0, 0, 12, y1, 3.0)
    for x, y in splice_holes():
        if y < PANEL_H / 2:
            bar -= cyl_z(x, y, SPLICE_HOLE, -1, 4)
    return bar


def fit_test():
    """穴の大きさを確かめる試し刷り。左から小・中・大（幅と高さを0.3mmずつ変える）。"""
    sizes = [(KEY_W - 0.3, KEY_H - 0.3), (KEY_W, KEY_H), (KEY_W + 0.3, KEY_H + 0.3)]
    w, h = 3 * 24.0, 30.0
    body = box(0, 0, 0, w, h, PLATE_T)
    body += box(0, 0, 0, w, LIP_T, 8) + box(0, h - LIP_T, 0, w, h, 8)
    for i, (kw, kh) in enumerate(sizes):
        x = 12 + i * 24
        body -= box(x - kw / 2, h / 2 - kh / 2, -1, x + kw / 2, h / 2 + kh / 2, 9)
        # 目印: 穴の上に i+1 個の小さな凹み（1=小 2=中 3=大）
        for k in range(i + 1):
            mx = x - i * 2 + k * 4
            body -= cyl_z(mx, 4.0, 1.6, -1, 0.6)
    return body


def save(man, path):
    mesh = man.to_mesh()
    t = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts)
    # 正面が z=0（底面）なので、そのまま正面を下にして印刷できる
    t.export(path)
    b = t.bounds
    print(f"{os.path.basename(path)}: {b[1][0]-b[0][0]:.1f} x {b[1][1]-b[0][1]:.1f} x {b[1][2]-b[0][2]:.1f} mm")


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
    os.makedirs(out, exist_ok=True)
    p = panel()
    save(p, os.path.join(out, "patch_panel_10port_1U.stl"))
    left, right = split_halves(p)
    save(left, os.path.join(out, "patch_panel_10port_1U_left.stl"))
    save(right, os.path.join(out, "patch_panel_10port_1U_right.stl"))
    save(splice_plate(), os.path.join(out, "splice_bar_x2.stl"))
    save(fit_test(), os.path.join(out, "keystone_fit_test.stl"))


if __name__ == "__main__":
    main()
