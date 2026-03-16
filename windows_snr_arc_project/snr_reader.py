from __future__ import annotations

from pathlib import Path
from datetime import date, datetime, timezone, timedelta
import gzip
import re
import numpy as np

SNR_NAME_RE = re.compile(
    r"(?P<station>[A-Za-z0-9]{4})(?P<doy>\d{3})0\.(?P<yy>\d{2})\.snr\d+(?:\.gz)?$"
)


def read_snr_file(path: str | Path) -> np.ndarray:
    """Read local .snr or .snr.gz file into a 2D array."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SNR file not found: {path}")

    opener = gzip.open if path.suffix == ".gz" else open
    rows: list[list[float]] = []

    with opener(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            parts = line.split()
            try:
                rows.append([float(x) for x in parts])
            except ValueError:
                continue

    if not rows:
        raise ValueError(f"No numeric SNR data rows found in {path}")

    return np.array(rows, dtype=float)


def parse_snr_filename_day(path: str | Path) -> tuple[int, int]:
    """Parse (year, doy) from names like mchl0120.25.snr99.gz."""
    path = Path(path)
    m = SNR_NAME_RE.match(path.name)
    if not m:
        raise ValueError(f"Unrecognized SNR filename format: {path.name}")
    yy = int(m.group("yy"))
    year = 2000 + yy if yy < 80 else 1900 + yy
    doy = int(m.group("doy"))
    return year, doy


def date_from_year_doy(year: int, doy: int) -> date:
    return date(year, 1, 1).fromordinal(date(year, 1, 1).toordinal() + doy - 1)


def merge_daily_snr_files(files: list[str | Path]) -> tuple[np.ndarray, date]:
    """Merge daily SNR files and shift seconds to a continuous timeline.

    Returns merged array and the reference date for 0 second offset.
    """
    if not files:
        raise ValueError("No SNR files provided for merge")

    parsed: list[tuple[Path, int, int]] = []
    for f in files:
        p = Path(f)
        year, doy = parse_snr_filename_day(p)
        parsed.append((p, year, doy))

    parsed.sort(key=lambda x: (x[1], x[2], x[0].name))
    ref_date = date_from_year_doy(parsed[0][1], parsed[0][2])

    arrays: list[np.ndarray] = []
    for p, year, doy in parsed:
        arr = read_snr_file(p)
        cur_date = date_from_year_doy(year, doy)
        day_delta = (cur_date - ref_date).days
        arr = arr.copy()
        arr[:, 3] = arr[:, 3] + day_delta * 86400
        arrays.append(arr)

    return np.vstack(arrays), ref_date


def seconds_to_unix(ref_date: date, seconds: float) -> int:
    """Convert seconds from ref_date 00:00:00 UTC to Unix timestamp."""
    dt = datetime(ref_date.year, ref_date.month, ref_date.day, tzinfo=timezone.utc) + timedelta(seconds=float(seconds))
    return int(dt.timestamp())
