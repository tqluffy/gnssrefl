from __future__ import annotations

import argparse
from pathlib import Path
import csv
from datetime import date

from arc_extractor import ArcConfig, extract_arcs
from pt_exporter import save_arcs_pt
from snr_reader import (
    date_from_year_doy,
    merge_daily_snr_files,
    parse_snr_filename_day,
    read_snr_file,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Extract & filter arcs from local SNR file(s)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--snr", help="Path to one .snr/.snr.gz file")
    src.add_argument("--snr-dir", help="Folder containing daily SNR files for batch processing")

    p.add_argument("--pattern", default="*.snr99.gz", help="Glob pattern used with --snr-dir")
    p.add_argument("--freq", type=int, default=1, help="Frequency used for CSV export")
    p.add_argument("--e1", type=float, default=5.0)
    p.add_argument("--e2", type=float, default=25.0)
    p.add_argument("--azlist", nargs="+", type=float, default=[0, 360], help="Pairs: start end [start end ...]")
    p.add_argument("--min-pts", type=int, default=20)
    p.add_argument("--poly-order", type=int, default=4, help="Polynomial order for dSNR detrending")
    p.add_argument("--dbhz", action="store_true", help="Keep SNR in dB-Hz for detrending")

    p.add_argument("--output", default="arcs_summary.csv", help="CSV file for single-file mode")
    p.add_argument("--output-dir", default="arcs_output", help="Output folder for --snr-dir mode")
    p.add_argument("--no-neighbor-days", action="store_true", help="Disable previous/next-day buffering in batch mode")

    p.add_argument("--export-pt", action="store_true", help="Save detrended arc sequences to .pt")
    p.add_argument("--pt-output", default="arcs_dsnr.pt", help=".pt output file for single-file mode")
    p.add_argument("--pt-output-dir", default="arcs_pt", help=".pt output folder for batch mode")
    return p


def _write_csv(path: Path, arcs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "sat", "freq", "arc_num", "arc_type", "arc_timestamp", "arc_timestamp_abs",
            "az_min_ele", "num_pts", "delT_minutes"
        ])
        for a in arcs:
            w.writerow([
                a.sat, a.freq, a.arc_num, a.arc_type,
                f"{a.arc_timestamp:.4f}", f"{a.arc_timestamp_abs:.4f}",
                f"{a.az_min_ele:.2f}", a.num_pts, f"{a.delT_minutes:.2f}"
            ])


def _cfg_from_args(args, freq: int, day_start_hour: float = 0.0) -> ArcConfig:
    return ArcConfig(
        freq=freq,
        e1=args.e1,
        e2=args.e2,
        azlist=tuple(args.azlist),
        min_pts=args.min_pts,
        poly_order=args.poly_order,
        dbhz=args.dbhz,
        day_start_hour=day_start_hour,
    )


def _extract_with_freqs(snr, args, day_start_hour: float) -> dict[int, list]:
    arcs_by_freq = {}
    for f in (1, 2):
        arcs_by_freq[f] = extract_arcs(snr, _cfg_from_args(args, f, day_start_hour))
    return arcs_by_freq


def _run_single(args) -> None:
    snr = read_snr_file(args.snr)
    arcs_csv = extract_arcs(snr, _cfg_from_args(args, args.freq, 0.0))
    _write_csv(Path(args.output), arcs_csv)
    print(f"Extracted {len(arcs_csv)} arcs (freq={args.freq}) -> {args.output}")

    if args.export_pt:
        try:
            year, doy = parse_snr_filename_day(args.snr)
            ref_date = date_from_year_doy(year, doy)
        except Exception:
            ref_date = date.today()
        arcs_by_freq = _extract_with_freqs(snr, args, 0.0)
        pt_path = save_arcs_pt(arcs_by_freq, ref_date, Path(args.pt_output))
        print(f"Saved L1/L2 detrended arc data -> {pt_path}")


def _run_batch(args) -> None:
    snr_dir = Path(args.snr_dir)
    files = sorted(snr_dir.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched {args.pattern} in {snr_dir}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pt_dir = Path(args.pt_output_dir)
    if args.export_pt:
        pt_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for i, current in enumerate(files):
        merge_list = [current]
        day_start_hour = 0.0
        if not args.no_neighbor_days:
            if i > 0:
                merge_list.insert(0, files[i - 1])
                day_start_hour = 24.0
            if i + 1 < len(files):
                merge_list.append(files[i + 1])

        snr, ref_date = merge_daily_snr_files(merge_list)
        arcs_csv = extract_arcs(snr, _cfg_from_args(args, args.freq, day_start_hour))

        year, doy = parse_snr_filename_day(current)
        out = out_dir / f"arcs_{current.stem}_{year}_{doy:03d}.csv"
        _write_csv(out, arcs_csv)
        total += len(arcs_csv)
        print(f"[{i+1}/{len(files)}] {current.name}: {len(arcs_csv)} arcs -> {out}")

        if args.export_pt:
            arcs_by_freq = _extract_with_freqs(snr, args, day_start_hour)
            pt_out = pt_dir / f"arcs_{current.stem}_{year}_{doy:03d}.pt"
            save_arcs_pt(arcs_by_freq, ref_date, pt_out)
            print(f"    saved .pt -> {pt_out}")

    print(f"Done. Processed {len(files)} files, extracted {total} arcs in total.")


def main() -> None:
    args = build_parser().parse_args()
    if len(args.azlist) % 2 != 0:
        raise ValueError("--azlist must contain pairs")

    if args.snr:
        _run_single(args)
    else:
        _run_batch(args)


if __name__ == "__main__":
    main()
