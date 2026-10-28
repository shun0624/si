"""過去の元帳（ある銀行口座の部分）から、その口座の仕訳ルール表を作る。

使い方:
  python build_rules.py ledger.csv rules.json [--keywords keywords.csv]

ledger.csv の列: 日付, 相手勘定科目, 相手補助科目, 税区分, 摘要, 入金額, 出金額
  （入金額＝預金の借方、出金額＝預金の貸方）
keywords.csv の列（任意）: 相手勘定科目, 相手補助科目, 通帳キーワード
  元帳の摘要が漢字で通帳がカナのときなど、通帳での表記を追加で教えるためのもの。
"""

import argparse
import json
import statistics
from collections import Counter, defaultdict

from common import LEDGER_COLUMNS, is_fee_text, match_key, parse_amount, parse_date, read_csv

FEE_ACCOUNT = "支払手数料"
INTEREST_ACCOUNTS = ("支払利息", "支払利息割引料")
FEE_MAX = 1100  # これ以下の支払手数料を振込手数料とみなす


def is_loan_account(account: str) -> bool:
    return "借入金" in account


def build(ledger_rows: list[dict], keyword_rows: list[dict]) -> dict:
    entries = []
    for i, r in enumerate(ledger_rows, start=2):
        try:
            deposit, withdrawal = parse_amount(r["入金額"]), parse_amount(r["出金額"])
            date = parse_date(r["日付"])
        except ValueError as e:
            raise SystemExit(f"元帳 {i}行目: {e}")
        if deposit == 0 and withdrawal == 0:
            continue
        entries.append({
            "date": date,
            "account": (r["相手勘定科目"] or "").strip(),
            "sub": (r.get("相手補助科目") or "").strip(),
            "tax": (r.get("税区分") or "").strip(),
            "text": (r.get("摘要") or "").strip(),
            "direction": "入金" if deposit else "出金",
            "amount": deposit or withdrawal,
        })

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for e in entries:
        groups[(e["direction"], e["account"], e["sub"], e["tax"])].append(e)

    patterns = []
    for n, ((direction, account, sub, tax), items) in enumerate(
        sorted(groups.items(), key=lambda kv: -len(kv[1])), start=1
    ):
        amounts = [e["amount"] for e in items]
        keys = Counter(match_key(e["text"]) for e in items if match_key(e["text"]))
        examples = list(dict.fromkeys(e["text"] for e in sorted(items, key=lambda e: e["date"], reverse=True)))[:5]
        if account == FEE_ACCOUNT:
            keys.update(["テスウリヨウ", "手数料"])
        patterns.append({
            "id": f"P{n:03d}",
            "direction": direction,
            "account": account,
            "sub": sub,
            "tax": tax,
            "count": len(items),
            "keys": [k for k, _ in keys.most_common()],
            "examples": examples,
            "amount_min": min(amounts),
            "amount_max": max(amounts),
            "amount_median": int(statistics.median(amounts)),
            "amount_fixed": len(set(amounts)) == 1 and len(amounts) >= 2,
            "days": sorted(Counter(e["date"].day for e in items)),
            "last_date": max(e["date"] for e in items).isoformat(),
            "last_amount": max(items, key=lambda e: e["date"])["amount"],
        })

    _attach_keywords(patterns, keyword_rows)
    _attach_fee_habits(patterns, entries)
    _attach_loans(patterns, entries)
    return {"patterns": patterns, "entry_count": len(entries)}


def _attach_keywords(patterns: list[dict], keyword_rows: list[dict]) -> None:
    for r in keyword_rows:
        key = match_key(r.get("通帳キーワード", ""))
        if not key:
            continue
        hit = [p for p in patterns
               if p["account"] == r.get("相手勘定科目", "").strip() and p["sub"] == r.get("相手補助科目", "").strip()]
        if not hit:
            print(f"注意: キーワード「{r.get('通帳キーワード')}」の科目 {r.get('相手勘定科目')}/{r.get('相手補助科目')} は元帳にありません")
        for p in hit:
            if key not in p["keys"]:
                p["keys"].insert(0, key)


def _attach_fee_habits(patterns: list[dict], entries: list[dict]) -> None:
    """支払と同じ日に振込手数料があるか（手数料当方負担か）を相手先ごとに調べる。"""
    fees_by_date: dict = defaultdict(list)
    for e in entries:
        if e["direction"] == "出金" and (e["account"] == FEE_ACCOUNT or is_fee_text(e["text"])) and e["amount"] <= FEE_MAX:
            fees_by_date[e["date"]].append(e["amount"])
    for p in patterns:
        p["fee_rate"], p["fee_amount"] = 0.0, 0
        if p["direction"] != "出金" or p["account"] == FEE_ACCOUNT or p["account"] in INTEREST_ACCOUNTS or is_loan_account(p["account"]):
            continue
        dates = sorted({e["date"] for e in entries if _belongs(e, p)})
        with_fee = [d for d in dates if fees_by_date.get(d)]
        if dates:
            p["fee_rate"] = round(len(with_fee) / len(dates), 2)
        if with_fee:
            p["fee_amount"] = Counter(fees_by_date[with_fee[-1]]).most_common(1)[0][0]


def _attach_loans(patterns: list[dict], entries: list[dict]) -> None:
    """借入金返済の元本と、同じ日の支払利息の組を返済履歴として残す。"""
    interest_by_date: dict = defaultdict(list)
    for e in entries:
        if e["direction"] == "出金" and e["account"] in INTEREST_ACCOUNTS:
            interest_by_date[e["date"]].append(e)
    interest_pattern = next((p for p in patterns if p["direction"] == "出金" and p["account"] in INTEREST_ACCOUNTS), None)
    loan_patterns = [p for p in patterns if p["direction"] == "出金" and is_loan_account(p["account"])]
    for p in loan_patterns:
        history = []
        for e in sorted((e for e in entries if _belongs(e, p)), key=lambda e: e["date"]):
            candidates = interest_by_date.get(e["date"], [])
            interest = _pick_interest(e, candidates, len([q for q in loan_patterns if _paid_on(q, e["date"], entries)]))
            if interest is None:
                continue
            history.append({"date": e["date"].isoformat(), "principal": e["amount"], "interest": interest["amount"]})
        if not history:
            continue
        p["loan"] = {
            "history": history,
            "interest_pattern_id": interest_pattern["id"] if interest_pattern else None,
            "interest_account": interest_pattern["account"] if interest_pattern else "支払利息",
            "interest_tax": interest_pattern["tax"] if interest_pattern else "",
            "interest_sub": interest_pattern["sub"] if interest_pattern else "",
        }


def _pick_interest(principal_entry: dict, candidates: list[dict], loans_that_day: int):
    if not candidates:
        return None
    if len(candidates) == 1 and loans_that_day == 1:
        return candidates[0]
    # 同じ日に複数の返済がある場合は、摘要が同じものだけを組にする（組めなければ履歴に入れない）
    key = match_key(principal_entry["text"])
    same = [c for c in candidates if key and match_key(c["text"]) == key]
    return same[0] if len(same) == 1 else None


def _belongs(e: dict, p: dict) -> bool:
    return (e["direction"], e["account"], e["sub"], e["tax"]) == (p["direction"], p["account"], p["sub"], p["tax"])


def _paid_on(p: dict, date, entries: list[dict]) -> bool:
    return any(_belongs(e, p) and e["date"] == date for e in entries)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger")
    ap.add_argument("output")
    ap.add_argument("--keywords")
    args = ap.parse_args()
    ledger = read_csv(args.ledger, LEDGER_COLUMNS)
    keywords = read_csv(args.keywords, ["相手勘定科目", "相手補助科目", "通帳キーワード"]) if args.keywords else []
    rules = build(ledger, keywords)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=1)
    loans = [p for p in rules["patterns"] if p.get("loan")]
    print(f"元帳 {rules['entry_count']}件 → 仕訳パターン {len(rules['patterns'])}種類"
          f"（うち借入返済 {len(loans)}件、手数料込みの支払先 {sum(1 for p in rules['patterns'] if p['fee_rate'] >= 0.5)}件）")


if __name__ == "__main__":
    main()
