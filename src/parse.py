"""Subsurface の .ssrf（XML）をパースしてダイブリストを返す"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Sample:
    time_sec: int
    depth_m: float


@dataclass
class Dive:
    date: str
    time: str
    duration: str
    location: str
    max_depth_m: float
    samples: list[Sample] = field(default_factory=list)


def parse_dir(cache_dir: Path) -> list[Dive]:
    dives: list[Dive] = []
    for ssrf_file in sorted(cache_dir.rglob("*.ssrf")):
        dives.extend(_parse_file(ssrf_file))
    dives.sort(key=lambda d: (d.date, d.time), reverse=True)
    return dives


def _parse_file(path: Path) -> list[Dive]:
    dives = []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return dives

    for dive_el in tree.iterfind(".//dive"):
        date = dive_el.get("date", "")
        time = dive_el.get("time", "")
        duration = dive_el.get("duration", "")

        loc_el = dive_el.find("location")
        location = loc_el.text.strip() if loc_el is not None and loc_el.text else ""

        depth_el = dive_el.find(".//depth")
        max_depth_m = 0.0
        if depth_el is not None:
            raw = depth_el.get("max", "0 m").replace("m", "").strip()
            try:
                max_depth_m = float(raw)
            except ValueError:
                pass

        samples = []
        for s in dive_el.iterfind(".//divecomputer/sample"):
            raw_time = s.get("time", "0:00 min")
            raw_depth = s.get("depth", "0 m")
            try:
                mins, secs = raw_time.replace(" min", "").split(":")
                time_sec = int(mins) * 60 + int(secs)
                depth_m = float(raw_depth.replace("m", "").strip())
                samples.append(Sample(time_sec, depth_m))
            except (ValueError, AttributeError):
                continue

        dives.append(Dive(date, time, duration, location, max_depth_m, samples))
    return dives
