from __future__ import annotations

from pathlib import Path
from typing import Any
import pickle
import numpy as np

from snr_reader import seconds_to_unix


def _torch_save_or_pickle(obj: Any, out_path: Path) -> None:
    try:
        import torch  # type: ignore
        torch.save(obj, out_path)
    except Exception:
        with out_path.open("wb") as f:
            pickle.dump(obj, f)


def _closest_5deg_idx(ele: np.ndarray) -> int:
    return int(np.argmin(np.abs(ele - 5.0)))


def arcs_to_serializable(arcs, ref_date):
    records = []
    for a in arcs:
        idx5 = _closest_5deg_idx(a.ele)
        ts_utc_unix = seconds_to_unix(ref_date, a.seconds[idx5])
        records.append(
            {
                "sat": int(a.sat),
                "freq": int(a.freq),
                "arc_num": int(a.arc_num),
                "arc_type": a.arc_type,
                "arc_timestamp_hour": float(a.arc_timestamp),
                "arc_timestamp_abs_hour": float(a.arc_timestamp_abs),
                "az_min_ele": float(a.az_min_ele),
                "num_pts": int(a.num_pts),
                "delT_minutes": float(a.delT_minutes),
                "closest_5deg_unix_ts": int(ts_utc_unix),
                "ele": a.ele.astype(float),
                "azi": a.azi.astype(float),
                "seconds": a.seconds.astype(float),
                "raw_snr": a.raw_snr.astype(float),
                "trend_snr": a.trend_snr.astype(float),
                "dsnr": a.dsnr.astype(float),
                "poly_coeffs": a.poly_coeffs.astype(float),
            }
        )
    return records


def save_arcs_pt(arcs_by_freq: dict[int, list], ref_date, out_path: str | Path) -> Path:
    """Save arc dSNR sequences to .pt with L1/L2 grouped records."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "meta": {
            "format": "snr_arc_dsnr_v1",
            "ref_date": ref_date.isoformat(),
            "frequencies": sorted(list(arcs_by_freq.keys())),
        },
        "L1": arcs_to_serializable(arcs_by_freq.get(1, []), ref_date),
        "L2": arcs_to_serializable(arcs_by_freq.get(2, []), ref_date),
    }

    _torch_save_or_pickle(payload, out_path)
    return out_path
