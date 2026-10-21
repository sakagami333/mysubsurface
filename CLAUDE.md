# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Subsurface Cloud（cloud.subsurface-divelog.org）からダイビングログを取得し、静的 HTML として公開するビューア。さくらのレンタルサーバに FTP デプロイする。

## アーキテクチャ

```
Subsurface Cloud (git + .ssrf XML)
        ↓ git clone (Basic Auth)
src/fetch.py      # クラウドからデータ取得
src/parse.py      # .ssrf XML をパース → Python オブジェクト
src/generate.py   # Jinja2 テンプレートで静的 HTML 生成
src/templates/    # HTML テンプレート群
        ↓
public/           # 生成された静的ファイル（.gitignore 対象）
        ↓ FTP
さくらのレンタルサーバ
```

GitHub Actions（`.github/workflows/build-deploy.yml`）が定期実行してこの一連の流れを自動化する。

## 主要コマンド

```bash
# 依存インストール
pip install -r requirements.txt

# ローカルでビルド（環境変数が必要）
SUBSURFACE_EMAIL=xxx SUBSURFACE_PASSWORD=xxx python src/build.py

# 生成結果の確認
python -m http.server 8000 --directory public
```

## 環境変数（GitHub Secrets に登録）

| 変数名 | 内容 |
|---|---|
| `SUBSURFACE_EMAIL` | Subsurface Cloud のメールアドレス |
| `SUBSURFACE_PASSWORD` | Subsurface Cloud のパスワード |
| `SAKURA_FTP_HOST` | さくらのサーバのFTPホスト |
| `SAKURA_FTP_USER` | FTPユーザー名 |
| `SAKURA_FTP_PASSWORD` | FTPパスワード |

## .ssrf フォーマット

Subsurface Cloud は git リポジトリ（XML形式の `.ssrf` ファイル）。
クローン URL: `https://cloud.subsurface-divelog.org/git/<email>`
