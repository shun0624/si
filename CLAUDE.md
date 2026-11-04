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

## 年末調整（顧問先の依頼に答えるとき）

**年分を最初に確かめる。** 令和8年分（2026年分）は基礎控除・給与所得控除・扶養の所得要件などが大きく変わったので、ほかの年分の数字と混ぜない。記憶の数字ではなく、次の資料の数字を使う。

| 用途 | 場所 |
|---|---|
| 令和8年分の要点（改正点・控除額の表・計算の流れ・Q&A） | Googleドライブ `01_税務会計/23_参考資料/令和08年度_年末調整_要点メモ.md`（ファイルID `1rxwrjEcW2h_Tr3eQpSMNEKnWcfiLbOxA`） |
| 令和8年分の計算式（ツールが使えないとき用） | 同じフォルダの `令和08年度_年末調整_計算式.md`（ファイルID `1Er4Oxe8hnL-6fRextntA6jmg9b5sDbYP`） |
| 令和8年分の年税額の計算 | `tools/nencho_r8.py`（`--example` で国税庁の設例と一致することを確認できる） |
| 元の資料（細かい点の確認） | 国税庁「令和8年分 年末調整のしかた」ほか https://www.nta.go.jp/publication/pamph/gensen/nencho2026/01.htm |

- 計算を頼まれたら手計算せず `tools/nencho_r8.py` を使い、途中の数字（給与所得控除後の金額・各控除額・課税給与所得金額）も示す。
- 顧問先・従業員の個人情報（氏名・マイナンバー・給与額など）はコミットしない。計算用のファイルは作業用フォルダに置き、終わったら消す。
- メモにないことや、判断が分かれることは、国税庁の資料（上のURL）を確認してから答え、確認した箇所を伝える。

## Googleドライブの資料（必要なときに読む）

ユーザーの情報は Googleドライブの `00_マイハブ` にまとまっている。Google Drive コネクタで読む
（`.md` は `get_file_metadata` の `snippetVerbosity: MAX_ALLOWED` で本文が取れる）。
毎回全部読むのではなく、**話題に関係するものだけ**読む。ファイルIDで見つからなければ、ファイル名で `search_files` する。

| 読むとき | ファイル（場所） | ファイルID |
|---|---|---|
| ユーザーの前提・答え方の方針を確認したいとき | `SSOT.md`（03_AI環境/51_SSOT） | `1S6IlfP0n7GfnPXCE5pCx-1tRNB79qAlx` |
| 過去にどんな相談をしたか、続きの話か確かめたいとき | `2026-10-29_Claudeチャット履歴_整理.md`（03_AI環境/54_共有コンテキスト） | `1BqYE9hdyyNcyHsRBgK009vdd_4kau63L` |
| 楽天API・ホームサーバー・パッチパネルの経緯 | `2026-10-29_ClaudeCode作業まとめ_楽天API_ホームサーバー.md`（同上） | `1fjrKOuQh3WCp-_ZW5LjOqsKI-5OdK6jH` |
| 税務・住宅・車・投資・開発の進行中案件 | `context_summary.md`（同上） | `1HXSLqxxKMueUHlft9zXQmWbbfTY6Hgvm` |
| ドライブにファイルを保存・整理するとき（フォルダ構成と命名規則） | `00_INDEX.md`（00_マイハブ直下） | `1-MGz87SK3Wpe5rBLJ-9de0Cv25M3Xuj8` |
| マイハブでの作業ルール（削除はごみ箱へ、触ってはいけないもの） | `CLAUDE.md`（00_マイハブ直下） | `115eMIDYKJlZBeyPGIT1CBOCM93KmNcP3` |
| サーバー機（Open WebUI・ComfyUI・Ollama）の起動や接続 | `サーバー機_やることリスト.md`（03_AI環境/51_SSOT） | `1qllNFuSQIgoGhko2CUHXA_D51WGmsL17` |

- マイハブのトップは11分類（01_税務会計／02_自作アプリ／03_AI環境／04_マンガ制作／05_買い物ガジェット／06_車／07_新築住宅／08_木工DIY／09_ホームサーバー／10_情報整理／11_旅行生活）。
- 分野別の詳しい資料は `03_AI環境/54_共有コンテキスト/knowledge/` にある（新築住宅・車両・投資資産・税務会計・開発プロジェクト）。
- `01_税務会計/10_顧問先/` は顧問先の税務・財務データ。必要なときだけ読み、外部サービスに送らない。
- ドライブに新しく保存するときは、`03_AI環境/54_共有コンテキスト`（AI向けの記録）か各分類のフォルダ、迷ったら `00_受信箱（未整理）` に置く。既存ファイルを書き換える前はユーザーに確認する。
