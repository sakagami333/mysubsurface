"""パース済みダイブデータから静的 HTML を生成する"""
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
PUBLIC_DIR = Path("public")


def generate(dives: list) -> None:
    PUBLIC_DIR.mkdir(exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    # トップページ（ダイブ一覧）
    tmpl = env.get_template("index.html")
    (PUBLIC_DIR / "index.html").write_text(
        tmpl.render(dives=dives, total=len(dives)), encoding="utf-8"
    )

    # 個別ダイブページ
    detail_tmpl = env.get_template("dive.html")
    for i, dive in enumerate(dives):
        def _s(s):
            d: dict = {"t": s.time_sec, "d": s.depth_m}
            if s.temp_c is not None:
                d["c"] = s.temp_c
            if s.pressure_bar is not None:
                d["p"] = s.pressure_bar
            if s.stopdepth_m is not None:
                d["s"] = s.stopdepth_m
            return d
        samples_json = json.dumps([_s(s) for s in dive.samples])
        html = detail_tmpl.render(dive=dive, samples_json=samples_json, dive_id=i)
        (PUBLIC_DIR / f"dive-{i}.html").write_text(html, encoding="utf-8")
