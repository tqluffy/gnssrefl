from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import numpy as np

GAP_TIME_LIMIT = 600
MIN_ARC_POINTS = 20
SNR_COLUMN_MAP = {
    1: 7, 101: 7, 201: 7, 301: 7,
    2: 8, 20: 8, 102: 8, 302: 8,
    5: 9, 205: 9, 305: 9,
    206: 6, 306: 6,
    207: 10, 307: 10,
    208: 11, 308: 11,
}


@dataclass
class ArcConfig:
    freq: int = 1
    e1: float = 5.0
    e2: float = 25.0
    azlist: tuple[float, ...] = (0.0, 360.0)
    min_pts: int = MIN_ARC_POINTS
    poly_order: int = 4
    dbhz: bool = False
    split_arcs: bool = True
    filter_to_day: bool = True
    day_start_hour: float = 0.0


@dataclass
class ArcResult:
    sat: int
    freq: int
    arc_num: int
    arc_type: str
    arc_timestamp: float
    arc_timestamp_abs: float
    az_min_ele: float
    num_pts: int
    delT_minutes: float
    ele: np.ndarray
    azi: np.ndarray
    seconds: np.ndarray
    raw_snr: np.ndarray
    trend_snr: np.ndarray
    dsnr: np.ndarray
    poly_coeffs: np.ndarray


def _check_azimuth(az: float, azlist: Iterable[float]) -> bool:
    azv = list(azlist)
    for i in range(0, len(azv), 2):
        if azv[i] <= az <= azv[i + 1]:
            return True
    return False


def _detect_arc_boundaries(ele: np.ndarray, seconds: np.ndarray, min_pts: int) -> list[tuple[int, int, int]]:
    if len(ele) < min_pts:
        return []

    ddate = np.ediff1d(seconds)
    delv = np.ediff1d(ele)
    bkpt = np.array([len(ddate)])
    bkpt = np.append(bkpt, np.where(ddate > GAP_TIME_LIMIT)[0])
    bkpt = np.append(bkpt, np.where(np.diff(np.sign(delv)))[0])
    bkpt = np.sort(np.unique(bkpt))

    result: list[tuple[int, int, int]] = []
    arc_num = 0
    for i, b in enumerate(bkpt):
        s = 0 if i == 0 else bkpt[i - 1] + 1
        e = b + 1
        if e - s < min_pts:
            continue
        arc_num += 1
        result.append((s, e, arc_num))
    return result


def _remove_dc(ele: np.ndarray, snr: np.ndarray, poly_order: int, dbhz: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = snr.copy() if dbhz else np.power(10, snr / 20)
    poly_coeffs = np.polyfit(ele, raw, poly_order)
    trend = np.polyval(poly_coeffs, ele)
    dsnr = raw - trend
    return raw, trend, dsnr, poly_coeffs


def extract_arcs(snr_array: np.ndarray, cfg: ArcConfig) -> list[ArcResult]:
    if cfg.freq not in SNR_COLUMN_MAP:
        raise ValueError(f"Unsupported frequency code: {cfg.freq}")

    ncols = snr_array.shape[1]
    icol = SNR_COLUMN_MAP[cfg.freq] - 1
    if icol >= ncols:
        raise ValueError(f"SNR data has only {ncols} columns, but freq={cfg.freq} needs column {icol + 1}")

    sats = snr_array[:, 0].astype(int)
    ele_all = snr_array[:, 1]
    azi_all = snr_array[:, 2]
    sec_all = snr_array[:, 3]
    snr_all = snr_array[:, icol]

    in_pele = (ele_all >= cfg.e1) & (ele_all <= cfg.e2)
    sats, ele_all, azi_all, sec_all, snr_all = (
        sats[in_pele], ele_all[in_pele], azi_all[in_pele], sec_all[in_pele], snr_all[in_pele]
    )

    out: list[ArcResult] = []
    for sat in np.unique(sats):
        sat_mask = sats == sat
        if np.sum(sat_mask) < cfg.min_pts:
            continue

        ele = ele_all[sat_mask]
        azi = azi_all[sat_mask]
        sec = sec_all[sat_mask]
        snr = snr_all[sat_mask]

        boundaries = _detect_arc_boundaries(ele, sec, cfg.min_pts) if cfg.split_arcs else [(0, len(ele), 1)]

        for s, e, arc_num in boundaries:
            aele, aazi, asec, asnr = ele[s:e], azi[s:e], sec[s:e], snr[s:e]
            nz = asnr > 1
            if np.sum(nz) < cfg.min_pts:
                continue
            aele, aazi, asec, asnr = aele[nz], aazi[nz], asec[nz], asnr[nz]

            emask = (aele > cfg.e1) & (aele <= cfg.e2)
            if np.sum(emask) < 15:
                continue

            aele, aazi, asec, asnr = aele[emask], aazi[emask], asec[emask], asnr[emask]
            az_min_ele = float(aazi[np.argmin(aele)])
            if not _check_azimuth(az_min_ele, cfg.azlist):
                continue

            raw_snr, trend_snr, dsnr, poly_coeffs = _remove_dc(aele, asnr, cfg.poly_order, cfg.dbhz)
            arc_ts_abs = float(np.mean(asec) / 3600.0)
            if cfg.filter_to_day and not (cfg.day_start_hour <= arc_ts_abs < cfg.day_start_hour + 24.0):
                continue

            out.append(
                ArcResult(
                    sat=int(sat),
                    freq=cfg.freq,
                    arc_num=arc_num,
                    arc_type="rising" if aele[-1] > aele[0] else "setting",
                    arc_timestamp=arc_ts_abs - cfg.day_start_hour,
                    arc_timestamp_abs=arc_ts_abs,
                    az_min_ele=az_min_ele,
                    num_pts=len(aele),
                    delT_minutes=float((np.max(asec) - np.min(asec)) / 60.0),
                    ele=aele,
                    azi=aazi,
                    seconds=asec,
                    raw_snr=raw_snr,
                    trend_snr=trend_snr,
                    dsnr=dsnr,
                    poly_coeffs=poly_coeffs,
                )
            )

    return out
