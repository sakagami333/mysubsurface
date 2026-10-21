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

### 一覧ページ（`index.html`）
- 全ダイブ一覧テーブル（ダイビングNo・日付・場所・最大深度・潜水時間）
- ダイビングNo は Subsurface の `Dive-NNN` ファイル名から直接取得

### 個別ダイブ詳細ページ（`dive-{No}.html`）
URL はダイビングNo と一致（例: `dive-1000.html`）

**プロパティカード（2段構成）**

| 段 | 内容 |
|---|---|
| 1段目（全幅） | 潜水開始日時 ～ 終了時刻（潜水時間） 例: `2026/10/01 06:56 ～ 07:48 (52:20 min)` |
| 2段目 | 最大深度 / 平均水深 / 平均水温 / 酸素濃度 / GF値 |

- アイコンは Lucide を使用（酸素濃度: Fuel アイコン）
- アイコンサイズは JS で `1em` に統一（Lucide が埋め込む `width="24"` を上書き）

**深度プロファイルグラフ**
- Chart.js v4 による折れ線グラフ（残圧・減圧停止深度を重ね表示）
- 深度変化レートに応じた3色ライン（重ね描き方式）:

| 変化速度 | 色 | 描画レイヤー |
|---|---|---|
| 7 m/min 未満 | 青 | ベース（塗り） |
| 7〜9 m/min | 黄 | オーバーレイ |
| 10 m/min 以上 | 赤 | 最前面 |

  Chart.js v4 は `order` 値が小さいほど最前面に描画されるため、赤=10・黄=20・青=30 を設定。

**水温グラフ**
- メインチャートと時間軸を同期（プロットエリアの左右余白を JS で補正）
- グリッドは 5 分間隔（メインチャートと統一）

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
YYYY/MM/DD-trip/DD-DayName-HH=MM=SS/      ← 同月内のダイブ
YYYY/MM/DD-trip/MM-DD-DayName-HH=MM=SS/   ← 月をまたぐダイブ（月番号を含む）
    Dive-NNN        — ダイブメタデータ（深度・時間・機材情報など）
                      NNN がダイビング通算本数
    Divecomputer    — サンプルデータ（深度・水温・残圧・減圧停止深度）
YYYY/MM/00-Trip     — トリップの場所情報
01-Divesites/Site-XXXXXXXX  — ダイブサイト名
```

> **注意**: トリップが月をまたぐ場合、ダイブディレクトリが親の月ディレクトリと異なる月になることがある（例: 9月のトリップに10月1日のダイブが含まれる）。`parse.py` はディレクトリ名の `MM-DD-DayName` 形式を検出して正しい月を取得する。

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| [Jinja2](https://jinja.palletsprojects.com/) | HTML テンプレートエンジン |
| [Chart.js 4](https://www.chartjs.org/)（CDN） | ダイブプロファイルグラフ |
| [Lucide](https://lucide.dev/)（CDN） | アイコン |

---

## セットアップ手順（新環境・初回構築）

### 1. リポジトリのクローン

```bash
git clone https://github.com/sakagami333/mysubsurface.git
cd mysubsurface
pip install -r requirements.txt
```

### 2. ローカル動作確認

```bash
SUBSURFACE_EMAIL=you@example.com SUBSURFACE_PASSWORD=yourpassword python3 src/build.py
python3 -m http.server 8000 --directory public
# → http://localhost:8000 を開いて確認
```

### 3. GitHub Secrets の登録

GitHub リポジトリの **Settings → Secrets and variables → Actions** に以下を登録:

| シークレット名 | 内容 |
|---|---|
| `SUBSURFACE_EMAIL` | Subsurface Cloud のメールアドレス |
| `SUBSURFACE_PASSWORD` | Subsurface Cloud のパスワード |
| `SAKURA_FTP_HOST` | さくらサーバの FTP ホスト名 |
| `SAKURA_FTP_USER` | FTP ユーザー名 |
| `SAKURA_FTP_PASSWORD` | FTP パスワード |

### 4. さくらのサーバ側の準備

FTP でログインし、デプロイ先ディレクトリが存在することを確認:

```
./mysubsurface/   ← このディレクトリが存在すること
```

存在しない場合はあらかじめ作成しておく。

### 5. GitHub Actions の初回実行

GitHub リポジトリの **Actions タブ → Build and Deploy → Run workflow** で手動実行。  
ログが全ステップ ✅ になれば完了。

### 6. 公開 URL の確認

さくらのサーバの公開 URL（例: `https://yourname.sakura.ne.jp/mysubsurface/`）で  
`index.html` が表示されることを確認。

---

## 開発履歴

### 2026-10 セッション（初回実装 → 本格拡張）

| フェーズ | 内容 |
|---|---|
| 初期構成 | fetch / parse / generate パイプライン、GitHub Actions、FTP デプロイ |
| Phase 1 | ローカルビルド初回動作確認（`python3 src/build.py`）|
| Phase 2 | 深度グラフ拡張（残圧・デコ・水温チャート）、詳細情報カード追加 |
| Phase 3 | ダイビングNo取得（`Dive-NNN` ファイル名）、URL を No に一致（`dive-1000.html`）|
| Phase 4 | 潜水開始〜終了時刻カード（全幅・1段目）、潜水時間カード廃止 |
| Phase 5 | 深度変化レート別3色グラフ（青/黄/赤の重ね描き、Chart.js v4 order 制御）|
| Phase 6 | 月またぎダイブのパースバグ修正（`MM-DD-DayName` 形式対応）|
| Phase 7 | 水温グラフ時間軸をメインと同期、グリッド 5 分統一 |

### 既知の仕様・注意事項

- **ダイビングNo のオフセット**: Subsurface Cloud の `Dive-NNN` ファイル名が正として使用。本数が増えても自動追従。
- **Chart.js v4 の描画順**: `order` 値が**小さいほど最前面**（降順ループで描画）。青=30・黄=20・赤=10 で設定。
- **Lucide アイコンサイズ**: `createIcons()` が `width="24"` を SVG に埋め込むため、JS で `style.width = '1em'` を後付けして上書き。
- **水温グラフの軸ずれ**: 右軸（残圧）の有無で左余白が変わるため、`syncAreas()` でレンダリング後に両チャートの `layout.padding` を補正。
