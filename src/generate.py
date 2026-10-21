"""パース済みダイブデータから静的 HTML を生成する"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
PUBLIC_DIR = Path("public")


def _calc_time_range(date: str, time: str, duration: str) -> str:
    """'2026-08-23', '14:43:17', '33:10' → '2026/08/23 14:43 ～ 15:16 (33:10)'"""
    try:
        start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        mins, secs = map(int, duration.split()[ 0].split(":"))
        end = start + timedelta(minutes=mins, seconds=secs)
        return f"{start.strftime('%Y/%m/%d %H:%M')} ～ {end.strftime('%H:%M')}"
    except (ValueError, AttributeError, IndexError):
        return f"{date} {time[:5]}"


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
        time_range = _calc_time_range(dive.date, dive.time, dive.duration)
        html = detail_tmpl.render(dive=dive, samples_json=samples_json, dive_id=i, time_range=time_range)
        filename = f"dive-{dive.dive_number}.html" if dive.dive_number else f"dive-{i}.html"
        (PUBLIC_DIR / filename).write_text(html, encoding="utf-8")
