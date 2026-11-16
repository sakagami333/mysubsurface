"""Subsurface Cloud から .ssrf ファイルを git clone で取得する"""
import os
import subprocess
import urllib.parse
from pathlib import Path

CACHE_DIR = Path(".ssrf-cache")

def fetch(email: str, password: str) -> Path:
    """クラウドリポジトリを clone または pull してキャッシュディレクトリを返す"""
    encoded_email = urllib.parse.quote(email, safe="")
    encoded_password = urllib.parse.quote(password, safe="")
    url = f"https://{encoded_email}:{encoded_password}@cloud.subsurface-divelog.org/git/{email}"

    if CACHE_DIR.exists():
        subprocess.run(["git", "pull"], cwd=CACHE_DIR, check=True, capture_output=True)
    else:
        # Subsurface はメールアドレス名のブランチに保存するので、あればそれを取得する
        heads = subprocess.run(
            ["git", "ls-remote", "--heads", url], check=True, capture_output=True, text=True
        ).stdout.split()
        branch_args = ["-b", email] if f"refs/heads/{email}" in heads else []
        subprocess.run(["git", "clone", *branch_args, url, str(CACHE_DIR)], check=True, capture_output=True)

    log = subprocess.run(
        ["git", "log", "-1", "--format=%D / %ci"], cwd=CACHE_DIR, check=True, capture_output=True, text=True
    ).stdout.strip()
    print(f"  最新コミット: {log}")

    return CACHE_DIR
