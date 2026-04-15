<!-- ─────────── 第 26 轮提示词（复制给执行型 AI） ─────────── -->

```text
你是本仓库的执行型重构 AI。本轮任务：Phase 3 — Round 26：test_panel.py 宿主残留调用热修复。
本轮不是组件化轮，而是对 R22 遗留回归的最小范围修复 + 审计清单加固。严格按范围执行，不做额外重构。

─────────────────────────────────────
一、背景与问题根因
─────────────────────────────────────
• 仓库路径：/Users/promise/Downloads/3/Intership/ThreePhase_entier/ThreePhase
• 当前 PowerSyncUI 继承链：5-Mixin（本轮不减 Mixin，维持 5）
• Python 环境：/Users/promise/opt/anaconda3/envs/power_gui/bin/python
• 快照测试基线：13 passed

【问题链路】
  - ui/test_panel.py:1216 在 `_on_tp_start_step` 的 step==1 分支仍调用
      self._on_toggle_loop_test_mode()
  - 但 R22 已将切换逻辑迁进 LoopTestTab._on_toggle_loop_mode（ui/tabs/loop_test_tab.py:197）
  - PowerSyncUI 现在只持有组件实例（ui/main_window.py:117），不再拥有宿主私有方法
  - 结果：进入/退出第一步测试时抛 AttributeError —— 属于"宿主残留调用"

【定性】
  - 不是 service/controller 问题
  - 是 test_panel.py 对旧 UI 宿主私有方法的遗留耦合
  - 验证了 test_panel.py 仍是最大风险文件

─────────────────────────────────────
二、本轮唯一目标
─────────────────────────────────────
  1. 修复 ui/test_panel.py:1213 `_on_tp_start_step` 的 step==1 分支，改为通过 Controller 公开接口驱动
  2. 在 MAINTENANCE_CHECKLIST.md §5（审计清单）新增"跨面板/跨 Tab 悬空调用扫描"硬门禁，防止 R27+ 再犯
  3. 在 §9 轮次历史记录本轮为"R22 验收遗漏热修复"

─────────────────────────────────────
三、必须的修改（只改这一处代码）
─────────────────────────────────────
把 ui/test_panel.py:1213-1216 的：

    def _on_tp_start_step(self):
        step = self._current_test_step()
        if step == 1:
            self._on_toggle_loop_test_mode()

改为：

    def _on_tp_start_step(self):
        step = self._current_test_step()
        if step == 1:
            if self.ctrl.sim_state.loop_test_mode:
                self.ctrl.exit_loop_test_mode()
            else:
                self.ctrl.enter_loop_test_mode()

语义说明：
  - 与 LoopTestTab._on_toggle_loop_mode 完全一致（后者读 self._api.sim_state.loop_test_mode
    并调用 enter/exit_loop_test_mode）
  - step 2-5 分支已经是这种"读状态 + 公开方法"模板，step 1 也对齐

─────────────────────────────────────
四、禁止事项（硬门禁）
─────────────────────────────────────
✗ 禁止在 PowerSyncUI 中重新补 _on_toggle_loop_test_mode 兼容壳（会把刚拆掉的宿主耦合缝回来）
✗ 禁止让 test_panel.py 调用 self._loop_test_tab._on_toggle_loop_mode()（跨组件私有调用，更糟）
✗ 禁止修改 services/ / domain/ / adapters/ / tests/ 下任何文件
✗ 禁止顺手重构 test_panel.py 其他内容（本轮是热修复，不是 test_panel 拆分）
✗ 禁止改动任何 ui/tabs/*.py
✗ 禁止新增/修改 Controller 公开方法（enter_loop_test_mode / exit_loop_test_mode / sim_state 已存在，直接用）

─────────────────────────────────────
五、审计清单加固（本轮必须同步落地）
─────────────────────────────────────
在 MAINTENANCE_CHECKLIST.md §5 新增以下硬门禁项（作为 R27 及之后所有组件化轮的必检项）：

  【悬空宿主调用扫描】每轮组件化结束后必须执行：
    grep -rn "_on_toggle_\(loop\|pt_voltage\|pt_phase\|sync\)" ui/
  结果必须只出现在组件自身文件内（ui/tabs/*_tab.py），
  不得出现在 ui/test_panel.py、ui/main_window.py 或其他兄弟模块。

说明加一句：
  "R22 验收时遗漏了 test_panel.py 对宿主私有方法的调用，导致 step 1 切换抛 AttributeError，
   R26 补修。后续组件化轮必须执行此扫描，防止同类回归。"

─────────────────────────────────────
六、验收自检（完成后必须全绿才算收工）
─────────────────────────────────────
在仓库根执行并粘贴输出：
  1) grep -rn "_on_toggle_loop_test_mode" --include="*.py"
       → 无匹配（既不在 test_panel.py 也不在 PowerSyncUI）
  2) grep -rn "_on_toggle_\(loop\|pt_voltage\|pt_phase\|sync\)" ui/
       → 仅在 ui/tabs/*_tab.py 内出现
  3) git diff --name-only services domain adapters tests ui/tabs ui/main_window.py
       → 空
  4) git diff --name-only
       → 仅应包含 ui/test_panel.py、MAINTENANCE_CHECKLIST.md
  5) /Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q
       → 13 passed
  6) 手动 GUI 冒烟（由用户执行并反馈）：
     • 启动 app，切到底部测试面板，选 step 1
     • 点"开始第一步" → 应进入回路检查模式，无 AttributeError
     • 点"退出第一步" → 应正常退出，无 AttributeError
     • 切 step 2/3/4/5，各自点一次"开始/退出"，确认均无回归

─────────────────────────────────────
七、交付物
─────────────────────────────────────
请仅修改以下 2 个文件，且只修改这 2 个：
  • ui/test_panel.py           （step==1 分支改为 Controller 公开接口，约 4 行）
  • MAINTENANCE_CHECKLIST.md   （§5 新增悬空宿主调用扫描门禁；§9 记录 R26 热修复）

完成后输出"第 26 轮已自检通过，待用户手动 GUI 冒烟验证"，然后等待我的审计。
禁止自行 git commit。
```

<!-- ─────────── 第 26 轮提示词 结束 ─────────── -->

# 维护与重构清单 v2

最后更新：`2026-04-15`

用途：
- 给人看：明确当前项目的维护边界、阶段目标、已完成进度。
- 给 AI 看：后续新对话先读本文件，再决定下一轮该做什么，不再重复讨论方向。

---

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
| 当前阶段 | Phase 3 — UI 组件化（进行中：LoopTestTab / PtVoltageCheckTab / PtPhaseCheckTab / SyncTestTab 已完成） |
| 已完成的高/严重问题 | `C1`、`C2(第一步)`、`H1`、`H2`、`H3`、`H4`、`H5` |
| 当前最大风险文件 | `ui/test_panel.py`(2417)、`ui/styles.py`(1007) |
| 下一轮默认起点 | Phase 3 — Round 27：PtExamTab 组件化 |

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
  - 输入接口：`pt_phase_orders` + `blackbox_orders` + `fault_config`（只读）
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
- [ ] **`PtExamTab`（20 处 ctrl 引用）**
- [ ] **`WaveformTab`（5 处 ctrl 引用，注意 matplotlib canvas 生命周期）**
- [ ] **`CircuitTab`（10 处 ctrl 引用）**
- [ ] **`ControlPanel`（12 处 ctrl 引用）**
- [ ] **`TestPanel`（111 处 ctrl 引用）— 最后做，最复杂**
  - 先按步骤拆成 5 个独立 StepWidget
  - 每个 StepWidget 接收自己步骤的 State + 有限命令回调
  - TestPanel 本身变成纯容器：装配 5 个 StepWidget + 步骤导航

#### TestPanel 子拆分明细

- [ ] `ui/test_steps/step1_loop.py` — 第一步 UI 与交互
- [ ] `ui/test_steps/step2_voltage.py` — 第二步 UI 与交互
- [ ] `ui/test_steps/step3_phase.py` — 第三步 UI 与交互
- [ ] `ui/test_steps/step4_exam.py` — 第四步 UI 与交互
- [ ] `ui/test_steps/step5_sync.py` — 第五步 UI 与交互
- [ ] `ui/test_steps/blackbox_dialogs.py` — 黑盒弹窗逻辑
- [ ] `ui/test_steps/score_dialogs.py` — 成绩单与结果弹窗
- [ ] `ui/test_steps/common.py` — 公共按钮、提示、文本助手
- [ ] 将步骤业务判断从 UI 中迁回状态/服务层，UI 只读取状态

完成标准：
- `PowerSyncUI` 不再使用 Mixin 多重继承，改为组合式装配。
- `ui/test_panel.py` 主文件降到 <= 500 行。
- 每个 Tab 组件是独立的 `QWidget`，可脱离其他 Tab 理解。
- 新增 UI 逻辑落在拆出的子模块中，不回写主文件。

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
- `ui/test_panel.py` 仍是当前最大风险文件。

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

**Phase 3：**
1. `PtExamTab` 组件化
2. `WaveformTab` / `CircuitTab` 顺序迁移
3. 最后处理 `ui/test_panel.py`

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
