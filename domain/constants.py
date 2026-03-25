import matplotlib
import matplotlib.pyplot as plt

# 全局字体与绘图环境配置
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ── 清晰度 / 抗锯齿配置 ─────────────────────────────────────────────────────
plt.rcParams['text.antialiased']   = True
plt.rcParams['lines.antialiased']  = True
plt.rcParams['patch.antialiased']  = True
plt.rcParams['figure.dpi']         = 100
plt.rcParams['savefig.dpi']        = 150
plt.rcParams['font.size']          = 9        # 全局基础字号
plt.rcParams['axes.titlesize']     = 11
plt.rcParams['axes.labelsize']     = 9

# 用户可见量：额定线电压 RMS (V)
GRID_AMP  = 10500.0   # 10.5 kV — gen.amp 及所有 UI 控件使用此单位
GRID_FREQ = 50.0
XS = 1.0                         # 线路等效阻抗
TRIP_CURRENT = 300.0             # 高压系统继电保护跳闸阈值放大为 300A
MAX_POINTS = 200

# CT 电流互感器参数
CT_PRIMARY_A = 500.0             # CT 一次侧量程 (500A)
CT_SECONDARY_A = 5.0             # CT 二次侧标准输出 (5A 标准)
CT_RATIO = CT_PRIMARY_A / CT_SECONDARY_A  # 变比 (100:1)

NEUTRAL_RESISTOR_OHMS = 10.0     # 中性点接地小电阻 (10Ω，高压机组常用)

# 下垂控制系数 (因电压放大，无功下垂系数需缩小以防剧烈震荡)
KP_DROOP = 0.0005
KQ_DROOP = 0.0002

from domain.enums import SystemMode

AVAILABLE_MODES = [SystemMode.ISOLATED_BUS, SystemMode.ISLAND, SystemMode.GRID_TIED, SystemMode.BLACKSTART]
