# Instagram 週次自動投稿ツール

週はじめに1週間分の画像とキャプションを登録しておくと、
毎日1枚ずつ自動でInstagramに投稿し、月曜の朝に1週間分のリマインダーメール、
投稿後に結果メール(成功/失敗)を送ってくれるツールです。

費用はGitHub Actionsの無料枠の範囲で収まるため、実質0円で運用できます。
(Instagram Graph API自体の利用料も無料です)

---

## 全体の仕組み

1. 毎週はじめに、`week/` フォルダに7枚の画像(mon.jpg〜sun.jpg)と
   `week/schedule.json` にキャプションを書いてGitHubにpushする
2. 月曜の朝、GitHub Actionsが自動でその週の予定をメールでリマインドしてくれる
3. 毎日、GitHub Actionsが自動でその日の画像をInstagramに投稿し、結果をメールしてくれる

---

## 事前準備(最初の1回だけ)

### 1. Instagramアカウントの準備
- Instagramを **ビジネスアカウントまたはクリエイターアカウント** に切り替える(個人アカウントは不可)
- そのInstagramアカウントと連携したFacebookページを用意する

### 2. Meta for Developers でアプリを作成
1. https://developers.facebook.com/ にアクセスしてアプリを新規作成
2. アプリに「Instagram Graph API」を追加
3. 「アクセストークン取得」ツールなどを使って、以下の権限を持つアクセストークンを取得
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
4. 取得した短期トークンを、長期(60日)トークンに交換する
5. InstagramのビジネスアカウントID(`IG_ACCOUNT_ID`)を取得する

   ※ ここはMetaの審査(App Review)が必要になる場合があります。手順の細部は
   Meta公式ドキュメント(developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing)
   を必ず確認してください。

   ⚠️ **長期トークンは60日で失効します。** 60日ごとに手動で更新するか、
   更新を自動化する仕組みを別途追加することをおすすめします(必要であれば追加で作成します)。

### 3. メール送信用の準備(Gmailの例)
1. Googleアカウントで2段階認証を有効にする
2. 「アプリパスワード」を発行する(Googleアカウント設定 → セキュリティ → アプリパスワード)
3. 発行された16桁のパスワードを後で `EMAIL_APP_PASSWORD` として使う

### 4. このプロジェクトをGitHubにアップロード
1. GitHubで新しいリポジトリを作成する(**Public(公開)推奨**。
   Instagram側が画像URLを読み込むために、画像が外部からアクセスできる必要があるため)
2. このフォルダの内容をそのリポジトリにpushする

### 5. GitHub Secretsの設定
リポジトリの `Settings → Secrets and variables → Actions → New repository secret` で、
以下を登録してください。

| Secret名 | 内容 |
|---|---|
| `IG_ACCOUNT_ID` | InstagramビジネスアカウントID |
| `IG_ACCESS_TOKEN` | 長期アクセストークン |
| `EMAIL_FROM` | 送信元のGmailアドレス |
| `EMAIL_TO` | 通知を受け取りたいメールアドレス(自分のアドレスでOK) |
| `EMAIL_APP_PASSWORD` | 上で発行したGmailアプリパスワード |

---

## 毎週の運用方法

1. `week/mon.jpg` 〜 `week/sun.jpg` にその週投稿したい画像を入れる
2. `week/schedule.json` の `caption` を、それぞれの曜日のキャプションに書き換える
   (画像を使わない日は、`"image": ""` のように空にしておくとその日はスキップされます)
3. GitHubにpushする

これだけで、月曜の朝にリマインダーメールが届き、毎日その日の画像が自動投稿され、
投稿が完了(または失敗)するとメールで知らせてくれます。

---

## 投稿時刻・リマインダー時刻を変えたい場合

- 毎日の投稿時刻: `.github/workflows/daily-post.yml` の `cron: "0 1 * * *"` を編集
- 週はじめのリマインダー時刻: `.github/workflows/weekly-reminder.yml` の `cron: "0 23 * * 0"` を編集

cronはUTC(協定世界時)で指定するため、日本時間(JST)にする場合は **9時間引いた時刻** を書きます。
(例: 日本時間10:00に投稿したい → UTC 1:00 → `0 1 * * *`)

---

## 動作確認したい場合

GitHubリポジトリの「Actions」タブから、各ワークフローを選んで
「Run workflow」ボタンを押すと、スケジュールを待たずにすぐ実行できます。
本番投稿前に一度試してみることをおすすめします。

---

## ファイル構成

```
instagram-weekly-poster/
├── .github/workflows/
│   ├── daily-post.yml       # 毎日の自動投稿ワークフロー
│   └── weekly-reminder.yml  # 週はじめのリマインダーワークフロー
├── week/
│   ├── schedule.json         # 曜日ごとの画像ファイル名とキャプション
│   ├── README.txt
│   └── (mon.jpg 等の画像をここに置く)
├── post_to_instagram.py      # 投稿処理本体
├── weekly_reminder.py        # リマインダーメール送信
├── email_utils.py            # メール送信の共通処理
└── requirements.txt
```
