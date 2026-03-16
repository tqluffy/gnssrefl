from __future__ import annotations

import pickle
from pathlib import Path

import wx
import numpy as np

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure


def load_pt(path: Path):
    try:
        import torch  # type: ignore
        return torch.load(path, map_location="cpu")
    except Exception:
        with path.open("rb") as f:
            return pickle.load(f)


class ArcViewerFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="SNR Arc 可视化统计", size=(1100, 750))
        panel = wx.Panel(self)

        self.data = None
        self.records = []

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        ctrl = wx.BoxSizer(wx.HORIZONTAL)

        self.file_picker = wx.FilePickerCtrl(panel, message="选择 .pt 文件", wildcard="PT files (*.pt)|*.pt")
        self.freq_choice = wx.Choice(panel, choices=["L1", "L2"])
        self.freq_choice.SetSelection(0)
        self.arc_type_choice = wx.Choice(panel, choices=["all", "rising", "setting"])
        self.arc_type_choice.SetSelection(0)
        self.sat_text = wx.TextCtrl(panel, value="", style=wx.TE_PROCESS_ENTER)

        load_btn = wx.Button(panel, label="加载")
        draw_btn = wx.Button(panel, label="更新图像")

        ctrl.Add(wx.StaticText(panel, label="文件:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ctrl.Add(self.file_picker, 1, wx.RIGHT, 10)
        ctrl.Add(wx.StaticText(panel, label="频率:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ctrl.Add(self.freq_choice, 0, wx.RIGHT, 10)
        ctrl.Add(wx.StaticText(panel, label="弧段类型:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ctrl.Add(self.arc_type_choice, 0, wx.RIGHT, 10)
        ctrl.Add(wx.StaticText(panel, label="卫星号(可空):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        ctrl.Add(self.sat_text, 0, wx.RIGHT, 10)
        ctrl.Add(load_btn, 0, wx.RIGHT, 5)
        ctrl.Add(draw_btn, 0)

        self.stats = wx.StaticText(panel, label="未加载数据")

        self.fig = Figure(figsize=(10, 6))
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        self.canvas = FigureCanvas(panel, -1, self.fig)

        top_sizer.Add(ctrl, 0, wx.EXPAND | wx.ALL, 8)
        top_sizer.Add(self.stats, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        top_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(top_sizer)

        load_btn.Bind(wx.EVT_BUTTON, self.on_load)
        draw_btn.Bind(wx.EVT_BUTTON, self.on_draw)

    def on_load(self, _evt):
        p = Path(self.file_picker.GetPath())
        if not p.exists():
            wx.MessageBox("请选择有效的 .pt 文件", "错误", wx.OK | wx.ICON_ERROR)
            return
        self.data = load_pt(p)
        self.on_draw(None)

    def _filtered_records(self):
        if self.data is None:
            return []
        freq_key = self.freq_choice.GetStringSelection()
        records = list(self.data.get(freq_key, []))

        t = self.arc_type_choice.GetStringSelection()
        if t != "all":
            records = [r for r in records if r.get("arc_type") == t]

        sat_s = self.sat_text.GetValue().strip()
        if sat_s:
            try:
                sat_i = int(sat_s)
                records = [r for r in records if int(r.get("sat", -1)) == sat_i]
            except ValueError:
                pass
        return records

    def on_draw(self, _evt):
        records = self._filtered_records()
        self.ax1.clear()
        self.ax2.clear()

        if not records:
            self.stats.SetLabel("当前筛选条件下无数据")
            self.canvas.draw()
            return

        az = np.array([float(r["az_min_ele"]) for r in records])
        ts = np.array([float(r["arc_timestamp_hour"]) for r in records])

        self.ax1.hist(az, bins=36, color="steelblue", alpha=0.85)
        self.ax1.set_title("弧段方位角分布")
        self.ax1.set_xlabel("az_min_ele (deg)")
        self.ax1.set_ylabel("count")

        self.ax2.hist(ts, bins=24, color="tomato", alpha=0.85)
        self.ax2.set_title("弧段时间分布")
        self.ax2.set_xlabel("UTC hour")
        self.ax2.set_ylabel("count")

        self.stats.SetLabel(f"记录数: {len(records)}")
        self.fig.tight_layout()
        self.canvas.draw()


def main():
    app = wx.App(False)
    frame = ArcViewerFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
