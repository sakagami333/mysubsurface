"""Subsurface Cloud git リポジトリ（ディレクトリ形式）をパース"""
import re
from dataclasses import dataclass, field
from pathlib import Path

# ダイブディレクトリ名: [YYYY-][MM-]DD-曜日-hh=mm=ss[~重複回避用hex]
_DIVE_DIR_RE = re.compile(
    r"^(?:(\d{4})-)?(?:(\d{2})-)?(\d{2})-[A-Za-z]{3}-(\d{2})[=:](\d{2})[=:](\d{2})(?:~[0-9a-fA-F]+)?$"
)


@dataclass
class Sample:
    time_sec: int
    depth_m: float
    temp_c: float | None = None
    pressure_bar: float | None = None
    stopdepth_m: float | None = None


@dataclass
class Dive:
    date: str
    time: str
    duration: str
    location: str
    max_depth_m: float
    samples: list[Sample] = field(default_factory=list)
    mean_depth_m: float = 0.0
    mean_temp_c: float | None = None
    deco_model: str = ""
    o2_percent: float | None = None
    dive_number: int | None = None
    sac_l_min: float | None = None
    sac_detail: str = ""
    # 残圧グラフの瞬間 SAC 色分け（Subsurface 互換）に使う値
    tank_size_l: float | None = None
    he_percent: float | None = None
    cylinder_start_bar: float | None = None
    cylinder_end_bar: float | None = None
    surface_pressure_bar: float = 1.013
    salinity_g_l: float = 1025.0


def parse_dir(cache_dir: Path) -> list[Dive]:
    divesites = _load_divesites(cache_dir)
    dives: list[Dive] = []

    for year_dir in sorted(cache_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = year_dir.name

        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            month = month_dir.name

            # トリップに入っていないダイブは月ディレクトリ直下に置かれる
            dive_dirs: list[tuple[Path, dict[str, str]]] = []
            for entry in sorted(month_dir.iterdir()):
                if not entry.is_dir():
                    continue
                if _DIVE_DIR_RE.match(entry.name):
                    dive_dirs.append((entry, {}))
                    continue
                trip_kv = _parse_kv_file(entry / "00-Trip")
                dive_dirs += [(d, trip_kv) for d in sorted(entry.iterdir()) if d.is_dir()]

            for dive_dir, trip_kv in dive_dirs:
                dive_file = next((f for f in sorted(dive_dir.iterdir()) if f.name == "Dive" or f.name.startswith("Dive-")), None)
                # ダイブコンピュータが複数台だと Divecomputer-001, -002 … になる
                dc_file = next((f for f in sorted(dive_dir.iterdir()) if f.name.startswith("Divecomputer")), None)
                if not dive_file or not dc_file:
                    continue

                date, time = _parse_dir_datetime(dive_dir.name, year, month)
                if not date:
                    continue

                dive_kv = _parse_kv_file(dive_file)
                duration = dive_kv.get("duration", "")
                dive_number = int(dive_file.name.split("-")[1]) if "-" in dive_file.name else None

                siteid = dive_kv.get("divesiteid", "")
                location = divesites.get(siteid, "") or trip_kv.get("location", "")

                max_depth, mean_depth, deco_model, samples, surface_pressure, salinity = _parse_divecomputer(dc_file)

                temps = [s.temp_c for s in samples if s.temp_c is not None]
                mean_temp = round(sum(temps) / len(temps), 1) if temps else None

                cylinder = dive_kv.get("cylinder", "")
                o2_match = re.search(r"o2=(\d+\.?\d*)%", cylinder)
                o2_percent = float(o2_match.group(1)) if o2_match else None

                size_match = re.search(r"vol=(\d+\.?\d*)l", cylinder)
                tank_size_l = float(size_match.group(1)) if size_match else None

                he_match = re.search(r"he=(\d+\.?\d*)%", cylinder)
                he_percent = float(he_match.group(1)) if he_match else None
                start_match = re.search(r"start=(\d+\.?\d*)bar", cylinder)
                cylinder_start = float(start_match.group(1)) if start_match else None
                end_match = re.search(r"end=(\d+\.?\d*)bar", cylinder)
                cylinder_end = float(end_match.group(1)) if end_match else None

                sac, sac_detail = _calc_sac(
                    samples, tank_size_l, duration, mean_depth, surface_pressure, salinity,
                    o2_percent, he_percent, cylinder_start, cylinder_end,
                )

                dives.append(Dive(
                    date, time, duration, location, max_depth, samples,
                    mean_depth, mean_temp, deco_model, o2_percent, dive_number, sac, sac_detail,
                    tank_size_l=tank_size_l,
                    he_percent=he_percent,
                    cylinder_start_bar=cylinder_start,
                    cylinder_end_bar=cylinder_end,
                    surface_pressure_bar=surface_pressure,
                    salinity_g_l=salinity,
                ))

    dives.sort(key=lambda d: (d.date, d.time), reverse=True)
    return dives


def _parse_kv_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            result[parts[0]] = parts[1].strip('"')
    return result


def _parse_dir_datetime(dir_name: str, year: str, month: str) -> tuple[str, str]:
    """'12-Sat-13=45=33' / '07-24-Fri-08=43=56' / '2025-12-31-Wed-08=43=56~1a2b3c4' から (date, time) を返す"""
    m = _DIVE_DIR_RE.match(dir_name)
    if not m:
        return "", ""
    y, mo, day, h, mi, s = m.groups()
    # 年・月は親ディレクトリと異なるときだけ名前に付く（トリップが月や年をまたぐ場合）
    return f"{y or year}-{mo or month}-{day}", f"{h}:{mi}:{s}"


def _parse_divecomputer(path: Path) -> tuple[float, float, str, list[Sample], float, float]:
    """(max_depth_m, mean_depth_m, deco_model, samples, surface_pressure_bar, salinity_g_l) を返す"""
    text = path.read_text(encoding="utf-8", errors="replace")
    max_depth_declared = 0.0
    mean_depth_declared = 0.0
    deco_model = ""
    surface_pressure = 1.013
    salinity = 1025.0
    samples = []

    for line in text.splitlines():
        if line.startswith("maxdepth "):
            try:
                max_depth_declared = float(line.split()[1].rstrip("m"))
            except (ValueError, IndexError):
                pass
        elif line.startswith("meandepth "):
            try:
                mean_depth_declared = float(line.split()[1].rstrip("m"))
            except (ValueError, IndexError):
                pass
        elif line.startswith("surfacepressure "):
            try:
                surface_pressure = float(line.split()[1].rstrip("bar"))
            except (ValueError, IndexError):
                pass
        elif line.startswith("salinity "):
            try:
                salinity = float(line.split()[1].rstrip("g/l"))
            except (ValueError, IndexError):
                pass
        elif line.startswith('keyvalue "Deco model"'):
            m = re.search(r'keyvalue "Deco model" "([^"]*)"', line)
            if m:
                deco_model = m.group(1)
        elif line.startswith(" "):
            stripped = line.strip()
            if stripped.startswith(("event", "keyvalue")):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            try:
                mins, secs = parts[0].split(":")
                time_sec = int(mins) * 60 + int(secs)
                depth_m = float(parts[1].rstrip("m"))
            except (ValueError, AttributeError):
                continue

            temp_c = None
            pressure_bar = None
            stopdepth_m = None
            for token in parts[2:]:
                if token.endswith("°C"):
                    try:
                        temp_c = float(token[:-2])
                    except ValueError:
                        pass
                elif "bar:" in token:
                    try:
                        pressure_bar = float(token.split("bar:")[0])
                    except ValueError:
                        pass
                elif token.startswith("stopdepth="):
                    try:
                        stopdepth_m = float(token[10:].rstrip("m"))
                    except ValueError:
                        pass

            samples.append(Sample(time_sec, depth_m, temp_c, pressure_bar, stopdepth_m))

    max_depth = max_depth_declared or max((s.depth_m for s in samples), default=0.0)
    return max_depth, mean_depth_declared, deco_model, samples, surface_pressure, salinity


def _gas_compressibility(bar: float, o2_percent: float | None, he_percent: float | None) -> float:
    """ガスの圧縮係数 Z（Subsurface core/gas-model.cpp と同じ式）"""
    def virial_m1(c: tuple[float, float, float], x: float) -> float:
        return x * c[0] + x * x * c[1] + x * x * x * c[2]

    bar = min(max(bar, 0.0), 500.0)
    o2 = round(o2_percent * 10) if o2_percent else 209
    he = round(he_percent * 10) if he_percent else 0
    z = (virial_m1((-7.18092073703e-04, 2.81852572808e-06, -1.50290620492e-09), bar) * o2
         + virial_m1((4.87320026468e-04, -8.83632921053e-08, 5.33304543646e-11), bar) * he
         + virial_m1((-2.19260353292e-04, 2.92844845532e-06, -2.07613482075e-09), bar) * (1000 - o2 - he))
    return z * 0.001 + 1.0


def _calc_sac(
    samples: list[Sample],
    tank_size_l: float | None,
    duration_str: str,
    mean_depth_m: float,
    surface_pressure_bar: float = 1.013,
    salinity_g_l: float = 1025.0,
    o2_percent: float | None = None,
    he_percent: float | None = None,
    cylinder_start_bar: float | None = None,
    cylinder_end_bar: float | None = None,
) -> tuple[float | None, str]:
    """SAC (L/min) を Subsurface（core/divelist.cpp の calculate_sac()）と同じ式で求める
    SAC = 消費ガス量(水面換算L、圧縮係数で補正) / 平均水深の絶対圧(atm) / 潜水時間(min)
    開始・終了圧はシリンダーの記録、なければ最初と最後の残圧サンプル
    Returns (sac_l_min, detail_str)"""
    if tank_size_l is None or tank_size_l <= 0:
        return None, ""
    pressures = [s.pressure_bar for s in samples if s.pressure_bar is not None]
    start_bar = cylinder_start_bar or (pressures[0] if pressures else None)
    end_bar = cylinder_end_bar or (pressures[-1] if pressures else None)
    if not start_bar or not end_bar or start_bar <= end_bar:
        return None, ""
    try:
        parts = duration_str.split()[0].split(":")
        duration_sec = int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None, ""
    if duration_sec <= 0 or mean_depth_m <= 0:
        return None, ""

    def gas_volume_ml(bar: float) -> int:
        return int(tank_size_l * 1000 * (bar / 1.01325) / _gas_compressibility(bar, o2_percent, he_percent))

    airuse_l = (gas_volume_ml(start_bar) - gas_volume_ml(end_bar)) / 1000
    mean_mbar = round(surface_pressure_bar * 1000 + mean_depth_m * 1000 * salinity_g_l * 10 * 0.981 / 100000)
    sac = round(airuse_l / (mean_mbar / 1013.25) * 60 / duration_sec, 1)
    detail = f"{start_bar:.0f}→{end_bar:.0f} bar"
    return sac, detail


def _load_divesites(cache_dir: Path) -> dict[str, str]:
    sites: dict[str, str] = {}
    sites_dir = cache_dir / "01-Divesites"
    if not sites_dir.exists():
        return sites
    for f in sites_dir.iterdir():
        if f.name.startswith("Site-"):
            kv = _parse_kv_file(f)
            sites[f.name[5:]] = kv.get("name", "")
    return sites
