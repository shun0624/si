#!/usr/bin/env python3
"""楽天市場の商品を検索して、安い順に一覧表示するスクリプト。

使い方:
    python3 tools/rakuten_search.py BS2039009
    python3 tools/rakuten_search.py "ブランドストーン 2039" --max 30000 --hits 30

アプリIDとアクセスキーは環境変数から読み込みます（コードやチャットに書かない）:
    RAKUTEN_APP_ID      楽天ウェブサービスのアプリID
    RAKUTEN_ACCESS_KEY  楽天ウェブサービスのアクセスキー
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

SORTS = {
    "price": "+itemPrice",
    "price-desc": "-itemPrice",
    "review": "-reviewCount",
    "new": "-updateTimestamp",
    "standard": "standard",
}


def search(keyword, app_id, access_key, sort, hits, page, min_price, max_price):
    params = {
        "applicationId": app_id,
        "keyword": keyword,
        "sort": SORTS[sort],
        "hits": hits,
        "page": page,
        "formatVersion": 2,
        "availability": 1,  # 在庫ありの商品だけ
    }
    if min_price:
        params["minPrice"] = min_price
    if max_price:
        params["maxPrice"] = max_price

    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"accessKey": access_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if "CLIENT_IP_NOT_ALLOWED" in body:
            sys.exit(
                "エラー: この接続元IPが楽天アプリで許可されていません。\n"
                "楽天ウェブサービスのアプリ設定で、許可IPを追加してください。"
            )
        sys.exit(f"エラー: HTTP {e.code}\n{body}")


def items_of(data):
    # formatVersion=2 は平らな配列、1 は {"Item": {...}} で包まれている
    for it in data.get("Items") or data.get("items") or []:
        yield it.get("Item", it) if isinstance(it, dict) else it


def main():
    p = argparse.ArgumentParser(description="楽天市場を安い順に検索")
    p.add_argument("keyword", help="検索キーワード（品番など）")
    p.add_argument("--sort", choices=SORTS, default="price", help="並び順（既定: 安い順）")
    p.add_argument("--hits", type=int, default=20, help="表示件数（1〜30）")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--min", type=int, dest="min_price", help="最低価格")
    p.add_argument("--max", type=int, dest="max_price", help="最高価格")
    p.add_argument("--json", action="store_true", help="結果をJSONのまま出力")
    args = p.parse_args()

    app_id = os.environ.get("RAKUTEN_APP_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")
    if not app_id or not access_key:
        sys.exit("エラー: 環境変数 RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY を設定してください。")

    data = search(args.keyword, app_id, access_key, args.sort, args.hits,
                  args.page, args.min_price, args.max_price)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    items = list(items_of(data))
    if not items:
        print("見つかりませんでした。")
        return

    print(f"「{args.keyword}」 {data.get('count', len(items))}件中 {len(items)}件を表示\n")
    for i, it in enumerate(items, 1):
        price = it.get("itemPrice", 0)
        shipping = "送料無料" if it.get("postageFlag") == 0 else "送料別"
        point = it.get("pointRate", 1)
        print(f"{i:>2}. {price:>8,}円  {shipping}  ポイント{point}倍  {it.get('shopName', '')}")
        print(f"    {it.get('itemName', '')[:80]}")
        print(f"    {it.get('itemUrl', '')}\n")


if __name__ == "__main__":
    main()
