#!/usr/bin/env python3
"""楽天市場とYahoo!ショッピングをまとめて検索し、安い順に1つの一覧で表示するスクリプト。

使い方:
    python3 tools/price_compare.py BS2039009
    python3 tools/price_compare.py "ブランドストーン 2039" --max 30000 --hits 15

環境変数（コードやチャットに書かない）:
    RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY  楽天ウェブサービス
    YAHOO_CLIENT_ID                      Yahoo!デベロッパーネットワーク
片方が未設定やエラーでも、もう片方の結果は表示します。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rakuten_search  # noqa: E402
import yahoo_search  # noqa: E402


def from_rakuten(keyword, hits, min_price, max_price):
    app_id = os.environ.get("RAKUTEN_APP_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not app_id or not access_key:
        raise SystemExit("環境変数 RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY が未設定です。")
    data = rakuten_search.search(keyword, app_id, access_key, "price", hits, 1,
                                 min_price, max_price)
    for it in rakuten_search.items_of(data):
        yield {
            "site": "楽天",
            "price": it.get("itemPrice", 0),
            "shipping": "送料無料" if it.get("postageFlag") == 0 else "送料別",
            "point": f"ポイント{it.get('pointRate', 1)}倍",
            "shop": it.get("shopName", ""),
            "name": it.get("itemName", ""),
            "url": it.get("itemUrl", ""),
        }


def from_yahoo(keyword, hits, min_price, max_price):
    client_id = os.environ.get("YAHOO_CLIENT_ID")
    if not client_id:
        raise SystemExit("環境変数 YAHOO_CLIENT_ID が未設定です。")
    data = yahoo_search.search(keyword, client_id, "price", hits, 1, min_price, max_price)
    for it in data.get("hits", []):
        yield {
            "site": "Yahoo",
            "price": it.get("price", 0),
            "shipping": yahoo_search.SHIPPING.get((it.get("shipping") or {}).get("code"), "送料別"),
            "point": f"ポイント{(it.get('point') or {}).get('amount', 0):,}円分",
            "shop": (it.get("seller") or {}).get("name", ""),
            "name": it.get("name", ""),
            "url": it.get("url", ""),
        }


def main():
    p = argparse.ArgumentParser(description="楽天とYahoo!ショッピングを安い順に比較")
    p.add_argument("keyword", help="検索キーワード（品番など）")
    p.add_argument("--hits", type=int, default=15, help="各サイトから取る件数（1〜30）")
    p.add_argument("--min", type=int, dest="min_price", help="最低価格")
    p.add_argument("--max", type=int, dest="max_price", help="最高価格")
    args = p.parse_args()

    items = []
    for name, fetch in (("楽天", from_rakuten), ("Yahoo", from_yahoo)):
        try:
            items.extend(fetch(args.keyword, args.hits, args.min_price, args.max_price))
        except SystemExit as e:
            print(f"[{name}] 取得できませんでした: {e}\n")

    if not items:
        print("見つかりませんでした。")
        return

    items.sort(key=lambda it: it["price"])
    print(f"「{args.keyword}」 楽天・Yahooあわせて {len(items)}件（安い順）\n")
    for i, it in enumerate(items, 1):
        print(f"{i:>2}. [{it['site']}] {it['price']:>8,}円  {it['shipping']}  {it['point']}  {it['shop']}")
        print(f"    {it['name'][:80]}")
        print(f"    {it['url']}\n")


if __name__ == "__main__":
    main()
