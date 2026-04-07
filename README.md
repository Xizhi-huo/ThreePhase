# ThreePhase — 三相电并网仿真教学系统

> 基于 PyQt5 的高压机组并网操作培训桌面应用，模拟隔离母排模式下的完整五步并网流程，包含 14 个可注入的错误场景供教学使用（E15/E16 暂时禁用，开发中）。

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
│   ├── assessment.py                # 考核模式事件 / 会话 / 成绩结果数据结构
│   ├── test_states.py               # 各步骤状态类
│   ├── fault_scenarios.py           # 错误场景定义（当前启用 E01-E14，E15/E16 已注释禁用）
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
│   ├── sync_test_service.py         # 第 5 步：同期功能测试
│   └── assessment_service.py        # 考核模式自动评分与成绩汇总
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
| `fault_reverse_bc` | Gen2 B/C 相内部反相兼容标志（当前主要保留给手动陷阱开关） |
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
| 3. PT 相序检查 | `PtPhaseCheckService` | 同步骤 2 | PT1/PT3 相序表指示；按真实三字母结果逐相记录端子错位 |
| 4. PT 压差考核 | `PtExamService` | Gen1/Gen2 交替上母线 | 9 对 PT 端子间向量压差；验证同期就绪 |
| 5. 同期功能测试 | `SyncTestService` | Gen2 自动模式追踪 Gen1 | Δf < 0.5 Hz，ΔV < 500 V，Δθ < 15° 收敛后合闸 |

### 第二步特殊行为

- Gen1 以 ±0.02 Hz / ±5 V 随机游走模拟真实抖动（仅 Auto 模式）
- Gen2 以秒级步长慢速追赶 Gen1（仅 Auto 模式）
- 手动模式下两台机组均不受自动追踪影响，学员可自由调参
- 测试面板滑块加有 `isSliderDown()` 保护，拖动时不被每帧渲染覆盖

---

## 错误场景

> 当前启用 E01–E14，E15/E16（原 E05/E06）代码已注释禁用（开发中）。

### 非接线类故障（E01–E04）

| 编号 | 状态 | 故障内容 | 检出步骤 | 第五步行为 | 风险等级 |
|------|------|----------|----------|------------|----------|
| E01 | ✅ 启用 | Gen1 A/B 相接线互换 | 步骤 1（回路断路）/ 步骤 3（相序逆序）/ 步骤 4（压差矩阵异常） | Gen2 合闸触发**致命事故弹窗** | recoverable |
| E02 | ✅ 启用 | Gen2 B/C 相接线互换 | 步骤 1（回路断路）/ 步骤 3（相序逆序）/ 步骤 4（压差矩阵异常） | Gen2 合闸触发**致命事故弹窗** | recoverable |
| E03 | ✅ 启用 | PT3 A 相极性反接 | 步骤 2（PT3\_AB/CA ≈ 106 V 标红）/ 步骤 3（PT3\_A 相位不匹配）/ 步骤 4（A 行压差矩阵异常） | Gen2 自动同期收敛至 180° 错误相位；强行手动合闸触发**致命事故弹窗** | accident |
| E04 | ✅ 启用 | PT3 实际变比 11000:93（≈118.28），额定应为 11000:193（≈56.99） | 步骤 2（PT3 二次侧 ≈ 88 V 标红）/ 步骤 4（PT3 各行压差均偏小） | 无 | recoverable |

### Gen1/PT1 接线矩阵场景（E05–E14）

信号链：Gen1 → [G节点] → Bus → [P1节点] → PT1一次侧 → [P2节点] → PT1二次侧

| 编号 | 状态 | 场景名 | G | P1 | P2 | 步骤1 | 步骤3 | 步骤4 | 诊断难度 |
|------|------|--------|---|----|----|-------|-------|-------|---------|
| E05 | ✅ 启用 | 反反反(同) | A↔B | A↔B | A↔B | ❌ 断路 | ❌ 逆序 | ⚠️ A端0V陷阱 | 中 |
| E06 | ✅ 启用 | 正反正 | 正 | A↔B | 正 | ✅ | ❌ 逆序 | ❌ 全相183V | 中 |
| E07 | ✅ 启用 | 正正反 | 正 | 正 | A↔B | ✅ | ❌ 逆序 | ❌ 全相183V | 中（同E06，拆检区分） |
| E08 | ✅ 启用 | 正反反(同)·**完全隐性** | 正 | A↔B | A↔B | ✅ | ✅ 假正序 | ✅ 假0V | 🔴 最高（四步全过） |
| E09 | ✅ 启用 | 反正反(同) | A↔B | 正 | A↔B | ❌ 断路 | ✅ 假正序 | ❌ 全相183V | 高 |
| E10 | ✅ 启用 | 反反正(同) | A↔B | A↔B | 正 | ❌ 断路 | ✅ 假正序 | ❌ 全相183V | 高（同E09，拆检区分） |
| E11 | ✅ 启用 | 正反反(不同) | 正 | A↔B | B↔C | ✅ | ✅ 假正序 | ❌ 三相全183V | 🔴 最高（步骤四唯一出路） |
| E12 | ✅ 启用 | 反正反(不同) | A↔B | 正 | B↔C | ❌ 断路 | ✅ 假正序 | ⚠️ A端0V/B端183V | 极高 |
| E13 | ✅ 启用 | 反反正(不同) | A↔B | B↔C | 正 | ❌ 断路 | ✅ 假正序 | ⚠️ A端0V/B端183V | 极高（同E12，拆检区分） |
| E14 | ✅ 启用 | BAC×ACB×CAB 三级互消 | BAC | B↔C | CAB | ❌ 断路 | ✅ 假正序 | ⚠️ C端0V/A/B端183V | 极高 |

### 暂时禁用

| 编号 | 故障内容 |
|------|---------|
| E15（原 E05）| Gen2 过电压 13 kV（AVR 故障） |
| E16（原 E06）| Gen2 相角追踪禁用（强制非同期合闸） |

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

- `ui/main_window.py::_check_fault_detection()` 现在对 `danger_level == 'accident'` 的场景只更新检测状态，不在步骤 1~4 检测阶段提前弹修复框。
- 因此 E01/E02/E03 的修复入口统一保留在第五步真实事故弹窗，不再出现前面步骤“一键修复”绕过流程的行为。

### Gen1/PT1 接线矩阵注入机制（E05–E14）

信号链：Gen1 → [G节点] → Bus → [P1节点] → PT1一次侧 → [P2节点] → PT1二次侧

**params 字段**：
- `pt1_phase_order`（必填）：PT1 二次侧净相序，如 `['B','A','C']`（BAC）或 `['A','B','C']`（隐性正序）
- `g1_loop_swap`（可选）：Gen1 机端对调端子对，如 `('A','B')`
- `g1_blackbox_order`（可选）：G1 黑盒图显示用实际机端相序
- `p1_pri_blackbox_order`（可选）：PT1 一次侧物理接线顺序（黑盒图显示用）
- `pt2_sec_blackbox_order`（可选）：PT1 二次侧输出相序（黑盒图显示用）

**注入时写入**（`inject_fault()`）：
1. `pt_phase_orders['PT1'] = pt1_phase_order` — PT1 端子净相序
2. 若有 `g1_loop_swap` **且非 E01**，同步交换 `pt_phase_orders['PT2']` — Gen1 换相影响 Bus 端子相位映射
3. E01 专属：直接设 `pt_phase_orders['PT1'] = pt_phase_orders['PT2'] = ['B','A','C']`

> `g1_blackbox_order` 才是 G1 机端物理接线的运行态真值源；`pt_phase_orders['PT2']` 是同步后的派生结果，供回路/测量计算使用。

**检测触发**：
- 步骤一：凡有 `g1_loop_swap` 的场景（E05/E09/E10/E12/E13/E14），回路断路时置 `fc.detected = True`
- 步骤四：凡有 `pt1_phase_order` 且 PT1 与 Bus 异相时置 `fc.detected = True`，覆盖步骤一无断路的 E06/E07/E11；E08（全部同相）永不触发（完全隐性设计）

**修复时**（`repair_fault()`）：`pt_phase_orders['PT1']` 和 `pt_phase_orders['PT2']` 均还原为 `['A','B','C']`。
交互黑盒修复中，`_on_confirm()` 仅在“当前场景所有可修复黑盒目标”全部恢复为 `['A','B','C']` 时才自动触发 `repair_fault()`；也就是说，Gen1/PT1 场景会检查 `g1_blackbox_order`、`pt1_pri_blackbox_order`、`pt1_sec_blackbox_order`，Gen2 场景会检查 `g2_blackbox_order`。单处修复正确时只更新运行态黑盒状态及其同步后的 `pt_phase_orders`，提示学员继续检查其他位置。

### 故障注入通用流程

1. 教师在右侧控制面板选择故障场景
2. `FaultConfig` 注入 `SimulationState`（E02 通过 `g2_blackbox_order` / `pt3_phase_order` 注入 Gen2 端子错接）
3. `PhysicsEngine` 读取故障参数扭曲测量值
4. UI 轮询 `fault_config.detected` 标志，触发警告横幅
5. 黑盒内实际修复完成 → `repair_fault()` → `repaired = True`，允许继续测试
6. E01/E02/E03 例外：修复时机在第五步合闸事故弹窗内，而非步骤 4→5 过渡时

### 流程模式策略（teaching / engineering / assessment）

- 控制器在 [app/main.py](/abs/path/c:/Users/AW57P/Documents/ThreePhase_entier/app/main.py) 统一维护 `FLOW_MODE_POLICIES`，`test_flow_mode` 不再只代表一个模式名，而是映射到一组流程规则。
- `FLOW_MODE_POLICIES` 的值已类型化为 `FlowModePolicy`，控制器通过属性访问读取策略，避免策略键名拼错后静默回落到 `False`。
- 业务层与 UI 不再直接散落写“教学 / 工程 / 考核”判断，改为读取控制器语义接口，如 `can_advance_with_fault()`、`should_block_step5_until_blackbox_fixed()`、`should_show_fault_detected_banner()`、`should_record_assessment_metrics()`。
- 三种模式的核心差异：
  - `teaching`：允许带异常完成当前步骤并继续收集故障证据
  - `engineering`：要求当前步骤结果合格后才能完成并进入下一步
- `assessment`：要求当前步骤合格才能推进；弱化诊断提示；记录完整过程事件；在第四步闭环完成时自动结算成绩，第五步不计分
  - 进入考核模式后，在第一步回路测试未完成前，母排拓扑图默认隐藏发电机与母排之间的连线；第一步完成后自动恢复显示
- 三种模式当前保持一致的策略：
  - 都要求先完成本步规定测量项
  - 都要求第五步前完成黑盒真实修复
  - 都允许黑盒查看与交互修复
 - 其中 `assessment` 额外约束：
  - 管理员快捷按钮不可用
  - 故障检测横幅与定位性提示弱化
  - 考核范围限定在步骤 1~4 + 黑盒修复闭环
  - 达到“第四步闭环完成”条件后立即生成成绩弹窗，不等待第五步
  - 场景选择弹窗采用“故障场景滚动列表 + 固定流程模式区”布局，避免场景数量增加后遮挡 `assessment` 选项

### 考核模式事件与评分

- 考核模式运行时，控制器会创建 `AssessmentSession`，并持续记录事件流：
  - `assessment_started`
  - `step_entered`
  - `step_finalize_attempted`
  - `step_completed`
  - `advance_blocked`
  - `measurement_recorded`
  - `fault_detected`
  - `blackbox_opened`
  - `blackbox_swap`
  - `blackbox_confirm_attempted`
  - `fault_repaired`
  - `hazard_action`
  - `assessment_finished`
- `fault_detected` 只通过控制器 `mark_fault_detected(step, source, ...)` 在真实发现点写入，不再由主循环 `_tick()` 以 `step=0` 兜底补记；考核中的“第几步发现异常”现在按真实步骤计分。
- `AssessmentSession` 在结算前会冻结 `state_snapshot`，评分优先读取会话快照，不再直接依赖控制器后续活体状态。
- 自动评分由 [services/assessment_service.py](/abs/path/c:/Users/AW57P/Documents/ThreePhase_entier/services/assessment_service.py) 负责，当前输出：
  - 总分 / 满分 / 是否通过
  - 分项汇总卡：流程纪律、第一步回路测试、第二步PT电压检查、第三步PT相序检查、第四步压差考核、异常识别与故障定位、黑盒修复、效率与规范性
  - `score_items` 完整计分点列表（编号 / 类别 / 状态 / 满分 / 实得 / 说明）
  - 扣分明细、关键统计指标、简短结论
- 当前评分标准已升级为 **30 个细分计分点** 的 100 分制：
  - 流程纪律 16
  - 第一步回路测试 10
  - 第二步 PT 电压检查 12
  - 第三步 PT 相序检查 12
  - 第四步压差考核 16
  - 异常识别与故障定位 14
  - 黑盒修复 12
  - 效率与规范性 8
- 30 个计分点按 `A1-H2` 输出到成绩单详细表，覆盖步骤顺序、各步记录完整性、显性/隐性故障识别、定位、黑盒修复与效率控制。
- 黑盒定位与修复评分已升级到层级级目标，不再只按设备级判断。当前使用的目标粒度为：
  - `G1.terminal`
  - `PT1.primary`
  - `PT1.secondary`
  - `G2.terminal`
- 对于 `E08` 这类隐性故障，若学员直到第四步闭环门禁触发后才意识到仍有问题，将失去“隐性故障识别 / 定位不依赖系统门禁”等关键分项，不能再拿满分。
- 第四步闭环完成的判定口径是：
  - 步骤 1~4 已完成
  - 若当前场景存在可修复黑盒目标，则 `repair_fault()` 已在真实修复后触发
  - 若当前场景不存在可修复黑盒目标（如 E04），则不再强制要求 `fault_config.repaired == True`
  - 满足后立即展示表格化“考核成绩单”窗口；第五步仅保留为后续流程，不计入考核
- 步骤 1~4 现在都能记录 `measurement_invalid` 事件，`F2`“无效重复测量控制”已有真实事件来源，不再是空转分项。
- 考核模式下，步骤 1 / 3 与物理万用表侧的异常提示会通过 `should_show_diagnostic_hints()` 自动降级为非定位性提示，系统只给状态，不直接给出接线位置答案。
- 相序仪快捷记录 `_on_record_psm()` 已改为通过控制器 `record_phase_sequence()` 调用 `PtPhaseCheckService.record_phase_sequence()`，UI 不再直接写第三步状态或直接设置 `fault_config.detected`。
- E01/E02/E03 的第五步事故弹窗修复入口现在会按 `step=5` 记录 `fault_repaired` 事件来源，不再误记为第四步修复。

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
# E02 故障: g2_blackbox_order=['A','C','B'] → PT3 端子 B→C 相、C→B 相
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
- **第四步快捷按钮** `⚡ 快捷记录全部 18 组`：管理员模式与考核模式均可显示，调用 `record_all_pt_measurements_quick()`，跳过逐组表笔测量直接写入 Gen1 + Gen2 共 18 组压差
- **现阶段重构收敛**：
  - 第四步后进入第五步前的黑盒门禁判断已下沉到控制器 `get_test_progress_snapshot()`
  - 考核模式第四步闭环后的自动结算已下沉到控制器 `finish_assessment_session_if_ready()`
  - 黑盒确认修复后的运行态写回、事件记录、自动清故障判断已下沉到控制器 `apply_blackbox_repair_attempt()`
  - `test_panel.py` 继续负责 UI 输入与显示，但不再直接承担这三类核心业务编排

### 第一步回路测试 UI 变更

路径动画（绿色流动球 / 红色断路 X）已注释（`ui/tabs/circuit_tab.py`）。表笔搭接后图面无任何动态变化，学员只能通过万用表面板读数（`0.0 Ω` / `不导通`）判断通断。

### 物理接线黑盒检查（渐进式交互修复）

"物理接线检查"区（`_add_blackbox_section`）在**第 1～4 步控制台均显示**，4 个按钮弹出图形化接线图（`_GenWiringWidget` / `_PTWiringWidget`，QPainter 绘制）：

| 按钮 | 内容 | 可修复 | 数据来源 |
|------|------|--------|---------|
| G1 机端接线 | 内部绕组（A黄/B绿/C红）→ 接线柱（U/V/W），交叉=错接 | ✅ 点击互换 | `g1_blackbox_order` / `pt_phase_orders['PT2']` |
| G2 机端接线 | 同上，按 Gen2 当前端子实际接线绘制 | ✅ 点击互换 | `g2_blackbox_order` / `pt_phase_orders['PT3']` |
| PT1 接线盒 | 六点式：电缆→一次侧 / 二次侧→测量端口，均按物理接线绘制 | ✅ 点击互换一次侧或二次侧 | `p1_pri_blackbox_order` / `pt2_sec_blackbox_order` |
| PT3 接线盒 | 同上；E03 额外显示极性反接警告 | ✅ 点击互换二次侧 | `pt_phase_orders['PT3']` / `fault_reverse_bc` |

**渐进式修复逻辑**：点击"确认修复"后，仅当 `g1_blackbox_order`、`pt1_pri_blackbox_order`、`pt1_sec_blackbox_order` **同时还原为 `['A','B','C']`** 时才调用 `repair_fault()` 清除故障；单个组件修复正确后显示蓝色"继续检查其他位置"提示，不提前清除故障。学员需对所有涉及故障的接线位置逐一修复，方可推进下一步。

---

## 当前状态

- **2026-04 黑盒接线逻辑校正**：
  - G1 / PT1 黑盒对话框现在读取的是控制器运行态黑盒状态，而不是 `fault_scenarios.py` 中的静态 `params` 快照。
  - G1 运行态真值源为 `ctrl.g1_blackbox_order`；`pt_phase_orders['PT2']` 仍用于回路/测量计算，但它是由黑盒状态同步得到的派生结果，不再应视为唯一物理真值源。
  - PT1 黑盒运行态真值源为 `ctrl.pt1_pri_blackbox_order` 与 `ctrl.pt1_sec_blackbox_order`；`pt_phase_orders['PT1']` 是由 G1 Bus 相序 + PT1 一次侧 + PT1 二次侧组合推导出的净相序。
  - PT1 黑盒支持一次侧、二次侧分别交互修复，不再是“仅二次侧可修复”。
  - `has_unrepaired_wiring_fault()` 与黑盒自动清故障判断已经扩展到 G2：E02 场景下 `g2_blackbox_order` 也会参与“是否仍有未修复接线故障”的判断。
  - `repair_fault()` 的自动触发条件已改为：`g1_blackbox_order`、`pt1_pri_blackbox_order`、`pt1_sec_blackbox_order` 三者都恢复为 `['A','B','C']`；不再仅凭 `pt_phase_orders['PT1']` / `['PT2']` 的净结果判定。
  - 对于 E06 / E10，此前文档里容易混淆的 PT1 二次侧黑盒状态现已固定为正常 `['A','B','C']`，故障只在 PT1 一次侧。

- **已完成并验证**：隔离母排模式完整五步骤仿真；E01 / E02 场景全步骤测试通过
- **已实现待验证**：E03 步骤 5；E04 步骤 2；E05–E14 物理注入；物理接线黑盒检查交互修复（第 1～4 步均显示，渐进式逐组件修复）
- **最新修复**：E01 double-swap bug；黑盒 params 键名统一（`g1_blackbox_order` / `p1_pri_blackbox_order` / `pt2_sec_blackbox_order` / `g2_blackbox_order`）；PT1 一次侧/二次侧独立修复；Gen2 机端接线黑盒改为终端接线级可交互修复；黑盒对话框运行态回显修复；`teaching / engineering / assessment` 三模式差异已收敛到 `FLOW_MODE_POLICIES`；考核模式事件流与自动评分已接入
- **现阶段重构**：`FlowModePolicy` 已类型化；`loop_test_service.py` 与 `pt_phase_check_service.py` 已先改为通过控制器语义方法写回状态；控制器已新增 `get_test_progress_snapshot()`、`get_blackbox_runtime_state()`、`finish_assessment_session_if_ready()`、`apply_blackbox_repair_attempt()` 作为最小只读/编排接口，用于收敛 `test_panel.py` 的业务判断
- **暂时禁用（代码已注释保留，开发中）**：E15（Gen2 过电压 AVR 故障）；E16（强行非同期合闸）


‘’‘

全量代码审查报告
1. Bug 与潜在缺陷
🔴 严重 — _on_record_psm() 71 行不可达死代码
文件：ui/test_panel.py:1406-1477


1405:        self._tp_s3_rec_btns[pt_name].setEnabled(False)
1406:    return                    # ← 此处提前返回
1407:    # 把相序仪结果写入 pt_phase_check_state（逐相批量写入）
1408:    state = self.ctrl.pt_phase_check_state
       ...                       # ← 以下 71 行全部不可达
1477:        self._tp_s3_rec_btns[pt_name].setEnabled(False)
原因是该逻辑已被重构到 record_phase_sequence() 服务方法中，但旧代码未清理，留下了一个 return 和整段残留逻辑。

修复：删除 1406 行的 return 以及 1407-1477 的全部残留代码。

🟡 警告 — _UI_NODES[n1] 无防御性守卫
文件：services/_physics_measurement.py:144


if n1 and n2:
    info1, info2 = _UI_NODES[n1], _UI_NODES[n2]   # KeyError 风险
n1/n2 来自 sim.probe1_node/probe2_node，正常情况下由 UI 点击事件设置为合法 NODES 键。但若有外部代码设置非法值，将直接抛 KeyError。

修复：


if n1 and n2 and n1 in _UI_NODES and n2 in _UI_NODES:
🟡 警告 — _resolve_terminal_actual_phase() 无守卫的 .index()
文件：services/_physics_measurement.py:101


idx = ('A', 'B', 'C').index(terminal)   # terminal 不是 A/B/C 时 ValueError
此方法被 _update_multimeter() 和 record_all_pt_measurements_quick() 间接调用，调用链上没有对 terminal 做前置校验。虽然目前数据流上不会出错，但该函数是公共接口，缺乏防御。

修复：


if terminal not in ('A', 'B', 'C'):
    return terminal   # 或 raise ValueError
idx = ('A', 'B', 'C').index(terminal)
🟡 警告 — 4 处 except Exception: pass 静默吞异常
文件：ui/test_panel.py:1292-1295、1371-1374、1383-1386


try:
    self.connect_phase_seq_meter(pt_name)   # Mixin 方法，可能不存在
except Exception:
    pass   # 完全静默——如果是 MRO 问题之外的 bug 也会被吞掉
这些是跨 Mixin 调用相序仪的防御代码。问题在于 Exception 过于宽泛——不仅捕获 AttributeError（Mixin 不存在），也捕获了所有运行时异常。

修复：缩窄为 except AttributeError: 或至少添加 traceback.print_exc()。

🟡 警告 — _resolve_terminal_actual_phase 私有属性访问
文件：ui/test_panel.py:1393-1396


try:
    seq = self.phase_seq_meter._sequence
except Exception:
    seq = 'unknown'
直接访问 _sequence 私有属性，且用异常捕获代替存在性检查。

修复：seq = getattr(self.phase_seq_meter, '_sequence', 'unknown')

2. 代码一致性与规范
🟡 警告 — domain/constants.py 在领域层执行 matplotlib 副作用
文件：domain/constants.py:1-16


import matplotlib
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', ...]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 100
...
domain/ 是纯领域层，不应有任何 UI 依赖。所有 matplotlib 配置应移到 ui/ 层（如 ui/styles.py 或 ui/__init__.py）。这也意味着未来迁移到 React+Tauri 时 domain/ 层无法被干净地复用。

🟡 警告 — params 键名与实例变量名不一致
文件：domain/fault_scenarios.py:17-21 ↔ app/main.py:175-176

params 键（fault_scenarios.py）	实例变量名（app/main.py）	含义
p1_pri_blackbox_order	pt1_pri_blackbox_order	PT1 一次侧
pt2_sec_blackbox_order	pt1_sec_blackbox_order	PT1 二次侧
虽然已在文件头部加了命名约定注释，但 pt2_sec 在字面上仍然像是 PT2 的键。未来增加 E15+ 场景时极易用错。

🟢 建议 — E15/E16 注释代码块未清理
文件：

domain/fault_scenarios.py:520-577（58 行注释代码）
services/_physics_arbitration.py:274-277（4 行）
services/_physics_measurement.py:251-256, 322-344（散落 E05 残留判断）
ui/tabs/circuit_tab.py:770-778（回路动画被注释禁用）
应该移到独立的 feature 分支，或在注释中注明跟踪 issue 编号。

3. 架构与设计
🟡 警告 — _update_multimeter() 271 行巨型函数
文件：services/_physics_measurement.py:124-395

此函数内含三大分支（回路测量 / PT 内线电压 / PT 间压差），每个分支约 80-90 行。应拆分为：

_handle_loop_measurement()
_handle_intra_pt_measurement()
_handle_cross_pt_measurement()
🟡 警告 — UI 层直接修改 sim_state
文件：ui/test_panel.py ~880-886


def _update_ratio(...):
    ratio = pri / sec           # 业务计算
    setattr(self.ctrl.sim_state, _a, ratio)   # UI 直接写 sim_state
PT 变比计算和写入应委托给 controller 方法，保持 UI → Controller → State 的单向数据流。

🟢 建议 — domain/constants.py 底部反向导入
文件：domain/constants.py:36-38


from domain.enums import SystemMode
AVAILABLE_MODES = [SystemMode.ISOLATED_BUS, ...]
constants.py 导入 enums.py 中的类，这在当前单向依赖下可以工作，但若 enums.py 未来需要引用常量，会形成循环导入。AVAILABLE_MODES 更适合放在 enums.py 中。

4. 可维护性
🟢 建议 — _physics_arbitration.py 中的 pass 语句
文件：services/_physics_arbitration.py ~48-59


elif self.bus_reference_gen == 1 and g1_on_bus:
    pass                       # ← 功能上正确但增加理解成本
elif self.bus_reference_gen == 2 and g2_on_bus:
    pass
这两个 pass 分支的含义是"保持当前引用不变"。加一行注释就能消除歧义：


elif self.bus_reference_gen == 1 and g1_on_bus:
    pass   # 基准不变，保持 Gen1
5. 回归风险
🟡 警告 — inject_fault() 中场景排除列表手动维护
文件：app/main.py:1233


if scenario_id.startswith('E0') and scenario_id not in ('', 'E01', 'E02', 'E03', 'E04'):
    self.sync_pt1_blackbox_to_phase_orders()
未来增加新场景时，开发者必须记住手动更新这个排除列表。如果遗漏，新场景可能错误地触发 PT1 同步。

修复建议：改为正向匹配（检查 params 中是否含有特定键）代替反向排除。



’‘’


