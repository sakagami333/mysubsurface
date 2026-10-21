"""エントリーポイント: fetch → parse → generate を順に実行する"""
import os
import sys

from fetch import fetch
from parse import parse_dir
from generate import generate


def main() -> None:
    email = os.environ.get("SUBSURFACE_EMAIL")
    password = os.environ.get("SUBSURFACE_PASSWORD")

    if not email or not password:
        print("エラー: SUBSURFACE_EMAIL と SUBSURFACE_PASSWORD を設定してください")
        sys.exit(1)

    print("Subsurface Cloud からデータ取得中...")
    cache_dir = fetch(email, password)

    print(".ssrf ファイルをパース中...")
    dives = parse_dir(cache_dir)
    print(f"  {len(dives)} 件のダイブを検出")

    print("HTML を生成中...")
    generate(dives)
    print("完了: public/ に出力しました")


if __name__ == "__main__":
    main()
