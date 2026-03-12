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
PT_SECONDARY_V_LINE = 100.0      # PT二次侧额定线电压 (指导书要求 100VAC)

# 计算相电压幅值 (V_peak = (V_line / sqrt(3)) * sqrt(2))
PRIMARY_AMP = (PRIMARY_VOLTAGE_KV * 1000 / math.sqrt(3)) * math.sqrt(2) 
PT_RATIO = (PRIMARY_VOLTAGE_KV * 1000) / PT_SECONDARY_V_LINE 

GRID_AMP = PRIMARY_AMP           # 主电网额定幅值升级为高压 (约 8573.2V)
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

# ========== 系统运行模式枚举 ==========
class SystemMode:
    ISOLATED_BUS = "隔离母排"     # 无外部电网，母排由首台并入的机组建立电压
    ISLAND = "孤岛运行"           # (预留) 脱网后的负载-发电平衡模式
    GRID_TIED = "并网运行"        # (预留) 外接无穷大电网，经典同期并网
    BLACKSTART = "黑启动"         # (预留) 全站失电后的恢复启动流程

AVAILABLE_MODES = [SystemMode.ISOLATED_BUS, SystemMode.ISLAND, SystemMode.GRID_TIED, SystemMode.BLACKSTART]

# 断路器物理位置枚举
class BreakerPosition:
    DISCONNECTED = "脱开位置"    # 绝缘测试用
    TEST = "试验位置"            # 单机调试二次回路用
    WORKING = "工作位置"         # 并网用

# 万用表测量节点坐标已迁移至 ui.py（NODES 是 UI 拓扑图的布局数据，
# 不属于物理/电气常量，放在此处会造成 config ↔ UI 跨层耦合）。
# physics.py 通过 ctrl.ui_nodes 属性访问，config 中不再定义 NODES。

# 下垂控制系数 (因电压放大，无功下垂系数需缩小以防剧烈震荡)
KP_DROOP = 0.0005        
KQ_DROOP = 0.0002