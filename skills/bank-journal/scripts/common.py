"""共通処理：文字の正規化、金額・日付の読み取り、CSVの読み書き。"""

import csv
import datetime as dt
import re
import unicodedata

# 元帳CSV（標準形式）の列名
LEDGER_COLUMNS = ["日付", "相手勘定科目", "相手補助科目", "税区分", "摘要", "入金額", "出金額"]
# 通帳CSV（標準形式）の列名
PASSBOOK_COLUMNS = ["日付", "摘要", "出金額", "入金額", "残高", "読取メモ"]

_SMALL_KANA = str.maketrans("ァィゥェォッャュョヮヵヶ", "アイウエオツヤユヨワカケ")

# 通帳・元帳の摘要によく付く、相手先の判別に関係ない語（長いものから順に除去する）
_NOISE_WORDS = sorted(
    [
        "フリコミシキン", "フリコミ", "フリカエ", "コウザフリカエ", "コウフリ", "ジドウハライコミ",
        "ジハライ", "ジフリ", "デンサイ", "ネツト", "ＩＢ", "IB", "EB", "ATM", "カ-ド", "カード",
        "振込", "振替", "口座振替", "自動払込", "自払", "入金", "出金", "支払", "支払い", "引落", "引落し",
        "カブシキガイシヤ", "ユウゲンガイシヤ", "ゴウドウガイシヤ", "株式会社", "有限会社", "合同会社",
        "(株)", "(有)", "(同)", "(カ)", "(ユ)", "(ド)", "カ)", "(カ", "ユ)", "(ユ", "ド)", "(ド",
        "分", "月分", "様", "御中",
    ],
    key=len,
    reverse=True,
)

FEE_WORDS = ["テスウリヨウ", "手数料", "フリコミテスウリヨウ", "振込手数料"]


def to_katakana(text: str) -> str:
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in text)


def normalize(text: str) -> str:
    """全角半角・ひらがな・小書き文字の違いをそろえる。"""
    text = unicodedata.normalize("NFKC", text or "")
    text = to_katakana(text).upper().translate(_SMALL_KANA)
    text = text.replace("ｰ", "ー").replace("－", "-")
    return re.sub(r"\s+", "", text)


def match_key(text: str) -> str:
    """摘要から相手先を表す部分だけを取り出した照合用キー。"""
    full = normalize(text)
    key = full
    for word in _NOISE_WORDS:
        key = key.replace(normalize(word), "")
    key = re.sub(r"[0-9０-９]+", "", key)
    key = re.sub(r"[()（）\[\]「」『』・.,、。/\\:：\-ー_]", "", key)
    # 「カード ATM」のように定型語だけの摘要は、そのまま照合に使う
    return key or re.sub(r"[0-9()（）\-ー]", "", full)


def is_fee_text(text: str) -> bool:
    n = normalize(text)
    return any(normalize(w) in n for w in FEE_WORDS)


def parse_amount(value) -> int:
    if value is None:
        return 0
    s = unicodedata.normalize("NFKC", str(value)).replace(",", "").replace("円", "").replace("¥", "").strip()
    if s in ("", "-", "*"):
        return 0
    negative = s.startswith("△") or s.startswith("▲") or s.startswith("-")
    s = s.lstrip("△▲-")
    try:
        amount = int(round(float(s)))
    except ValueError:
        raise ValueError(f"金額として読めません: {value!r}")
    return -amount if negative else amount


def parse_date(value) -> dt.date:
    """2026/04/01、2026-04-01、R8.4.1、令和8年4月1日 などを読む。"""
    s = unicodedata.normalize("NFKC", str(value)).strip()
    m = re.match(r"^(令和|R)\s*(\d+|元)[年./-](\d+)[月./-](\d+)", s, re.I)
    if m:
        year = 1 if m.group(2) == "元" else int(m.group(2))
        return dt.date(2018 + year, int(m.group(3)), int(m.group(4)))
    m = re.match(r"^(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})", s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    raise ValueError(f"日付として読めません: {value!r}")


def read_csv(path: str, required: list[str]) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if rows:
        missing = [c for c in required if c not in rows[0]]
        if missing:
            raise SystemExit(f"{path} に必要な列がありません: {', '.join(missing)}")
    return rows
