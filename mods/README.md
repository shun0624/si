# 自分用 mods（Claude Code の機能追加）

Claude Code の見た目や動きを自分用に変える追加機能です。

| mod | できること | 使い方 |
|---|---|---|
| `komonsaki-guard` | `10_顧問先` の資料を読んだあと、ネット検索や外部サービスへ送る前に「許可しますか？」と確認する | 解除は `/komonsaki-off` |
| `nedan` | 楽天と Yahoo!ショッピングを安い順に比べる（調べた日付つき） | `/nedan 品番`、上限つき `/nedan 品番 --max 30000`。si フォルダで Claude Code を開いて使う |
| `shinchoku-bar` | 画面の下に進捗バーと使用量（会話の容量・5時間枠・週の枠）を表示。80%を超えたらお知らせ | 確認は `/shinchoku` |
| `henkou-matome` | ファイルを変えた作業のあと「何を・なぜ・影響」を3行でまとめる | 一覧は `/henkou` |

## PC へのインストール

Claude Code（ターミナル）の入力欄で、1つずつ貼り付けて Enter:

```
/plugin install komonsaki-guard --marketplace shun0624/si
```

```
/plugin install nedan --marketplace shun0624/si
```

```
/plugin install shinchoku-bar --marketplace shun0624/si
```

```
/plugin install henkou-matome --marketplace shun0624/si
```

最初に `Add marketplace?` と聞かれたら `y`、次の画面はそのまま Enter（user＝自分のすべての作業で使う）。

コマンドの画面（シェル）からなら:

```
claude plugin install nedan --marketplace shun0624/si
```

デスクトップアプリで `/plugin` が使えないとき: 入力欄の横の「+」→ Plugins → Add marketplace に `shun0624/si` → Add plugin。

※ このリポジトリが非公開の場合、PC で GitHub にログイン済み（`gh auth login` のあと `gh auth setup-git`）である必要があります。
