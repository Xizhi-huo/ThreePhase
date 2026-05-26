# ThreePhase 项目上下文

## 项目定位

ThreePhase 是一个基于 PyQt5 的三相电并网仿真教学系统，用于模拟高压机组在隔离母排模式下的并网前测试流程。当前项目只保留教学与工程训练功能，核心能力包括物理仿真、五步测试、故障注入、测量记录、黑盒接线修复和回归测试。

入口：

```bash
python app/main.py
```

测试：

```bash
python -m pytest
```

推荐 Python 环境为 3.11.9。

## 目录结构

```text
ThreePhase/
├── app/
│   ├── main.py              # PowerSyncController 与程序入口
│   └── controller_signals.py # Controller -> UI 信号
├── adapters/
│   └── render_state.py      # UI 渲染快照
├── domain/
│   ├── constants.py
│   ├── enums.py
│   ├── models.py
│   ├── test_states.py
│   ├── fault_scenarios.py
│   ├── node_map.py
│   └── phase_order_state.py
├── services/
│   ├── physics_engine.py
│   ├── _physics_core.py
│   ├── _physics_arbitration.py
│   ├── _physics_protection.py
│   ├── _physics_measurement.py
│   ├── loop_test_service.py
│   ├── pt_voltage_check_service.py
│   ├── pt_phase_check_service.py
│   ├── pt_exam_service.py
│   ├── sync_test_service.py
│   ├── flow_mode_manager.py
│   ├── fault_manager.py
│   ├── blackbox_repair_handler.py
│   ├── hardware_actions.py
│   └── phase_order_resolver.py
├── ui/
│   ├── main_window.py
│   ├── test_panel.py
│   ├── panels/
│   ├── styles/
│   ├── tabs/
│   └── widgets/
└── tests/
```

## 架构概览

```text
PowerSyncUI
  ↑ render_visuals(RenderState)
  ↓ 用户操作
PowerSyncController
  ├── SimulationState
  ├── PhysicsEngine
  ├── FaultManager
  ├── BlackboxRepairHandler
  ├── HardwareActions
  └── 五步测试 Service
```

`SimulationState` 是唯一运行态数据源。`PhysicsEngine` 每帧更新波形、母排参考、断路器保护、PT 二次侧电压和万用表读数。五步 Service 负责流程记录与完成条件判断。UI 通过控制器接口读取和修改状态。

## 当前维护状态

- `services/` 已完成显式依赖注入收口，业务服务不再持有 UI 控制器。
- 物理引擎拆为波形、仲裁、保护、测量四个 Mixin。
- 第一步回路测试记录为六组：`AA/BB/CC/AB/AC/BC`。
- PT1、PT2、PT3 的相序、变比和黑盒状态已拆分为独立运行态。
- E03 可通过 PT3 接线盒二次侧极性标识修复。
- E04 可通过右侧控制台恢复 PT3 额定变比 `11000:193` 修复。
- 第五步完成后会稳定双机并联状态并重置波形历史。
- 中性点接地断开时只隐藏电阻下方三条竖线的下段，保留汇合线、汇合点和电阻连接。
- 流程模式只保留 `teaching` 与 `engineering`。

## 五步测试流程

| 步骤 | 服务类 | 电气状态 | 核心验证 |
|------|--------|----------|----------|
| 1. 回路导通测试 | `LoopTestService` | 双机手动、工作位、合闸、未启机，拆除接地电阻 | `AA/BB/CC` 导通，`AB/AC/BC` 隔离 |
| 2. PT 电压检查 | `PtVoltageCheckService` | Gen1 并入母排，Gen2 运行但断路器分闸 | PT1/PT2/PT3 三相线电压在容差内 |
| 3. PT 相序检查 | `PtPhaseCheckService` | 同步骤 2 | PT1/PT2/PT3 相序为正序、反序或异常 |
| 4. PT 压差测试 | `PtExamService` | Gen1/Gen2 交替与 PT2 比对 | 9 对 PT 端子间矢量压差 |
| 5. 同期功能测试 | `SyncTestService` | Gen2 自动追踪 Gen1 | 频率、电压、相角满足同期条件后合闸 |

第四步压差公式：

```python
gen_ph = gen_line / sqrt(3)
bus_ph = bus_line / sqrt(3)
same_phase = abs(gen_ph - bus_ph)
cross_phase = sqrt(gen_ph**2 + bus_ph**2 + gen_ph * bus_ph)
```

E03 的 PT3 A 相极性反接会使同相压差变为 `gen_ph + bus_ph`，跨相压差变为 `sqrt(gen_ph**2 + bus_ph**2 - gen_ph * bus_ph)`。

## 流程模式

`FlowModeManager` 当前只保留两种模式：

- `teaching`：发现异常后，只要本步测量项齐全，就允许完成该步并继续收集证据。
- `engineering`：要求当前步骤结果合格后才能完成并推进。

共同策略：

- 存在可修复黑盒目标时，第五步前必须完成真实修复。
- E01/E02 保留第五步事故弹窗修复入口。
- E03 优先通过 PT3 接线盒极性修复。
- E04 通过 PT3 变比面板修复。

## 故障场景

| 编号 | 状态 | 故障内容 | 检出步骤 | 修复入口 |
|------|------|----------|----------|----------|
| E01 | 启用 | Gen1 A/B 相接线互换 | 1、3、4、5 | 第五步事故弹窗 |
| E02 | 启用 | Gen2 B/C 相接线互换 | 1、3、4、5 | G2 机端黑盒 / 事故弹窗 |
| E03 | 启用 | PT3 A 相极性反接 | 2、3、4、5 | PT3 接线盒极性标识 |
| E04 | 启用 | PT3 实际变比 `11000:93` | 2、4 | 控制台 PT3 变比恢复 |
| E05-E14 | 启用 | Gen1/PT1 接线矩阵故障 | 1、3、4 | G1/PT1 黑盒 |
| E17-E21 | 启用 | PT2 母排 PT 二次侧三线接反 | 3、4 | PT2 接线盒 |
| E15-E16 | 禁用 | Gen2 过电压、强行非同期合闸 | 开发中 | 暂无 |

黑盒修复采用渐进式模型。用户保存某个接线盒后，会先写回对应运行态；只有当前场景涉及的全部可修复目标恢复为 `['A', 'B', 'C']`，`FaultManager.repair_fault()` 才会清除故障。

## 关键运行态

- `SimulationState.gen1/gen2`：两台发电机频率、电压、相位、起机和断路器状态。
- `SimulationState.fault_config`：当前故障是否激活、是否发现、是否修复和场景参数。
- `PhaseOrderState.pt_phase_orders`：PT1/PT2/PT3 当前二次端子对应的实际相。
- `g1_blackbox_order` / `g2_blackbox_order`：发电机端子盒运行态真值。
- `pt1_pri_blackbox_order` / `pt1_sec_blackbox_order`：PT1 一次侧、二次侧接线真值。
- `pt2_sec_blackbox_order`：母排 PT2 二次侧接线真值。
- `loop_test_state`、`pt_voltage_check_state`、`pt_phase_check_state`、`pt_exam_states`、`sync_test_state`：五步测试记录和完成状态。

## 黑盒修复

黑盒入口在第 1～4 步控制台均可见：

- G1 机端接线
- G2 机端接线
- PT1 接线盒
- PT2 接线盒
- PT3 接线盒

PT3 在 E03 激活时显示二次侧极性状态，用户可将 `-++` 恢复为 `+++`。PT2 用于 E17-E21 母排 PT 二次侧三线接反场景。

## UI 结构

- `ui/main_window.py`：主窗口、Tab 管理、渲染调度、事故弹窗。
- `ui/panels/control_panel.py`：右侧控制柜、故障选择、流程模式选择。
- `ui/test_panel.py`：测试模式右侧步骤面板。
- `ui/tabs/circuit_tab/`：母排拓扑、相序仪、记录表。
- `ui/widgets/pt_wiring_widget.py`：PT 接线盒图形化交互。
- `ui/widgets/gen_wiring_widget.py`：发电机端子盒图形化交互。
- `ui/widgets/load_share_cabinet_widget.py`：负载分配控制柜接线界面。

## 测试覆盖

当前回归重点：

- 物理引擎正常与 E01 快照
- 第一步六组回路记录
- 第三步相序正序轮换判定
- 第五步完成态稳定
- E04 PT3 变比修复
- 黑盒修复编排

常用命令：

```bash
python -m pytest
git -c core.whitespace=cr-at-eol diff --check
```
<<<<<<< HEAD
=======
PyQt5       # GUI框架
matplotlib  # 波形/相量/拓扑图绘制
numpy       # 数值计算
```
## 2026-04-09 Phase 0 安全网进度

- 已新增 `tests/` 目录和快照测试入口：
  - `tests/test_physics_snapshot.py`
  - `tests/test_assessment_snapshot.py`
  - `tests/support/stubs.py`
  - `tests/support/snapshots.py`
- 已验证：
  - `PhysicsEngine` 可在无 UI 的 `ControllerStub` 下运行 `update_physics()` + `build_render_state()`
  - `AssessmentService.build_result()` 可在最小替身控制器下独立运行
- 已生成快照基线：
  - `tests/snapshots/physics_normal.json`
  - `tests/snapshots/physics_fault_E01.json`
  - `tests/snapshots/assessment_normal.json`
  - `tests/snapshots/assessment_fault_random.json`
- 当前测试命令：
  - `python -m pytest tests/`
- Phase 0 已闭环；旧 UI Mixin 依赖扫描文档已随 Tab 组件化完成移除，当前不再维护 `/docs/` 下的 Mixin 映射文件



Hello everyone. Today I will show a Three-Phase Power Synchronization Training System.

The goal of this project is to make a safe training tool for generator synchronization. In real power systems, synchronization is important and can be dangerous if the steps are wrong. So this system lets users practice the process in a simulation before doing it in real life.

The UI has two main parts. On the left, we have the main simulation and test pages. On the right, we have the control panel. In the control panel, users can control two generators. They can change frequency, voltage, phase angle, running mode, breaker position, start or stop the generator, and open or close the breaker.

The first page shows real-time waveforms and the synchronization panel. Users can see three-phase waveforms, the bus waveform, the phasor diagram, and the synchronization result. The system checks the frequency difference, voltage difference, and phase angle difference. Then it tells the user whether closing the breaker is allowed.

The second page shows the bus topology. It shows the generators, bus, PTs, breakers, grounding, and measurement points. Users can use a virtual multimeter and phase sequence meter to check the system. The system also has a black-box mode. In this mode, some wiring is hidden, so students need to find the problem by using measurement results.

The main part of this project is the five-step pre-synchronization test.

Step one is the loop continuity test. It checks whether the same phases are connected and different phases are isolated.

Step two is the PT line voltage check. It checks the line voltages of PT1, PT2, and PT3.

Step three is the PT phase sequence check. It uses the phase sequence meter to check whether the phase order is correct.

Step four is the PT secondary terminal voltage difference test. It compares the generator-side PT and the bus-side PT. This helps check whether the synchronization circuit is correct.

Step five is the synchronization function test. One generator follows the other generator automatically. The system checks whether the frequency, voltage, and phase angle become close enough for synchronization.

I also added fault training. The system supports many fault cases, from E01 to E14. These include wrong phase wiring, PT polarity reverse, wrong PT ratio, and hidden wiring faults. Some faults can be found in the first step. Some faults can only be found after the phase sequence check or voltage difference test. This helps students learn not only the steps, but also how to find faults from data.

The system has three modes: teaching mode, engineering mode, and assessment mode. In teaching mode, users can continue even if there is a fault. In engineering mode, users must pass the current step before moving to the next step. In assessment mode, the system gives fewer hints, records the user’s actions, and gives a final score.

For the implementation, this project is not just a static UI. It has a physics engine in the background. The engine calculates three-phase waveforms, bus status, breaker protection, PT measurements, and synchronization conditions. The logic is also divided into different service modules, such as loop test, PT voltage check, phase sequence check, voltage difference test, synchronization test, fault management, and scoring.

So far, I have completed the main simulation UI, the control panel, the five-step test process, real-time waveforms, phasor diagram, bus topology, virtual multimeter, phase sequence meter, fault injection, black-box wiring repair, assessment scoring, and automated tests.

In summary, this project is an interactive training system for power synchronization. It changes a complex electrical process into something users can see, operate, test, and practice safely. Users can learn the process, find faults, and understand the synchronization workflow better.

Thank you.
>>>>>>> ad07e428980fdc5b8a83ef6d669da3308cb6b245


Next, I will present the second project: the Three-Phase Grid Synchronization Assessment System.

Unlike the previous teaching mode, this assessment mode no longer provides five-step guidance, process scoring, or fault answers. After the user clicks Start Random Assessment, the system secretly injects a random fault. The student must use tools such as the multimeter, phase sequence meter, measurement records, black-box inspection, and PT ratio adjustment to identify and repair the problem independently.

The core design of this interface is to show only engineering phenomena, without making judgments for the student. For example, the system only displays voltage values, OL, buzzer status, and phase sequence results. It does not tell the student whether something is “normal” or “abnormal,” or where the fault is. This avoids exposing the answer and makes the assessment closer to a real troubleshooting scenario.

The right-side free operation panel keeps all necessary assessment functions, including random assessment startup, measurement records, black-box inspection, neutral grounding, PT ratio settings, and Gen1 / Gen2 start, stop, open, and close controls. Students can operate freely without being restricted by fixed steps.

Finally, when the student believes all conditions are satisfied, they use the normal Gen2 close button to connect it to the busbar. This closing attempt is the final submission: if synchronization succeeds, the student passes; if it fails or protection is triggered, the student does not pass.

In summary, the teaching mode is used to teach the process, while the assessment mode is used to evaluate real ability. It removes hints, gives the judgment back to the student, and uses hidden faults plus a one-time synchronization result to verify whether the student has truly mastered pre-synchronization checks and fault troubleshooting.
