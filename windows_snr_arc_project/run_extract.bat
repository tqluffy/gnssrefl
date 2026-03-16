@echo off
REM Windows quick start script (no installation needed)
python -m pip install -r requirements.txt

REM Single file CSV export
python main.py --snr sample.snr99.gz --freq 1 --e1 5 --e2 25 --azlist 0 360 --poly-order 4 --output arcs_summary.csv

REM Export L1/L2 detrended dSNR arcs into .pt
python main.py --snr sample.snr99.gz --export-pt --pt-output arcs_dsnr.pt

REM Batch folder with cross-day support + .pt export
REM python main.py --snr-dir D:\data\snr --pattern "*.snr99.gz" --freq 1 --output-dir D:\data\arc_csv --export-pt --pt-output-dir D:\data\arc_pt

REM Launch wxPython GUI (requires wxpython installed manually)
REM python gui_wx.py
pause
