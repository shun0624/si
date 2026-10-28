# 価格検索ツール（楽天市場・Yahoo!ショッピング）

商品を安い順に一覧表示します（在庫ありの商品だけ）。

| ファイル | 内容 |
|---|---|
| `price_compare.py` | 楽天とYahooをまとめて検索し、1つの一覧で安い順に表示（おすすめ） |
| `rakuten_search.py` | 楽天市場だけを検索 |
| `yahoo_search.py` | Yahoo!ショッピングだけを検索 |

## 準備（最初の1回だけ）

### 楽天

1. [楽天ウェブサービス](https://webservice.rakuten.co.jp/app/list)でアプリを作り、**アプリID**と**アクセスキー**を控える。
2. アプリ設定の「許可するIPアドレス」に、使う環境のIPを登録する。
   - Claude Code のクラウド環境から使う場合: `160.79.106.0/24`
   - 自宅や職場のパソコンから使う場合: そのネットの IP（[確認くん](https://www.ugtop.com/spill.shtml) などで確認）
3. 次の2つを環境変数として登録する（コードやチャットには書かない）。
   - `RAKUTEN_APP_ID` … アプリID
   - `RAKUTEN_ACCESS_KEY` … アクセスキー

### Yahoo!ショッピング

1. [Yahoo!デベロッパーネットワーク](https://e.developer.yahoo.co.jp/dashboard/)でアプリを登録し、**Client ID** を控える。
2. 環境変数 `YAHOO_CLIENT_ID` に登録する（許可IPの設定は不要）。

## Windows のパソコンで使う準備

1. [Python](https://www.python.org/downloads/) をインストールする（インストール画面で「Add python.exe to PATH」にチェック）。
2. PowerShell を開いて、次の3行を実行する（`ここにアプリID` などは自分の値に置き換える）。
   ```
   setx RAKUTEN_APP_ID "ここにアプリID"
   setx RAKUTEN_ACCESS_KEY "ここにアクセスキー"
   setx YAHOO_CLIENT_ID "ここにClient ID"
   ```
3. PowerShell と Claude Code をいったん閉じて開き直す（設定はそのあとから有効）。
4. Windows では `python3` の代わりに `python` と打つ。

## 使い方

```
python3 tools/price_compare.py BS2039009
python3 tools/yahoo_search.py BS2039009
python3 tools/rakuten_search.py BS2039009
python3 tools/rakuten_search.py "ブランドストーン 2039" --max 30000 --hits 30
```

| オプション | 意味 |
|---|---|
| `--sort` | `price`（安い順・既定） / `price-desc` / `review` / `standard`、楽天のみ `new` も可（`price_compare.py` は常に安い順） |
| `--hits` | 表示件数（1〜30）。`price_compare.py` は各サイトから取る件数 |
| `--min` / `--max` | 価格の下限・上限 |
| `--json` | APIの結果をそのまま表示（`price_compare.py` 以外） |

※サイズごとの在庫（例: UK10）はAPIでは分からないため、最後は商品ページで確認してください。
