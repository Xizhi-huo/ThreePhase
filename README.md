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
│   ├── styles.py                    # 浅色主题入口与全局 QSS 设计令牌
│   ├── test_panel.py                # 测试模式控制面板（第 1～5 步控制台）
│   ├── panels/
│   │   └── control_panel.py        # 右侧控制面板 Mixin
│   ├── tabs/
│   │   ├── _step_style.py          # 步骤页通用样式辅助
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
| 3. PT 相序检查 | `PtPhaseCheckService` | 同步骤 2 | PT1/PT3 相序表仅显示正序 / 反序 / 异常；记录表与快捷记录均按工程口径写入 |
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
  - 随机故障考核会在第四步成绩单弹出前先要求学员提交最终场景判断
  - 第四步未完成时点击“完成第四步测试”不再提示缺项，而是直接记入违规推进事件并影响评分
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
- 额外扣分当前包括：
  - 前两步每打开一次 PT 黑盒，额外扣 10 分
  - 随机故障考核中最终场景判断错误，额外扣 10 分
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

### UI 现代化（2026-04）

当前 UI 继续保留 `PyQt5 + QWidget` 体系，不引入新的控件框架，采用“浅色主题 + 设计令牌 + 语义属性 QSS”的渐进式迭代方式：

- **主题基线**
  - 浅色优先，当前不提供深色主题
  - 中性专业风
  - 标准信息密度
  - 青蓝主色，圆角统一为 8px
  - 保留系统原生标题栏
- **主题入口**
  - `ui/styles.py` 提供全局令牌、组件 QSS、语义属性样式与 `apply_app_theme()`
  - 若运行环境安装 `qdarkstyle`，会优先叠加 light palette；未安装时自动回退到项目内置浅色样式
- **语义化样式策略**
  - 控件不再大量直接拼接内联 `setStyleSheet()`，而是通过 `property` 驱动样式
  - `ui/panels/control_panel.py` 收敛了按钮、badge、toggle、卡片的公共样式辅助
  - `ui/tabs/_step_style.py` 负责步骤页壳层、动作按钮、状态文本、记录值等通用样式辅助
  - `ui/test_panel.py` 通过反馈标签、说明文字、行容器、弹窗骨架等语义 helper 收口高频样式
- **本轮已覆盖区域**
  - 主窗口、主 Tab、右侧控制面板
  - `test_panel.py` 顶部栏、底部栏、步骤反馈、管理员区、成绩单与黑盒弹窗公共骨架
  - Tab 2～6 的页面壳层与主要动作按钮
  - 第 1/2/3 步中的高频动态文本、记录值、状态提示
- **当前边界**
  - matplotlib 图表区目前主要完成外围容器与主题接入，未对波形绘图区做深度视觉统一
  - 仍保留少量强语义或强动态的局部样式，例如步骤圆点、部分成绩单强调卡片、个别 PT 分组提示色块

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

**渐进式修复逻辑**：点击黑盒底部按钮后，控制器始终先写回当前接线状态并记录 `blackbox_confirm_attempted / blackbox_swap` 事件；仅当当前场景所有可修复目标都恢复为 `['A','B','C']` 时才自动触发 `repair_fault()`。考核模式下黑盒不再显示“修复成功 / 仍异常 / 继续检查其他位置”等结果提示，只保留“接线已保存，请返回外部流程复测”的中性反馈。

---

## 当前状态

- **2026-04 UI 现代化收敛**：
  - 主题路线已固定为“浅色主题 + 语义属性 QSS + 渐进式改造”，当前不做深色主题。
  - `ui/styles.py` 已升级为全局主题入口；`ui/tabs/_step_style.py` 已作为步骤页公共样式层加入。
  - 主窗口、主 Tab、右侧控制面板、测试面板、步骤页壳层和主要弹窗已完成第一轮统一。

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

全面代码审查：三相电源同步模拟器

### 1. 架构概览


#### 设计模式

* **Mixin 组合 (物理引擎):** `PhysicsEngine` 继承自 4 个 mixin (`WaveformMixin`, `ArbitrationMixin`, `ProtectionMixin`, `MeasurementMixin`)。每个 mixin 都在独立的文件中。
* **Mixin 组合 (UI):** `PowerSyncUI` 继承自 8 个以上的 mixin 以及 `QMainWindow`。每个选项卡和面板都是一个 mixin。
* **中介者/控制器 (Mediator/Controller):** `PowerSyncController` 充当中央中介者。所有服务、物理引擎和 UI 都引用 `ctrl`。服务将跨领域操作委托给控制器。
* **快照/DTO (Snapshot/DTO):** `RenderState` 数据类提供从物理引擎到 UI 的不可变帧快照。边界清晰。
* **策略对象 (Policy Object):** `FlowModePolicy` 冻结数据类参数化了教学/工程/评估行为。

#### 数据流向

```
QTimer (33ms) → ctrl._tick()
  → physics.update_physics()    [读取/写入 ctrl.sim_state]
  → physics.build_render_state() → RenderState
  → ui.render_visuals(rs)       [直接读取 RenderState + ctrl.*]
```

---

### 2. 代码质量问题

#### 2.1 废弃代码 / 未使用的导入

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| LOW | `app/main.py:21` | `from dataclasses import dataclass` — 已使用，但第 27 行的 `from typing import Any, Dict, Optional` 导入了仅间接使用的 `Any`。`Dict` 和 `Optional` 被使用了。 |
| LOW | `app/main.py:20` | `import math` — 仅在第 1034 行使用过一次 (`math.degrees`)。可以使用 `np.degrees`。 |
| LOW | `app/main.py:22` | 顶部 `import random`，以及 `control_panel.py:15` 中的 `import random as _random` — 在不同的模块中，但命名不一致值得注意。 |
| MEDIUM | `domain/enums.py:9-14` | `AVAILABLE_MODES` 列出了 4 种模式，但只有 `ISOLATED_BUS` 是有效的。其他 3 种 (`ISLAND`, `GRID_TIED`, `BLACKSTART`) 都是带有 `"(预留)"` 标记的存根，并在 UI 中被禁用。这些是废弃的功能存根。 |

#### 2.2 命名不一致

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | 贯穿各处 | 语言混合：变量名和文档字符串混合了中文和英文。注释主要使用中文，但代码标识符使用英文。这是有意为之（教育背景），但方法命名不一致 —— 例如，不同服务中的 `_set_loop_test_feedback` 与 `_set_feedback`。 |
| MEDIUM | `app/main.py:1197` | 旧的键名 `p1_pri_blackbox_order` / `pt2_sec_blackbox_order` 与 `pt1_pri_blackbox_order` / `pt1_sec_blackbox_order` 共存。回退逻辑在多处重复。 |
| LOW | `services/_physics_measurement.py` | 局部变量如 `_sim_r`, `_pt_ratio`, `_fc_e04` 不一致地使用了下划线前缀（这些不应是私有的模块级名称，而只是局部变量）。 |

#### 2.3 函数过长 / 职责过多

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| HIGH | `app/main.py` `PowerSyncController` | 上帝类 (God Class)：约 1270 行。它拥有 sim_state，委托给 6 个服务，管理故障注入/修复，评估会话生命周期，黑盒接线修复，PT 相位解析，断路器门控以及 UI 回调。这是可维护性的最大风险。 |
| HIGH | `services/assessment_service.py:19-597` | `build_result()` 是一个 560 多行的单一方法。极难测试或修改。所有 30 个评分项、惩罚计算和总结生成都在一个函数中。 |
| MEDIUM | `ui/main_window.py` `show_e01/e02/e03_accident_dialog` | 三个几乎相同、各 100 多行的对话框方法（总计约 390 行）。它们仅在故障描述文本上有所不同。应参数化为一个单一方法。 |
| MEDIUM | `services/_physics_measurement.py` `_update_multimeter` | 65 行的方法，包含深度嵌套的条件分支，用于处理回路/跨PT/无效状态等。 |

#### 2.4 缺失 / 不充分的错误处理

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | `app/main.py:1384-1392` | `_tick()` 捕获所有异常并使用 `traceback.print_exc()` — **静默吞噬**。物理引擎崩溃会打印到控制台，但在 GUI 中不可见。模拟会静默产生陈旧的帧。 |
| MEDIUM | `app/main.py:1376-1379` | `rebuild_circuit_view()` 被包裹在裸露的 `except Exception: traceback.print_exc()` 中。电路图可能会在刷新时静默失败。 |
| LOW | `ui/main_window.py:133-136` | `setTabVisible` 被包裹在裸露的 `except AttributeError: pass` 中。为了 Qt 版本的兼容性这是可以接受的，但应该添加注释说明需要兼容哪个版本。 |

#### 2.5 静默故障风险

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| HIGH | `services/_physics_core.py:131-133` | `interval_dt = max(self.animation_time - prev_animation_time, self.wave_sample_dt)` — 如果 `animation_time` 倒退（例如浮点漂移或重置），`interval_dt` 被限制在 `wave_sample_dt` 而不是被检测为错误。结合 `np.linspace`，这可能产生失真的波形。 |
| MEDIUM | `services/_physics_measurement.py:66-73` | `_ema_update` 通过 `hasattr` 延迟初始化 `_meter_ema_dict`。如果另一个 mixin 引入了同名的属性，将会发生静默冲突。 |

---

### 3. 架构坏味道

#### 3.1 紧耦合

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| CRITICAL | `services/_physics_protection.py:189-231` | **物理引擎直接调用 UI**：`self.ctrl.ui.show_e01_accident_dialog()` 是从物理引擎的断路器逻辑内部调用的。这意味着物理帧更新可能会在模态对话框上阻塞。物理引擎应该触发一个事件/标志；UI 应该轮询它。 |
| HIGH | `app/main.py:1059` | 控制器直接操作 UI：`self.ui.tab_widget.setCurrentIndex(5)`。控制器不应该知道选项卡的索引。 |
| HIGH | `app/main.py:1260-1263` | 针对 E04 的 `inject_fault` 直接触及 UI 数字框控件：`_rows['pt3_ratio']` → `sec_spin.setValue(93)`。控制器不应该接触 UI 控件。 |
| MEDIUM | 所有服务 | 每个服务都持有 `self._ctrl`，并通过回调控制器来完成所有操作（例如 `self._ctrl.physics.meter_status`）。服务层不是真正独立的 —— 它与控制器内部结构紧密耦合。 |

#### 3.2 上帝类

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| CRITICAL | `app/main.py` `PowerSyncController` | 处理：模拟状态的所有权，6 个服务的编排，故障注入/修复，黑盒修复，评估会话管理，PT 相位解析，流程策略评估，断路器门控，硬件操作，UI 通知。约有 85+ 个公共方法。 |
| HIGH | `ui/main_window.py` `PowerSyncUI` | 继承自 9 个 mixin。MRO（方法解析顺序）很复杂。mixin 之间的任何方法名冲突都是静默错误。 |

#### 3.3 循环依赖风险

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | controller ↔ UI ↔ physics | `ctrl` 持有 `physics` 和 `ui`。`physics` 持有 `ctrl` (用于 `ctrl.sim_state`, `ctrl.pt_phase_orders`, `ctrl.ui.show_*`)。`ui` 持有 `ctrl`。这个三角形是一个循环引用图。Python 的垃圾回收器会处理它，但这使得隔离测试变得不可能。 |
| LOW | `domain/node_map.py:1-4` | 注释写着 "独立为单独模块，避免 physics ↔ ui 循环导入" — 证明团队已经遇到过循环导入问题。 |

#### 3.4 关注点混合

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| CRITICAL | `services/_physics_protection.py:189-231` | 物理引擎直接显示 UI 对话框 (`self.ctrl.ui.show_e01_accident_dialog()`)。物理计算绝对不应该触发模态 UI。 |
| HIGH | `app/main.py:1260-1263` | 控制器在故障注入期间操作 UI 数字框值。业务逻辑应该更新模型；UI 应该观察模型变化。 |
| MEDIUM | `ui/panels/control_panel.py:253-254` | UI 直接设置模型状态：`lambda v: setattr(c.sim_state, 'remote_start_signal', v)`。没有验证边界。 |

---

### 4. 物理引擎完整性

#### 4.1 模拟循环鲁棒性

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| HIGH | `app/main.py:1384-1392` | 主 `_tick()` 将整个物理+渲染包裹在 `try/except` 中。任何子步骤（波形，仲裁，保护，测量）的崩溃都会静默导致**整帧失败**，包括渲染。屏幕上会显示旧的状态。如果错误是持续的，模拟器在视觉上冻结，但实际上仍“活着”。 |
| MEDIUM | `services/_physics_core.py:60-64` | `_advance_time` 将 `animation_time` 增加 `0.002 * sim.sim_speed`。在最大速度（10x，滑块最大值 1000/100）下，这相当于每 33ms 帧 0.02s。波形历史使用 `np.linspace` 进行插值，但是高速会为 50Hz 信号产生每帧 1 个以上的样本 —— 当 `sim_speed > ~5x` 时可能会产生混叠。 |
| LOW | `services/_physics_arbitration.py:127` | `self.dead_bus_timer += 0.033 * sim.sim_speed` — 硬编码的 0.033s 假定恰好为 30fps。如果定时器触发较晚（系统负载重），死母线倒计时就会漂移。应该使用实际消耗的时间。 |

#### 4.2 故障注入的边缘情况

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | `app/main.py:1265-1278` | `inject_fault` 在 E01/E02 特定处理**之后**应用 E05–E14 的通用接线。对于 E01，第 1252 行设置 `g1_blackbox_order = ['B','A','C']`，但第 1265 行随后将其**覆盖**为 `fc.params.get('g1_blackbox_order', self.g1_blackbox_order)`。由于 E01 参数没有 `g1_blackbox_order`，它会回退到已经设置的值。这属于巧合有效，但很脆弱 —— 如果向 E01 的参数中添加 `g1_blackbox_order`，将会静默覆盖正确的值。 |
| LOW | `domain/fault_scenarios.py`: E08 | E08 是一个“完全隐藏”的故障 (`affected_steps: []`, `detection_step: None`)。评估打分通过 `hidden_fault` 逻辑处理，但注释说通过测量无法检测 —— 评估仍然期望学生检查黑盒。如果学生正常完成所有 5 个步骤，网关会阻挡他们，没有任何可见证据说明原因。 |

#### 4.3 相序逻辑

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| LOW | `services/_physics_measurement.py:99-112` | `_resolve_terminal_actual_phase` 正确地仅对 PT3 应用了 `fault_reverse_bc`。对于 B↔C 交换逻辑是健全的。 |
| LOW | `app/main.py:714-750` | `get_pt_phase_sequence` 正确处理了 g2b/g2c 键交换的 `fault_reverse_bc`。对于 E03 (PT3 A反接) 返回 `FAULT` 是正确的 —— 真实的相序表无法对单相反接信号进行分类。 |

#### 4.4 保护状态机

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | `services/_physics_protection.py:165-198` | 模式 "stop" 无条件断开断路器 (行 166-167)。但是，如果发电机先前已闭合，且模式由于 UI 竞争条件更改为 "stop"，断路器将在没有继电保护消息的情况下断开。继电消息在第 69-72 行设置，即在过流检查**之前**但模式-"stop"逻辑**之后**，因此 "monitoring" 消息会覆盖任何 stop-trip 消息。 |
| MEDIUM | `services/_physics_protection.py:256-266` | 闪烁帧使用 `setattr(self, flash_attr, 15)` 并每帧递减。在 30fps 下，这是 0.5 秒的闪烁。但如果模拟暂停，闪烁仍会递减 (暂停只停止 `_advance_time`，不停止 `_update_breaker_logic`)。闪烁在暂停期间会过期。 |

---

### 5. PyQt5 特定问题

#### 5.1 信号/槽问题

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| CRITICAL | `services/_physics_protection.py:189` | `self.ctrl.ui.show_e01_accident_dialog()` 从 `_update_breaker_state()` 调用，后者运行在 `update_physics()` 内，后者又运行在 `_tick()` 内，而 `_tick()` 是一个 QTimer 槽。调用 `.exec_()` (模态对话框) 会阻塞定时器回调。在对话框打开期间，**没有物理帧被计算**，没有 UI 更新发生，所有 QTimer 事件排队。关闭对话框后，排队的定时器会快速连续触发。 |
| MEDIUM | `ui/panels/control_panel.py:409-429` | 滑块的 `valueChanged` 和 LineEdit 的 `editingFinished` 都会更新同一个模型属性。`_update_generator_buttons` 中的 `blockSignals(True/False)` 保护措施可防止无限循环，但 LineEdit 的 `editingFinished` + `returnPressed` 都连接了 —— 按 Enter 会触发两次，导致重复写入。 |
| LOW | `ui/panels/control_panel.py:158` | `rb.toggled` 在选中和取消选中时都会触发。处理程序检查是否被选中 (`if checked`)，这没错，但会产生不必要的调用。 |

#### 5.2 组件生命周期

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | `ui/main_window.py:216-265` | `_show_blackbox_required_dialog` 每次被调用时都创建一个 `QDialog(self)`。对话框执行后被垃圾回收。这是可接受的，但在快速点击下，理论上可能会创建多个对话框实例。 |
| LOW | `ui/test_panel.py:32-167` | `_GenWiringWidget` 和 `_PTWiringWidget` 使用 `setFixedSize()`。它们无法适应不同的 DPI 或窗口大小。 |

#### 5.3 线程安全

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| LOW | N/A | 所有物理运算都在 UI 线程运行（通过 QTimer）。从线程角度来看这是安全的（无竞争条件），但意味着繁重的物理计算可能导致 UI 卡顿。在 33ms 的间隔下，预算很紧张。Numpy 操作是向量化的，所以对于 200 个数据点可能没问题，但增加更多生成器或更高分辨率可能会导致掉帧。 |

#### 5.4 资源泄漏

| 严重程度 | 位置 | 问题 |
| :--- | :--- | :--- |
| MEDIUM | matplotlib 画布 | 波形图和电路图选项卡创建了嵌入 Qt 的 matplotlib 图形。对当前活动选项卡每帧调用 `draw_idle()`。matplotlib 图形永远不会显式关闭。在很长的会话中没问题（图形被复用），但如果重建选项卡，旧的图形可能会泄漏。 |

---

### 6. 回归风险分布图

**排名前 5 的最脆弱区域**

1.  **故障注入/修复链 — `app/main.py:1231-1336`**
    * **原因:** `inject_fault` 和 `repair_fault` 在每个场景下手动设置/重置 8 个以上的状态变量 (`pt_phase_orders`, `g1_blackbox_order`, `pt1_pri_blackbox_order`, `fault_reverse_bc`, UI 数字框值)。添加 E15 需要修改此方法并确保 `repair_fault` 中所有的清理路径都更新。
    * **缺失保障:** 无自动化测试。无声明式注入系统 —— 所有逻辑都是过程化的 if/elif 链。在 `repair_fault` 中遗漏一个清理步骤，就会在“修复”后留下幽灵故障效果。
2.  **物理 → UI 对话框耦合 — `services/_physics_protection.py:185-231`**
    * **原因:** 物理断路器逻辑直接调用 `self.ctrl.ui.show_e0X_accident_dialog()`。UI 的任何重构（重命名方法、更改对话框流程）都会静默破坏物理行为。模态对话框冻结模拟循环。
    * **缺失保障:** 物理层与 UI 层之间没有接口/协议。没有事件总线或回调注册。
3.  **PowerSyncUI 中的 Mixin 命名冲突 — `ui/main_window.py:54-65`**
    * **原因:** 9 个 mixin 共享一个命名空间。如果两个 mixin 定义了同名的方法，Python 的 MRO 会静默选择一个。没有 `__init_subclass__` 保护或命名约定来防止这种情况。
    * **缺失保障:** 跨 mixin 无检测方法名冲突的 Lint 规则或测试。
4.  **`_compute_pt1_net_order` 级联 — `app/main.py:1148-1159`**
    * **原因:** PT1 的有效相序是通过链接 3 个排列层 (`g1_blackbox_order` → `pt1_pri_blackbox_order` → `pt1_sec_blackbox_order`) 计算得出的。对任何一层的修改都需要通过 `sync_pt1_blackbox_to_phase_orders()` 重新同步。多个调用者在不同时间调用它；遗漏一个同步调用会产生不一致的 PT1 读数。
    * **缺失保障:** 无不变性检查来确保 `pt_phase_orders['PT1']` 始终等于计算出的净相序。
5.  **评估打分巨石 — `services/assessment_service.py:19-597`**
    * **原因:** 一个 560 行的方法计算所有 30 个打分项。事件流的任何结构性更改（重命名事件、更改负载）都会静默改变得分。该方法没有单元测试，并且依赖确切的事件类型字符串。
    * **缺失保障:** 没有事件类型名称的常量。对事件负载没有 Schema 验证。单个打分项没有单元测试。

---

### 7. 优先级改进建议

#### 紧急 (CRITICAL)

| # | 发现点 | 具体修复建议 |
| :--- | :--- | :--- |
| C1 | 物理层调用 UI 对话框 (`_physics_protection.py:189-231`) | 将 `self.ctrl.ui.show_e0X_accident_dialog()` 替换为设置一个标志：`self.ctrl.pending_accident = 'E01'`。在 `render_visuals()` 或 `_tick()` 中，检查该标志并在物理计算**完成后**显示对话框。这将解耦物理与 UI 并防止定时器阻塞。 |
| C2 | 上帝控制器 (`app/main.py:143`, 1270+ 行) | 将故障管理提取到一个 `FaultManager` 类中 (注入/修复/黑盒/接线顺序)。将评估生命周期提取到一个独立的协调器中。控制器应仅负责将服务连接起来，而不应包含业务逻辑。 |

#### 高级 (HIGH)

| # | 发现点 | 具体修复建议 |
| :--- | :--- | :--- |
| H1 | 滴答 (tick) 静默失败 (`app/main.py:1384-1392`) | 添加一个帧错误计数器。如果 >N 个连续帧失败，在 UI 中显示一个非模态的错误横幅。将回溯日志记录到文件。考虑将物理和渲染分成两个 try/except 块，这样渲染失败就不会跳过物理计算。 |
| H2 | 三重重复的事故对话框 (`main_window.py:268-657`) | 重构为 `_show_accident_dialog(scenario_id)`，从 `SCENARIOS[scenario_id]` 中读取标题/描述/症状/修复内容。消除约 300 行重复代码。 |
| H3 | 控制器触及 UI 组件 (`app/main.py:1260-1263`) | 控制器应该发出一个信号或更新 `sim_state.pt3_ratio`；UI 应该观察模型并在 `render_visuals()` 中更新数字框。 |
| H4 | 评估 `build_result` 巨石 (`assessment_service.py:19-597`) | 拆分成按类别的辅助方法：`_score_flow_discipline()`, `_score_loop_test()` 等。在共享模块中定义事件类型常量。按类别添加单元测试。 |
| H5 | 硬编码的定时器间隔 (`_physics_arbitration.py:127`) | 从 `_tick()` 传递实际的 `dt`，而不是假定为 `0.033`。计算 `dt = current_time - last_tick_time`。 |

#### 中级 (MEDIUM)

| # | 发现点 | 具体修复建议 |
| :--- | :--- | :--- |
| M1 | 遗留的参数键名回退 (`p1_pri_blackbox_order`, `pt2_sec_blackbox_order`) | 将所有场景参数迁移到规范名称。移除回退查找逻辑。在 `inject_fault` 中添加一个验证流程，对无法识别的参数键发出警告。 |
| M2 | 闪烁定时器在暂停期间递减 | 保护闪烁递减逻辑：`if not sim.paused: setattr(self, flash_attr, getattr(self, flash_attr) - 1)`。 |
| M3 | `.gitignore` 中缺少 `__pycache__` | 将 `__pycache__/` 和 `*.pyc` 添加到 `.gitignore`。目前在 git status 中被追踪。 |
| M4 | `_ema_update` 通过 `hasattr` 延迟初始化 | 在 `PhysicsEngine.__init__()` 中显式初始化 `_meter_ema_dict = {}`。 |
| M5 | 缺少测试套件 | 优先级：为故障注入 → 检测 → 修复全流程添加集成测试。为 `assessment_service.build_result()` 添加单元测试。 |

#### 低级 (LOW)

| # | 发现点 | 具体修复建议 |
| :--- | :--- | :--- |
| L1 | `AVAILABLE_MODES` 包含 3 个死存根 | 移除或注释掉无功能的模式，以减少混淆。 |
| L2 | `_GenWiringWidget`/`_PTWiringWidget` 使用固定大小 | 使用 `sizeHint()` 和 `minimumSizeHint()` 配合宽高比策略，以实现更好的 DPI 缩放。 |
| L3 | gen 滑块上 `editingFinished` + `returnPressed` 的双重连接 | 移除 `returnPressed` 的连接；`editingFinished` 已经涵盖了 Enter 键。 |
| L4 | `app/main.py` 中的 `sys.path.insert(0, ...)` | 替换为合适的包设置 (`pyproject.toml` 或 `setup.py`)，以便可以干净地安装和导入该项目。 |


’‘’
