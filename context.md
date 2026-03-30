# ThreePhase 项目上下文文档

> 供新对话快速理解项目全貌，可直接作为 Claude 对话开头的参考材料。详细的用户文档见 README.md。

---

## 项目简介

**三相电并网仿真教学系统**（ThreePhase Synchronization Training System）

基于 PyQt5 的桌面应用，模拟高压机组并网前的"隔离母排"操作流程，供电力系统操作员培训使用。系统包含完整的物理仿真、交互式测量工具、五步测试工作流，以及六个错误场景训练模块。

**入口**：`python app/main.py`（从项目根目录运行）

---

## 目录结构

```
ThreePhase/
├── app/
│   ├── main.py              # 应用入口、PowerSyncController（总控制器）
├── domain/                  # 领域模型与常量
│   ├── constants.py         # 物理参数（电压、频率、阻抗等）
│   ├── enums.py             # 系统模式、断路器状态枚举
│   ├── models.py            # GeneratorState、SimulationState 数据类
│   ├── test_states.py       # 各步骤状态类（LoopTestState 等）
│   ├── fault_scenarios.py   # 6个错误场景定义
│   └── node_map.py          # 测量节点坐标
├── services/                # 业务逻辑与物理引擎
│   ├── physics_engine.py    # 物理引擎主类（Mixin 组合）
│   ├── _physics_core.py     # 波形生成 Mixin
│   ├── _physics_arbitration.py  # 母线仲裁与同步 Mixin
│   ├── _physics_protection.py   # 继电保护与断路器逻辑 Mixin
│   ├── _physics_measurement.py  # PT/万用表测量 Mixin
│   ├── loop_test_service.py     # 第1步：回路导通测试
│   ├── pt_voltage_check_service.py  # 第2步：PT电压检查
│   ├── pt_phase_check_service.py    # 第3步：PT相序检查
│   ├── pt_exam_service.py           # 第4步：PT压差考核
│   └── sync_test_service.py         # 第5步：同期功能测试
├── ui/                      # PyQt5 用户界面（Mixin 拼装）
│   ├── main_window.py       # PowerSyncUI 主窗口
│   ├── styles.py            # 全局 QSS 样式
│   ├── test_panel.py        # 测试模式控制面板 Mixin（含第1~5步控制台）
│   ├── panels/
│   │   └── control_panel.py # 右侧控制面板 Mixin
│   ├── tabs/
│   │   ├── waveform_tab.py      # Tab 0: 波形 & 相量图
│   │   ├── circuit_tab.py       # Tab 1: 母线拓扑（最大，~970行）
│   │   ├── loop_test_tab.py     # Tab 2: 回路测试 UI
│   │   ├── pt_voltage_check_tab.py  # Tab 3: PT电压检查 UI
│   │   ├── pt_phase_check_tab.py    # Tab 4: PT相序 UI
│   │   ├── pt_exam_tab.py           # Tab 5: PT压差 UI
│   │   └── sync_test_tab.py         # Tab 6: 同期测试 UI
│   └── widgets/
│       ├── multimeter_widget.py # 数字万用表 UI（QPainter绘制）
│       └── phase_seq_meter.py   # 相序计 UI
├── adapters/
│   └── render_state.py      # RenderState 数据类（UI渲染快照）
├── README.md                # GitHub 项目文档
└── context.md               # Claude 对话上下文摘要
```

---

## 架构概览

```
PowerSyncUI (View - 多 Mixin)
        ↑ render_visuals(RenderState)
        ↓ 用户操作事件
PowerSyncController (Application Layer - app/main.py)
  - 持有 SimulationState（唯一数据源）
  - 持有 PhysicsEngine 实例
  - 持有 5 个测试服务实例
  - 33ms 定时器驱动主循环
        ↑ build_render_state()
        ↓ update_physics()
PhysicsEngine（4个Mixin组合）
  ├─ WaveformMixin:      三相正弦波形生成
  ├─ ArbitrationMixin:   母线仲裁 & 自动同步（类PLL）
  ├─ ProtectionMixin:    继电保护 & 断路器联锁
  └─ MeasurementMixin:   PT二次侧电压 & 万用表读数
        ↑ 读取 sim_state
        ↓ 更新测量值
Domain Models
  - GeneratorState: 频率、幅值、相位、断路器状态
  - SimulationState: 双机状态、故障配置、接地模式
  - FaultConfig: 故障场景注入参数
```

---

## 核心数据模型

### GeneratorState（domain/models.py）
| 字段 | 含义 |
|------|------|
| `freq` | 发电机频率（Hz） |
| `amp` | 输出电压幅值（V，线电压RMS） |
| `phase_deg` | 相位（度） |
| `mode` | 手动/自动 |
| `breaker_closed` | 主断路器状态 |
| `running` | 是否启机 |

### SimulationState（domain/models.py）
| 字段 | 含义 |
|------|------|
| `gen1`, `gen2` | 两台发电机状态 |
| `system_mode` | 当前系统模式（目前仅启用 ISOLATED_BUS 隔离母排） |
| `fault_config` | 当前激活的故障场景配置 |
| `fault_reverse_bc` | Gen2 B/C相物理对调标志（E02专用，影响波形和PT3测量） |
| `pt_gen_ratio` | PT1（Gen1侧）变比，默认 11000/193 ≈ 56.99；步骤2可配置 |
| `pt3_ratio` | PT3（Gen2侧）变比，默认 11000/193 ≈ 56.99；E04注入时改为 11000/93 ≈ 118.28 |
| `pt_bus_ratio` | PT2（母排侧）变比，默认 10500/105 = 100；二次侧额定 105V |
| `grounding_mode` | "小电阻接地" / "断开" |
| `probe1_node`, `probe2_node` | 万用表表笔位置 |
| `loop_test_mode` | 第1步回路测试专用模式 |

**PT变比分离设计**：PT1与PT3各用独立字段（`pt_gen_ratio` / `pt3_ratio`），是为了支持E04场景（仅PT3变比错误，PT1保持正确）。步骤2控制台分三行分别显示并可独立修改。

---

## 五步测试工作流

| 步骤 | 服务类 | 电气状态 | 核心验证 |
|------|--------|----------|----------|
| 1. 回路导通测试 | `LoopTestService` | 双机手动/工作位/合闸/未启机，拆除接地电阻 | A/B/C三相回路导通；检出相序接线错误 |
| 2. PT电压检查 | `PtVoltageCheckService` | Gen1并网，Gen2运行但断路器分闸 | PT1/PT2/PT3三相线电压，±15%容差（额定10.5kV） |
| 3. PT相序检查 | `PtPhaseCheckService` | 同步骤2 | PT1/PT3相序表指示；检出BC相互换故障 |
| 4. PT压差考核 | `PtExamService` | 分两个子测试（Gen1/Gen2交替上母线） | 9对PT端子间向量压差；验证同期就绪 |
| 5. 同期功能测试 | `SyncTestService` | Gen2自动模式追踪Gen1 | Δf<0.5Hz，ΔV<500V，Δθ<15°收敛后合闸 |

### 第二步特殊行为（_physics_arbitration.py）
- Gen1 以 ±0.02Hz / ±5V 随机游走模拟真实抖动（仅 Auto 模式）
- Gen2 以秒级步长慢速追赶 Gen1（仅 Auto 模式）
- **手动模式下两台机组均不受自动追踪影响，学员可自由调参**
- 第二步测试面板的滑块加有 `sl.isSliderDown()` 保护，拖动时不被每帧渲染覆盖

---

## 六个错误场景（domain/fault_scenarios.py）

| 编号 | 故障内容 | 检出步骤 | 第五步行为 | 风险等级 |
|------|----------|----------|------------|----------|
| E01 | Gen1 A/B相接线互换 | 步骤1（回路断路）+ 步骤3（相序异常）+ 步骤4（压差矩阵异常） | Gen2合闸时触发**致命事故弹窗** | recoverable |
| E02 | Gen2 B/C相接线互换 | 步骤1（回路断路）+ 步骤3（相序异常）+ 步骤4（压差矩阵异常） | Gen2合闸时触发**致命事故弹窗** | recoverable |
| E03 | PT3 A相极性反接 | 步骤2（PT3_AB/CA≈106V标红）+ 步骤3（PT3_A相位不匹配）+ 步骤4（A行压差矩阵异常） | Gen2自动追踪收敛至180°错误相位；同步仪显示~180°相位差；强行合闸触发**致命事故弹窗** | accident |
| E04 | PT3实际变比11000:93（≈118.28），额定应为11000:193（≈56.99） | 步骤2（PT3二次侧≈88V，远低于额定184V，标红）+ 步骤4（PT3各行压差均偏小） | 无（recoverable，学员在步骤4~5前修复即可） | recoverable |
| E05 | Gen2过电压（13000V，AVR故障） | 步骤2（PT3电压超容差）+ 步骤4（PT3同相压差偏大）+ 步骤5（幅值同步失败） | 无 | recoverable |
| E06 | Gen2相角追踪禁用（强制非同期合闸） | 步骤5（Δθ不收敛） | 持续警告，强行合闸触发事故 | accident |

### E04 场景详解（关键设计）

E04 的核心：PT3 **硬件实际变比** 为 118.28，但**额定铭牌**应为 56.99。系统注入E04时：
- `sim.pt3_ratio` 设为 118.28（控制台同步显示 11000:93，让学员看到真实变比）
- 物理测量也用 118.28，二次侧输出 ≈ 10500/118.28 ≈ **88.8V**
- **阈值比较使用额定变比 56.99**（在 `_physics_measurement.py` 和 `pt_voltage_check_service.py` 中均做特殊处理）：阈值范围 8925/56.99 ≈ 156.6V ~ 211.9V，88.8V 远低于下限 → **红色[异常]**
- 检测触发：`meter_status == 'danger'` 时置 `fc.detected = True`
- 记录表格：`primary_v = meter_v_sec × 56.99 ≈ 5060V`，不在 [8925, 12075]V → 表格也标红
- 反馈文本中"偏离额定"显示动态计算的额定二次侧值（PT3为184V，PT2为105V），不再硬编码

### E01 / E02 / E03 事故触发机制（关键设计）

E01/E02/E03 均在步骤1~4可被检出，但**不在进入步骤5时弹修复对话框**。事故在 Gen2 断路器合闸瞬间触发，有**两层拦截**：

**第一层（UI层，app/main.py `toggle_breaker()`）**：
```python
# 仅当 is_sync_test_active()（步骤5同期测试进行中）才拦截手动合闸
if fc.scenario_id == 'E01': show_e01_accident_dialog(); return
if fc.scenario_id == 'E02': show_e02_accident_dialog(); return
if fc.scenario_id == 'E03': show_e03_accident_dialog(); return
# → cmd_close 不被设置，合闸请求被完全阻断
```

**第二层（物理层，_physics_protection.py `_update_breaker_state()`）**：
```python
# 兜底：sync_ok=True 分支（E01/E02/E03 auto 合闸拦截）
if fc.scenario_id == 'E01': show_e01_accident_dialog()
elif fc.scenario_id == 'E02': show_e02_accident_dialog()
elif fc.scenario_id == 'E03': show_e03_accident_dialog()
# → breaker_closed 保持 False

# 额外：E03 sync_ok=False 分支（180°相位差时 manual 强行合闸）
if fc.scenario_id == 'E03': show_e03_accident_dialog()
# → 替代通用"爆炸"消息，改为事故弹窗
```

弹窗说明：事故原因、可见异常现象、修复方法。学员选"修复故障"→ `repair_fault()` → 可继续第五步。

**E03 步骤 2~4 弹窗屏蔽**：
- `_check_fault_detection()`（main_window.py）：`danger_level == 'accident'` 且 `scenario_id == 'E03'` 时直接 return，不弹窗（异常数据通过横幅提示即可）
- `test_panel.py` 第五步前修复关卡：E03 加入排除列表 `('E06','E01','E02','E03')`，不在进入步骤 5 时弹修复对话框
- 结果：步骤 2~4 学员只看到异常测量值 + 横幅"已发现异常证据"，可直接记录推进；事故仅在步骤 5 合闸触发

**E03 工程原理**：PT3 A 相极性反接使同期装置参考角偏差 180°。`_handle_live_bus_sync` 中 E03 激活时，`auto_adjust_phase` 目标改为 `target_phase_deg + 180°`，Gen2 收敛至反相位置；sync_ok=False，仲裁器显示红色警告。学员若仍强行合闸，触发事故弹窗。

**E01/E02 工程原理**：自动同步以 A 相参考角收敛（Δf/ΔV/Δθ 均满足），同期仪误判条件满足，但 E01 合闸后 A/B 错相 120° 短路，E02 合闸后 B/C 跨相 120° 短路。物理引擎单相等效电路无法计算跨相电流，故在保护层硬编码拦截。

### 故障注入机制（通用流程）
1. 教师在右侧控制面板选择故障场景
2. `FaultConfig` 注入 `SimulationState`（及 `fault_reverse_bc` 等专属标志）
3. `PhysicsEngine` 读取故障参数扭曲测量值
4. UI 轮询 `fault_config.detected` 标志，更新横幅提示（E04/E05 另在步骤4→5过渡时弹修复对话框）
5. 学员"修复"确认 → `repaired = True`，允许继续测试
6. E01/E02/E03 例外：修复时机在第五步合闸事故弹窗内，步骤2~4仅显示横幅不弹窗

---

## 物理引擎关键算法

### 每帧更新顺序（33ms/帧）
```
_update_bus_reference()     → 确定母线参考源（Gen1 or Gen2）
_update_arbitration()       → 自动同步调节（PLL式）
_advance_time()             → 推进仿真时间
_update_actual_amplitudes() → 电压斜坡上升（调速器模型）
_compute_wave_state()       → 角频率、相位计算
_update_protection_state()  → 计算线路电流，过流检测（300A跳闸）
_apply_droop_control()      → 频率下垂调节
_update_wave_history()      → 更新200点波形缓冲
_update_breaker_logic()     → 联锁执行、保护跳闸、E01/E02事故拦截
_update_pt_measurements()   → PT二次侧电压（含相序映射）
_update_multimeter()        → 万用表读数（probe1 ↔ probe2）
```

### 自动同步控制（ArbitrationMixin）
```python
error_freq  = gen2.freq     - bus_freq
error_amp   = gen2.amp      - bus_amp
error_phase = (gen2.phase_deg - bus_phase_deg) % 360°

gen2.freq     += K_sync * error_freq
gen2.amp      += K_sync * error_amp
gen2.phase_deg += K_sync * error_phase

# 三者同时在容差内（0.5Hz / 500V / 15°）→ 允许合闸
```

### PT相序映射与压差计算
```python
# 正常: pt_phase_orders = ['A','B','C']
# E02故障: fault_reverse_bc=True → PT3端子B→C相、C→B相
actual_phase = _resolve_terminal_actual_phase(pt_name, terminal)

# 【第二步 intra-PT 线电压】通用相量差公式（_compute_intra_pt_voltage）：
# gen_ph = pt_line_v / √3
# angle1 = _PHASE_ANGLES[phase1]，E03 PT3 A端子: angle += π（极性反接）
# meter_v = |gen_ph·e^(jθ1) − gen_ph·e^(jθ2)|
# 正常/E01/E02: 两相角差120° → √3·gen_ph = pt_line_v（不变）
# E03 PT3_AB/CA: 角差60° → gen_ph = pt_line_v/√3 ≈ 106V（偏低标红）
# E03 PT3_BC: 不含A端子，角差120° → 正常
#
# E04 阈值特殊处理（_physics_measurement.py 和 pt_voltage_check_service.py）：
# 即使 sim.pt3_ratio=118.28，阈值计算强制用额定变比56.99
# → 阈值下限 8925/56.99≈156.6V，测量≈88.8V → 红色[异常]

# 【第四步 cross-PT 压差】
# 同相压差: abs(gen_ph - bus_ph)
# 异相压差: sqrt(gen_ph² + bus_ph² + gen_ph·bus_ph)  [cos120°=-0.5]
# E03极性反接AA: gen_ph+bus_ph（≈166V）;  E03极性反接AB/AC: sqrt(V1²+V2²-V1·V2)（≈92V）
```

---

## 关键常量（domain/constants.py）

| 常量 | 值 | 单位 | 用途 |
|------|----|------|------|
| `GRID_FREQ` | 50.0 | Hz | 额定频率 |
| `GRID_AMP` | 10500.0 | V | 额定线电压（RMS） |
| `XS` | 1.0 | Ω | 线路等效阻抗 |
| `TRIP_CURRENT` | 300.0 | A | 继电保护跳闸阈值 |
| `CT_RATIO` | 100:1 | — | 电流互感器变比 |
| `MAX_POINTS` | 200 | 点 | 示波器缓冲深度 |
| `KP_DROOP` | 0.0005 | — | 有功下垂系数 |
| `KQ_DROOP` | 0.0002 | — | 无功下垂系数 |

---

## UI 架构

`PowerSyncUI` 由9个 Mixin 组合：

| Mixin | 职责 |
|-------|------|
| `WidgetBuilderMixin` | 右侧控制面板（系统模式、接地、故障选择） |
| `WaveformTabMixin` | Tab 0：波形图 & 相量图（matplotlib） |
| `CircuitTabMixin` | Tab 1：母线拓扑 & 测量点（最大文件，~970行） |
| `LoopTestTabMixin` | Tab 2：回路测试 |
| `PtVoltageCheckTabMixin` | Tab 3：PT电压检查 |
| `PtPhaseCheckTabMixin` | Tab 4：PT相序 |
| `PtExamTabMixin` | Tab 5：PT压差 |
| `SyncTestTabMixin` | Tab 6：同期测试 |
| `TestPanelMixin` | 测试模式竖向控制栏（替换右侧面板，含第1~5步控制台） |

### 测试模式面板（test_panel.py）重要细节
- 进入测试模式：`ctrl_container.setVisible(False)`，`test_panel.setVisible(True)`
- 每步控制台由 `_build_step1~5` 构建，`_refresh_tp_step1~5` 每帧刷新
- **管理员模式**：开启后 Tab 2~6 可见，步骤点可手动跳转
- **第二步变比控制台**：PT1/PT3/PT2 分三行独立显示，`_tp_s2_ratio_rows` 字典存储各行控件引用（键为 `'pt_gen_ratio'`/`'pt3_ratio'`/`'pt_bus_ratio'`），**该属性挂在 `self.ui`（PowerSyncUI实例）上，不在 `self.ui.test_panel`（QWidget）上**
- **第四步管理员快捷按钮** `⚡ 快捷记录全部18组`：仅管理员模式显示，调用 `record_all_pt_measurements_quick()`，跳过逐组表笔测量直接写入 Gen1+Gen2 共18组压差

### 快捷记录实现（pt_exam_service.py）
```python
def record_all_pt_measurements_quick(self):
    # 检查前三步完成 + 第四步已开始
    # 直接读取 physics.pt1_v / pt2_v / pt3_v
    # 对 Gen1+Gen2 各9组 (gen_term × bus_phase) 计算压差
    # 使用与 _update_multimeter 完全相同的公式（含E03极性修正）
    # 一次性写入 pt_exam_states[1/2].records
```

---

## 项目当前状态

- **已完成并验证**：隔离母排模式完整五步骤仿真；E01 / E02 场景全步骤测试通过
- **本轮完成功能**：
  - E03 步骤5方案B：Gen2追踪目标偏移+180°，双层拦截，事故弹窗
  - E04 步骤2完整实现：
    - PT1/PT3变比拆分为独立字段（`pt_gen_ratio` / `pt3_ratio`）
    - 控制台三行分别显示 PT1/PT3/PT2，PT2额定变比10500:105（二次侧105V）
    - E04注入时控制台显示真实变比11000:93（sim.pt3_ratio=118.28）
    - 万用表读数与记录表格均使用额定变比56.99作为阈值基准 → 88.8V标红
    - 检测机制：`meter_status == 'danger'` 触发 `fc.detected`
    - 反馈文本动态显示各PT额定二次侧值（不再硬编码100V）
- **待运行验证**：
  - E03：步骤5方案B已实现，待实际运行验证
  - E04：步骤2修复已完成，待端到端运行验证
  - E05：步骤2 PT3电压超容差
  - E06：步骤5相角不收敛，强行合闸触发事故

---

## 依赖

```
PyQt5       # GUI框架
matplotlib  # 波形/相量/拓扑图绘制
numpy       # 数值计算
```
