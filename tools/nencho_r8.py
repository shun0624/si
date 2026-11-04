"""令和8年分（2026年分）の年末調整の計算ツール。

国税庁「令和8年分 年末調整のしかた」「源泉徴収簿を使用した年末調整の手順」
（電子計算機等による年末調整の計算式）に沿って、1人分の年調年税額と過不足額を計算する。

※ 令和8年分専用。令和7年分以前・令和9年分以後には使わないこと。
※ 年末調整で扱う所得金額調整控除は「子ども・特別障害者等」のものだけ。

使い方:
    python tools/nencho_r8.py 入力.json
    python tools/nencho_r8.py --example      # 国税庁の設例で計算して確認

入力JSONの例（項目は省略すると0・なし扱い）:
{
  "氏名": "山川太郎",
  "給与総額": 8970000,             # 本年中に支給日が来た給与・賞与の合計（年調対象）
  "徴収税額": 156670,              # 1〜12月に源泉徴収した税額の合計
  "社会保険料等": 1386102,         # 給与天引き＋申告分の社会保険料・小規模企業共済等掛金
  "給与以外の合計所得": 0,         # 本人の給与所得以外の所得（基礎・配偶者控除の判定用）
  "所得金額調整控除の要件あり": true,  # 本人が特別障害者、または23歳未満の扶養親族・特別障害者の配偶者/扶養親族あり
  "23歳未満の扶養親族あり": true,     # 生命保険料控除の特例（計算式Ⅱ）
  "生命保険": {"新生命": 80000, "旧生命": 35000, "介護医療": 80000,
               "新個人年金": 30000, "旧個人年金": 90000},
  "地震保険料": 42000,
  "旧長期損害保険料": 14800,
  "配偶者": {"合計所得": 500000, "70歳以上": false},   # 配偶者控除等申告書の提出がある場合のみ
  "特定親族の合計所得": [1000000],                     # 特定親族1人ごとの合計所得金額
  "扶養": {"一般": 1, "特定": 1, "老人": 0, "同居老親等": 1},
  "障害者": {"一般": 1, "特別": 0, "同居特別": 0},
  "寡婦": false, "ひとり親": false, "勤労学生": false,
  "住宅ローン控除額": 76500
}
"""

import json
import math
import sys
from fractions import Fraction


# ---------------------------------------------------------------- 給与所得
def nenchou_kyuyogaku(total):
    """年調給与額（220万〜660万未満は4,000円刻みの下限に置き換える）。"""
    if 2_200_000 <= total < 6_600_000:
        return total - (total - 2_200_000) % 4_000
    return total


def kyuyo_shotoku(total):
    """令和8年分 給与所得控除後の給与等の金額。"""
    a = nenchou_kyuyogaku(total)
    if a < 741_000:
        return 0
    if a < 2_191_000:
        return a - 740_000
    if a < 2_193_000:
        return 1_451_000
    if a < 2_196_000:
        return 1_453_000
    if a < 2_200_000:
        return 1_456_000
    if a < 3_600_000:
        return math.floor(a * Fraction(70, 100) - 80_000)
    if a < 6_600_000:
        return math.floor(a * Fraction(80, 100) - 440_000)
    if a < 8_500_000:
        return math.floor(a * Fraction(90, 100) - 1_100_000)
    return a - 1_950_000


def shotoku_chosei(total, eligible):
    """所得金額調整控除（子ども・特別障害者等）。"""
    if not eligible or total <= 8_500_000:
        return 0
    return math.ceil((min(total, 10_000_000) - 8_500_000) * Fraction(10, 100))


# ---------------------------------------------------------------- 保険料
def _shiki1(p):  # 新生命・介護医療・新個人年金
    if p <= 20_000:
        return Fraction(p)
    if p <= 40_000:
        return Fraction(p, 2) + 10_000
    if p <= 80_000:
        return Fraction(p, 4) + 20_000
    return Fraction(40_000)


def _shiki2(p):  # 23歳未満の扶養親族がいる場合の新生命（令和8・9年分）
    if p <= 30_000:
        return Fraction(p)
    if p <= 60_000:
        return Fraction(p, 2) + 15_000
    if p <= 120_000:
        return Fraction(p, 4) + 30_000
    return Fraction(60_000)


def _shiki3(p):  # 旧生命・旧個人年金
    if p <= 25_000:
        return Fraction(p)
    if p <= 50_000:
        return Fraction(p, 2) + 12_500
    if p <= 100_000:
        return Fraction(p, 4) + 25_000
    return Fraction(50_000)


def _best(new, old, new_calc, cap_both):
    cands = []
    if new:
        cands.append(math.ceil(new_calc(new)))
    if old:
        cands.append(math.ceil(_shiki3(old)))
    if new and old:
        cands.append(min(math.ceil(new_calc(new)) + math.ceil(_shiki3(old)), cap_both))
    return max(cands) if cands else 0


def seimei_hoken(h, under23):
    h = h or {}
    ippan = _best(h.get("新生命", 0), h.get("旧生命", 0),
                  _shiki2 if under23 else _shiki1, 60_000 if under23 else 40_000)
    kaigo = math.ceil(_shiki1(h.get("介護医療", 0))) if h.get("介護医療", 0) else 0
    nenkin = _best(h.get("新個人年金", 0), h.get("旧個人年金", 0), _shiki1, 40_000)
    return min(ippan + kaigo + nenkin, 120_000), {"一般": ippan, "介護医療": kaigo, "個人年金": nenkin}


def jishin_hoken(jishin, kyuchoki):
    a = min(jishin, 50_000)
    if kyuchoki <= 10_000:
        b = Fraction(kyuchoki)
    elif kyuchoki <= 20_000:
        b = Fraction(kyuchoki, 2) + 5_000
    else:
        b = Fraction(15_000)
    return min(math.ceil(a + b), 50_000)


# ---------------------------------------------------------------- 人的控除
def kiso(goukei):
    for limit, amount in [(4_890_000, 1_040_000), (6_550_000, 670_000), (23_500_000, 620_000),
                          (24_000_000, 480_000), (24_500_000, 320_000), (25_000_000, 160_000)]:
        if goukei <= limit:
            return amount
    return 0


# 配偶者特別控除：配偶者の合計所得の上限 → (A:900万以下, B:950万以下, C:1,000万以下)
_HAIGU_TOKUBETSU = [
    (950_000, (380_000, 260_000, 130_000)),
    (1_000_000, (360_000, 240_000, 120_000)),
    (1_050_000, (310_000, 210_000, 110_000)),
    (1_100_000, (260_000, 180_000, 90_000)),
    (1_150_000, (210_000, 140_000, 70_000)),
    (1_200_000, (160_000, 110_000, 60_000)),
    (1_250_000, (110_000, 80_000, 40_000)),
    (1_300_000, (60_000, 40_000, 20_000)),
    (1_330_000, (30_000, 20_000, 10_000)),
]


def haigusha(honnin_goukei, spouse):
    """(控除額, 種類)。spouse = {"合計所得": int, "70歳以上": bool} または None。"""
    if not spouse or honnin_goukei > 10_000_000:
        return 0, ""
    col = 0 if honnin_goukei <= 9_000_000 else 1 if honnin_goukei <= 9_500_000 else 2
    s = spouse.get("合計所得", 0)
    if s <= 620_000:
        table = (480_000, 320_000, 160_000) if spouse.get("70歳以上") else (380_000, 260_000, 130_000)
        return table[col], "配偶者控除"
    for limit, row in _HAIGU_TOKUBETSU:
        if s <= limit:
            return row[col], "配偶者特別控除"
    return 0, ""


_TOKUTEI = [(850_000, 630_000), (900_000, 610_000), (950_000, 510_000), (1_000_000, 410_000),
            (1_050_000, 310_000), (1_100_000, 210_000), (1_150_000, 110_000),
            (1_200_000, 60_000), (1_230_000, 30_000)]


def tokutei_shinzoku(income):
    if income <= 620_000:
        return 0  # 特定扶養親族（扶養控除63万円）の方で数える
    for limit, amount in _TOKUTEI:
        if income <= limit:
            return amount
    return 0


def fuyo_shogai(d):
    f = d.get("扶養", {}) or {}
    s = d.get("障害者", {}) or {}
    total = (380_000 * f.get("一般", 0) + 630_000 * f.get("特定", 0)
             + 480_000 * f.get("老人", 0) + 580_000 * f.get("同居老親等", 0))
    total += 270_000 * (s.get("一般", 0) + bool(d.get("寡婦")) + bool(d.get("勤労学生")))
    total += 400_000 * s.get("特別", 0) + 750_000 * s.get("同居特別", 0)
    total += 350_000 if d.get("ひとり親") else 0
    return total


# ---------------------------------------------------------------- 税額
def sanshutsu(taxable):
    for limit, rate, ded in [(1_950_000, 5, 0), (3_300_000, 10, 97_500), (6_950_000, 20, 427_500),
                             (9_000_000, 23, 636_000), (18_000_000, 33, 1_536_000),
                             (18_050_000, 40, 2_796_000)]:
        if taxable <= limit:
            return taxable * rate // 100 - ded
    raise ValueError("課税給与所得金額が1,805万円超のため年末調整の対象外")


def calc(d):
    total = d.get("給与総額", 0)
    if total > 20_000_000:
        raise ValueError("給与総額2,000万円超のため年末調整の対象外")
    r = {"氏名": d.get("氏名", "")}
    r["給与総額"] = total
    r["給与所得控除後の金額"] = kyuyo_shotoku(total)
    r["所得金額調整控除額"] = shotoku_chosei(total, d.get("所得金額調整控除の要件あり"))
    r["給与所得控除後の金額（調整控除後）"] = max(r["給与所得控除後の金額"] - r["所得金額調整控除額"], 0)
    goukei = r["給与所得控除後の金額（調整控除後）"] + d.get("給与以外の合計所得", 0)
    r["本人の合計所得金額"] = goukei

    r["社会保険料等控除額"] = d.get("社会保険料等", 0)
    r["生命保険料控除額"], r["生命保険料の内訳"] = seimei_hoken(d.get("生命保険"), d.get("23歳未満の扶養親族あり"))
    r["地震保険料控除額"] = jishin_hoken(d.get("地震保険料", 0), d.get("旧長期損害保険料", 0))
    r["配偶者（特別）控除額"], r["配偶者控除の種類"] = haigusha(goukei, d.get("配偶者"))
    r["特定親族特別控除額"] = sum(tokutei_shinzoku(x) for x in d.get("特定親族の合計所得", []))
    r["扶養控除額及び障害者等の控除額"] = fuyo_shogai(d)
    r["基礎控除額"] = kiso(goukei)
    koujo = sum(r[k] for k in ["社会保険料等控除額", "生命保険料控除額", "地震保険料控除額",
                               "配偶者（特別）控除額", "特定親族特別控除額",
                               "扶養控除額及び障害者等の控除額", "基礎控除額"])
    r["所得控除額の合計額"] = koujo
    taxable = max(r["給与所得控除後の金額（調整控除後）"] - koujo, 0) // 1000 * 1000
    r["課税給与所得金額"] = taxable
    r["算出所得税額"] = sanshutsu(taxable)
    loan = d.get("住宅ローン控除額", 0)
    r["住宅借入金等特別控除額"] = min(loan, r["算出所得税額"])
    if loan > r["算出所得税額"]:
        r["（注）源泉徴収票の住宅借入金等特別控除可能額"] = loan
    r["年調所得税額"] = r["算出所得税額"] - r["住宅借入金等特別控除額"]
    r["年調年税額"] = r["年調所得税額"] * 1021 // 1000 // 100 * 100
    diff = d.get("徴収税額", 0) - r["年調年税額"]
    r["過不足"] = f"超過額（還付） {diff:,}円" if diff >= 0 else f"不足額（徴収） {-diff:,}円"
    return r


EXAMPLES = [
    # 「令和8年分 年末調整のしかた」p57〜59の設例 → 年調年税額 41,400円、超過額 115,270円
    ({"氏名": "設例1（年末調整のしかた p57）", "給与総額": 8_970_000, "徴収税額": 156_670,
      "社会保険料等": 1_386_102, "所得金額調整控除の要件あり": True, "23歳未満の扶養親族あり": True,
      "生命保険": {"新生命": 80_000, "旧生命": 35_000, "介護医療": 80_000,
                   "新個人年金": 30_000, "旧個人年金": 90_000},
      "地震保険料": 42_000, "旧長期損害保険料": 14_800,
      "配偶者": {"合計所得": 500_000}, "特定親族の合計所得": [1_000_000],
      "扶養": {"一般": 1, "特定": 1, "同居老親等": 1}, "障害者": {"一般": 1},
      "住宅ローン控除額": 76_500},
     {"年調年税額": 41_400, "所得控除額の合計額": 4_826_102}),
    # 「源泉徴収簿を使用した年末調整の手順」の過不足額の精算の設例 → 年調年税額 26,100円、超過額 25,745円
    ({"氏名": "設例2（源泉徴収簿の手順）", "給与総額": 4_390_000, "徴収税額": 51_845,
      "社会保険料等": 641_525, "生命保険": {"旧生命": 50_200, "新個人年金": 56_000},
      "地震保険料": 45_000, "配偶者": {"合計所得": 0}, "扶養": {"一般": 1}},
     {"年調年税額": 26_100, "所得控除額の合計額": 2_558_075}),
]


def show(r):
    for k, v in r.items():
        print(f"  {k}: {v:,}" if isinstance(v, int) else f"  {k}: {v}")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--example":
        ok = True
        for data, expect in EXAMPLES:
            r = calc(data)
            print(f"■ {data['氏名']}")
            show(r)
            for k, v in expect.items():
                mark = "OK" if r[k] == v else "NG"
                ok &= r[k] == v
                print(f"  [{mark}] {k}: 計算 {r[k]:,} ／ 国税庁 {v:,}")
            print()
        sys.exit(0 if ok else 1)
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    for d in data if isinstance(data, list) else [data]:
        print(f"■ {d.get('氏名', '')}")
        show(calc(d))
        print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
