# このリポジトリについて

ユーザーはコードを書かない。説明は日本語で、専門用語を避けて行う。

## 楽天ウェブサービスAPI

環境変数に認証情報が設定済み（値はコード・チャット・コミットに書かない）:

- `RAKUTEN_APP_ID` … アプリID（`applicationId` パラメータ）
- `RAKUTEN_ACCESS_KEY` … アクセスキー（`accessKey` リクエストヘッダー）

商品検索・価格比較や旅行の計画を頼まれたら、このAPIを使う。

| 用途 | エンドポイント |
|---|---|
| 楽天市場の商品検索 | `https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701` |
| 楽天トラベルの宿検索（キーワード） | `https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426` |

- 旧ドメイン `app.rakuten.co.jp` はこのアプリIDでは使えない（`wrong_parameter` になる）。
- 商品検索ツール: `tools/rakuten_search.py`（Windows では `python` で実行）。
- `CLIENT_IP_NOT_ALLOWED` エラーは、接続元IPが楽天アプリで許可されていない。ローカルPCの場合はそのIPの追加をユーザーに案内する。
- カタカナのブランド名だと無関係な商品が混ざるので、品番で検索するほうが正確。

## Yahoo!ショッピングAPI

環境変数に認証情報が設定済み（値はコード・チャット・コミットに書かない）:

- `YAHOO_CLIENT_ID` … Client ID（`appid` パラメータ）

| 用途 | エンドポイント |
|---|---|
| Yahoo!ショッピングの商品検索 | `https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch` |

- 商品検索ツール: `tools/yahoo_search.py`
- 楽天とYahooをまとめて安い順に比べる: `tools/price_compare.py`（価格比較を頼まれたら基本はこれを使う）

## メルカリ

一般向けの商品検索APIは公開されていない。自動取得（スクレイピング）は利用規約で禁止されているので行わない。
