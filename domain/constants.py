# 用户可见量：额定线电压 RMS (V)
GRID_AMP  = 10500.0   # 10.5 kV — gen.amp 及所有 UI 控件使用此单位
GRID_FREQ = 50.0
SYNC_FREQ_OK_HZ = 0.5
SYNC_VOLT_OK_V = 490.0
SYNC_PHASE_OK_DEG = 15.0
XS = 1.0                         # 线路等效阻抗
TRIP_CURRENT = 300.0             # 高压系统继电保护跳闸阈值放大为 300A
MAX_POINTS = 200

# CT 电流互感器参数
CT_PRIMARY_A = 500.0             # CT 一次侧量程 (500A)
CT_SECONDARY_A = 5.0             # CT 二次侧标准输出 (5A 标准)
CT_RATIO = CT_PRIMARY_A / CT_SECONDARY_A  # 变比 (100:1)

NEUTRAL_RESISTOR_OHMS = 10.0     # 中性点接地小电阻 (10Ω，高压机组常用)

# 主循环定时器
TICK_MS = 33                       # QTimer 间隔 (ms)
TICK_DT = TICK_MS / 1000.0         # 每帧时间步长 (s)，供物理引擎使用

# 下垂控制系数 (因电压放大，无功下垂系数需缩小以防剧烈震荡)
KP_DROOP = 0.0005
KQ_DROOP = 0.0002
