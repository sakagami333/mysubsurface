# MEMORY.md — mysubsurface プロジェクト記録

## プロジェクト目標
Subsurface Cloud のダイビングログを毎日自動取得し、静的 HTML として公開する。
さくらのレンタルサーバに FTP デプロイ。URL は未定（さくらのサーバ側で確認が必要）。

---

## 実装済みコンポーネント（すべて `feat: 初期構成` コミットに含まれる）

| ファイル | 役割 | 状態 |
|---|---|---|
| `src/fetch.py` | Subsurface Cloud から git clone/pull | 動作確認済 |
| `src/parse.py` | ディレクトリ形式 → `Dive`/`Sample` オブジェクト | 動作確認済（667本検出） |
| `src/generate.py` | Jinja2 で静的 HTML 生成 | 動作確認済（668ファイル生成） |
| `src/build.py` | fetch → parse → generate を順に呼ぶ | 動作確認済 |
| `src/templates/index.html` | ダイブ一覧ページ | 実装済・表示未確認 |
| `src/templates/dive.html` | 個別ダイブページ（Chart.js 深度グラフ付き） | 実装済・表示未確認 |
| `.github/workflows/build-deploy.yml` | 毎日 JST 11:00 自動ビルド & FTP デプロイ | 実装済・未実行 |

---

## 残タスク（優先順）

### Phase 1: ローカル動作確認 ✅ 完了
- [x] `pip install -r requirements.txt`（jinja2 はすでにインストール済みだった）
- [x] `python src/build.py` → 667本のダイブを検出・668ファイル生成
- [x] **重要**: フォーマットは `.ssrf` XML ではなくディレクトリ＋テキスト形式。`parse.py` を全面書き直し済
- [ ] `python -m http.server 8000 --directory public` でブラウザ表示確認（未実施）

### Phase 2: GitHub Secrets 登録と CI 初回実行
- [ ] リポジトリの Settings → Secrets で以下5変数が登録されているか確認
  - `SUBSURFACE_EMAIL`
  - `SUBSURFACE_PASSWORD`
  - `SAKURA_FTP_HOST`
  - `SAKURA_FTP_USER`
  - `SAKURA_FTP_PASSWORD`
- [ ] `workflow_dispatch` で手動実行
- [ ] Actions ログでエラーがないか確認

### Phase 3: さくらのサーバ確認
- [ ] FTP でサーバに接続し `./mysubsurface/` ディレクトリが存在するか確認
  （なければ作成するか、workflow の `server-dir` を変更）
- [ ] デプロイ後の公開 URL でブラウザアクセス確認

### Phase 4: 運用確認（Phase 1〜3 完了後）
- [ ] 翌日の定期実行（JST 11:00）が成功するか確認
- [ ] 必要に応じてデザイン・表示の調整

---

## 意思決定ログ

| 日付 | 決定事項 | 理由 | 不採用案 |
|---|---|---|---|
| 初期 | Subsurface Cloud を git clone で取得 | `.ssrf` は git リポジトリとして提供される | REST API（存在しない） |
| 2026-10-21 | `parse.py` をディレクトリ形式対応に全面書き直し | 実際のリポジトリは `.ssrf` XML ではなく `YYYY/MM/DD-trip/DD-Day-HH=MM=SS/{Dive-NNN,Divecomputer}` 形式だった | XML パース継続 |
| 初期 | さくらへのデプロイに FTP-Deploy-Action を使用 | さくらのレンタルサーバは FTP しか使えない | SSH/rsync（不可） |
| 初期 | Chart.js を CDN から読み込み | ビルドツール不要でシンプル | バンドル |

---

## セッションログ

### 2026-10-21（初回記録）
- 取り組んだこと: プロジェクト状況の棚卸し、MEMORY.md / ERRORS.md 作成
- 完了: 実装済みコンポーネントの確認、残タスク整理
- 次回拾うべき項目: **Phase 1（ローカル動作確認）から開始**。`SUBSURFACE_EMAIL` と `SUBSURFACE_PASSWORD` を用意してから実行する。
