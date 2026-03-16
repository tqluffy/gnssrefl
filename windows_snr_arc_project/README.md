# Windows SNR Arc Project（免安装版）

这是一个普通 Python 项目（不是 Python 包），可直接运行：
- 本地 SNR 文件 -> 弧段提取 -> 弧段筛选
- 支持单文件和文件夹批处理
- 支持跨天弧段（邻日拼接）
- 支持多项式去趋势，并将弧段 dSNR 数据导出为 `.pt`
- 提供 wxPython 可视化界面用于筛选统计和绘图

## 目录结构
- `main.py`：命令行入口（直接执行）
- `snr_reader.py`：读 `.snr/.snr.gz`、解析文件名日期、跨天拼接、UTC 时间转换
- `arc_extractor.py`：弧段切分与筛选、多项式去趋势
- `pt_exporter.py`：将 L1/L2 弧段 dSNR 保存为 `.pt`
- `gui_wx.py`：wxPython 可视化窗口
- `requirements.txt`：依赖

## 环境要求
- Windows 10/11
- Python 3.9+
- GUI 额外依赖：`wxPython`（建议手工安装）

## 使用方式（免安装）
```powershell
cd windows_snr_arc_project
python -m pip install -r requirements.txt
```

## 1) 单文件处理（CSV）
```powershell
python main.py --snr D:\data\mchl0120.25.snr66.gz --freq 1 --e1 5 --e2 25 --azlist 0 90 180 270 --poly-order 4 --output D:\data\arcs_summary.csv
```

## 2) 导出弧段 dSNR 到 `.pt`（自动保留 L1/L2）
```powershell
python main.py --snr D:\data\mchl0120.25.snr66.gz --export-pt --pt-output D:\data\arcs_dsnr.pt
```

`.pt` 内包含：
- `L1` / `L2` 两组弧段记录
- 每条弧段的 `dsnr` 序列、`raw_snr`、`trend_snr`、多项式系数
- 最接近 5° 仰角点的 UTC Unix 时间戳 `closest_5deg_unix_ts`

## 3) 文件夹批处理（默认支持跨天弧段）
```powershell
python main.py --snr-dir D:\data\snr --pattern "*.snr99.gz" --freq 1 --output-dir D:\data\arc_csv --export-pt --pt-output-dir D:\data\arc_pt
```

## 4) 可视化窗口（wxPython）
先安装 wxPython（Windows）：
```powershell
python -m pip install wxPython
```
运行：
```powershell
python gui_wx.py
```
功能：
- 加载 `.pt` 文件
- 选择 L1/L2
- 按弧段类型（all/rising/setting）与卫星号筛选
- 统计弧段数量
- 绘制方位角分布直方图与时间分布直方图

## 参数说明（main.py）
- `--snr`: 单个 SNR 文件（`.snr` / `.gz`）
- `--snr-dir`: SNR 文件目录（批处理）
- `--pattern`: 批处理匹配模式，默认 `*.snr99.gz`
- `--freq`: CSV 输出使用的频点代码（如 `1/2/5/20/101/201`）
- `--e1 --e2`: 仰角筛选区间
- `--azlist`: 方位角区间（成对输入）
- `--min-pts`: 最小点数阈值
- `--poly-order`: 多项式去趋势阶数
- `--dbhz`: 以 dB-Hz 单位去趋势
- `--output`: 单文件模式输出 CSV
- `--output-dir`: 批处理模式输出目录
- `--export-pt`: 输出 `.pt`
- `--pt-output`: 单文件模式 `.pt` 输出路径
- `--pt-output-dir`: 批处理模式 `.pt` 输出目录
- `--no-neighbor-days`: 关闭跨天邻日拼接

## 文件命名约定
跨天拼接与 UTC 时间转换需要从文件名解析日期，支持如：
- `mchl0120.25.snr99.gz`
- `abcd3650.24.snr66`
