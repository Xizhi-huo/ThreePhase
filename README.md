# ThreePhase — 三相电并网仿真教学系统

> 基于 PyQt5 的高压机组并网操作培训桌面应用，模拟隔离母排模式下的完整五步并网流程，包含六个可注入的错误场景供教学使用。

---

## 快速开始

**依赖**

```
Python 3.9+
PyQt5
matplotlib
numpy
```

**运行**

```bash
pip install PyQt5 matplotlib numpy
python app/main.py
```

---

## 项目结构

```
ThreePhase/
├── app/
│   └── main.py                      # 应用入口 & PowerSyncController（总控制器）
├── domain/                          # 领域模型与常量
│   ├── constants.py                 # 物理参数（电压、频率、阻抗等）
│   ├── enums.py                     # 系统模式、断路器状态枚举
│   ├── models.py                    # GeneratorState、SimulationState 数据类
│   ├── test_states.py               # 各步骤状态类
│   ├── fault_scenarios.py           # 六个错误场景定义
│   └── node_map.py                  # 测量节点坐标
├── services/                        # 业务逻辑与物理引擎
│   ├── physics_engine.py            # 物理引擎主类（Mixin 组合）
│   ├── _physics_core.py             # 波形生成 Mixin
│   ├── _physics_arbitration.py      # 母线仲裁与自动同步 Mixin
│   ├── _physics_protection.py       # 继电保护与断路器逻辑 Mixin
│   ├── _physics_measurement.py      # PT / 万用表测量 Mixin
│   ├── loop_test_service.py         # 第 1 步：回路导通测试
│   ├── pt_voltage_check_service.py  # 第 2 步：PT 电压检查
│   ├── pt_phase_check_service.py    # 第 3 步：PT 相序检查
│   ├── pt_exam_service.py           # 第 4 步：PT 压差考核
│   └── sync_test_service.py         # 第 5 步：同期功能测试
├── ui/                              # PyQt5 用户界面（Mixin 拼装）
│   ├── main_window.py               # PowerSyncUI 主窗口
│   ├── styles.py                    # 全局 QSS 样式
│   ├── test_panel.py                # 测试模式控制面板（第 1～5 步控制台）
│   ├── panels/
│   │   └── control_panel.py        # 右侧控制面板 Mixin
│   ├── tabs/
│   │   ├── waveform_tab.py         # Tab 0：波形 & 相量图
│   │   ├── circuit_tab.py          # Tab 1：母线拓扑（~970 行）
│   │   ├── loop_test_tab.py        # Tab 2：回路测试 UI
│   │   ├── pt_voltage_check_tab.py # Tab 3：PT 电压检查 UI
│   │   ├── pt_phase_check_tab.py   # Tab 4：PT 相序 UI
│   │   ├── pt_exam_tab.py          # Tab 5：PT 压差 UI
│   │   └── sync_test_tab.py        # Tab 6：同期测试 UI
│   └── widgets/
│       ├── multimeter_widget.py    # 数字万用表（QPainter 绘制）
│       └── phase_seq_meter.py      # 相序计 UI
├── adapters/
│   └── render_state.py             # RenderState 数据类（UI 渲染快照）
├── README.md
└── context.md                      # Claude 对话上下文摘要
```

---

## 架构概览

```
PowerSyncUI  (View — 多 Mixin)
      ↑  render_visuals(RenderState)
      ↓  用户操作事件
PowerSyncController  (app/main.py)
  ├─ SimulationState  — 唯一数据源
  ├─ PhysicsEngine    — 33ms 定时器驱动
  └─ 5 个测试服务实例
      ↑  build_render_state()
      ↓  update_physics()
PhysicsEngine  (4 个 Mixin 组合)
  ├─ WaveformMixin      — 三相正弦波形生成
  ├─ ArbitrationMixin   — 母线仲裁 & 自动同步（类 PLL）
  ├─ ProtectionMixin    — 继电保护 & 断路器联锁
  └─ MeasurementMixin   — PT 二次侧电压 & 万用表读数
```

---

## 核心数据模型

### `GeneratorState`　(`domain/models.py`)

| 字段 | 含义 |
|------|------|
| `freq` | 发电机频率（Hz） |
| `amp` | 输出线电压（V，RMS） |
| `phase_deg` | 相位（°） |
| `mode` | `"stop"` / `"manual"` / `"auto"` |
| `breaker_closed` | 主断路器状态 |
| `running` | 是否启机 |

### `SimulationState`　(`domain/models.py`)

| 字段 | 含义 |
|------|------|
| `gen1`, `gen2` | 两台发电机状态 |
| `system_mode` | 当前系统模式（目前仅启用 `ISOLATED_BUS`） |
| `fault_config` | 当前激活的故障场景配置 |
| `fault_reverse_bc` | Gen2 B/C 相物理对调标志（E02 专用） |
| `pt_gen_ratio` | PT1（Gen1侧）变比，默认 11000/193 ≈ 56.99 |
| `pt3_ratio` | PT3（Gen2侧）变比，默认 11000/193 ≈ 56.99；E04注入时改为 11000/93 ≈ 118.28 |
| `pt_bus_ratio` | PT2（母排侧）变比，默认 10500/105 = 100，二次侧额定 105V |
| `grounding_mode` | `"小电阻接地"` / `"断开"` |
| `probe1_node`, `probe2_node` | 万用表表笔位置 |
| `loop_test_mode` | 第 1 步回路测试专用模式（允许不起机合闸） |

---

## 五步测试工作流

| 步骤 | 服务类 | 电气状态 | 核心验证 |
|------|--------|----------|----------|
| 1. 回路导通测试 | `LoopTestService` | 双机工作位 / 合闸 / 未启机 | A/B/C 三相回路导通；检出相序接线错误 |
| 2. PT 电压检查 | `PtVoltageCheckService` | Gen1 并网，Gen2 运行断路器分闸 | PT1/PT2/PT3 三相线电压，±15% 容差（额定 10.5 kV） |
| 3. PT 相序检查 | `PtPhaseCheckService` | 同步骤 2 | PT1/PT3 相序表指示；检出 B/C 互换故障 |
| 4. PT 压差考核 | `PtExamService` | Gen1/Gen2 交替上母线 | 9 对 PT 端子间向量压差；验证同期就绪 |
| 5. 同期功能测试 | `SyncTestService` | Gen2 自动模式追踪 Gen1 | Δf < 0.5 Hz，ΔV < 500 V，Δθ < 15° 收敛后合闸 |

### 第二步特殊行为

- Gen1 以 ±0.02 Hz / ±5 V 随机游走模拟真实抖动（仅 Auto 模式）
- Gen2 以秒级步长慢速追赶 Gen1（仅 Auto 模式）
- 手动模式下两台机组均不受自动追踪影响，学员可自由调参
- 测试面板滑块加有 `isSliderDown()` 保护，拖动时不被每帧渲染覆盖

---

## 六个错误场景

| 编号 | 故障内容 | 检出步骤 | 第五步行为 | 风险等级 |
|------|----------|----------|------------|----------|
| E01 | Gen1 A/B 相接线互换 | 步骤 1（回路断路）/ 步骤 3（相序逆序）/ 步骤 4（压差矩阵异常） | Gen2 合闸触发**致命事故弹窗** | recoverable |
| E02 | Gen2 B/C 相接线互换 | 步骤 1（回路断路）/ 步骤 3（相序逆序）/ 步骤 4（压差矩阵异常） | Gen2 合闸触发**致命事故弹窗** | recoverable |
| E03 | PT3 A 相极性反接 | 步骤 2（PT3\_AB/CA ≈ 106 V 标红）/ 步骤 3（PT3\_A 相位不匹配）/ 步骤 4（A 行压差矩阵异常） | Gen2 自动同期收敛至 180° 错误相位；强行手动合闸触发**致命事故弹窗** | accident |
| E04 | PT3 实际变比 11000:93（≈118.28），额定应为 11000:193（≈56.99） | 步骤 2（PT3 二次侧 ≈ 88 V，远低于额定 184 V，标红）/ 步骤 4（PT3 各行压差均偏小） | 无 | recoverable |
| E05 | Gen2 过电压 13 kV（AVR 故障） | 步骤 2（PT3 电压超容差）/ 步骤 4（PT3 同相压差偏大）/ 步骤 5（幅值同步失败） | 无 | recoverable |
| E06 | Gen2 相角追踪禁用（强制非同期合闸） | 步骤 5（Δθ 不收敛） | 持续警告，强行合闸触发事故 | accident |

### E04 场景说明

PT3 的**硬件实际变比**为 118.28（11000:93），**额定铭牌**应为 56.99（11000:193）。系统注入 E04 时：

- 控制台同步显示真实变比 11000:93（`sim.pt3_ratio = 118.28`）
- PT3 二次侧物理测量 ≈ 10500 / 118.28 ≈ **88.8 V**
- 阈值比较使用**额定变比 56.99**：下限 = 8925 / 56.99 ≈ 156.6 V → 88.8 V 远低于下限 → **红色[异常]**
- 记录表格中换算一次侧也用额定变比：88.8 × 56.99 ≈ 5060 V，不在 [8925, 12075] V 范围内 → 表格标红
- 反馈文本显示"偏离额定 184 V"（动态计算，非硬编码）

### E01 / E02 事故触发机制

E01 / E02 属于**接线相序错误**，步骤 1/3/4 可被检出，**不在进入步骤 5 时弹修复对话框**，而是等到 Gen2 断路器实际合闸瞬间触发，设有两层拦截：

**第一层 — UI 层** (`app/main.py` `toggle_breaker()`)

```python
# 仅当 is_sync_test_active()（步骤 5 同期测试进行中）拦截手动合闸
if fc.scenario_id == 'E01':
    show_e01_accident_dialog(); return   # cmd_close 不被设置
elif fc.scenario_id == 'E02':
    show_e02_accident_dialog(); return
```

**第二层 — 物理层** (`_physics_protection.py` `_update_breaker_state()`)

```python
# 兜底：覆盖 auto 自动同期合闸 + 步骤 5 同期未启动时的手动合闸
if fc.scenario_id == 'E01':   show_e01_accident_dialog()
elif fc.scenario_id == 'E02': show_e02_accident_dialog()
# breaker_closed 保持 False，合闸被完全阻断
```

学员选择"修复故障" → `repair_fault()` → 可继续第五步流程。

> **工程原理**：E02 中 Gen2 B/C 端子对调，自动同步以 A 相参考角收敛（Δf/ΔV/Δθ 均满足），同期仪误判条件满足，但合闸瞬间 B/C 两相跨接母线造成 120° 相位差的直接短路。物理引擎采用单相等效电路，无法计算跨相短路电流，故在保护层硬编码拦截。

### 故障注入通用流程

1. 教师在右侧控制面板选择故障场景
2. `FaultConfig` 注入 `SimulationState`（E02 同时置 `fault_reverse_bc=True`）
3. `PhysicsEngine` 读取故障参数扭曲测量值
4. UI 轮询 `fault_config.detected` 标志，触发警告横幅
5. 学员"修复"确认 → `repaired = True`，允许继续测试
6. E01/E02/E03 例外：修复时机在第五步合闸事故弹窗内，而非步骤 4→5 过渡时

---

## 物理引擎关键算法

### 每帧更新顺序（33 ms / 帧）

```
_update_bus_reference()      → 确定母线参考源（Gen1 or Gen2）
_update_arbitration()        → 自动同步调节（PLL 式）
_advance_time()              → 推进仿真时间
_update_actual_amplitudes()  → 电压斜坡上升（调速器模型）
_compute_wave_state()        → 角频率、相位计算
_update_protection_state()   → 计算线路电流，过流检测（300 A 跳闸）
_apply_droop_control()       → 频率下垂调节
_update_wave_history()       → 更新 200 点波形缓冲
_update_breaker_logic()      → 联锁执行、保护跳闸、E01/E02 事故拦截
_update_pt_measurements()    → PT 二次侧电压（含相序映射）
_update_multimeter()         → 万用表读数（probe1 ↔ probe2）
```

### 自动同步控制（`ArbitrationMixin`）

```python
error_freq  = gen2.freq     - bus_freq
error_amp   = gen2.amp      - bus_amp
error_phase = (gen2.phase_deg - bus_phase_deg + 180) % 360 - 180

gen2.freq      += K_sync * error_freq
gen2.amp       += K_sync * error_amp
gen2.phase_deg += K_sync * error_phase

# 三者同时在容差内（0.5 Hz / 500 V / 15°）→ 允许合闸
```

### PT 相序映射与压差计算

```python
# 正常:   pt_phase_orders = ['A', 'B', 'C']
# E02 故障: fault_reverse_bc=True → PT3 端子 B→C 相、C→B 相
actual_phase = _resolve_terminal_actual_phase(pt_name, terminal)

# 【第二步 intra-PT 线电压】_compute_intra_pt_voltage() 通用相量差：
# gen_ph = pt_line_v / √3；E03 PT3 A 端子极性反接 → angle += π
# 正常/E01/E02: 角差 120° → √3·gen_ph（不变）
# E03 PT3_AB/CA: 角差 60°  → gen_ph ≈ 106 V（偏低标红）
# E03 PT3_BC:   不含 A，角差 120° → 正常
# E04: sim.pt3_ratio=118.28 但阈值用额定 56.99 → 88.8 V 标红

# 【第四步 cross-PT 压差】
# 同相压差:  abs(gen_ph - bus_ph)
# 异相压差:  sqrt(gen_ph² + bus_ph² + gen_ph·bus_ph)   [cos120° = −0.5]
# E03 极性反接 AA:    gen_ph + bus_ph  ≈ 166 V
# E03 极性反接 AB/AC: sqrt(V1² + V2² − V1·V2)  ≈ 92 V
```

---

## 关键常量（`domain/constants.py`）

| 常量 | 值 | 单位 | 用途 |
|------|----|------|------|
| `GRID_FREQ` | 50.0 | Hz | 额定频率 |
| `GRID_AMP` | 10500.0 | V | 额定线电压（RMS） |
| `XS` | 1.0 | Ω | 线路等效阻抗 |
| `TRIP_CURRENT` | 300.0 | A | 继电保护跳闸阈值 |
| `CT_RATIO` | 100 : 1 | — | 电流互感器变比 |
| `MAX_POINTS` | 200 | 点 | 示波器缓冲深度 |
| `KP_DROOP` | 0.0005 | — | 有功下垂系数 |
| `KQ_DROOP` | 0.0002 | — | 无功下垂系数 |

---

## UI 架构

`PowerSyncUI` 由 9 个 Mixin 组合：

| Mixin | 职责 |
|-------|------|
| `WidgetBuilderMixin` | 右侧控制面板（系统模式、接地、故障选择） |
| `WaveformTabMixin` | Tab 0：波形图 & 相量图（matplotlib） |
| `CircuitTabMixin` | Tab 1：母线拓扑 & 测量点 |
| `LoopTestTabMixin` | Tab 2：回路测试 |
| `PtVoltageCheckTabMixin` | Tab 3：PT 电压检查 |
| `PtPhaseCheckTabMixin` | Tab 4：PT 相序 |
| `PtExamTabMixin` | Tab 5：PT 压差 |
| `SyncTestTabMixin` | Tab 6：同期测试 |
| `TestPanelMixin` | 测试模式竖向控制栏（第 1～5 步控制台） |

### 测试模式面板（`test_panel.py`）

- 进入测试模式：右侧控制面板隐藏，测试面板显示
- 每步控制台由 `_build_step1~5` 构建，`_refresh_tp_step1~5` 每帧刷新
- **管理员模式**：开启后 Tab 2～6 可见，步骤可手动跳转
- **第二步 PT 变比控制台**：PT1 / PT3 / PT2 分三行独立显示，`_tp_s2_ratio_rows` 字典挂在 `self.ui`（非 `self.ui.test_panel`）上
- **第四步管理员快捷按钮** `⚡ 快捷记录全部 18 组`：仅管理员模式显示，调用 `record_all_pt_measurements_quick()`，跳过逐组表笔测量直接写入 Gen1 + Gen2 共 18 组压差

---

## 当前状态

- **已完成并验证**：隔离母排模式完整五步骤仿真；E01 / E02 场景全步骤测试通过
- **已实现待验证**：E03 步骤 5（Gen2 追踪 +180° 目标，双层拦截，事故弹窗）；E04 步骤 2（PT3 标红、记录表格标红、检测触发）；E05 步骤 2；E06 步骤 5
