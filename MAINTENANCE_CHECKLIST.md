# 维护与重构清单 v2

最后更新：`2026-04-16`

用途：
- 给人看：明确当前项目的维护边界、阶段目标、已完成进度。
- 给 AI 看：后续新对话先读本文件，再决定下一轮该做什么，不再重复讨论方向。

## 1. 维护边界总原则

### 1.1 总目标
- 当前阶段 `不新增功能`。
- 当前阶段只做两类事：
  - 提高代码可读性
  - 提高代码可靠性
- 重构的终极目的：`剥离 UI 与业务/物理/评分逻辑`，使核心引擎可独立测试，UI 可被整体替换。

### 1.2 文件大小参考标准

| 等级 | 标准 | 行动 |
|---|---|---|
| 健康 | `<= 500` 行 | 无需操作 |
| 需要审查 | `501 - 800` 行 | 评估是否存在多职责 |
| 必须拆分 | `> 800` 行 | 列入本轮或下轮攻坚目标 |

说明：
- 纯数据声明文件（如 `fault_scenarios.py`、`styles.py`）不适用此标准，除非其中混入了逻辑代码。
- 行数下降是接口隔离的副产品，不是目标本身。**核心度量标准是"模块间接口是否隔离"。**
- 大文件基线使用脚本入口：`python scripts/report_large_files.py --top 10`。

### 1.3 工程边界红线
- 不再往大文件里继续堆新逻辑。
- 不再新增上帝类。
- 不再新增巨石函数（单函数 > 80 行应审查）。
- 不再新增 `physics -> ui` 的直接调用。
- 不再新增 `controller -> 具体 UI 控件` 的直接写入。
- 不再新增大范围 `try/except Exception` 静默吞异常。
- 不再新增长期保留的过渡死代码。
- 每次重构必须同步删除旧实现，不能长期双轨并存。
- Controller 只负责命令下发和编排，禁止 `ctrl.xxxWidget.setText()/setValue()` 一类直接控件写入。
- 重构核心逻辑前，必须先具备最小黑盒回归验证能力；没有验证保护的重构，不进入核心逻辑。

### 1.4 接口隔离原则
- Service 不再新增对 `self._ctrl` 的穿透式属性访问（如 `self._ctrl.sim_state.gen1.xxx`）。
- 每个 Service 的公开方法应只接收它真正需要的数据，而非整个 ctrl。
- 过渡期做法：新增或修改的 Service 方法，优先改为显式参数传入，旧方法暂时保留。
- 最终目标：Service 的构造函数只接收自己负责的 State 切片 + 有限的回调接口，不再持有 ctrl 引用。
- 验证方式：新增的 Service 方法中 `self._ctrl` 引用数不增长。

### 1.5 单向数据流规范

严格的数据流方向：

```
User Action (槽函数)
    │
    ▼
Controller.command_xxx()        ← UI 只调用 Controller 的命令方法
    │
    ▼
Service / PhysicsEngine         ← Controller 委托给 Service 处理
    │
    ▼
State 对象变更                  ← Service 只写入自己负责的 State
    │
    ▼
_tick() → build_render_state()  → RenderState
    │
    ▼
UI.render_visuals(rs)           ← UI 只从 RenderState 读取并刷新
```

违禁模式（新代码中禁止）：
- UI 槽函数里直接修改 `sim_state`。
- Service 里读取其他 Service 的状态。
- UI 里调用 Service 的内部方法。
- 任何组件绕过 Controller 直接修改状态。

所有后端计算结果只能写入 `SimulationState / RenderState / AssessmentResult` 这类状态对象。
UI 只能读取状态刷新自己，不能反向污染业务状态。

### 1.6 每轮迭代固定动作
- 每轮有且只有一个主攻目标。做深做透，不蜻蜓点水。
- 新实现落地后，同轮就删旧实现。
- 每轮结束必须更新本文件（§9 轮次历史 + §10 下一轮起点）。
- 每轮结束必须通过回归清单（§8）验证。

### 1.7 禁止事项
- 禁止"顺手加功能"。
- 禁止"只抽函数，不删旧逻辑"。
- 禁止"因为赶进度继续把逻辑塞回 `app/main.py` 或 `ui/test_panel.py`"。
- 禁止"只搬方法，不定义接口边界"。每次拆分的第一步是定义新模块的输入/输出边界，再动手搬代码。
- 禁止"未记录进度就结束本轮重构"。

---

## 2. 当前高风险文件基线

| 文件 | 行数 | 状态 | 核心问题 |
|---|---:|---|---|
| `ui/test_panel.py` | 2417 | 必须拆分 | 9 个 Mixin 中最大的，111 处 ctrl 引用 |
| `app/main.py` | 502 | 需要审查 | Controller 已完成 Phase 1 收尾，保留编排与少量 UI 胶水 |
| `ui/styles.py` | 1007 | 纯数据，暂缓 | 纯静态样式声明，无逻辑耦合，优先级低 |
| `services/assessment_service.py` | 399 | 健康 | 评分系统已完成模块化 + 类型化 + 单域快照保护，Phase 2 已闭环 |
| `ui/main_window.py` | 528 | 需要审查 | 9-Mixin 继承入口，待迁移为组合式 |
| `domain/fault_scenarios.py` | 520 | 纯数据，暂缓 | 纯场景定义字典，不含逻辑 |
| `services/pt_exam_service.py` | 385 | 健康，观察 | 48 处 `self._ctrl` 引用需逐步收口 |
| `services/_physics_measurement.py` | 372 | 健康，观察 | 保持稳定 |
| `services/pt_phase_check_service.py` | 345 | 健康，观察 | 37 处 `self._ctrl` 引用需逐步收口 |

说明：
- 核心攻坚对象：`ui/test_panel.py`。
- **耦合度指标比行数更重要**。各文件的 `self._ctrl` / `self.ctrl` 引用数是关键度量。

### 当前耦合度基线（2026-04-09）

| 层 | 文件 | `ctrl` 引用数 |
|---|---|---:|
| services | `pt_exam_service.py` | 48 |
| services | `fault_manager.py` | 39 |
| services | `pt_phase_check_service.py` | 37 |
| services | `sync_test_service.py` | 26 |
| services | `pt_voltage_check_service.py` | 23 |
| services | `loop_test_service.py` | 20 |
| services | `assessment_service.py` | 0 |
| ui | `test_panel.py` | 111 |
| ui | `pt_exam_tab.py` | 20 |
| ui | `sync_test_tab.py` | 16 |
| ui | `loop_test_tab.py` | 14 |
| ui | `control_panel.py` | 12 |
| ui | 其余 Tab | 各 5-10 |

---

## 3. 当前总体进度

| 项目 | 当前状态 |
|---|---|
| 当前阶段 | Phase 3 已关闭：R32 收口完成（Mixin 决策方案 B 落地；`ui/test_panel.py` 已压到 `478` 行；`ui/widgets/step_panels/_dialogs/` 子包已外提）。下一轮进入 Phase 4。 |
| 已完成的高/严重问题 | `C1`、`C2(第一步)`、`H1`、`H2`、`H3`、`H4`、`H5` |
| 当前最大风险文件 | `ui/styles.py`(1007)、`ui/panels/control_panel.py`(776)、`ui/widgets/step_panels/_panel_builders.py`(347) |
| 下一轮默认起点 | Phase 4 — Round 33：引入 `ControllerSignals(QObject)`，把 UI 轮询刷新逐步切到 Signal/Slot 管道 |

---

## 4. 重构路线图

### Phase 0: 安全网建设（1-2 轮）

**目标：** 在不动任何核心逻辑的前提下，建立最小回归保护网。这是后续所有重构的前提。

- [x] **PhysicsEngine 可脱离 UI 独立实例化**
  - 构造一个不含 UI 的最小 ctrl 替身（只含 `sim_state` + `pt_phase_orders` 等纯数据属性）
  - 验证 `PhysicsEngine(stub).update_physics()` + `build_render_state()` 可以独立运行
  - 如果不行，先修到能独立实例化（这本身就是在解耦）
- [x] **PhysicsEngine 快照测试**
  - 创建 `tests/test_physics_snapshot.py`
  - 基线场景 1：正常状态（双机空载）→ `tests/snapshots/physics_normal.json`
  - 基线场景 2：E01 故障注入后 → `tests/snapshots/physics_fault_E01.json`
  - RenderState 序列化为 JSON，float 精度小数点后 4 位
  - 首次运行生成基线，后续比对差异
- [x] **AssessmentService 快照测试**
  - 创建 `tests/test_assessment_snapshot.py`
  - 基线场景 1：正常满分流程 → `tests/snapshots/assessment_normal.json`
  - 基线场景 2：随机故障考核流程 → `tests/snapshots/assessment_fault_random.json`
  - 构造固定的 `AssessmentSession`（预填事件流），调用 `build_result(session, context)` 比对输出
- [x] **Mixin 属性交叉引用扫描**
  - 列出每个 Mixin 创建的 `self.xxx` 属性
  - 标注哪些属性被其他 Mixin 访问
  - 输出为 `docs/mixin_dependency_map.md`
  - 这是 Phase 3 UI 组件化的前置依赖图

完成标准：
- `pytest tests/` 可以跑通，物理和评分快照全部 PASS。
- PhysicsEngine 可以不依赖 PyQt5 实例化。
- Mixin 属性依赖图已输出。

### Phase 1: Controller 瘦身 — 接口隔离（3-5 轮）

**目标：** 把 `PowerSyncController` 从上帝类收回到纯编排层。关键不是"搬方法"，而是"定义接口边界"。

- [x] **拆出 `FlowModeManager`**
  - 将 `FlowModePolicy` + `FLOW_MODE_POLICIES` 字典 + 30+ 个 `flow_policy_flag` 包装方法移出
  - 输入接口：`test_flow_mode: str`
  - 输出接口：`FlowModePolicy` 查询
  - Controller 持有实例，只转发查询
- [x] **拆出 `AssessmentCoordinator`**
  - 将考核会话生命周期管理（`start/finish/capture_snapshot/submit_guess` 等）移出
  - 输入接口：`AssessmentSession` + `SimulationState`（只读快照）+ 各步骤 `completed` 状态
  - 输出接口：`AssessmentResult` + 事件列表
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **拆出 `BlackboxRepairHandler`**
  - 将 `get_blackbox_runtime_state` / `apply_blackbox_repair_attempt` 及相关方法移出
  - 输入接口：`fault_config` + `blackbox_orders` + `pt_phase_orders`
  - 输出接口：`BlackboxRepairOutcome`
  - 修复结果通过返回值传回 Controller，由 Controller 写入状态
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **拆出 `PhaseOrderResolver`**
  - 将 `resolve_pt_node_plot_key` / `get_pt_phase_sequence` / `resolve_loop_node_phase` 移出
  - 输入接口：`pt_phase_orders` + `blackbox_orders` + `fault_config`(只读)
  - 输出接口：纯函数返回值
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **拆出 `HardwareActions`**
  - 将发电机启停、断路器合分、即时同期动作移出
  - 输入接口：`SimulationState`（读写）
  - 输出接口：状态变更直接写入传入的 State 对象
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **删除 Controller 中已迁出的旧方法**
  - 不保留纯转发壳层（如 `def is_loop_test_complete(self): return self._loop_svc.is_loop_test_complete()`）
  - UI 直接调用对应 Service 的方法，或通过 Controller 暴露的有限接口
  - 第 15 轮已完成第一阶段：`HardwareActions`、`PhaseOrderResolver`、`BlackboxRepairHandler`、`FaultManager`、`LoopTestService`、`PtVoltageCheckService`、`PtPhaseCheckService`、`PtExamService`、`SyncTestService` 相关纯转发壳已删除
  - 第 16 轮已完成第二阶段：`FlowModeManager`、`AssessmentCoordinator` 相关纯转发壳已删除；`AssessmentService` 句柄已公开化
- [x] **每步完成后跑快照测试验证**

完成标准：
- `app/main.py` 降到 ~600 行以下。
- Controller 中不再堆叠策略查询、考核生命周期、黑盒修复、相序解析四类实现细节。
- 新拆出的模块之间无直接引用，只通过 Controller 编排。
- 快照测试全部 PASS。

### Phase 2: 评分系统模块化（2-3 轮）

**目标：** `assessment_service.py` 变成可独立测试的评分管道。

- [x] **定义 `AssessmentContext` dataclass**
  - 将 `build_result()` 中从 `self._ctrl` 读取的所有数据（loop_records、voltage_records 等）封装为一个 dataclass
  - Controller 在调用 `build_result()` 之前打包好 Context 传入
  - `build_result(session, context)` 不再访问 `self._ctrl`
- [x] **评分事件常量化**
  - 消除 `build_result()` 内部的魔法字符串（`"fault_detected"` / `"step_entered"` 等）
  - 集中到 `domain/assessment.py` 的常量类中
- [x] **按评分域拆分为纯函数模块**
  - `services/scoring/discipline.py` — A 类：流程纪律评分
  - `services/scoring/step_quality.py` — B/C/D/E 类：步骤 1-4 质量评分
  - `services/scoring/fault_diagnosis.py` — F 类：故障定位评分
  - `services/scoring/blackbox_efficiency.py` — G/H 类：黑盒与效率评分
  - 每个模块暴露纯函数：`score_xxx(context) -> List[AssessmentScoreItem]`
- [x] **`score_context` 改为 `ScoringContext` dataclass**
  - `services/scoring/context.py` 已落地 `@dataclass(frozen=True)` 的 `ScoringContext`
  - 4 个评分域模块已从 `ctx["xxx"]` 切换为 `ctx.xxx`
  - 评分阶段所需的 4 个原闭包已迁入 `services/scoring/_common.py`，改为独立纯函数
- [x] **`assessment_service.py` 主文件降到 <= 500 行**
  - 主文件只做组装：调用各评分域函数，合并结果
- [x] **为每个评分域补充独立快照测试**

完成标准：
- `build_result()` 只做组装，不含具体评分逻辑。
- 每个评分域能单独阅读、修改、测试。
- `assessment_service.py` 中 `self._ctrl` 引用数 = 0。
- 快照测试全部 PASS。

### Phase 3: UI 组件化 — 告别 Mixin（5-8 轮）

**目标：** `PowerSyncUI` 从 9-Mixin 深度继承变成组合式装配。

#### 迁移策略

每个 Tab 从 Mixin 变为独立的 `QWidget` 子类：
- 定义该 Tab 需要的最小 Protocol 接口
- Controller 实现该 Protocol
- `PowerSyncUI` 实例化独立 Tab，而非继承 Mixin
- 迁移完成后从继承链中删除对应 Mixin

#### 迁移顺序（从简到繁）

- [x] **概念验证：`LoopTestTab`（14 处 ctrl 引用）**
  - 从 `LoopTestTabMixin` 改为独立 `QWidget` 子类
  - 定义 `LoopTestTabAPI(Protocol)`：`get_loop_test_state()` / `record_loop_measurement()` / `is_loop_test_complete()`
  - 从 `PowerSyncUI` 继承链中删除 `LoopTestTabMixin`
  - 验证全流程正常
- [x] **`PtVoltageCheckTab`（10 处 ctrl 引用）**
- [x] **`PtPhaseCheckTab`（10 处 ctrl 引用）**
- [x] **`SyncTestTab`（16 处 ctrl 引用）**
- [x] **`PtExamTab`（20 处 ctrl 引用）**
- [x] **`WaveformTab`（5 处 ctrl 引用，注意 matplotlib canvas 生命周期）**
- [x] **`CircuitTab`（10 处 ctrl 引用）**
- [ ] **`ControlPanel`（12 处 ctrl 引用）**
- [x] **`TestPanel`（111 处 ctrl 引用）— 最后做，最复杂**
  - R30 已把骨架迁移为单体 `TestPanelWidget(QWidget)`，`_GenWiringWidget` / `_PTWiringWidget` 外提到 `ui/widgets/`
  - R31 按 Step1~5 继续把 `_build_step*` / `_refresh_tp_step*` 外提为 5 个独立 `QGroupBox` 子面板，`ui/test_panel.py` 收敛为 677 行的协调器
  - 子面板只通过 `TestPanelAPI + 构造注入回调` 协作，零 `self.ctrl`、零 service 穿透、零反向寻址
  - 剩余收口：`ui/test_panel.py` 还需从 677 降到 ≤ 500（抽顶部栏/步骤点/底部按钮构建函数到 `_panel_builders.py`）

#### TestPanel 子拆分明细

R30/R31 实际落点为 `ui/widgets/step_panels/`（不是最初规划的 `ui/test_steps/`）：

- [x] `ui/widgets/step_panels/loop_test_panel.py` — 第一步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/pt_voltage_check_panel.py` — 第二步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/pt_phase_check_panel.py` — 第三步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/pt_exam_panel.py` — 第四步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/sync_test_panel.py` — 第五步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/_panel_builders.py::show_blackbox_dialog` / `show_blackbox_required_dialog` — 黑盒弹窗逻辑（R31；可在 R32 继续拆成独立 `_dialogs` 子模块）
- [x] `ui/widgets/step_panels/_panel_builders.py::show_assessment_result_dialog` / `show_random_fault_identification_dialog` — 成绩单与结果弹窗（R31；同上）
- [x] `ui/widgets/step_panels/_panel_builders.py::make_group/make_button/make_note_label/...` — 公共按钮、提示、文本助手（R31）
- [ ] 将步骤业务判断从 UI 中迁回状态/服务层，UI 只读取状态（**留给 Phase 4**：Signal/Slot + Service `self._ctrl` 收口同轮处理）

完成标准：
- `PowerSyncUI` 业务层面的 UI 不再使用 Mixin 多重继承，改为组合式装配。
  允许保留 **至多 1 个纯 UI 宿主构造层 Mixin**（当前为 `WidgetBuilderMixin`），
  但必须同时满足 §7.5 「纯构造层 Mixin 例外条款」全部项目，否则必须在下一轮
  降级为独立 `QWidget` 或 `ControlPanelBuilder` facade。
  - R32 状态：已按方案 B 收口；`WidgetBuilderMixin` 本体零改动，且 §5.2 守门扫描结果 = 0。
- `ui/test_panel.py` 主文件降到 <= 500 行。
  - R32 状态：`478` 行，已达标。
- 每个 Tab 组件是独立的 `QWidget`，可脱离其他 Tab 理解。
  - R31 状态：已达标（7 个 Tab + TestPanelWidget + 5 个 Step 子面板全部独立 `QWidget` / `QGroupBox`）。
- 新增 UI 逻辑落在拆出的子模块中，不回写主文件。
  - R32 状态：已达标；`_dialogs/` 子包已独立承接 4 个对话框函数。

### Phase 4: 通信标准化与清理（2-3 轮）

**目标：** 建立清晰的 Controller <-> UI 通信管道，完成最终清理。

- [ ] **引入 Qt Signal/Slot 通信**
  - 定义 `ControllerSignals(QObject)` 信号集
  - 核心信号：`render_state_updated(RenderState)` / `step_state_changed(int, object)` / `assessment_finished(AssessmentResult)`
  - 各 Tab 组件连接自己关心的信号，替代轮询式刷新
- [ ] **收口 Service 对 ctrl 的剩余直接访问**
  - 逐步将旧 Service 的 `self._ctrl` 改为显式参数/State 注入
  - 目标：所有 Service 的 `self._ctrl` 引用数归零
- [ ] **收口旧键名兼容逻辑**
  - 清理历史命名债务
- [ ] **收口状态真值源**
  - 明确 `pt_phase_orders` 是否为派生值
  - 消除 `blackbox_order` 与 `pt_phase_orders` 之间的隐式同步
- [ ] **清理死代码、重复 UI、旧注释块**
- [ ] **补核心 `domain/services` 类型标注**
  - 从 `domain/` 开始，逐步覆盖 `services/`
  - 不急着覆盖 UI 层

完成标准：
- UI 与 Controller 之间通过 Signal/Slot 通信，无直接属性访问。
- 所有 Service 的 `self._ctrl` 引用数 = 0。
- 核心文件基本满足 `<= 500` 行。
- 主体架构边界清晰，新人可以在 30 分钟内理解系统分层。

---

## 5. 优先删除清单

| 优先级 | 删除对象 | 原因 |
|---|---|---|
| P1 | 已迁出后仅剩转发意义的旧方法 | 防止 Controller 继续变回上帝类 |
| P1 | 重复评分 helper 或旧评分拼装残留 | 防止评分系统继续臃肿 |
| P1 | `ui/test_panel.py` 中已被新子模块取代的旧步骤逻辑 | 防止步骤逻辑双轨并存 |
| P2 | 旧键名兼容回退逻辑 | 防止参数读取双轨并存 |
| P2 | 仅为过渡保留的旧 UI 包装方法 | 防止主窗口继续变胖 |

规则：新实现落地后，同轮就删旧实现。

### 5.1 组件化轮新增硬门禁：悬空宿主调用扫描

每轮组件化结束后必须执行：

```bash
grep -rn "_on_toggle_\(loop\|pt_voltage\|pt_phase\|sync\)" ui/
```

结果必须只出现在组件自身文件内（`ui/tabs/*_tab.py`），不得出现在 `ui/test_panel.py`、`ui/main_window.py` 或其他兄弟模块。

说明：
- R22 验收时遗漏了 `test_panel.py` 对宿主私有方法的调用，导致 step 1 切换抛 `AttributeError`，R26 补修。
- 后续组件化轮必须执行此扫描，防止同类回归。

### 5.2 WidgetBuilderMixin 例外守门扫描

每轮结束必须执行（基于仓库实际 `self.ctrl` 命名）：

```bash
grep -nE "self\.ctrl\.(flow_mgr|loop_svc|pt_voltage_svc|pt_phase_svc|pt_exam_svc|sync_svc|assessment_coord|fault_mgr|blackbox_handler|hw)\b" \
    ui/panels/control_panel.py
```

结果必须**为空**。任何 service / coordinator / hardware 层直连 = §7.5 例外条款失效 = 下一轮必须把 `WidgetBuilderMixin` 降级为独立 `QWidget` 或 `ControlPanelBuilder` facade。

说明：
- `self.ctrl.sim_state.*` 写入（如 `sim_state.multimeter_mode = checked`）与读取是被允许的“UI 参数层同步”，不计入本扫描。
- R32 建立此门时，现状 `ui/panels/control_panel.py` 结果 = 0，即 compliant。

---

## 6. 核心引擎快照测试规范

### 6.1 测试目录结构

```
tests/
├── snapshots/
│   ├── physics_normal.json
│   ├── physics_fault_E01.json
│   ├── assessment_normal.json
│   └── assessment_fault_random.json
├── test_physics_snapshot.py
└── test_assessment_snapshot.py
```

### 6.2 物理引擎快照流程
1. 构造最小 ctrl 替身（只含 `sim_state` + `pt_phase_orders` 等纯数据属性，不含 UI）。
2. 调用 `PhysicsEngine(stub).update_physics()` + `build_render_state()`。
3. 将 `RenderState` 序列化为 JSON（float 精度到小数点后 4 位）。
4. 首次运行生成基线文件，后续运行比对差异。

### 6.3 评分快照流程
1. 构造固定的 `AssessmentSession`，预填确定性事件流。
2. 调用 `AssessmentService.build_result(session, context)`。
3. 将 `AssessmentResult` 序列化比对。

### 6.4 何时必须跑
- 任何修改 `services/` 或 `domain/` 下文件的轮次。
- 快照不通过 = 要么是 Bug，要么需要更新基线并说明原因。
- 没有通过快照测试，不算完成本轮重构。

---

## 7. Mixin → 组合式组件 迁移规范

### 7.1 最终目标
`PowerSyncUI` 不再使用 Mixin 多重继承，改为组合式装配。

### 7.2 迁移模式

每个 Tab 从 Mixin 变为独立的 `QWidget` 子类：

```python
# 旧模式（Mixin，所有 self.xxx 共享命名空间）
class LoopTestTabMixin:
    def _build_loop_test_tab(self):
        self.loop_xxx = ...        # 污染宿主命名空间
        self.ctrl.xxx()            # 穿透式访问

# 新模式（独立 QWidget，隔离命名空间）
class LoopTestTab(QWidget):
    def __init__(self, api: LoopTestTabAPI):
        self._api = api            # 只接收最小接口
        self._loop_xxx = ...       # 属性自己持有
```

### 7.3 PowerSyncUI 最终形态

```python
class PowerSyncUI(QMainWindow):
    def __init__(self, ctrl):
        # ...
        self._waveform_tab = WaveformTab(ctrl)
        self._circuit_tab = CircuitTab(ctrl)
        self._loop_test_tab = LoopTestTab(ctrl)
        # ... 其余 Tab
        self.tab_widget.addTab(self._waveform_tab, "波形/相量")
        self.tab_widget.addTab(self._circuit_tab, "母排拓扑")
        # ...

    def render_visuals(self, rs: RenderState):
        self._waveform_tab.update_from(rs)
        self._circuit_tab.update_from(rs)
        # ...
```

### 7.4 过渡期规则
- 新增的 Tab 组件必须用独立 `QWidget` 类实现。
- 旧 Mixin 暂时保留，按 Phase 3 顺序逐个迁移。
- 每迁移完一个 Mixin，从继承链中删除。
- 不允许新增"宿主对象隐式共享一切状态"的 Mixin。

### 7.5 纯构造层 Mixin 例外条款

`PowerSyncUI` 至多保留 1 个纯 UI 宿主构造层 Mixin（当前为 `WidgetBuilderMixin`），必须同时满足下列全部条款：

1. **零 service 层穿透**：
   - **允许**：通过 `self.ctrl.sim_state.*` 做 UI 参数同步（读/写），以及通过构造出的 chrome 控件句柄让主窗口 / 其它组件消费。
   - **禁止**：`self.ctrl.flow_mgr` / `loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` / `sync_svc` / `assessment_coord` / `fault_mgr` / `blackbox_handler` / `hw` 等 service / coordinator / hardware 层直连。
   - 硬门：§5.2 扫描结果必须 = 0。
2. **仅构造 chrome 级控件**：只构造主窗口右侧栏 / 状态标签 / 场景选择 / 万用表 checkbox 等 chrome 层控件，不得构造任何步骤测试流程相关 UI（Step1~5 面板、测试模式生命周期控件等）。
3. **不得被独立 Tab 反向依赖**：任何 `ui/tabs/*_tab.py` / `ui/widgets/step_panels/*.py` 不得出现 `self.parent().multimeter_cb` 或类似的反向寻址；其需要消费的 host 属性必须通过主窗口装配时的构造期回调或显式 `@property` 注入。
4. **host 属性通过白名单暴露**：Mixin 构造出的共享属性（如 `multimeter_cb` / `bus_status_lbl` / `ctrl_container` 等）只能由主窗口显式消费；主窗口不得把“宿主对象上有这个属性”作为隐式契约下放给子组件。
5. **行数上限**：`ui/panels/control_panel.py` 行数 ≤ 900。超过时必须按职责再切。

违反任一条 = 下一轮必须立即降级。

---

## 8. 固定回归清单

每轮重构后，至少人工验证以下项目：

| 回归项 | 必查内容 |
|---|---|
| 正常场景全流程 | 五步流程可完成；最终成绩单 `total_score >= 80`；`veto_reason` 为空 |
| 指定故障流程 | 指定故障注入、检测、修复、成绩单正常；修复后相关故障状态已清除 |
| 随机故障考核流程 | 随机场景判定、第四步前后门禁、成绩单正常；场景判错时额外扣 `10` 分 |
| 黑盒修复流程 | 黑盒打开、保存接线、复测、修复闭环正常；考核模式不直接泄露修复结果 |
| 成绩单流程 | `score_items / penalties / metrics / summary` 正常显示；总分与扣分说明一致 |
| 事故弹窗流程 | `E01/E02/E03` 在预期触发点弹出；点击修复后可继续流程 |
| 同期与波形页 | UI 能正常刷新，不出现明显回归；无参考源时 `Δf/ΔV/Δθ` 显示 `--` |

说明：没有完成上述回归，不算完成本轮重构。

### 8.1 核心逻辑测试原则
- 重构 `Assessment / Physics / Arbitration / Protection / Fault` 相关核心逻辑前，必须先补最小黑盒测试。
- 黑盒测试优先级：
  1. `输入事件流 -> AssessmentResult`
  2. `给定 SimulationState -> 仲裁/保护输出`
  3. `故障注入 -> 修复 -> 状态恢复`
- 没有测试保护，不进入大规模核心逻辑重构。

---

## 9. 已完成进度与轮次历史

### 已完成
- `C1`：物理层不再直接弹事故对话框，改为帧末统一消费。
- `C2（第一步）`：已拆出 `services/fault_manager.py`。
- `H1`：`_tick()` 已拆成物理异常边界与渲染异常边界，并增加连续失败可见提示。
- `H2`：三套事故对话框已收口为 `_show_accident_dialog(...)`，旧 `_legacy` 已删除。
- `H3`：控制器不再直接切换 `tab_widget` 或直接写入 PT3 变比控件，改为 UI 请求消费。
- `H4`：`assessment_service.build_result()` 已拆成 helper 化结构。
- `H5`：死母线倒计时已改为使用真实 `frame_dt`，不再写死 `0.033`。

### 当前未完成但已明确方向
- Phase 3 收口 R32：①Mixin 方案 A/B 决策；②`ui/test_panel.py` 从 677 → ≤ 500；③`_panel_builders.py`（770）拆出 `_dialogs` 子模块以进一步降低单文件体量。
- Phase 4 主线：Qt Signal/Slot 通信、Service 对 `self._ctrl` 直连收口、旧键名与状态真值源清理、`domain/services` 类型标注补齐。

### 第 32 轮 (2026-04-16)：Phase 3 收口（方案 B + TestPanel 瘦身 + `_dialogs` 外提）
- 本轮唯一主攻目标：正式拍板保留 `WidgetBuilderMixin` 作为“纯 UI 宿主构造层”例外，同时完成 `ui/test_panel.py` 二次瘦身与 `ui/widgets/step_panels/_dialogs/` 子包外提，关闭 Phase 3。
- 实际完成：
  - `MAINTENANCE_CHECKLIST.md` 已按方案 B 修订：§4 完成标准改为“业务层面 UI 不再使用 Mixin 多重继承，但允许至多 1 个纯 UI 宿主构造层 Mixin”；新增 §5.2 守门扫描与 §7.5 例外条款。
  - `ui/test_panel.py` 已从 `677` 行降到 `478` 行；顶部栏、步骤点、滚动骨架、状态区、底部按钮条、`tp_dot_style`、`refresh_tp_gen_refs`、`refresh_tp_bottom` 与步骤动作查表分发均已迁入 `ui/widgets/step_panels/_panel_builders.py`。
  - `ui/widgets/step_panels/_dialogs/` 子包已落地，4 个对话框函数已从 `_panel_builders.py` 迁出：`show_assessment_result_dialog`、`show_random_fault_identification_dialog`、`show_blackbox_required_dialog`、`show_blackbox_dialog`。
  - `ui/widgets/step_panels/_panel_builders.py` 已瘦身至 `347` 行，只保留 builders / shared helpers / refresh helpers / `STEP_ACTION_TABLE` / `dispatch_step_action`。
  - `WidgetBuilderMixin` 本体、主窗口装配、controller、5 个 Step 子面板、各 Tab 与服务层文件均保持零改动。
- 删除了哪些旧代码：
  - 删除 `_panel_builders.py` 内原有 4 个对话框函数定义。
  - 删除 `ui/test_panel.py` 内本地 `_tp_dot_style`、`_refresh_tp_gen_refs`、`_refresh_tp_bottom` 与长 if/elif 步骤动作分发链。
- 接口变化：
  - 无新增公开接口；`TestPanelAPI` 签名保持不变。
  - `ui/test_panel.py` 中的对话框入口函数身份保持不变，只改为薄 wrapper 转调 `_dialogs` 子包。
- 耦合度变化：
  - `ui/test_panel.py` 继续从“协调器 + 少量 chrome 构建”收敛为更纯的协调器。
  - `_panel_builders.py` 不再承担对话框职责；对话框 import 链现在只由 `ui/test_panel.py` 直连 `_dialogs/`，符合协调器持有与派发规则。
  - Phase 3 结束时仓库仅剩 1 个 Mixin：`WidgetBuilderMixin`，并已被例外条款与守门扫描锁定边界。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（结构扫描、`py_compile`、offscreen 导入冒烟全部通过；真实 GUI 对话框路径与全流程冒烟需由用户在可交互环境确认）
- 下一轮起点：Phase 4 — Round 33：引入 `ControllerSignals(QObject)`，把 UI 刷新从轮询逐步切到 Signal/Slot

### 第 31 轮 (2026-04-16)：Phase 3-9（TestPanelWidget 步骤子面板解构）
- 本轮唯一主攻目标：按 Step1~5 将 `TestPanelWidget` 的 build + refresh 继续外提为独立 `QGroupBox` 子面板，保留 `ui/test_panel.py` 作为协调器，不改服务层、不改主窗口装配。
- 实际完成：
  - 新增 `ui/widgets/step_panels/` 包及 7 个文件：`__init__.py`、`_panel_builders.py`、`loop_test_panel.py`、`pt_voltage_check_panel.py`、`pt_phase_check_panel.py`、`pt_exam_panel.py`、`sync_test_panel.py`。
  - `ui/test_panel.py` 已瘦身为 `677` 行协调器组件，仅保留测试模式生命周期、顶部栏/步骤点/底部操作条、step 分发、共享状态刷新与 assessment/random-fault/blackbox 对话框薄包装。
  - `_build_step1~5`、`_refresh_tp_step1~5`、`_on_connect_psm` / `_on_disconnect_psm` / `_on_record_psm`、`_tp_s2_record`、以及 `_make_*` / `_tone_from_color` 这组共享构建方法已全部从 `ui/test_panel.py` 中移除。
  - 5 个 Step 面板均改为只通过 `TestPanelAPI + 构造注入回调` 协作，子面板内 `self.ctrl`、service 穿透与 `parent()/window()` 反向寻址均为 0 命中。
  - `_GenWiringWidget` / `_PTWiringWidget` 继续保留在 `ui/widgets/`，黑盒对话框与 wiring widget 交互通过 `_panel_builders.py` 的模块级 helper 复用，未改类名、未改构造签名、未改绘制逻辑。
- 删除了哪些旧代码：
  - 删除 `ui/test_panel.py` 中 Step1~5 的原地构建与刷新实现。
  - 删除 `ui/test_panel.py` 中原有的组装辅助方法族（`_make_grp` / `_make_btn` / `_make_step_list` / `_make_gen_block` / `_make_gen_fap_block` 等）。
- 接口变化：
  - `TestPanelAPI` 签名未变；Round 30 既有主窗口装配与 controller 薄转发全部复用。
  - 新增 5 个子面板统一对外接口：`refresh(rs, step)` / `reset()` / `on_enter()`。
- 耦合度变化：
  - `ui/test_panel.py` 行数 `2232 -> 677`。
  - `TestPanelWidget` 从“大而全单文件”收敛为“协调器 + 5 个 Step 子面板 + 1 个共享构建器”。
  - 仓库中 `Mixin` 只剩 `WidgetBuilderMixin` 1 个，符合 Phase 3 收尾目标。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（`py_compile`、`offscreen` 导入冒烟、G1–G13 结构/扫描硬门全部通过；人工 GUI 冒烟已由用户确认完成，覆盖启动 → 进入测试模式 → Step1~5 推进/完成/重置 → admin 跳步 → 黑盒必修门禁 → 成绩单 → 退出并重入）
- R31 验收审计结论：代码/自动化/结构审计全部通过；手动 GUI 冒烟由用户声明完成；最终判定 `第 31 轮可视为完成`。
- 下一轮起点：Phase 3 收口 R32 — ①Mixin 方案 A/B 决策；②`ui/test_panel.py` 677 → ≤ 500（抽顶部栏/步骤点/底部按钮构建到 `_panel_builders.py`）；③`_panel_builders.py` 770 行拆出 `_dialogs` 子模块。完成后进入 Phase 4。

### 第 30 轮 (2026-04-16)：Phase 3-8（TestPanelWidget 骨架拆分 + Wiring Widget 外提）
- 本轮唯一主攻目标：只落地方案 A，将 `TestPanelMixin` 迁移为单体 `TestPanelWidget`，并先把 `_GenWiringWidget` / `_PTWiringWidget` 外提到 `ui/widgets/`；**明确禁止启动 Step1~5 子面板拆分**。
- 实际完成：
  - `ui/widgets/gen_wiring_widget.py` 与 `ui/widgets/pt_wiring_widget.py` 已新增，`_GenWiringWidget` / `_PTWiringWidget` 原样外提；`ui/test_panel.py` 仅保留 import 与 3 处实例化点。
  - `ui/test_panel.py` 已删除 `TestPanelMixin`，新增 `TestPanelAPI(Protocol)` 与 `TestPanelWidget(QWidget)`；原 `_setup_test_panel`、`_render_test_panel`、`_refresh_tp_*`、`_on_tp_*`、管理员/黑盒/考核弹窗逻辑全部迁入组件内部。
  - `ui/main_window.py` 已从基类列表中移除 `TestPanelMixin`，当前主窗口只保留 `WidgetBuilderMixin + QMainWindow`；`render_visuals()` 中原 `self._render_test_panel(p)` 已收口为 `self._test_panel_widget.render(p)`。
  - 主窗口已通过 `enter_test_mode()` / `exit_test_mode()`、`test_panel` property 以及 `on_show_test_panel` / `on_set_current_tab` / `on_set_step_tabs_visible` / `on_toggle_multimeter` / `on_force_multimeter_off` / `on_connect_phase_seq_meter` / `on_disconnect_phase_seq_meter` / `get_phase_seq_meter_sequence` 八个构造期回调，保住旧调用面与宿主 UI 协调。
  - `ui/tabs/_step_style.py` 已新增 `apply_badge_tone(widget, tone)`，`TestPanelWidget` 不再依赖 `WidgetBuilderMixin` 的宿主样式方法；原 `self._set_props` / `self._apply_button_tone` / `self._apply_badge_tone` 已统一切到 `_step_style` 模块级 helper。
  - `app/main.py` 已补齐本轮所需 Controller 薄转发，包括管理员捷径、故障推进门禁、assessment 事件流、blackbox 运行态、PT 电压/相序完成度、相序记录、硬件开关量等接口，`ui/test_panel.py` 内对 `flow_mgr` / `loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` / `sync_svc` / `assessment_coord` / `fault_mgr` / `blackbox_handler` / `hw` 的直接穿透均已收口为 `self._api.xxx`。
- 删除了哪些旧代码：
  - 删除 `ui/test_panel.py` 中整套 `TestPanelMixin` 类定义。
  - 删除 `ui/test_panel.py` 内嵌的 `_GenWiringWidget` / `_PTWiringWidget` 类定义。
- 接口变化：
  - `PowerSyncUI` 的 UI Mixin 继承链从 2 个减至 1 个，仅剩 `WidgetBuilderMixin`。
  - 新增 `TestPanelAPI`，以显式接口承接原先散落在 `self.ctrl.*` 上的步骤状态、动作、考核、故障、硬件与物理层访问。
  - 保留 `PowerSyncUI.enter_test_mode()` / `exit_test_mode()` 与 `test_panel` 兼容入口，避免 `app/main.py` 与宿主装配层调用方式变化。
- 耦合度变化：
  - `ui/test_panel.py` 内部 `self.ctrl.flow_mgr` / `loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` / `sync_svc` / `assessment_coord` / `fault_mgr` / `blackbox_handler` / `hw` 穿透访问已收敛为 0。
  - `WidgetBuilderMixin` 被明确保留在宿主构造层，不再和本轮 TestPanel 迁移耦合推进；Round 31 只继续处理 `TestPanelWidget` 自身的步骤子面板解构。
  - `ui/test_panel.py` 行数已由 `2423` 降到 `2222`；主风险仍在，但已经从“宿主大 Mixin”变成“单组件大文件”，可在下一轮继续按 Step1~5 精细下沉。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化 grep / `py_compile` / `pytest` 全通过；真实 GUI 全流程冒烟待补，尤其要覆盖进入测试模式、Step 1~5 进退、管理员模式、随机故障识别弹窗与黑盒修复对话框）
- 下一轮起点：Phase 3 — Round 31：`TestPanelWidget` 步骤子面板解构（继续下沉 `_build_step1~5` 与 `_refresh_tp_step1~5`，目标把 `ui/test_panel.py` 压到可维护规模）

### 第 29 轮 (2026-04-15)：Phase 3-7（WidgetBuilderMixin / TestPanelMixin 组件化评估）
- 本轮唯一主攻目标：对 `WidgetBuilderMixin` 与 `TestPanelMixin` 做数据化评估，给出 Round 30 / Round 31 的单一明确执行方案，不做源码重构。
- 实际完成：
  - 已完成 `WidgetBuilderMixin` 数据画像：文件 `776` 行，`self.ctrl.` 穿透 `12` 处；但其构建出的宿主属性面很大，至少包括 `multimeter_cb`、`bus_status_lbl`、`bus_reference_lbl`、`arbitrator_lbl`、`relay_lbl`、`status1_lbl`、`status2_lbl`、`ctrl_layout`、`ctrl_inner` 等，并被 `ui/main_window.py`、`ui/test_panel.py`、步骤 Tab 回调广泛消费。
  - 已完成 `TestPanelMixin` 数据画像：文件 `2423` 行，`self.ctrl.` 穿透 `114` 处，实例方法 `62` 个；职责已确认横跨构建、测试模式生命周期、步骤动作分发、记录转发、管理员/故障弹窗、逐帧渲染刷新、内嵌 wiring widget 七大类。
  - 已确认 `TestPanelMixin` 的跨 Mixin / 宿主依赖面：直接依赖 `multimeter_cb`、`ctrl_container`、`tab_widget`、`phase_seq_meter`、`connect_phase_seq_meter()`、`disconnect_phase_seq_meter()`，并大量复用 `_apply_button_tone()`、`_apply_badge_tone()`、`_set_props()` 等宿主样式 helper。
  - 已完成三方案比较：单体 `TestPanelWidget`、按步骤子面板拆分、按职责分层浅组件化；最终推荐“两轮法”——Round 30 先抽 `TestPanelWidget` 骨架并外提 `_GenWiringWidget` / `_PTWiringWidget`，Round 31 再按步骤子面板继续解构。
  - 已明确结论：`WidgetBuilderMixin` 本轮后暂不做独立 QWidget 组件化，保留为宿主构造层；如后续仍需降耦，只考虑降级为 `ControlPanelBuilder / Facade` 形态，不单开一轮做激进搬迁。
- 删除了哪些旧代码：
  - 无。本轮是评估轮，只更新 `MAINTENANCE_CHECKLIST.md`。
- 接口变化：
  - 本轮无接口变更。
  - 下一轮建议新增 `TestPanelAPI`，显式收口 `sim_state` / 步骤状态快照 / 测试模式动作 / 评估事件 / 黑盒状态查询等当前散落在 `self.ctrl.*` 上的访问面。
- 耦合度变化：
  - 代码耦合本轮未变；但剩余高风险面已从“两个都要拆”收敛为“主拆 `test_panel.py`，`WidgetBuilderMixin` 先稳住宿主属性面”。
  - `ui/test_panel.py` 已被正面确认为 Phase 3 收尾主战场，`WidgetBuilderMixin` 则被降级为边界整理问题，而不是主组件化目标。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：BASELINE（本轮无 `.py` 改动；记录现状基线并完成评估，不做额外 GUI 重构验收）
- 下一轮起点：Phase 3 — Round 30：`TestPanelWidget` 骨架拆分 + `_GenWiringWidget` / `_PTWiringWidget` 外提（`WidgetBuilderMixin` 暂保留）

### 第 28 轮 (2026-04-15)：Phase 3-6（WaveformTab / CircuitTab 组件化）
- 本轮唯一主攻目标：将 `WaveformTabMixin` 与 `CircuitTabMixin` 同步迁移为独立 `QWidget` 组件，收敛 `PowerSyncUI` 继承链，并保住 matplotlib 画布生命周期与外部调用兼容面。
- 实际完成：
  - `ui/tabs/waveform_tab.py` 已彻底改写：删除 `WaveformTabMixin`，新增 `WaveformTabAPI(Protocol)` 与 `WaveformTab(QWidget)`，`Figure / FigureCanvas / ax_* / line_* / phasor_*` 全部收回组件实例持有。
  - `ui/tabs/circuit_tab.py` 已彻底改写：删除 `CircuitTabMixin`，保留模块级 `_qs(...)` 供 `pt_phase_check_tab.py` 继续导入，同时新增 `CircuitTabAPI(Protocol)` 与 `CircuitTab(QWidget)`。
  - `app/main.py` 已补齐 3 个薄转发：`get_pt_blackbox_mode()`、`get_pt_phase_sequence()`、`is_assessment_mode()`；原有 `is_loop_test_complete()` 直接复用。
  - `ui/main_window.py` 已从基类列表中删除 `WaveformTabMixin` 与 `CircuitTabMixin`，当前只保留 `WidgetBuilderMixin + TestPanelMixin + QMainWindow`。
  - `render_visuals()` 中原先分散的 10 个波形/拓扑私有渲染入口已合并为 `self._waveform_tab.render(rs)` 与 `self._circuit_tab.render(p)` 两次转发。
  - 主窗口已保留 `rebuild_circuit_diagram()`、`connect_phase_seq_meter()`、`disconnect_phase_seq_meter()` 等价转发，并补了 `ax_circuit` / `canvas2` / `phase_seq_meter` 兼容属性，确保 `app/main.py`、`ui/test_panel.py`、`WidgetBuilderMixin._on_circuit_click()` 调用方式不变。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/waveform_tab.py` 中整套 Mixin 实现。
  - 删除 `ui/tabs/circuit_tab.py` 中整套 Mixin 实现。
  - 删除 `ui/main_window.py` 中对 `_setup_tab_waveforms()`、`_setup_tab_circuit()`、`_init_lines()` 以及 10 个波形/拓扑私有渲染入口的直接依赖。
- 接口变化：
  - `WaveformTab` 通过 `WaveformTabAPI` 读取 `sim_state + physics`，本轮保留 `physics` property 是为了原样保留 `fixed_deg / bus_freq / bus_phase` 三处读取点，避免再人为拆出一层非必要包装后改变渲染边界。
  - `CircuitTab` 通过 `CircuitTabAPI` 读取 `sim_state`、各步骤状态切片与 4 个只读查询接口，不再暴露 `flow_mgr` / `loop_svc` / `phase_resolver` 等 service 对象。
  - `PowerSyncUI` 的 UI Mixin 继承链从 4 个减至 2 个，Phase 3 只剩 `WidgetBuilderMixin` 与 `TestPanelMixin` 待收口。
- 耦合度变化：
  - `WaveformTab` / `CircuitTab` 内部 `self.ctrl` 穿透访问已收敛为 0。
  - `PowerSyncUI` 不再直接持有 Waveform/Circuit 的 matplotlib 初始化与渲染细节，主窗口职责进一步缩回到装配与少量兼容转发。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（自动化回归 13/13、`py_compile` 通过；人工 GUI 冒烟已覆盖：Tab 0 波形/相量首屏渲染正常、Tab 1 母排拓扑首屏渲染正常、resize 后两处画布重绘无残影且相量指针不跳；第一步进入/退出、第四步 PT 记录、第五步同步流程手动走读无回归）
- 下一轮起点：Phase 3 — Round 29：`WidgetBuilderMixin / TestPanelMixin` 组件化评估（最终两轮收尾）

### 第 27 轮 (2026-04-15)：Phase 3-5（PtExamTab 组件化）
- 本轮唯一主攻目标：将 `PtExamTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/pt_exam_tab.py` 已彻底改写：删除 `PtExamTabMixin`，新增 `PtExamTabAPI(Protocol)` 与 `PtExamTab(QWidget)`。
  - `PtExamTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第四步流程补了 3 个薄转发方法：`get_pt_exam_steps()`、`get_generator_state()`、`get_current_pt_exam_phase_match()`。
  - `ui/main_window.py` 已从基类列表中删除 `PtExamTabMixin`，改为组合装配 `self._pt_exam_tab = PtExamTab(...)`，并将渲染路径切换为 `self._pt_exam_tab.render(p)`。
  - 第四步状态文本、步骤列表和 9 组记录标签已统一切到 `ui.tabs._step_style` 的共享 helper，不再保留本地内联 `setStyleSheet(...)` 与 `_BTN` 常量。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/pt_exam_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - PtExamTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `PtExamTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 5 个 UI Mixin 减至 4 个。
- 耦合度变化：
  - `PtExamTab` 内部 `self.ctrl` / `self.pt_exam_svc` / `_get_generator_state` / `_get_current_pt_phase_match` 引用已收敛为 0。
  - Phase 3 的组件化范式已连续在前五个步骤 Tab 上复用成功。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；完整人工点击第四步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 28：`WaveformTab / CircuitTab` 组件化

### 第 26 轮 (2026-04-15)：Phase 3（`test_panel.py` 宿主残留调用热修复）
- 本轮唯一主攻目标：修复 `ui/test_panel.py` 对第一步旧宿主私有方法的残留调用，并补上后续组件化轮的审计门禁。
- 实际完成：
  - `ui/test_panel.py` 中 `_on_tp_start_step()` 的 `step == 1` 分支已改为直接通过 `self.ctrl.sim_state.loop_test_mode + enter/exit_loop_test_mode()` 驱动。
  - 修复后，第一步开始/退出测试不再依赖 `PowerSyncUI._on_toggle_loop_test_mode()` 这一已被 R22 移除的宿主私有方法。
  - `MAINTENANCE_CHECKLIST.md` §5 已新增“悬空宿主调用扫描”硬门禁，要求后续组件化轮强制执行 `_on_toggle_*` 搜索。
- 删除了哪些旧代码：
  - 删除 `ui/test_panel.py` 中对 `_on_toggle_loop_test_mode()` 的宿主残留调用。
- 接口变化：
  - 无新增接口；仅将 `test_panel.py` 的第一步切换逻辑对齐到现有 controller 公开能力。
- 耦合度变化：
  - `test_panel.py` 不再依赖已迁移步骤组件对应的宿主私有方法。
  - 本轮属于 R22 验收遗漏回归的最小范围热修复，不改变当前 5-Mixin 基线。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；step 1-5 的完整手动 GUI 冒烟仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 27：`PtExamTab` 组件化

### 第 25 轮 (2026-04-15)：Phase 3-4（SyncTestTab 组件化）
- 本轮唯一主攻目标：将 `SyncTestTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/sync_test_tab.py` 已彻底改写：删除 `SyncTestTabMixin`，新增 `SyncTestTabAPI(Protocol)` 与 `SyncTestTab(QWidget)`。
  - `SyncTestTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_waveform_tab` 回调注入。
  - `app/main.py` 为第五步流程补了 3 个薄转发方法：`get_sync_test_steps()`、`is_sync_test_complete()`、`is_gen_synced()`。
  - `ui/main_window.py` 已从基类列表中删除 `SyncTestTabMixin`，改为组合装配 `self._sync_test_tab = SyncTestTab(...)`，并将渲染路径切换为 `self._sync_test_tab.render(p)`。
  - 第五步状态文本、步骤列表和两轮记录标签已统一切到 `ui.tabs._step_style` 的共享 helper，不再保留本地内联 `setStyleSheet(...)`。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/sync_test_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - SyncTestTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `SyncTestTabAPI + 1 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 6 个 UI Mixin 减至 5 个。
- 耦合度变化：
  - `SyncTestTab` 内部 `self.ctrl` / `self.sync_svc` 引用已收敛为 0。
  - Phase 3 的组件化范式已连续在前四个步骤 Tab 上复用成功。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；完整人工点击第五步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 26：`PtExamTab` 组件化

### 第 24 轮 (2026-04-15)：Phase 3-3（PtPhaseCheckTab 组件化）
- 本轮唯一主攻目标：将 `PtPhaseCheckTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/pt_phase_check_tab.py` 已彻底改写：删除 `PtPhaseCheckTabMixin`，新增 `PtPhaseCheckTabAPI(Protocol)` 与 `PtPhaseCheckTab(QWidget)`。
  - `PtPhaseCheckTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第三步流程补了 1 个薄转发方法：`get_pt_phase_check_steps()`。
  - `ui/main_window.py` 已从基类列表中删除 `PtPhaseCheckTabMixin`，改为组合装配 `self._pt_phase_check_tab = PtPhaseCheckTab(...)`，并将渲染路径切换为 `self._pt_phase_check_tab.render(p)`。
  - 第三步色调映射继续复用 `ui.tabs._step_style.tone_from_color()`；`meter_phase_match` 的三态颜色分支仍保留 `_qs(...)` fallback。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/pt_phase_check_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - PtPhaseCheckTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `PtPhaseCheckTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 7 个 UI Mixin 减至 6 个。
- 耦合度变化：
  - `PtPhaseCheckTab` 内部 `self.ctrl` / `self.pt_phase_svc` 引用已收敛为 0。
  - Phase 3 的组件化范式已连续在前三个步骤 Tab 上复用成功。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；组件级离屏实例化与 render 校验通过，完整人工点击第三步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 25：`SyncTestTab` 组件化

### 第 23 轮 (2026-04-14)：Phase 3-2（PtVoltageCheckTab 组件化）
- 本轮唯一主攻目标：将 `PtVoltageCheckTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/pt_voltage_check_tab.py` 已彻底改写：删除 `PtVoltageCheckTabMixin`，新增 `PtVoltageCheckTabAPI(Protocol)` 与 `PtVoltageCheckTab(QWidget)`。
  - `PtVoltageCheckTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第二步流程补了 1 个薄转发方法：`get_pt_voltage_check_steps()`。
  - `ui/main_window.py` 已从基类列表中删除 `PtVoltageCheckTabMixin`，改为组合装配 `self._pt_voltage_check_tab = PtVoltageCheckTab(...)`，并将渲染路径切换为 `self._pt_voltage_check_tab.render(p)`。
  - 第二步颜色映射已统一复用 `ui.tabs._step_style.tone_from_color()`，未在组件内重复造一套样式辅助。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/pt_voltage_check_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - PtVoltageCheckTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `PtVoltageCheckTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 8 个 UI Mixin 减至 7 个。
- 耦合度变化：
  - `PtVoltageCheckTab` 内部 `self.ctrl` / `self.pt_voltage_svc` 引用已收敛为 0。
  - 第二阶段组件化继续沿用“独立 QWidget 自持状态 + 最小 Protocol 接口”的固定范式。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；组件级离屏实例化与 render 校验通过，完整人工点击第二步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 24：`PtPhaseCheckTab` 组件化

### 第 22 轮 (2026-04-14)：Phase 3-1（LoopTestTab 组件化概念验证）
- 本轮唯一主攻目标：将 `LoopTestTabMixin` 改造为独立 `QWidget` 组件，作为 Phase 3 的范式试点。
- 实际完成：
  - `ui/tabs/loop_test_tab.py` 已彻底改写：删除 `LoopTestTabMixin`，新增 `LoopTestTabAPI(Protocol)` 与 `LoopTestTab(QWidget)`。
  - `LoopTestTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第一步流程补了 3 个薄转发方法：`get_loop_test_steps()`、`get_current_loop_phase_match()`、`is_loop_test_complete()`。
  - `ui/main_window.py` 已从基类列表中删除 `LoopTestTabMixin`，改为组合装配 `self._loop_test_tab = LoopTestTab(...)`，并将渲染路径切换为 `self._loop_test_tab.render(p)`。
  - `ui/tabs/_step_style.py` 已补充通用按钮 tone fallback 与 `tone_from_color()`，支撑独立 QWidget 复用步骤页样式辅助。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/loop_test_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - LoopTestTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `LoopTestTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 9 个 UI Mixin 减至 8 个。
- 耦合度变化：
  - `LoopTestTab` 内部 `self.ctrl` / `self.loop_svc` 引用已收敛为 0。
  - 第一阶段组件化已从“宿主共享命名空间”切换为“独立 QWidget 自持状态”模式。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；离屏启动级冒烟已尝试，完整人工点按流程需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 23：`PtVoltageCheckTab` 组件化

### 第 21 轮 (2026-04-14)：Phase 2-4（评分域独立快照测试）
- 本轮唯一主攻目标：为四个评分域各自建立输入/输出级别的独立快照测试，补齐 Phase 2 的最后一块安全网。
- 实际完成：
  - 新增 `tests/support/scoring_fixtures.py`，手动构造 `NORMAL_CONTEXT` / `FAULT_CONTEXT` 两套 `ScoringContext` 夹具，不依赖 `AssessmentService` 组装路径。
  - 新增 4 个评分域测试文件：`tests/test_scoring_discipline.py`、`tests/test_scoring_step_quality.py`、`tests/test_scoring_fault_diagnosis.py`、`tests/test_scoring_blackbox_efficiency.py`。
  - 为四个评分域各补 2 份 JSON 快照基线（normal / fault），共新增 8 份 `tests/snapshots/scoring_*.json`。
  - 保持整链路评分快照测试不变，新增测试只覆盖评分域纯函数输入/输出。
- 删除了哪些旧代码：
  - 删除本文件顶部遗留的 Round 21 任务提示词，恢复 checklist 作为唯一长期事实来源的入口形态。
- 接口变化：
  - 无生产代码接口变化；仅新增测试侧 `ScoringContext` 夹具工厂与 4 组评分域独立快照。
- 耦合度变化：
  - 生产代码零耦合变化；评分系统的测试颗粒度从“整链路”补齐到“整链路 + 单评分域”双层保护。
- 快照测试：PASS（`pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（原 5 条 + 新 8 条快照均通过；既有 `assessment_*.json` 基线无改动）
- 下一轮起点：Phase 3 — UI 组件化（告别 Mixin），从 `LoopTestTab` 概念验证开始

### 第 20 轮 (2026-04-14)：Phase 2-3（`score_context` 改为 `ScoringContext` dataclass）
- 本轮唯一主攻目标：将 dict 型 `score_context` 升级为 `@dataclass(frozen=True) ScoringContext`，并把 4 个闭包抽成共享纯函数。
- 实际完成：
  - 在 `services/scoring/context.py` 新增 `ScoringContext`，显式收口评分阶段使用的 33 个数据字段，并补入 `step_enter_events` 这一处原先被闭包隐式捕获的隐藏依赖。
  - 在 `services/scoring/_common.py` 新增 `count_present`、`trio_completion_score`、`nine_group_completion_score`、`first_step_index` 4 个纯函数，与原闭包行为保持一致。
  - 4 个评分域模块已统一改签为 `score_xxx(ctx: ScoringContext)`，所有 `ctx["xxx"]` 访问已切换为 `ctx.xxx`。
  - `services/assessment_service.py` 中 `score_context = {...}` 已改为构造 `ScoringContext(...)`，并删除主文件内 4 个闭包定义。
- 删除了哪些旧代码：
  - 删除 `services/assessment_service.py` 中 `first_step_index`、`trio_completion_score`、`nine_group_completion_score`、`count_present` 四处本地定义。
  - 删除 dict 版 `score_context` 组装结构及其对闭包的隐式注入。
- 接口变化：
  - 评分域模块签名从 `score_xxx(ctx: dict)` 改为 `score_xxx(ctx: ScoringContext)`。
  - `ScoringContext` 只承载数据字段，不包含方法与 `Callable` 字段；闭包能力全部改由 `_common.py` 中的纯函数显式提供。
- 耦合度变化：
  - `services/assessment_service.py` 行数 `429 -> 399`
  - `services/scoring/_common.py` 行数 `46 -> 79`
  - 新增 `services/scoring/context.py` `43` 行
  - `services/scoring/discipline.py` `107` 行
  - `services/scoring/step_quality.py` `296` 行
  - `services/scoring/fault_diagnosis.py` `106` 行
  - `services/scoring/blackbox_efficiency.py` `186` 行
- 快照测试：PASS（`python -m pytest tests/ -q -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（`services/scoring/*.py` 中 `ctx["` 搜索结果为 0；`services/assessment_service.py` 中 4 个原闭包定义搜索结果为 0；`tests/snapshots/` 无改动）
- 下一轮起点：Phase 2-4（可选）— 评分域独立快照测试；或转入 Phase 3 — UI 组件化（由 Round 21 决策）

### 第 18 轮 (2026-04-13)：Phase 2-1（评分事件常量化 + AssessmentContext 建立）
- 本轮唯一主攻目标：为 `AssessmentService` 建立事件常量与 `AssessmentContext` 输入边界，切断 `build_result()` 对 ctrl 的入口依赖。
- 实际完成：
  - 在 `domain/assessment.py` 新增 `AssessmentEventType` 常量类，集中定义评分事件类型。
  - 在 `domain/assessment.py` 新增 `AssessmentContext` dataclass，并落地 `from_snapshot_and_ctrl(snapshot, ctrl)`。
  - `services/assessment_service.py` 的 `build_result()` 已改签为 `build_result(session, context)`。
  - `services/assessment_coordinator.py` 与 `tests/test_assessment_snapshot.py` 已统一通过 `AssessmentContext.from_snapshot_and_ctrl(...)` 调用评分入口。
  - 真实生产路径与快照构造路径中的事件类型读取/主要入队点已改为常量引用。
- 删除了哪些旧代码：
  - 删除 `AssessmentService.build_result()` 入口段中基于 `self._ctrl` 的 13 处兜底读取。
  - 删除 `AssessmentService.__init__(self, ctrl)` 的 ctrl 依赖，改为无参构造。
- 接口变化：
  - `AssessmentService.build_result(session)` -> `AssessmentService.build_result(session, context)`
  - `AssessmentContext` 仅封装评分入口原本依赖 ctrl 兜底读取的记录/完成态/故障修复状态，不额外扩张边界。
- 耦合度变化：
  - `services/assessment_service.py` 中 `self._ctrl` 引用数 `13 -> 0`
  - `services/assessment_service.py` 行数 `791 -> 784`
- 快照测试：PASS（`python -m pytest tests/ -q -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（评分结果与现有快照基线保持一致，`tests/snapshots/` 无改动）
- 下一轮起点：Phase 2-2 — 按评分域拆分为纯函数模块（`services/scoring/` 子包）

### 第 19 轮 (2026-04-14)：Phase 2-2（按评分域拆分为纯函数模块）
- 本轮唯一主攻目标：将 `AssessmentService` 从单体评分器收口为“组装器 + 4 个评分域纯函数模块”。
- 实际完成：
  - 新增 `services/scoring/` 子包与 5 个文件：`_common.py`、`discipline.py`、`step_quality.py`、`fault_diagnosis.py`、`blackbox_efficiency.py`
  - 建立 `make_score_item(...)` 纯函数，替代原 `add_score_item` / `add_penalty` 闭包语义
  - 已将 A/B/C/D/E/F/G/H 八段评分逻辑按评分域迁出，`build_result()` 改为顺序组装 4 个评分器返回值
  - 已删除 `AssessmentService` 中全部 `_score_*` 方法，以及 `score_context` 中闭包注入键
- 删除了哪些旧代码：
  - 删除 `services/assessment_service.py` 中 8 个 `_score_xxx` 方法
  - 删除 `build_result()` 内的 `add_score_item` / `add_penalty` 两个闭包
- 接口变化：
  - `services/scoring/discipline.py` → `score_discipline(ctx)`
  - `services/scoring/step_quality.py` → `score_step_quality(ctx)`
  - `services/scoring/fault_diagnosis.py` → `score_fault_diagnosis(ctx)`
  - `services/scoring/blackbox_efficiency.py` → `score_blackbox_efficiency(ctx)`
  - `score_context` 仍保持 dict，留待下一轮做 `ScoringContext` dataclass 化
- 耦合度变化：
  - `services/assessment_service.py` 行数 `784 -> 429`
  - `services/scoring/__init__.py` `11` 行
  - `services/scoring/_common.py` `46` 行
  - `services/scoring/discipline.py` `107` 行
  - `services/scoring/step_quality.py` `299` 行
  - `services/scoring/fault_diagnosis.py` `105` 行
  - `services/scoring/blackbox_efficiency.py` `185` 行
- 快照测试：PASS（`python -m pytest tests/ -q -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（评分结果与现有快照基线保持一致，`tests/snapshots/` 无改动）
- 下一轮起点：Phase 2-3 — ScoringContext dataclass 化

### 第 16 轮 (2026-04-13)：Phase 1 收尾（第二阶段：FlowMgr / AssessmentCoord / AssessmentService 公开化 + 剩余壳清理）
- 本轮唯一主攻目标：公开 `flow_mgr / assessment_coord / assessment_svc`，删除 Controller 中剩余的流程策略与考核生命周期转发壳
- 实际完成：
  - 将 `self._flow_mgr`、`self._assessment_coord`、`self._assessment_svc` 分别公开为 `self.flow_mgr`、`self.assessment_coord`、`self.assessment_svc`
  - UI、服务层、测试替身中的旧调用点已改为 `ctrl.<service>.method(...)`
  - `tests/support/stubs.py` 已同步 `flow_mgr` 与 `assessment_coord` 公开句柄，保留原有直接方法签名
- 删除了哪些旧代码：
  - `app/main.py` 中 `FlowModeManager` 相关 21 个纯转发壳
  - `app/main.py` 中 `AssessmentCoordinator` 相关 11 个纯转发壳
  - 本轮共清理剩余纯转发壳 32 个
- 接口变化：
  - Controller 不再承担流程策略与考核生命周期查询/命令的转发职责
  - `AssessmentService` 仅完成句柄公开化，内部实现保持不变，Phase 2 再拆
- 耦合度变化：
  - `app/main.py` 行数 `483 -> 502`
  - Controller 已完成 12 个服务句柄的公开化与壳清理，正式退回编排层
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（按服务族逐步推进并持续回归）
- 下一轮起点：Phase 2 — 定义 `AssessmentContext` 并切断评分对 ctrl 的依赖

### 第 15 轮 (2026-04-13)：Phase 1 收尾（第一阶段：9 个服务句柄公开化 + 纯转发壳清理）
- 本轮唯一主攻目标：只处理 9 个低频/局部服务句柄，不触碰 `FlowModeManager`、`AssessmentCoordinator`、`AssessmentService`
- 实际完成：
  - 将 `hw`、`phase_resolver`、`blackbox_handler`、`fault_mgr`、`loop_svc`、`pt_voltage_svc`、`pt_phase_svc`、`pt_exam_svc`、`sync_svc` 公开化
  - UI 与跨服务调用点已改为 `ctrl.<service>.method(...)`
  - `tests/support/stubs.py` 已补齐本轮涉及的公开服务句柄，保留原有直接方法签名
  - `FlowMgr / AssessmentCoord / AssessmentService` 零改动，留待下一轮
- 删除了哪些旧代码：
  - `app/main.py` 中上述 9 组服务对应的 34 个纯转发壳
  - 其中包含硬件动作、相序解析、黑盒修复、故障门禁、Loop/PT/Sync 五步测试查询壳
- 接口变化：
  - Controller 不再对这 9 组能力提供旧的 `ctrl.method(...)` 壳入口
  - 外部统一改为 `ctrl.<service>.method(...)`
- 耦合度变化：
  - `app/main.py` 行数 `725 -> 483`
  - Controller 主文件已低于 500 行，四类已迁出能力的旧壳层基本清空
- 快照测试：PASS（按批次持续执行 `python -m pytest tests/ -v -p no:cacheprovider`，最终 5/5 通过）
- 回归清单：PASS（每完成一组服务句柄都跑一次快照）
- 下一轮起点：Phase 1 收尾（第二阶段）— 公开 `FlowMgr` / `AssessmentCoord` 并删除剩余壳层

### 第 14 轮 (2026-04-10)：Phase 1 第五步（拆出 HardwareActions）
- 本轮唯一主攻目标：将发电机启停、断路器合分、即时同期三类硬件动作从 Controller 中独立出去
- 实际完成：
  - 新增 `services/hardware_actions.py`
  - 将 `get_preclose_flow_blockers`、`instant_sync`、`toggle_engine`、`toggle_breaker` 及 4 个私有辅助方法迁入独立硬件动作模块
  - `PowerSyncController` 新增 `self._hw = HardwareActions(self)`
  - `app/main.py` 中 4 个对外硬件动作方法已改为转发壳，外部调用者零改动
  - 明确保留 `toggle_pause()` 在 Controller，不把直接操作 UI 控件的方法带入服务模块
- 删除了哪些旧代码：
  - `app/main.py` 中直接实现的合闸前流程检查、即时同期、发电机启停、断路器合分逻辑
  - `app/main.py` 中私有 helper：`_should_enforce_pt_exam_before_close`、`_should_limit_close_to_selected_pt_target`、`_on_engine_blocked`、`_on_breaker_blocked`
- 接口变化：
  - 新增 `HardwareActions(ctrl)`，本轮允许持有 ctrl
  - Controller 对外仍通过 `get_preclose_flow_blockers()`、`instant_sync()`、`toggle_engine()`、`toggle_breaker()` 提供原签名接口
- 耦合度变化：
  - `app/main.py` 行数 `849 -> 725`
  - 硬件动作实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 收尾 — 删除 Controller 中已迁出的纯转发壳层

### 第 13 轮 (2026-04-10)：Phase 1 第四步（拆出 PhaseOrderResolver）
- 本轮唯一主攻目标：将 PT 节点解析、相序判定、回路节点相位解析从 Controller 中独立出去
- 实际完成：
  - 新增 `services/phase_order_resolver.py`
  - 将 `resolve_pt_node_plot_key`、`get_pt_phase_sequence`、`resolve_loop_node_phase` 迁入独立解析器
  - `PowerSyncController` 新增 `self._phase_resolver = PhaseOrderResolver(self)`
  - `app/main.py` 中原有 3 个相序解析方法已改为转发壳，外部调用者零改动
  - `tests/support/stubs.py` 新增 `self._phase_resolver = PhaseOrderResolver(self)`，并将 3 个旧手工实现替换为转发壳
- 删除了哪些旧代码：
  - `app/main.py` 中直接实现的 PT 节点解析、相序判定、回路节点相位解析逻辑
  - `tests/support/stubs.py` 中对应 3 个方法的手工实现
- 接口变化：
  - 新增 `PhaseOrderResolver(ctrl)`，本轮允许持有 ctrl
  - Controller 与 ControllerStub 对外方法签名保持不变，仍通过 `resolve_xxx()` / `get_pt_phase_sequence()` 调用
- 耦合度变化：
  - `app/main.py` 行数 `910 -> 849`
  - 相序解析实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `HardwareActions`

### 第 12 轮 (2026-04-10)：Phase 1 第三步（拆出 BlackboxRepairHandler）
- 本轮唯一主攻目标：将黑盒运行态构造、黑盒修复执行、黑盒到相序同步从 Controller 中独立出去
- 实际完成：
  - 新增 `services/blackbox_repair_handler.py`
  - 将 `BlackboxRepairOutcome`、`get_blackbox_runtime_state`、`apply_blackbox_repair_attempt`、`_compute_pt1_net_order`、`sync_pt1_blackbox_to_phase_orders`、`sync_g2_blackbox_to_phase_orders` 迁入独立处理器
  - `PowerSyncController` 新增 `self._blackbox_handler = BlackboxRepairHandler(self)`
  - `app/main.py` 中对外暴露的 4 个黑盒相关方法已改为转发壳，`set_g2_terminal_fault()` 继续通过 Controller 转发调用同步方法
- 删除了哪些旧代码：
  - `app/main.py` 顶部内嵌的 `BlackboxRepairOutcome` dataclass
  - `app/main.py` 中直接实现的黑盒修复与黑盒到相序同步逻辑
  - `app/main.py` 中私有 helper `_compute_pt1_net_order`
- 接口变化：
  - 新增 `BlackboxRepairHandler(ctrl)`，本轮允许持有 ctrl
  - Controller 对外方法签名保持不变，外部仍通过 `ctrl.xxx()` 调用
- 耦合度变化：
  - `app/main.py` 行数 `1076 -> 910`
  - 黑盒修复实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `PhaseOrderResolver`

### 第 11 轮 (2026-04-10)：Phase 1 第二步（拆出 AssessmentCoordinator）
- 本轮唯一主攻目标：将考核会话生命周期与测试进度门禁从 Controller 中独立出去
- 实际完成：
  - 新增 `services/assessment_coordinator.py`
  - 将 `StepProgressSnapshot` 与 11 个考核会话/门禁方法迁入独立协调器
  - `PowerSyncController` 新增 `self._assessment_coord = AssessmentCoordinator(self)`
  - `app/main.py` 中原有 11 个方法已改为转发壳，外部调用者零改动
  - `self.assessment_session` 字段仍保留在 Controller 上，继续作为真值源
- 删除了哪些旧代码：
  - `app/main.py` 中内嵌的 `StepProgressSnapshot` dataclass
  - `app/main.py` 中直接实现的考核会话生命周期与测试进度门禁逻辑
- 接口变化：
  - 新增 `AssessmentCoordinator(ctrl)`，本轮允许持有 ctrl
  - Controller 对外方法签名保持不变，仍通过 `ctrl.xxx()` 调用
- 耦合度变化：
  - `app/main.py` 行数 `1276 -> 1076`
  - 考核会话实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `BlackboxRepairHandler`

### 第 10 轮 (2026-04-09)：Phase 1 第一步（拆出 FlowModeManager）
- 本轮唯一主攻目标：将 flow mode 策略定义与查询从 Controller 中独立出去
- 实际完成：
  - 新增 `services/flow_mode_manager.py`
  - 将 `FlowModePolicy`、`FLOW_MODE_POLICIES`、flow mode 查询方法移入独立模块
  - `PowerSyncController` 改为持有 `self._flow_mgr`
  - 保留 Controller 上的同名转发方法，外部调用者零改动
  - `test_flow_mode` 改为通过 Controller 属性代理到 `FlowModeManager`
  - `tests/support/stubs.py` 已补齐 `FlowModeManager` 替身接入
- 删除了哪些旧代码：
  - `app/main.py` 中内嵌的 `FlowModePolicy`
  - `app/main.py` 中内嵌的 `FLOW_MODE_POLICIES`
  - `app/main.py` 中直接实现的 flow mode 策略查询逻辑
- 接口变化：
  - 新增 `FlowModeManager(test_flow_mode: str)` 纯查询模块
  - `PowerSyncController.test_flow_mode` 改为代理属性，对外接口不变
- 耦合度变化：
  - flow mode 策略定义已从 Controller 主文件剥离
  - 外部 UI / Service 调用点零改动
  - `app/main.py` 行数 `1340 -> 1276`
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `AssessmentCoordinator`

### 第 9 轮 (2026-04-09)：Phase 0 收尾（Mixin 属性交叉引用扫描）
- 本轮唯一主攻目标：输出 `docs/mixin_dependency_map.md`，闭环 Phase 0
- 实际完成：
  - 新增 `docs/mixin_dependency_map.md`
  - 扫描 `main_window + 9 个 Mixin` 的显式 `self.xxx` 创建属性
  - 输出共享属性交叉引用表
  - 统计各 Mixin 的 `self.ctrl` 使用次数
  - 给出 Phase 3 的迁移顺序与拆分风险点
- 删除了哪些旧代码：无（本轮只做静态分析文档）
- 接口变化：无业务接口变化
- 耦合度变化：无代码耦合变化；已形成 UI 继承链依赖基线，后续可按图拆分
- 快照测试：未执行（本轮未修改业务代码）
- 回归清单：未执行（本轮未修改业务代码）
- 下一轮起点：Phase 1 — 拆出 `FlowModeManager`

### 第 8 轮 (2026-04-09)：Phase 0 安全网建设（快照测试）
- 本轮唯一主攻目标：为 PhysicsEngine 和 AssessmentService 建立最小回归安全网
- 实际完成：
  - 新增 `tests/support/stubs.py`，构造无 UI 的 `ControllerStub`
  - 新增 `tests/test_physics_snapshot.py`
  - 新增 `tests/test_assessment_snapshot.py`
  - 生成 4 份快照基线：`physics_normal.json`、`physics_fault_E01.json`、`assessment_normal.json`、`assessment_fault_random.json`
- 删除了哪些旧代码：无（本轮只新增测试，不动业务逻辑）
- 接口变化：无业务接口变化；仅新增测试侧替身与快照序列化工具
- 耦合度变化：
  - 已验证 `PhysicsEngine` 可脱离 PyQt5/UI 实例化并运行
  - 已验证 `AssessmentService.build_result()` 可在最小 ctrl 替身下独立运行
- 快照测试：PASS（`python -m pytest tests/`）
- 回归清单：PASS（基于快照与测试入口验证）
- 下一轮起点：完成 `docs/mixin_dependency_map.md`

### 早期摘要（第 1 - 4 轮）
- 已完成：`C1`、`C2（第一步）`、`H1`、`H2`
- 关键结果：
  - 切断 `physics -> ui` 事故弹窗直连
  - 拆出 `FaultManager`
  - `_tick()` 拆成物理 / 渲染两个异常边界
  - `E01/E02/E03` 事故弹窗收口为统一入口，并删除 `_legacy` 死代码

### 第 5 轮：控制器与 UI 解耦
- 本轮目标：去掉控制器对具体 UI 控件的直接写入
- 实际完成：`H3`
- 删除了哪些旧代码：E04 中对 PT3 比率控件的直接写入
- 当前阻塞：评分主函数仍过长
- 下一轮起点：修 `H4`

### 第 6 轮：评分主函数第一阶段拆分
- 本轮目标：拆 `build_result()` 巨石函数
- 实际完成：`H4（第一步）`
- 删除了哪些旧代码：无功能删除，完成 helper 化收口
- 当前阻塞：评分系统仍未按文件拆开
- 下一轮起点：修 `H5`

### 第 7 轮：仲裁时间步长修复
- 本轮目标：去掉死母线倒计时中的固定 `0.033`
- 实际完成：`H5`
- 删除了哪些旧代码：移除死母线逻辑里的固定帧时间假设
- 当前阻塞：主文件体积依旧过大
- 下一轮起点：Phase 0 安全网建设

---

## 10. 下一轮默认起点

如果后续没有新的明确指令，默认按以下顺序继续：

**Phase 4（R33 起，2-3 轮）：**
1. 引入 `ControllerSignals(QObject)`，核心三信号 `render_state_updated / step_state_changed / assessment_finished` 替代轮询式 `render_visuals(rs)`。
2. 收口 `AssessmentCoordinator` / `BlackboxRepairHandler` / `PhaseOrderResolver` / `HardwareActions` 对 `self._ctrl` 的直接引用，改为显式参数 / State 注入。
3. 清理旧键名兼容逻辑与 `pt_phase_orders` / `blackbox_order` 隐式同步；补 `domain/` / `services/` 类型标注。

---

## 11. 每轮更新模板

后续每一轮重构结束后，必须更新 §9 的轮次历史：

```text
### 第 N 轮 (YYYY-MM-DD)：[主攻目标名]
- 本轮唯一主攻目标：
- 实际完成：
- 删除了哪些旧代码：
- 接口变化：（新模块的输入/输出边界是什么）
- 耦合度变化：（哪个文件的 ctrl 引用数下降了多少）
- 快照测试：PASS / FAIL（失败原因）
- 回归清单：PASS / FAIL
- 下一轮起点：
```

---

## 12. 本文件使用规则

- 新对话开始时，先读取本文件。
- 如需刷新大文件基线，先运行 `python scripts/report_large_files.py`。
- 先看：
  - §3 当前总体进度
  - §9 已完成进度
  - §10 下一轮默认起点
- 未经确认，不得跳过当前 Phase 直接做后续 Phase 的大范围重构。
- 每次完成后，本文件优先级高于临时对话记忆。

---
