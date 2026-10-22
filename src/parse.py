"""Subsurface Cloud git リポジトリ（ディレクトリ形式）をパース"""
import re
from dataclasses import dataclass, field
from pathlib import Path


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

            for trip_dir in sorted(month_dir.iterdir()):
                if not trip_dir.is_dir():
                    continue
                trip_kv = _parse_kv_file(trip_dir / "00-Trip")

                for dive_dir in sorted(trip_dir.iterdir()):
                    if not dive_dir.is_dir():
                        continue
                    dive_file = next(dive_dir.glob("Dive-*"), None)
                    dc_file = dive_dir / "Divecomputer"
                    if not dive_file or not dc_file.exists():
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
                    sac, sac_detail = _calc_sac(samples, tank_size_l, duration, mean_depth, surface_pressure, salinity)

                    dives.append(Dive(
                        date, time, duration, location, max_depth, samples,
                        mean_depth, mean_temp, deco_model, o2_percent, dive_number, sac, sac_detail,
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
    """'12-Sat-13=45=33' または '07-24-Fri-08=43=56' から (date, time) を返す"""
    m = re.match(r"^(\d+)-(?:(\d+)-)?[A-Za-z]+-(\d{2})=(\d{2})=(\d{2})$", dir_name)
    if not m:
        return "", ""
    first, second, h, mi, s = m.groups()
    if second:
        # MM-DD-DayName 形式: first=月, second=日
        actual_month, day = first.zfill(2), second
    else:
        # DD-DayName 形式: first=日, 月は親ディレクトリのmonthを使用
        actual_month, day = month, first
    return f"{year}-{actual_month}-{day.zfill(2)}", f"{h}:{mi}:{s}"


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


def _calc_sac(
    samples: list[Sample],
    tank_size_l: float | None,
    duration_str: str,
    mean_depth_m: float,
    surface_pressure_bar: float = 1.013,
    salinity_g_l: float = 1025.0,
) -> tuple[float | None, str]:
    """SAC (L/min) = 消費気体量(L) / 潜水時間(min) / 平均絶対圧力(bar)
    平均絶対圧力 = surface_pressure + meandepth × (salinity/10000)
    Returns (sac_l_min, detail_str)"""
    if tank_size_l is None or tank_size_l <= 0:
        return None, ""
    pressures = [s.pressure_bar for s in samples if s.pressure_bar is not None]
    if len(pressures) < 2:
        return None, ""
    start_bar = pressures[0]
    end_bar = pressures[-1]
    consumed_bar = start_bar - end_bar
    if consumed_bar <= 0:
        return None, ""
    try:
        parts = duration_str.split()[0].split(":")
        duration_min = int(parts[0]) + int(parts[1]) / 60
    except (ValueError, IndexError):
        return None, ""
    if duration_min <= 0:
        return None, ""
    mean_abs_bar = surface_pressure_bar + mean_depth_m * (salinity_g_l / 10000)
    sac = round((consumed_bar * tank_size_l) / duration_min / mean_abs_bar, 1)
    detail = (
        f"{start_bar:.0f}→{end_bar:.0f} bar ({consumed_bar:.0f}bar×{tank_size_l:.0f}L) "
        f"÷ {duration_min:.1f}min ÷ {mean_abs_bar:.2f}bar"
        f"（水深{mean_depth_m:.1f}m, 塩分{salinity_g_l:.0f}g/L, 水面圧{surface_pressure_bar:.3f}bar）"
    )
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
