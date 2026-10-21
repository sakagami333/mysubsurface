# mysubsurface

Subsurface Cloud に記録したダイビングログを静的 HTML として公開するビューア。  
毎日自動ビルドし、さくらのレンタルサーバへ FTP デプロイする。

## 概要

```
Subsurface Cloud (git リポジトリ)
        ↓ git clone / pull
src/fetch.py      — クラウドからデータ取得
src/parse.py      — ディレクトリ形式ログを Python オブジェクトに変換
src/generate.py   — Jinja2 テンプレートで静的 HTML 生成
src/templates/    — HTML テンプレート群
        ↓
public/           — 生成済み静的ファイル（.gitignore 対象）
        ↓ FTP
さくらのレンタルサーバ ./mysubsurface/
```

GitHub Actions が毎日 JST 11:00 にこの一連の流れを自動実行する。

## 機能

- ダイビングログ一覧ページ（`index.html`）
- 個別ダイブ詳細ページ（`dive-N.html`）
  - 情報カード: 最大深度 / 平均水深 / 潜水時間 / 平均水温 / 酸素濃度 / GF値
  - 深度プロファイルグラフ（残圧・減圧停止深度を重ね表示）
  - 水温グラフ（別軸でコンパクト表示）

## ディレクトリ構成

```
.
├── src/
│   ├── build.py        # エントリーポイント（fetch → parse → generate）
│   ├── fetch.py        # Subsurface Cloud から git clone / pull
│   ├── parse.py        # ログファイルをパースして Dive / Sample オブジェクトに変換
│   ├── generate.py     # Jinja2 で HTML を生成
│   └── templates/
│       ├── index.html  # ダイブ一覧
│       └── dive.html   # 個別ダイブ詳細（Chart.js グラフ付き）
├── public/             # ビルド出力（git 管理外）
├── requirements.txt
└── .github/workflows/
    └── build-deploy.yml
```

## ローカルでの実行

```bash
# 依存インストール
pip install -r requirements.txt

# ビルド（環境変数が必要）
SUBSURFACE_EMAIL=you@example.com SUBSURFACE_PASSWORD=yourpassword python src/build.py

# 生成結果をブラウザで確認
python -m http.server 8000 --directory public
# → http://localhost:8000 を開く
```

## 環境変数 / GitHub Secrets

| 変数名 | 内容 |
|---|---|
| `SUBSURFACE_EMAIL` | Subsurface Cloud のメールアドレス |
| `SUBSURFACE_PASSWORD` | Subsurface Cloud のパスワード |
| `SAKURA_FTP_HOST` | さくらのサーバの FTP ホスト名 |
| `SAKURA_FTP_USER` | FTP ユーザー名 |
| `SAKURA_FTP_PASSWORD` | FTP パスワード |

GitHub リポジトリの **Settings → Secrets and variables → Actions** に登録する。

## 自動デプロイ

`.github/workflows/build-deploy.yml` により以下を自動実行する。

- トリガー: 毎日 JST 11:00（cron `0 2 * * *`）および手動実行（`workflow_dispatch`）
- ビルド環境: ubuntu-latest / Python 3.12
- デプロイ先: さくらのサーバ `./mysubsurface/`（[FTP-Deploy-Action](https://github.com/SamKirkland/FTP-Deploy-Action) を使用）

## Subsurface Cloud のデータ形式

Subsurface Cloud は git リポジトリとして提供される（XML ではない）。  
ディレクトリ構造:

```
YYYY/MM/DD-trip/DD-DayName-HH=MM=SS/
    Dive-NNN        — ダイブメタデータ（深度・時間・機材情報など）
    Divecomputer    — サンプルデータ（深度・水温・残圧・減圧停止深度）
YYYY/MM/00-Trip     — トリップの場所情報
01-Divesites/Site-XXXXXXXX  — ダイブサイト名
```

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| [Jinja2](https://jinja.palletsprojects.com/) | HTML テンプレートエンジン |
| [Chart.js 4](https://www.chartjs.org/)（CDN） | ダイブプロファイルグラフ |
