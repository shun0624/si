#!/usr/bin/env python3
"""Yahoo!ショッピングの商品を検索して、安い順に一覧表示するスクリプト。

使い方:
    python3 tools/yahoo_search.py BS2039009
    python3 tools/yahoo_search.py "ブランドストーン 2039" --max 30000 --hits 30

Client ID は環境変数から読み込みます（コードやチャットに書かない）:
    YAHOO_CLIENT_ID  Yahoo!デベロッパーネットワークの Client ID（アプリケーションID）
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

SORTS = {
    "price": "+price",
    "price-desc": "-price",
    "review": "-review_count",
    "standard": "-score",
}

SHIPPING = {2: "送料無料", 3: "条件付き送料無料"}


def search(keyword, client_id, sort, hits, page, min_price, max_price):
    params = {
        "appid": client_id,
        "query": keyword,
        "sort": SORTS[sort],
        "results": hits,
        "start": (page - 1) * hits + 1,
        "in_stock": "true",  # 在庫ありの商品だけ
    }
    if min_price:
        params["price_from"] = min_price
    if max_price:
        params["price_to"] = max_price

    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit(f"エラー: HTTP {e.code}\n{body}")


def main():
    p = argparse.ArgumentParser(description="Yahoo!ショッピングを安い順に検索")
    p.add_argument("keyword", help="検索キーワード（品番など）")
    p.add_argument("--sort", choices=SORTS, default="price", help="並び順（既定: 安い順）")
    p.add_argument("--hits", type=int, default=20, help="表示件数（1〜50）")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--min", type=int, dest="min_price", help="最低価格")
    p.add_argument("--max", type=int, dest="max_price", help="最高価格")
    p.add_argument("--json", action="store_true", help="結果をJSONのまま出力")
    args = p.parse_args()

    client_id = os.environ.get("YAHOO_CLIENT_ID")
    if not client_id:
        sys.exit("エラー: 環境変数 YAHOO_CLIENT_ID を設定してください。")

    data = search(args.keyword, client_id, args.sort, args.hits,
                  args.page, args.min_price, args.max_price)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    items = data.get("hits", [])
    if not items:
        print("見つかりませんでした。")
        return

    print(f"「{args.keyword}」 {data.get('totalResultsAvailable', len(items))}件中 {len(items)}件を表示\n")
    for i, it in enumerate(items, 1):
        price = it.get("price", 0)
        shipping = SHIPPING.get((it.get("shipping") or {}).get("code"), "送料別")
        point = (it.get("point") or {}).get("amount", 0)
        seller = (it.get("seller") or {}).get("name", "")
        print(f"{i:>2}. {price:>8,}円  {shipping}  ポイント{point:,}円分  {seller}")
        print(f"    {it.get('name', '')[:80]}")
        print(f"    {it.get('url', '')}\n")


if __name__ == "__main__":
    main()
