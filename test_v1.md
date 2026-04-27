# Test V1 修复计划

## Summary
本轮不建议把当前 review block 里的问题一次性打包全修。更稳的顺序是先做“机械小修 + 死分支删除”，再做“封装/API 收口”，再做“运行时鲁棒性”，最后才进入 `circuit_tab.py` 的结构性拆分。这样每一轮的风险、验证面和回滚成本都更可控。

推荐拆成 4 个修复轮次 + 2 个明确延后专项。每轮都以“源码改动 + `pytest` 回归 + 目标性冒烟”闭环，不混入无关格式化或类型标注扫仓。

## Round 1：机械小修 + 死分支清除
目标：先把最确定、最不应继续带入后续重构的噪音和假入口清掉。

修复项：
- `C1`：完整删除 PT 黑盒渲染残留链路
  - 删除 controller 上硬编码 `False` 的 `get_pt_blackbox_mode()`
  - 删除 `CircuitTab` API 里的 `get_pt_blackbox_mode`
  - 删除 `circuit_tab.py` 中全部 `pt_blackbox_mode` 分支和 `draw_pt_blackbox_symbol()`
  - 落地时显式 grep：`pt_blackbox_mode`、`on_pt_blackbox_toggle`、`reshuffle_pt_phase_orders`、`get_pt_blackbox_mode`、`set_g2_terminal_fault`
  - 目标是把这条假功能链路一次删净，不保留“以后也许会接回”的壳
- `M2`：把 `pt_name in "PT1"` 改成明确元组判断，按 `PT1/PT2 -> gen1`、`PT3 -> gen2`
- `M3`：统一三点接线结果标签绿色为 `#2ecc71`
- `M7`：给 `TestPanelAPI` 和 `TestPanelWidget` 加 `__test__ = False`，先消掉 pytest collection warning，不做类重命名
- `m1`：删 `_pt_recorded()` 和注释条件 `#and not self._pt_recorded(pt_name)`
- `m2`：删 `app/main.py` 里重复的 section 分割注释
- `m6`：删 `CircuitTab.__init__` 中冗余的 `_psm_terminal_markers` 初始化

落地原则（#5 commit 粒度）：
- 本轮 7 项每项独立 commit，不合并提交。
- commit message 统一前缀，便于回溯和 bisect：
  - `R48-C1: 删除 PT 黑盒渲染残留链路`
  - `R48-M2: 修正 PT 名归属为元组判断`
  - `R48-M3: 统一三点接线绿色为 #2ecc71`
  - `R48-M7: 给 TestPanel{API,Widget} 加 __test__ = False`
  - `R48-m1: 删除未使用的 _pt_recorded 与注释残留`
  - `R48-m2: 清理 app/main.py 重复 section 分割`
  - `R48-m6: 删除 CircuitTab.__init__ 冗余的 markers 初始化`
- 顺序建议：先做 m1 / m2 / m6 / M3 / M7 这类 1–5 行的零风险项，再做 M2（语义改动），最后做 C1（删除约 50+ 行死代码）。万一回归，bisect 命中点最大概率在 C1，单独的 commit 直接 revert 即可。

这一轮不做：
- 不改 `SyncTestService` 的接口名
- 不动 `PhaseSeqMeterWidget` 的 API
- 不开始拆 `circuit_tab.py`
- 不混入 repo-wide 格式化

完成标准：
- 顶层 PT 黑盒渲染相关符号在生产路径中消失。可执行的硬验证（#6 grep 固化）：
  ```
  rg -n 'pt_blackbox_mode|on_pt_blackbox_toggle|reshuffle_pt_phase_orders|get_pt_blackbox_mode|set_g2_terminal_fault|draw_pt_blackbox_symbol' --type py
  ```
  期望命中范围：
  - 仅允许命中 `MAINTENANCE_CHECKLIST.md` 历史段、`test_v1.md` 自身（这两个是文档不算）
  - 任何 `app/`、`domain/`、`services/`、`ui/`、`tests/` 下的命中都视为本轮未完成，必须继续清
- `pytest` 不再出现 `PytestCollectionWarning`（grep 验证：`python -m pytest -q 2>&1 | grep -c PytestCollectionWarning` 应为 0）
- 三点接线原有行为不回归，拓扑页正常渲染（手动冒烟）

## Round 2：封装边界和小型接口收口
目标：把“已经有 public 意图，但内部仍穿透私有实现”的位置收口干净。

修复项：
- `M4`：把同步判断统一切到公共接口
  - 在 `SyncTestService` 上新增或提升 `is_gen_synced(...)`
  - controller 的 `is_gen_synced()` wrapper 改调公共名
  - `SyncTestService` 内部 4 个自调用点全部改调公共名
  - `tests/support/stubs.py` 增加/改成同名 public stub
  - 私有 `_is_gen_synced` 两种方案二选一并固定下来：
    - 推荐：直接删除
    - 备选：保留一轮，做薄委托到 `is_gen_synced`
  - 不建议长期双轨并存
- `M5`：给 `PhaseSeqMeterWidget` 增加 `current_sequence()`
  - 规则固定为：
    - `_status == "connected"` 时返回 `_sequence` 原值（**包括 `"FAULT"` 这种特殊值，原样透传，不被 `"unknown"` 吞掉**）
    - 其他状态（`hidden` / `waiting`）统一返回 `"unknown"`
  - 这条 `FAULT` 透传规则是为了保持当前行为不回归（#7 FAULT 语义）：[pt_phase_check_panel.py:158](ui/widgets/step_panels/pt_phase_check_panel.py#L158) 现有 `if seq == "unknown": return` 是阻断点，对 `"FAULT"` 是放行的，下游 `record_phase_sequence` 会按 `FAULT` 处理；新 API 必须保持这条放行路径。
  - `ui/main_window.py` 的 lambda 改调 public API，不再 `getattr(..., "_sequence", ...)`
  - 完成标准里加一条：手动冒烟时模拟 `connect_pt(pt, "FAULT")`，确认 step3 panel 能进入 `record_phase_sequence` 而不是被 `"unknown"` 拦掉
- `m7`：把相序接线状态收口成共享常量或 `StrEnum`
  - 推荐新增一个轻量共享状态定义：`IDLE / WIRING / READY`
  - **文件位置（#8 StrEnum 位置）**：本轮放在 `ui/_phase_wiring_state.py`，原因：V1 是纯 UI 门槛、不入 domain/services 是早前共识；放在 `ui/` 顶层而非 `ui/tabs/circuit_tab.py` 内部，是为了让 `pt_phase_check_panel.py` 能干净地 `from ui._phase_wiring_state import PhaseWiringStatus` 而无需依赖 circuit tab 模块。
  - 模块内最小定义：
    ```python
    # ui/_phase_wiring_state.py
    from enum import StrEnum

    class PhaseWiringStatus(StrEnum):
        IDLE = "idle"
        WIRING = "wiring"
        READY = "ready"
    ```
    （选 `StrEnum` 而不是 `Enum`，是为了保持 `== "wiring"` 这种字符串比较仍然成立，零行为变更）
  - `CircuitTab`、`control_panel.py`、`pt_phase_check_panel.py` 统一从该模块导入消费，去掉跨文件裸字符串比较
  - **后续路径**：Round 4 拆分 `circuit_tab.py` 时再把这个模块迁到 `ui/tabs/circuit_tab/_phase_wiring.py` 内，此时它的 import 路径变更但语义不变；本轮先放 `ui/` 顶层是因为 Round 4 还没发生

这一轮不做：
- 不改同步算法本身
- 不改相序仪渲染行为
- 不做 `circuit_tab.py` 大拆分

完成标准：
- controller 不再调用 service 私有同步方法
- 主窗口不再读取 widget 私有 `_sequence`
- 相序接线状态名不再散落为裸字符串

## Round 3：运行时鲁棒性和异常处理
目标：修复“出错后持续刷屏”和“异常被过宽吞掉”的运行时问题。

修复项：
- `M8`：为主循环 tick 异常增加熔断
  - 连续失败计数达到阈值后停止 timer
  - 保留首次 traceback 和状态栏/警告提示，避免 30Hz 刷屏
  - **阈值改为 `5`（#3 阈值修正）**：原推荐 30 等价于在 1 秒内打 30 行 traceback，跟”避免刷屏”的目标半冲突。`5` 的依据：
    - 主循环 30fps，5 次失败 ≈ 165ms，stderr 累计 5 行 traceback，肉眼可读
    - 现有 `_handle_tick_failure` 在第 3 次时已 statusBar 提示，第 5 次再停 timer，与现有提示节奏自然衔接（提示 → 短暂观察 → 熔断）
    - 留 2 次余量给”短暂偶发抖动”（如 GC 暂停 + matplotlib 重排），避免误熔断
  - `_clear_tick_failure_state()` 保持能在恢复路径中清零
  - 落地后行为：连续 5 次失败 → `self._timer.stop()` + `self.ui.show_warning(“物理引擎已停止...”)`；用户继续操作不会触发新 tick，避免 stderr 被淹
- `m5`：收窄 `_place_phase_seq_meter()` 的异常处理
  - **不再用 `try/except Exception`，改为显式哨兵（#4 除零哨兵修正）**
  - 实测 matplotlib 在首次绘制前不会抛异常（`get_position()` / `get_xlim()` / `get_ylim()` 返回单位 bbox 与默认 `(0, 1)` lim），原描述”首次绘制前 bbox 尚不可用”不准确
  - 真正可能炸的是 `(xlim[1] - xlim[0])` 或 `(ylim[1] - ylim[0])` 退化为 0 时的除零
  - 目标实现形态：
    ```python
    def _place_phase_seq_meter(self) -> None:
        mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
        bbox = self.ax_circuit.get_position()
        xlim = self.ax_circuit.get_xlim()
        ylim = self.ax_circuit.get_ylim()
        if xlim[1] == xlim[0] or ylim[1] == ylim[0]:
            cw, ch = self.canvas2.width(), self.canvas2.height()
            px, py = cw // 2, ch // 2
        else:
            ax_fx = (0.50 - xlim[0]) / (xlim[1] - xlim[0])
            ax_fy = (0.72 - ylim[0]) / (ylim[1] - ylim[0])
            fig_fx = bbox.x0 + ax_fx * (bbox.x1 - bbox.x0)
            fig_fy = bbox.y0 + ax_fy * (bbox.y1 - bbox.y0)
            cw, ch = self.canvas2.width(), self.canvas2.height()
            px = int(fig_fx * cw)
            py = int((1.0 - fig_fy) * ch)
        # ... 后续 move/show/raise 逻辑保持不变 ...
    ```
  - 真实渲染异常（matplotlib 内部错误等）从此不再被 `except Exception` 静默吞掉，会正常向上抛，被 Round 3 的 M8 熔断机制接住
- `m4` 可选只做局部，不做全仓
  - 如果本轮刚好改到 `circuit_tab.py` / `pt_phase_check_panel.py`，顺手把当前触及行的空格风格修齐
  - 不做 `ruff format .`

完成标准：
- 确定性 tick 异常不会继续无限刷 traceback
- 相序仪定位 fallback 只覆盖已知合法场景
- 本轮改动不引入新的静默吞错路径

## Round 4：`circuit_tab.py` 结构性拆分
目标：把当前最大风险文件从”混合职责单体”拆回可维护边界。这一轮单独做，不和前面小修混提。

### 物理布局（#2 subpackage 布局，必须钉死）

将 `ui/tabs/circuit_tab.py` 升级为 subpackage `ui/tabs/circuit_tab/`，与 R45 拆 `ui/widgets/control_panel/` 的做法保持一致。

落地后目录结构：
```
ui/tabs/circuit_tab/
├── __init__.py          # 暴露 CircuitTab 类（from .circuit_tab import CircuitTab；或直接把类定义放本文件）
├── _phase_wiring.py     # 见下”拆分边界”
├── _record_tables.py    # 见下”拆分边界”
└── _draw_topology.py    # 见下”拆分边界”
```

外部 import 路径**必须保持不变**：
```python
# 落地前（现状）：
from ui.tabs.circuit_tab import CircuitTab

# 落地后（不变）：
from ui.tabs.circuit_tab import CircuitTab     # 指向 ui/tabs/circuit_tab/__init__.py
```

git 操作建议：
- `git mv ui/tabs/circuit_tab.py ui/tabs/circuit_tab/__init__.py`（保留历史 blame）
- 然后从 `__init__.py` 内逐块拆出到 `_phase_wiring.py` / `_record_tables.py` / `_draw_topology.py`，每搬一块独立 commit
- 不允许出现 `ui/tabs/circuit_tab.py` 与 `ui/tabs/circuit_tab/` 同时存在的中间状态（Python 解析会冲突）

### 拆分边界

- `_phase_wiring.py`
  - `PhaseWiringSession`
  - `get_phase_wiring_status()` / `get_phase_wiring_active_pt()`
  - `handle_phase_wiring_click()`
  - `connect_phase_seq_meter()` / `disconnect_phase_seq_meter()`
  - `_show_phase_seq_result()`
  - `_render_phase_wiring()`
  - **Round 2 在 `ui/_phase_wiring_state.py` 引入的 `PhaseWiringStatus` 枚举本轮迁入此处**：源文件 `ui/_phase_wiring_state.py` 删除，所有 import 路径改为 `from ui.tabs.circuit_tab._phase_wiring import PhaseWiringStatus`（消费方在 Round 2 时只需从一个地方迁到另一个地方，与本轮变更同步）
- `_record_tables.py`
  - PT 记录表渲染
  - `_mk` 一类表格构造 helper
- `_draw_topology.py`
  - `_draw_circuit_content()` 主体
  - 母排、CT、breaker、PT 端子盒、loop 动画等纯绘图逻辑

### 保留不变的外部接口

- `CircuitTab(QWidget)` 类名不变，仍在 `ui/tabs/circuit_tab` 包入口可 import
- `render()` / `rebuild_circuit_diagram()` / `redraw_canvas()` / `get_phase_wiring_status()` / `get_phase_wiring_active_pt()` 这些对宿主可见方法不改名
- 主窗口装配方式不改

实施原则：
- 先搬纯函数/纯 helper，再搬会读写 `self` 状态的逻辑
- 每搬一块就删原位置，不保留长期转发壳
- 不借这轮顺手改视觉或业务行为

完成标准：
- `circuit_tab.py` 降回“装配器 + render 入口”级别
- 拆出后的子模块按职责单一，不再反向依赖主窗口
- UI 行为与当前版本保持一致

## Deferred
以下两类不建议混进前 4 轮：

- `m3`：`services/` 类型标注专项
  - 先补统计脚本和统一口径，再记录基线数
  - 单独做一轮，不和行为修复混合
- `m8`：`ui/styles.py` 拆分
  - 这是样式组织问题，不是当前行为风险
  - 放到 UI 结构专项里单做

## Test Plan
每轮统一执行：
- `.\.venv\Scripts\python.exe -m pytest -q`
- 针对修改文件做 `py_compile` 或最小导入检查
- 只要改了 Qt/UI 层，就做一次手动冒烟

Round 1 冒烟重点：
- 打开拓扑页，确认 PT 图元正常显示，没有黑盒分支残留报错
- 三点接线：`PT1`、`PT3` 接入相序仪流程可用
- `pytest` 输出应从“有 collection warning”收敛到无该 warning

Round 2 冒烟重点：
- 第五步同步测试页仍能显示“已同步/未同步”
- 相序仪在 `hidden / waiting / connected` 三态下读取序列均正确
- 第三步面板与拓扑页之间的相序接线状态联动正常

Round 3 冒烟重点：
- 人为制造一次 tick 异常时，不再持续刷屏
- 相序仪首次显示和移动时仍能定位；真实异常不被吞没

Round 4 冒烟重点：
- 拓扑页整体渲染
- 相序接线交互
- PT 记录表显示
- Step3 与主窗口的相序仪联动
- 同步测试页打开电路拓扑和状态刷新

## Assumptions
- 本轮计划只覆盖当前顶部 review block 中已确认有效的问题，不包含环流/下垂/自动同期那条更大的物理逻辑线。
- `M7` 采用 `__test__ = False` 方案，不采用类重命名。
- `M4` 最终目标是消除生产路径中的 `_is_gen_synced` 私有调用，不保留长期双接口。
- `M6` 结构拆分必须单独成轮，不与前面机械修复混合提交。

---

# AI 执行提示词

下面 6 份提示词每一份都是**自包含的**，可以直接喂给新一次的 AI 对话，无需先读 `MAINTENANCE_CHECKLIST.md` 顶部 review。每份提示词包含：角色 / 背景 / 白名单 / 黑名单 / 具体修复项 / 完成标准（Hard Gates）/ 提交规范 / 不要做的事。

每轮落地后必须更新 `MAINTENANCE_CHECKLIST.md` §3 / §4 / §9 / §10，并在 §9 追加本轮的"实际完成"条目。

---

## Round 1 提示词：机械小修 + 死分支清除

### 角色
你现在是 ThreePhase 仓库 R48-Round1 的代码执行 AI。本轮只做"已确认安全、机械、低风险"的清理，不做任何架构性改动。

### 背景
- 仓库根目录：`/Users/promise/Downloads/3/Intership/ThreePhase_entier/ThreePhase`
- Python 环境：`/Users/promise/opt/anaconda3/envs/power_gui/bin/python`（macOS / conda env `power_gui`）
- 上一轮：R47 已完成（死 import 清理 + `domain/` 类型标注补齐 + 历史注释整理）
- 本轮范围：`MAINTENANCE_CHECKLIST.md` 顶部 review 中的 `C1 / M2 / M3 / M7 / m1 / m2 / m6` 共 7 项。

### 白名单（仅允许修改这些文件）
- `app/main.py`
- `ui/tabs/circuit_tab.py`
- `ui/test_panel.py`
- `ui/widgets/step_panels/pt_phase_check_panel.py`
- `MAINTENANCE_CHECKLIST.md`（仅追加 §9 的本轮记录、勾选 §4 中本轮覆盖的条目）

### 黑名单（绝不可修改）
- `services/**`（包括 `_physics_*.py`、`sync_test_service.py`）
- `domain/**`
- 任何 `tests/**`
- 其他 `ui/**`（除白名单 4 个文件外）
- `requirements.txt` / 任何环境配置

### 具体修复项

#### 1. C1：完整删除 PT 黑盒渲染残留链路
**位置：**
- [app/main.py:328-329](app/main.py#L328-L329) `def get_pt_blackbox_mode(self): return False` —— 删除整个方法
- [ui/tabs/circuit_tab.py:71](ui/tabs/circuit_tab.py#L71) `CircuitTabAPI` Protocol 中 `def get_pt_blackbox_mode(self) -> object: ...` —— 删除该行
- [ui/tabs/circuit_tab.py:290](ui/tabs/circuit_tab.py#L290) `pt_blackbox_mode = self._api.get_pt_blackbox_mode()` —— 删除该局部变量赋值
- [ui/tabs/circuit_tab.py:349](ui/tabs/circuit_tab.py#L349) `def draw_pt_blackbox_symbol(...)` 整个内嵌函数（约 25 行）—— 删除
- [ui/tabs/circuit_tab.py:386, 404, 601, 615](ui/tabs/circuit_tab.py) 6 处 `if pt_blackbox_mode:` 分支 —— 全部删除分支与 else 分支重构（保留 else 分支的内容作为唯一路径）

**操作要点：**
- 删除 `if pt_blackbox_mode:` 分支后，`else:` 分支内的代码上提一层，确保缩进正确
- `draw_pt_blackbox_symbol` 内嵌函数被删除后，确认所有调用点（grep 应为 0）

**验证 grep：**
```
rg -n 'pt_blackbox_mode|on_pt_blackbox_toggle|reshuffle_pt_phase_orders|get_pt_blackbox_mode|set_g2_terminal_fault|draw_pt_blackbox_symbol' --type py
```
期望命中：仅 `MAINTENANCE_CHECKLIST.md` 历史段、`test_v1.md` 自身。`app/`、`domain/`、`services/`、`ui/`、`tests/` 下命中数 = 0。

#### 2. M2：相序仪 freq 选择改回元组判断
**位置：** [ui/tabs/circuit_tab.py:198](ui/tabs/circuit_tab.py#L198)

**Before：**
```python
freq = sim.gen1.freq if pt_name in "PT1" else sim.gen2.freq
```

**After：**
```python
freq = sim.gen1.freq if pt_name in ("PT1", "PT2") else sim.gen2.freq
```

#### 3. M3：绿色色号 typo 修正
**位置：** [ui/tabs/circuit_tab.py:217](ui/tabs/circuit_tab.py#L217)

**Before：**
```python
color, label = "#2eec71", "正序"
```

**After：**
```python
color, label = "#2ecc71", "正序"
```

#### 4. M7：消除 pytest collection warning
**位置：** [ui/test_panel.py:34](ui/test_panel.py#L34), [ui/test_panel.py:112](ui/test_panel.py#L112)

操作：在 `class TestPanelAPI(Protocol):` 和 `class TestPanelWidget(QtWidgets.QWidget):` 类体的第一行各添加：
```python
__test__ = False
```

**禁止：** 不重命名类，不动消费方代码。

#### 5. m1：删除未使用的 `_pt_recorded` 与注释残留
**位置：** [ui/widgets/step_panels/pt_phase_check_panel.py:115-117, 126](ui/widgets/step_panels/pt_phase_check_panel.py#L115-L117)

操作：
- 删除 `def _pt_recorded(self, pt_name: str) -> bool:` 整个方法（L115-117）
- 删除 L126 的注释行 `#and not self._pt_recorded(pt_name)`

#### 6. m2：清理 `app/main.py` 重复 section 分割
**位置：** [app/main.py:408-413](app/main.py#L408-L413)

操作：删除 L408-410（"PT 节点解析辅助"那段孤立 section 注释，包括上下两条 `# ════` 分割线之间的内容），保留 L411-413 仍对应有效代码的 "小型辅助" section 头。

#### 7. m6：删除 `_psm_terminal_markers` 冗余初始化
**位置：** [ui/tabs/circuit_tab.py:100](ui/tabs/circuit_tab.py#L100)

操作：删除 `__init__` 中的 `self._psm_terminal_markers: dict[str, dict[str, Any]] = {}`。保留 `_draw_circuit_content` 内 L744 的真正初始化。

### 完成标准（Hard Gates）

- **G1 pytest：** `python -m pytest -q` 全 PASS（数量与 R47 baseline 一致或多 0），且**输出中 0 次 `PytestCollectionWarning`**
- **G2 py_compile：** 4 个白名单 `.py` 文件全部通过 `python -m py_compile`
- **G3 grep 验证：** 上面 #1 验证 grep 命令在 `app/` / `domain/` / `services/` / `ui/` / `tests/` 下 0 命中
- **G4 offscreen 冒烟：** `QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/mpl python -c "from app.main import PowerSyncController; ...; PowerSyncController()"` 启动无 `AttributeError / ImportError / Traceback`
- **G5 行为不回归（手动）：** 启动 GUI，进入第三步，依次接入 PT1 / PT3，三点接线流程仍可用
- **G6 边界：** diff 仅集中在白名单 4 个文件 + checklist；其他文件 diff = 0 行

### 提交规范
- 每项独立 commit，commit message 前缀统一为 `R48-<编号>:`
- 推荐顺序（风险倒序）：`m1 → m2 → m6 → M3 → M7 → M2 → C1`
- 最后一个 commit 更新 `MAINTENANCE_CHECKLIST.md`

### 不要做
- 不改 `SyncTestService` 任何接口（留给 Round 2）
- 不动 `PhaseSeqMeterWidget` 任何方法（留给 Round 2）
- 不开始拆 `circuit_tab.py`（留给 Round 4）
- 不混入任何 `ruff format .` 或全仓格式化
- 不顺手补类型标注（留给 Deferred）

---

## Round 2 提示词：封装边界与接口收口

### 角色
你现在是 ThreePhase 仓库 R48-Round2 的代码执行 AI。本轮收口"已经有 public 意图但内部仍穿透私有实现"的位置。

### 背景
- 仓库根目录：`/Users/promise/Downloads/3/Intership/ThreePhase_entier/ThreePhase`
- Python 环境：`/Users/promise/opt/anaconda3/envs/power_gui/bin/python`
- 上一轮：R48-Round1 已完成（C1 死代码删除 + 6 项机械小修）
- 本轮范围：`M4 / M5 / m7` 共 3 项

### 白名单
- `services/sync_test_service.py`
- `tests/support/stubs.py`
- `app/main.py`（仅 controller wrapper 一行）
- `ui/widgets/phase_seq_meter.py`
- `ui/main_window.py`
- `ui/_phase_wiring_state.py`（**新建文件**）
- `ui/tabs/circuit_tab.py`
- `ui/panels/control_panel.py`
- `ui/widgets/step_panels/pt_phase_check_panel.py`
- `MAINTENANCE_CHECKLIST.md`

### 黑名单
- `domain/**`
- `services/**`（除 `sync_test_service.py`）
- 其他 UI 文件

### 具体修复项

#### 1. M4：`SyncTestService._is_gen_synced` 改成 public
**步骤：**
1. [services/sync_test_service.py:59](services/sync_test_service.py#L59)：把 `def _is_gen_synced(self, follower, master, ...)` 改名为 `def is_gen_synced(self, follower, master, ...)`
2. 同文件 L92 / L100 / L174 / L205 共 4 处自调用 `self._is_gen_synced(...)` → `self.is_gen_synced(...)`
3. [tests/support/stubs.py:121](tests/support/stubs.py#L121)：把 stub 的 `def _is_gen_synced(...)` 改名为 `def is_gen_synced(...)`
4. [app/main.py:584-585](app/main.py#L584-L585) controller wrapper：
   ```python
   def is_gen_synced(self, gen_a, gen_b):
       return self.sync_svc.is_gen_synced(gen_a, gen_b)  # 不再调 _is_gen_synced
   ```
5. **不保留** `_is_gen_synced` 作为兼容委托 —— 直接删名，因为本轮已经改了所有调用方

**验证 grep：**
```
rg -n '_is_gen_synced' --type py
```
期望命中数 = 0。

#### 2. M5：给 `PhaseSeqMeterWidget` 增加 `current_sequence()` 公共方法
**位置：** [ui/widgets/phase_seq_meter.py](ui/widgets/phase_seq_meter.py)，在 `disconnect()` 方法后追加

**新增方法：**
```python
def current_sequence(self) -> str:
    """返回当前应当对外暴露的相序结果。

    规则：
    - _status == "connected" 时返回 _sequence 原值，含 "FAULT"（透传给消费方处理）
    - hidden / waiting 状态统一返回 "unknown"
    """
    if self._status == "connected":
        return self._sequence
    return "unknown"
```

**改 lambda：** [ui/main_window.py:192](ui/main_window.py#L192)
```python
# Before
get_phase_seq_meter_sequence=lambda: getattr(self.phase_seq_meter, "_sequence", "unknown"),
# After
get_phase_seq_meter_sequence=lambda: self.phase_seq_meter.current_sequence(),
```

**FAULT 透传冒烟：** 模拟 `phase_seq_meter.connect_pt("PT3", "FAULT")`，确认 `current_sequence()` 返回 `"FAULT"` 而不是 `"unknown"`，并能进入 `record_phase_sequence` 的 FAULT 处理分支。

#### 3. m7：把相序接线状态收口为 `StrEnum`
**新建文件：** `ui/_phase_wiring_state.py`
```python
from enum import StrEnum


class PhaseWiringStatus(StrEnum):
    IDLE = "idle"
    WIRING = "wiring"
    READY = "ready"
```

**改造消费方（4 处）：**

a. [ui/tabs/circuit_tab.py:175-180](ui/tabs/circuit_tab.py#L175-L180) `get_phase_wiring_status`：
```python
def get_phase_wiring_status(self) -> PhaseWiringStatus:
    if self._phase_wiring.active_pt is None:
        return PhaseWiringStatus.IDLE
    if self._phase_wiring.wired == {"A", "B", "C"}:
        return PhaseWiringStatus.READY
    return PhaseWiringStatus.WIRING
```

b. 同文件 L242 / L280 处的字符串比较 `== "wiring"` / `in {"wiring", "ready"}` 改用 `PhaseWiringStatus.WIRING` / `{PhaseWiringStatus.WIRING, PhaseWiringStatus.READY}`

c. [ui/panels/control_panel.py:300](ui/panels/control_panel.py#L300) `if self._circuit_tab.get_phase_wiring_status() == "wiring":` → `== PhaseWiringStatus.WIRING`

d. [ui/widgets/step_panels/pt_phase_check_panel.py:177, 185](ui/widgets/step_panels/pt_phase_check_panel.py) 的 `== "wiring"` / `== "ready"` 同样改成枚举值

**Hint：** `StrEnum` 与 `str` 兼容，所以 `pt_phase_check_panel.py:120` 的 `_refresh_record_buttons` 中 `status == "ready"` 即使继续写字面量也成立 —— 但本轮要求**全部改用枚举**，理由是消除"裸字符串"。

### 完成标准（Hard Gates）

- **G1 pytest：** 全 PASS，无新增 warning
- **G2 py_compile：** 9 个白名单 `.py` 文件通过
- **G3 grep：** `_is_gen_synced` 全仓 0 命中；`getattr(self.phase_seq_meter, "_sequence"` 全仓 0 命中；`"wiring"` / `"ready"` / `"idle"` 在 `ui/**` 仅出现在 `_phase_wiring_state.py` 内的字面量定义里
- **G4 offscreen 冒烟：** 启动 + 进入第三步 + 接入 PT1 + 三点接线 → 流程行为与 Round 1 完全一致
- **G5 FAULT 冒烟：** 手动构造 `phase_seq_meter._status = "connected"; _sequence = "FAULT"`，调 `current_sequence()` 应返回 `"FAULT"`
- **G6 边界：** diff 仅在白名单文件

### 提交规范
- 3 个独立 commit：`R48-M4: ...` / `R48-M5: ...` / `R48-m7: ...`
- 顺序：`M5 → m7 → M4`（M4 改 service 层最敏感，最后做）

### 不要做
- 不改同步算法本身（freq_tol / amp_tol / phase_tol 不动）
- 不改 `PhaseSeqMeterWidget` 渲染逻辑、信号
- 不开始拆 `circuit_tab.py`

---

## Round 3 提示词：运行时鲁棒性

### 角色
ThreePhase R48-Round3 代码执行 AI。本轮只解决两类运行时问题：tick 异常刷屏、过宽 except 吞错。

### 背景
- 上一轮：R48-Round2 完成（M4 / M5 / m7 收口）
- 本轮范围：`M8 / m5 / m4`（m4 仅做局部）

### 白名单
- `app/main.py`
- `ui/tabs/circuit_tab.py`
- `ui/widgets/step_panels/pt_phase_check_panel.py`（仅 m4 局部空格）
- `MAINTENANCE_CHECKLIST.md`

### 黑名单
- `services/**`、`domain/**`、`tests/**` 全部
- 其他 UI 文件

### 具体修复项

#### 1. M8：tick 失败熔断
**位置：** [app/main.py:601-614](app/main.py#L601-L614)

**改 `_handle_tick_failure`：**
```python
_TICK_FAILURE_THRESHOLD = 5  # 类常量，定义在 PowerSyncController 类内顶部

def _handle_tick_failure(self, stage: str):
    self._consecutive_tick_failures += 1
    traceback.print_exc()
    if self._consecutive_tick_failures == 3 and not self._tick_error_notified:
        self.ui.statusBar().showMessage(
            f"物理帧更新连续失败 {self._consecutive_tick_failures} 次（阶段: {stage}），请检查控制台错误日志。"
        )
        self._tick_error_notified = True
    if self._consecutive_tick_failures >= self._TICK_FAILURE_THRESHOLD and self._timer.isActive():
        self._timer.stop()
        self.ui.statusBar().showMessage(
            f"物理引擎已熔断停止（阶段: {stage}，连续失败 {self._consecutive_tick_failures} 次）。"
        )
```

**约束：**
- `_clear_tick_failure_state` 不动语义（成功一帧后仍清零）
- 阈值 = 5（30fps 下 ≈ 165ms，与 statusBar 第 3 次提示衔接）
- 熔断后**不再自动重启** timer，由用户操作恢复

#### 2. m5：`_place_phase_seq_meter` 替换 try/except 为显式哨兵
**位置：** [ui/tabs/circuit_tab.py:151-173](ui/tabs/circuit_tab.py#L151-L173)

**目标实现（完整替换）：**
```python
def _place_phase_seq_meter(self) -> None:
    mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
    bbox = self.ax_circuit.get_position()
    xlim = self.ax_circuit.get_xlim()
    ylim = self.ax_circuit.get_ylim()
    cw, ch = self.canvas2.width(), self.canvas2.height()
    if xlim[1] == xlim[0] or ylim[1] == ylim[0]:
        px, py = cw // 2, ch // 2
    else:
        ax_fx = (0.50 - xlim[0]) / (xlim[1] - xlim[0])
        ax_fy = (0.72 - ylim[0]) / (ylim[1] - ylim[0])
        fig_fx = bbox.x0 + ax_fx * (bbox.x1 - bbox.x0)
        fig_fy = bbox.y0 + ax_fy * (bbox.y1 - bbox.y0)
        px = int(fig_fx * cw)
        py = int((1.0 - fig_fy) * ch)

    mx = px - mw // 2
    my = py - mh // 2
    self.phase_seq_meter.move(mx, my)
    self.phase_seq_meter.setVisible(True)
    self.phase_seq_meter.raise_()
```

**约束：**
- 不再有 `try / except Exception`
- matplotlib 渲染异常从此向上抛，被 M8 熔断接住

#### 3. m4：仅本轮触及行的空格风格修齐
**位置：**
- [ui/tabs/circuit_tab.py:244](ui/tabs/circuit_tab.py#L244) `event.inaxes!= self.ax_circuit` → `event.inaxes != self.ax_circuit`
- [ui/widgets/step_panels/pt_phase_check_panel.py:156, 161, 192](ui/widgets/step_panels/pt_phase_check_panel.py) 删 trailing whitespace

**禁止：**
- 不动 [ui/tabs/circuit_tab.py:752+](ui/tabs/circuit_tab.py) 的 `markersize = 12` 风格（不在本轮触及范围）
- 不跑 `ruff format .`

### 完成标准（Hard Gates）

- **G1 pytest：** 全 PASS
- **G2 py_compile：** 3 个白名单 `.py` 文件通过
- **G3 熔断行为冒烟：** 在 `_tick` 内人为 `raise RuntimeError("test")`，确认：
  - 第 1-2 次：traceback 打印
  - 第 3 次：statusBar 显示 "失败 3 次"
  - 第 5 次：timer 停止，statusBar 显示 "已熔断停止"，stderr 不再继续刷
- **G4 m5 哨兵冒烟：** 模拟 `ax_circuit.set_xlim(0.5, 0.5)`，调 `_place_phase_seq_meter()`，相序仪应居中显示而不是抛错
- **G5 边界：** diff 仅在白名单文件

### 提交规范
- 3 个独立 commit：`R48-M8: tick 异常熔断` / `R48-m5: _place_phase_seq_meter 哨兵替换 except` / `R48-m4: 局部空格修齐`
- 顺序：`m4 → m5 → M8`

### 不要做
- 不动 physics 计算 / render 渲染本身的代码路径
- 不改 `_tick` 主体顺序
- 不混入 m4 全仓格式化

---

## Round 4 提示词：`circuit_tab.py` 结构性拆分

### 角色
ThreePhase R48-Round4 代码执行 AI。本轮做 4 轮中**唯一一轮结构性改动**：把 `circuit_tab.py` 拆成 subpackage。

### 背景
- 上一轮：R48-Round3 完成（M8 熔断 + m5 哨兵 + m4 局部空格）
- 本轮范围：`M6` 单项 —— `circuit_tab.py` 1238 行 → subpackage 4 文件
- Round 2 已建立 `ui/_phase_wiring_state.py`，本轮把它迁移到 subpackage 内

### 白名单
- `ui/tabs/circuit_tab.py` → 拆为 `ui/tabs/circuit_tab/__init__.py` + 3 个 `_xxx.py`
- `ui/_phase_wiring_state.py` → 删除（迁入 subpackage）
- 任何因 import 路径变更而需改的文件（grep 后确定，预期：`ui/main_window.py`、`ui/panels/control_panel.py`、`ui/widgets/step_panels/pt_phase_check_panel.py`）
- `MAINTENANCE_CHECKLIST.md`

### 黑名单
- `app/`、`domain/`、`services/`、`tests/` 全部（行为零变更）

### 物理布局

**目标结构：**
```
ui/tabs/circuit_tab/
├── __init__.py          # CircuitTab 类定义本身放在这里（保留 git blame）
├── _phase_wiring.py
├── _record_tables.py
└── _draw_topology.py
```

**git 操作：**
```bash
git mv ui/tabs/circuit_tab.py ui/tabs/circuit_tab/__init__.py
```
（这一步独立成第一个 commit，保留 blame）

### 拆分边界

| 目标文件 | 包含内容 |
|---|---|
| `__init__.py` | `CircuitTab(QWidget)` 类定义、`_build()`、`render()` 装配入口、`redraw_canvas()`、`rebuild_circuit_diagram()` |
| `_phase_wiring.py` | `PhaseWiringSession`、`PhaseWiringStatus`（**从 `ui/_phase_wiring_state.py` 迁入**）、`get_phase_wiring_status()`、`get_phase_wiring_active_pt()`、`_phase_target_nodes()`、`connect_phase_seq_meter()`、`disconnect_phase_seq_meter()`、`_show_phase_seq_result()`、`handle_phase_wiring_click()`、`_render_phase_wiring()`、`_place_phase_seq_meter()`（与相序仪定位绑定） |
| `_record_tables.py` | `_render_pt_record_tables()`（约 L1100-1240）、内部 `_mk` 表格构造 helper、所有 `tbl_s3_*` / `tbl_s4_*` / `tbl_s5_*` 相关渲染 |
| `_draw_topology.py` | `_draw_circuit_content()` 主体（约 L286-770）、母排 / CT / breaker / generator / PT 端子盒 / loop 动画绘图 |

**实施技巧（避免循环 import）：**
- 子模块定义为 **mixin 类**，`__init__.py` 内的 `CircuitTab` 多继承：
  ```python
  # __init__.py
  from ui.tabs.circuit_tab._phase_wiring import PhaseWiringMixin
  from ui.tabs.circuit_tab._record_tables import RecordTablesMixin
  from ui.tabs.circuit_tab._draw_topology import DrawTopologyMixin

  class CircuitTab(PhaseWiringMixin, RecordTablesMixin, DrawTopologyMixin, QtWidgets.QWidget):
      ...
  ```
- 或者：子模块只定义模块级函数，签名改为 `def _render_phase_wiring(tab: "CircuitTab") -> None:`，`__init__.py` 内的方法做薄委托。**优选 mixin 方案**（与 R31 `step_panels` 风格一致）。

### 外部接口契约（不变）

```python
# 落地前后保持一致：
from ui.tabs.circuit_tab import CircuitTab
```

`CircuitTab` 公开方法 `render` / `rebuild_circuit_diagram` / `redraw_canvas` / `get_phase_wiring_status` / `get_phase_wiring_active_pt` / `connect_phase_seq_meter` / `disconnect_phase_seq_meter` / `handle_phase_wiring_click` 全部不改名、不改签名。

### Round 2 引入的 `ui/_phase_wiring_state.py` 迁移

1. 把内容（`PhaseWiringStatus` 枚举）拷到 `_phase_wiring.py` 顶部
2. 删除原文件 `ui/_phase_wiring_state.py`
3. grep `from ui._phase_wiring_state import` 全仓替换为 `from ui.tabs.circuit_tab._phase_wiring import`

### 完成标准（Hard Gates）

- **G1 pytest：** 全 PASS，零新增 warning
- **G2 py_compile：** subpackage 4 个 `.py` + 所有改 import 路径的文件通过
- **G3 grep：** `from ui._phase_wiring_state` 全仓 0 命中；`ui/_phase_wiring_state.py` 文件不存在
- **G4 行数硬指标：** `wc -l ui/tabs/circuit_tab/__init__.py` ≤ 200；`_phase_wiring.py` ≤ 350；`_record_tables.py` ≤ 350；`_draw_topology.py` ≤ 500；4 个文件总和 ≤ 1238（即拆分后**不允许变胖**）
- **G5 offscreen 冒烟：** 进入第 3 / 4 / 5 步，所有相序仪、记录表、母排拓扑渲染与拆分前完全一致
- **G6 imports：** 仅 `__init__.py` import 三个 mixin；mixin 之间不互相 import；mixin 不反向 import `__init__.py`
- **G7 行为零变更：** 拆分前后随机抓 5 帧 `render_visuals(rs)` 输出做 snapshot 对比，应一致

### 提交规范
- 第 1 commit：`R48-M6: git mv ui/tabs/circuit_tab.py → ui/tabs/circuit_tab/__init__.py`
- 第 2 commit：`R48-M6: 拆出 _phase_wiring.py mixin`
- 第 3 commit：`R48-M6: 拆出 _record_tables.py mixin`
- 第 4 commit：`R48-M6: 拆出 _draw_topology.py mixin`
- 第 5 commit：`R48-M6: 迁移 PhaseWiringStatus 到 _phase_wiring.py，删除 ui/_phase_wiring_state.py`
- 第 6 commit：`R48-M6: 更新 checklist`

### 不要做
- 不顺手改 UI 视觉
- 不顺手改任何业务行为
- 不顺手补类型标注
- 不改 mixin 内部方法的签名（哪怕看起来可以简化）
- 不在 mixin 内部直接调用 `self.canvas2` / `self.ax_circuit` 之外的"看起来抽象更好"的对象

---

## Deferred A 提示词：`services/` 类型标注专项

### 角色
ThreePhase 类型标注专项轮的代码执行 AI。**触发条件：** 4 轮 R48 全部完成且 stable 至少 2 周后再启动。

### 背景
- `services/` 目录返回类型标注覆盖率约 37%（68/184，已排除 `__init__` / `__post_init__`）
- 数值密集模块（`_physics_arbitration.py` / `_physics_measurement.py` / `_physics_protection.py`）缺标注最多
- R47 已完成 `domain/` 类型标注；本轮目标是把 `services/` 拉到 ≥ 90%

### 白名单
- `services/**/*.py` 全部
- 必要的 `domain/**/*.py` 类型 stub（如需新增 `Protocol`）
- `MAINTENANCE_CHECKLIST.md`
- 新增 `scripts/check_annotation_coverage.py`（统计脚本）

### 黑名单
- `app/main.py`、`ui/**`、`tests/**` 全部不动
- 任何**业务逻辑改动**严禁出现 —— 本轮纯标注，零行为变更

### 操作流程

#### 1. 先建立统计基线
新建 `scripts/check_annotation_coverage.py`：
```python
"""统计 services/ 目录的返回类型标注覆盖率。

口径：
- 排除 __init__ / __post_init__
- 排除 dunder 方法（__xxx__）
- 把 @property / @staticmethod / @classmethod 计入分母
- 私有方法（单下划线开头）计入分母

阈值：本轮目标 ≥ 90%
"""
import ast, pathlib, sys

def main(target: str = "services") -> int:
    total = with_ann = 0
    missing_locs: list[tuple[str, int, str]] = []
    for p in sorted(pathlib.Path(target).rglob("*.py")):
        tree = ast.parse(p.read_text())
        for n in ast.walk(tree):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if n.name in ("__init__", "__post_init__"):
                continue
            if n.name.startswith("__") and n.name.endswith("__"):
                continue
            total += 1
            if n.returns is not None:
                with_ann += 1
            else:
                missing_locs.append((str(p), n.lineno, n.name))
    pct = 100 * with_ann / total if total else 0
    print(f"{target}/: {with_ann}/{total} = {pct:.1f}%")
    if pct < 90.0:
        print("缺失位置：")
        for loc in missing_locs[:50]:
            print(f"  {loc[0]}:{loc[1]} :: {loc[2]}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

记录基线：`python scripts/check_annotation_coverage.py services` → 起始百分比写入 checklist。

#### 2. 按文件批量补标注
**优先级（先简单后复杂）：**
1. `services/scoring/**` —— pure functions，最易补
2. `services/phase_order_resolver.py` / `services/flow_mode_manager.py` —— 状态机式
3. `services/loop_test_service.py` / `services/pt_voltage_check_service.py` / `services/pt_phase_check_service.py` / `services/pt_exam_service.py` / `services/sync_test_service.py` —— 业务 service
4. `services/blackbox_repair_handler.py` / `services/assessment_coordinator.py` / `services/assessment_service.py` —— 编排层
5. `services/_physics_*.py` —— 数值最密集，留最后

**每个文件落地一个 commit：** `R-Annot: services/<file>.py 类型标注补齐`

#### 3. 边补边更新基线脚本输出
每个 commit 后跑一次 `scripts/check_annotation_coverage.py`，把"本轮目前覆盖率"写入 commit message。

### 完成标准

- **G1 pytest：** 全 PASS（业务行为零变更）
- **G2 mypy 不强制：** 不要求过 mypy strict（有些类型推断代价高），但 `python scripts/check_annotation_coverage.py services` 退出码 = 0（即 ≥ 90%）
- **G3 行为零变更：** `git diff` 仅在标注、`Optional[X]` / `X | None`、`from typing import` 这类纯静态层面；任何 `if` / `for` / 表达式改动均不允许
- **G4 文档：** checklist §9 记录起始覆盖率与终点覆盖率

### 不要做
- 不顺手改业务逻辑（哪怕看到 bug）
- 不顺手抽 helper 函数
- 不顺手 inline 复杂表达式
- 不顺手补 docstring（这是另一专项）

---

## Deferred B 提示词：`ui/styles.py` 拆分

### 角色
ThreePhase UI 样式拆分专项的代码执行 AI。**触发条件：** 4 轮 R48 全部完成且 R-Annot 也已完成、stable 至少 2 周后再启动。本专项不阻塞任何业务功能。

### 背景
- `ui/styles.py` 当前 1007 行单文件 QSS 模板
- 大部分是 f-string 模板内的 QSS 字符串（按组件分块但未拆物理文件）
- 本轮目标：按组件域拆成 4-5 个 `.qss` 或 `.py` 子模块，主入口保持 `apply_app_theme()` API 不变

### 白名单
- `ui/styles.py` → 拆为 subpackage `ui/styles/`
- 任何 `import ui.styles` 的文件（预期：`ui/main_window.py`）
- `MAINTENANCE_CHECKLIST.md`

### 黑名单
- 任何**实际样式定义的改动**（颜色、间距、字号都不动）
- 任何 Python 业务文件
- `tests/**`

### 物理布局

```
ui/styles/
├── __init__.py          # 暴露 apply_app_theme / build_app_stylesheet（API 不变）
├── _theme_palette.py    # LIGHT_THEME / DARK_THEME 调色板字典
├── _buttons.qss         # QPushButton / 各种 tone 按钮
├── _panels.qss          # QGroupBox / panel surface / sidebar
├── _dialogs.qss         # QDialog / message box
├── _inputs.qss          # QLineEdit / QSpinBox / QSlider / QComboBox
└── _misc.qss            # tab / scrollbar / table / 其他
```

`__init__.py` 内：
```python
from pathlib import Path
from ui.styles._theme_palette import LIGHT_THEME

_QSS_DIR = Path(__file__).parent

def _load_qss_parts() -> str:
    parts = []
    for name in ("_buttons", "_panels", "_dialogs", "_inputs", "_misc"):
        text = (_QSS_DIR / f"{name}.qss").read_text(encoding="utf-8")
        parts.append(text.format(**LIGHT_THEME))
    return "\n\n".join(parts)


def build_app_stylesheet() -> str:
    base = _load_qdarkstyle_base()
    qss = _load_qss_parts()
    return f"{base}\n{qss}" if base else qss


def apply_app_theme(app) -> None:
    app.setStyleSheet(build_app_stylesheet())
```

### 拆分原则
- 把现有 `_QSS_TEMPLATE` 字符串按 QSS 选择器分组（如 `QPushButton[hero=true]` 一类是 buttons，`QGroupBox` 一类是 panels）
- 选择器分组**完全保留**：拆分前后 `build_app_stylesheet()` 输出的字符串经过 normalize（trim + 同顺序连接）后**应字符级别一致**

### 完成标准

- **G1 pytest：** 全 PASS
- **G2 字符串等价：** 写一次性 diff 脚本：拆分前后 `build_app_stylesheet()` 输出 normalize 后等价
- **G3 行为冒烟：** 启动 GUI，对比关键 widget 的渲染外观（按钮、面板、对话框、输入框）与拆分前一致
- **G4 import 兼容：** `from ui.styles import apply_app_theme, build_app_stylesheet` 在 `ui/main_window.py` 仍可用

### 不要做
- 不改任何颜色 / 字号 / 间距数值
- 不引入新的样式 token / 设计变量
- 不顺手做 dark theme（这是另一专项）
- 不动 `_load_qdarkstyle_base()` 的 fallback 行为
