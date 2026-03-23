import math

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

# 高压物理系统常量
PRIMARY_VOLTAGE_KV = 10.5        # 一次侧额定线电压 (10.5 kV)

# PT 变比（两侧不同）
PT_GEN_RATIO  = 11000.0 / 193.0  # 机组侧 PT 变比 (PT1/PT3): 11000V:193V ≈ 56.99
PT_BUS_RATIO  = 100.0            # 母排侧 PT 变比 (PT2): 100:1 → 10000V:100V

# 用户可见量：额定线电压 RMS (V)
GRID_AMP = PRIMARY_VOLTAGE_KV * 1000   # 10500V — gen.amp 及所有 UI 控件使用此单位

# 物理波形内部转换系数：线电压 RMS → 峰值相电压
# V_peak_phase = V_line_rms * sqrt(2/3)
PRIMARY_AMP = GRID_AMP * math.sqrt(2.0 / 3.0)   # ≈ 8573.2V，仅供波形生成内部使用
GRID_FREQ = 50.0
XS = 1.0                         # 线路等效阻抗
TRIP_CURRENT = 300.0             # 高压系统继电保护跳闸阈值放大为 300A
MAX_POINTS = 200

# CT 电流互感器参数
CT_PRIMARY_A = 500.0             # CT 一次侧量程 (500A)
CT_SECONDARY_A = 5.0             # CT 二次侧标准输出 (5A 标准)
CT_RATIO = CT_PRIMARY_A / CT_SECONDARY_A  # 变比 (100:1)

# 三相四线与馈线负载模型
NEUTRAL_RESISTOR_OHMS = 10.0     # 中性点接地小电阻 (10Ω，高压机组常用)
LOAD_RESISTANCE = 50.0           # 模拟馈线负载的等效阻抗 (Ω)

# 下垂控制系数 (因电压放大，无功下垂系数需缩小以防剧烈震荡)
KP_DROOP = 0.0005
KQ_DROOP = 0.0002

from domain.enums import SystemMode

AVAILABLE_MODES = [SystemMode.ISOLATED_BUS, SystemMode.ISLAND, SystemMode.GRID_TIED, SystemMode.BLACKSTART]
