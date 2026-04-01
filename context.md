# ThreePhase 项目上下文文档

> 供新对话快速理解项目全貌，可直接作为 Claude 对话开头的参考材料。详细的用户文档见 README.md。

---

## 项目简介

**三相电并网仿真教学系统**（ThreePhase Synchronization Training System）

基于 PyQt5 的桌面应用，模拟高压机组并网前的"隔离母排"操作流程，供电力系统操作员培训使用。系统包含完整的物理仿真、交互式测量工具、五步测试工作流，以及 14 个错误场景训练模块（E15/E16 暂时禁用，代码已注释保留）。

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
│   ├── fault_scenarios.py   # 错误场景定义（当前启用 E01-E14，E15/E16 已注释禁用）
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

## 错误场景（domain/fault_scenarios.py）

> 当前启用 E01–E14，E15/E16（原E05/E06）代码已注释禁用（开发中）。
> E01/E02 为 Gen2/PT3 侧接线场景；E05–E14 为 Gen1/PT1 侧接线矩阵场景。

### 非接线类故障（E01–E04）

| 编号 | 状态 | 故障内容 | 检出步骤 | 第五步行为 | 风险等级 |
|------|------|----------|----------|------------|----------|
| E01 | ✅ 启用 | Gen1 A/B相接线互换 | 步骤1（回路断路）+ 步骤3（相序异常）+ 步骤4（压差矩阵异常） | Gen2合闸触发**致命事故弹窗** | recoverable |
| E02 | ✅ 启用 | Gen2 B/C相接线互换 | 步骤1（回路断路）+ 步骤3（相序异常）+ 步骤4（压差矩阵异常） | Gen2合闸触发**致命事故弹窗** | recoverable |
| E03 | ✅ 启用 | PT3 A相极性反接 | 步骤2（PT3_AB/CA≈106V标红）+ 步骤3（PT3_A相位不匹配）+ 步骤4（A行压差异常） | Gen2追踪收敛至180°错误相位；强行合闸触发**致命事故弹窗** | accident |
| E04 | ✅ 启用 | PT3实际变比11000:93（≈118.28），额定应为11000:193（≈56.99） | 步骤2（PT3二次侧≈88V标红）+ 步骤4（PT3各行压差偏小） | 无 | recoverable |

### Gen1/PT1 接线矩阵场景（E05–E14）

信号链：Gen1 → [G节点] → Bus → [P1节点] → PT1一次侧 → [P2节点] → PT1二次侧

| 编号 | 状态 | 场景名 | G节点 | P1节点 | P2节点 | pt1_phase_order | 步骤1 | 步骤3 | 步骤4 | 诊断难度 |
|------|------|--------|-------|--------|--------|----------------|-------|-------|-------|---------|
| E05 | ✅ 启用 | 反反反(同) | A↔B | A↔B | A↔B | BAC | ❌断路 | ❌逆序 | ⚠️A端0V陷阱 | 中 |
| E06 | ✅ 启用 | 正反正 | 正 | A↔B | 正 | BAC | ✅ | ❌逆序 | ❌全相183V | 中 |
| E07 | ✅ 启用 | 正正反 | 正 | 正 | A↔B | BAC | ✅ | ❌逆序 | ❌全相183V | 中（同E06，需拆检区分） |
| E08 | ✅ 启用 | 正反反(同)·完全隐性 | 正 | A↔B | A↔B | ABC(隐) | ✅ | ✅假正序 | ✅假0V | 🔴最高（四步全过） |
| E09 | ✅ 启用 | 反正反(同) | A↔B | 正 | A↔B | ABC(隐) | ❌断路 | ✅假正序 | ❌全相183V | 高 |
| E10 | ✅ 启用 | 反反正(同) | A↔B | A↔B | 正 | ABC(隐) | ❌断路 | ✅假正序 | ❌全相183V | 高（同E09，需拆检区分） |
| E11 | ✅ 启用 | 正反反(不同) | 正 | A↔B | B↔C | CAB | ✅ | ✅假正序 | ❌三相全183V | 🔴最高（步骤四唯一出路） |
| E12 | ✅ 启用 | 反正反(不同) | A↔B | 正 | B↔C | CAB | ❌断路 | ✅假正序 | ⚠️A端0V陷阱/B端183V | 极高 |
| E13 | ✅ 启用 | 反反正(不同) | A↔B | B↔C | 正 | CAB | ❌断路 | ✅假正序 | ⚠️A端0V陷阱/B端183V | 极高（同E12，需拆检区分） |
| E14 | ✅ 启用 | BAC×ACB×CAB三级互消 | BAC | B↔C | CAB | ABC(隐) | ❌断路 | ✅假正序 | ⚠️C端0V陷阱/A/B端183V | 极高 |

### 暂时禁用

| 编号 | 故障内容 |
|------|---------|
| E15（原E05）| Gen2过电压（13000V，AVR故障） |
| E16（原E06）| Gen2相角追踪禁用（强制非同期合闸） |

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
- `test_panel.py` 第五步前修复关卡：E03 加入排除列表 `('E01','E02','E03')`（E06 已禁用，已从列表移除），不在进入步骤 5 时弹修复对话框
- 结果：步骤 2~4 学员只看到异常测量值 + 横幅"已发现异常证据"，可直接记录推进；事故仅在步骤 5 合闸触发

**E03 工程原理**：PT3 A 相极性反接使同期装置参考角偏差 180°。`_handle_live_bus_sync` 中 E03 激活时，`auto_adjust_phase` 目标改为 `target_phase_deg + 180°`，Gen2 收敛至反相位置；sync_ok=False，仲裁器显示红色警告。学员若仍强行合闸，触发事故弹窗。

**E01/E02 工程原理**：自动同步以 A 相参考角收敛（Δf/ΔV/Δθ 均满足），同期仪误判条件满足，但 E01 合闸后 A/B 错相 120° 短路，E02 合闸后 B/C 跨相 120° 短路。物理引擎单相等效电路无法计算跨相电流，故在保护层硬编码拦截。

### 故障注入机制（通用流程）
1. 教师在右侧控制面板选择故障场景
2. `FaultConfig` 注入 `SimulationState`（及 `fault_reverse_bc` 等专属标志）
3. `PhysicsEngine` 读取故障参数扭曲测量值
4. UI 轮询 `fault_config.detected` 标志，更新横幅提示（E05–E14 在步骤4→5过渡时弹修复对话框）
5. 学员"修复"确认 → `repaired = True`，允许继续测试
6. E01/E02/E03 例外：修复时机在第五步合闸事故弹窗内，步骤2~4仅显示横幅不弹窗

### Gen1/PT1 接线矩阵注入机制（E05–E14，通用参数驱动）

**params 字段**：
- `pt1_phase_order`（必填）：PT1 二次侧净相序，如 `['B','A','C']`（BAC）或 `['A','B','C']`（隐性正序）。注入时写入 `pt_phase_orders['PT1']`，修复时还原为 `['A','B','C']`。
- `g1_loop_swap`（可选）：Gen1 机端对调端子对，如 `('A','B')`。

**两处关键注入（inject_fault）**：
```python
# 1. PT1 端子相序
pt1_order = fc.params.get('pt1_phase_order')
if pt1_order:
    pt_phase_orders['PT1'] = list(pt1_order)

# 2. Gen1 换相同步影响母排（Bus）：Gen1 A↔B → Bus_A 载 B 相
swap = fc.params.get('g1_loop_swap')
if swap:
    p1, p2 = swap
    new_pt2 = list(pt_phase_orders['PT2'])
    new_pt2[i1], new_pt2[i2] = new_pt2[i2], new_pt2[i1]
    pt_phase_orders['PT2'] = new_pt2
```
> **设计原因**：若仅更新 PT1 而不更新 PT2，步骤四 cross-PT 压差计算会将 Bus 端子误判为 A 相，导致 E05 显示本该为 0V 的陷阱变成 183V，E09/E10/E14 本该为 183V 的异常变成 0V，E12/E13 的"A端0V陷阱"消失。

**步骤一断路检测**（`_physics_measurement.py`）：
```python
# E01/E02 硬编码 + E05–E14 通用（凡有 g1_loop_swap 的场景）
if fc.params.get('g1_loop_swap') or fc.params.get('g2_loop_swap'):
    fc.detected = True   # 回路断路时触发
```
触发场景：E05 / E09 / E10 / E12 / E13 / E14。

**步骤四异相检测**（`_physics_measurement.py`，补丁修复 Bug A）：
```python
# E05–E14 通用：PT1 端子与 Bus 相位不匹配时触发
elif (gen_pt_name == 'PT1'
      and fc.params.get('pt1_phase_order') is not None
      and not is_same_phase):
    fc.detected = True
```
覆盖 E06 / E07 / E11（这三个场景步骤一无断路，仅步骤四能暴露）。
E08 全部同相（pt1_phase_order=['A','B','C'] 且无 g1_loop_swap），永远不触发——这是设计意图（完全隐性故障）。

**各场景步骤四预期电压**（修复后）：
| 场景 | Bus_A | PT1_A | A端压差 | B端压差 | C端压差 |
|------|-------|-------|---------|---------|---------|
| E05 | B相 | B相 | **0V** (陷阱) | **0V** (陷阱) | 0V |
| E06 | A相 | B相 | **183V** ❌ | 183V ❌ | 0V |
| E07 | A相 | B相 | **183V** ❌ | 183V ❌ | 0V |
| E09/E10 | B相 | A相 | **183V** ❌ | 183V ❌ | 0V |
| E11 | A相 | B相 | **183V** ❌ | 183V ❌ | 183V ❌ |
| E12/E13 | B相 | B相 | **0V** (陷阱) | 183V ❌ | 183V ❌ |
| E14 | B相 | A相 | **183V** ❌ | 183V ❌ | **0V** (陷阱) |
| E08 | A相 | A相 | 0V ✅ | 0V ✅ | 0V ✅ |

**resolve_loop_node_phase（步骤一回路相位映射）**：
```python
swap = fc.params.get('g1_loop_swap')
if swap and gen_name == 'G1':
    p1, p2 = swap
    return {p1: p2, p2: p1}.get(terminal, terminal)
```

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

### 第一步回路测试 UI 变更
- **路径动画已注释**（`ui/tabs/circuit_tab.py`）：绿色流动球（导通）与红色 X 符号（断路）的路径动画全部注释，图面连线无任何动态变化。
- 学员**只能**通过万用表面板读数（`0.0 Ω` = 导通，`不导通` = 断路）判断通断，不再有视觉外挂提示。
- 动画相关 Plot 对象（`loop_anim_wire_ok` 等）保留但始终为空，`_clear_loop_anim()` 方法保留。

### 第四步黑盒接线检查（`_show_blackbox_dialog`）
第四步控制台"物理接线检查"区有 4 个按钮，点击弹出图形化接线图对话框。

**G1 / G2 发电机端子盒**（`_GenWiringWidget`）：
- 上方：3 个固定彩色圆 = 内部绕组（A黄 / B绿 / C红），位置永远固定
- 下方：3 个方块 = 输出接线柱（U / V / W）
- 连线根据 `mapping = {terminal: actual_phase}` 动态绘制
  - 正常 `['A','B','C']` → 三条平行竖线
  - 错接（如 A↔B swap）→ 黄线与绿线在画面中间交叉
- 数据来源：`g1_loop_swap`（或 `g2_loop_swap` + `fault_reverse_bc`）；**修复后（`fc.repaired=True`）读空 params，显示正常接线**

**PT1 / PT3 接线盒**（`_PTWiringWidget`，六点式）：
- 上方：测量端口 A/B/C（固定位置，固定颜色）
- 上半部连线：二次侧端子 a2/b2/c2 → 测量端口；基于 `sec_order`，相序不对则交叉
- 中间：变压器铁芯黑盒（虚线框）
- 下半部连线：输入电缆 A(黄)/B(绿)/C(红)（固定位置）→ 一次侧端子 A1/B1/C1；基于 `pri_order`，相序不对则交叉
- 数据来源：
  - PT1 `pri_order` = `pt_phase_orders['PT2']`（Bus 相序，随 G1 swap 变化）
  - PT1 `sec_order` = `pt_phase_orders['PT1']`（P1/P2 换相净结果）
  - PT3 `pri_order` = 由 `fault_reverse_bc` / `g2_loop_swap` 计算的 Gen2 输出相序
  - PT3 `sec_order` = `pt_phase_orders['PT3']` + `fault_reverse_bc` B/C 对调
- E03 激活时额外显示橙色提示：A1 正负极颠倒

**绘图逻辑关键**（两个 widget 共用）：
- 固定电缆/绕组位置：xs[0]=A, xs[1]=B, xs[2]=C
- 连线颜色 = 该线实际传输的相色
- 交叉判断：当 `src_x ≠ dst_x` 时线段对角，即为错接可视化

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
- **已实现待验证**：E03 步骤5（Gen2追踪+180°目标，双层拦截，事故弹窗）；E04 步骤2（PT3标红、记录表格标红、检测触发）；E05–E14 物理注入（通用参数驱动，含两处漏洞修复，见下方"Gen1/PT1接线矩阵注入机制"）
- **暂时禁用（代码已注释保留，开发中）**：
  - E15（原E05）：Gen2过电压（AVR故障），步骤2/4/5
  - E16（原E06）：强行非同期合闸，步骤5

---

## 依赖

```
PyQt5       # GUI框架
matplotlib  # 波形/相量/拓扑图绘制
numpy       # 数值计算
```
