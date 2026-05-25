# ThreePhase 三相电并网仿真教学系统

基于 PyQt5 的高压机组并网操作培训桌面应用。当前主流程为隔离母排模式，覆盖五步并网测试、错误场景注入、物理接线黑盒修复和基础回归测试。

详细实现背景见 [context.md](context.md)，长期维护清单见 [MAINTENANCE_CHECKLIST.md](MAINTENANCE_CHECKLIST.md)。

## 快速开始

当前验证环境：Python 3.11.9。

```bash
pip install PyQt5 matplotlib numpy pytest
python app/main.py
```

运行测试：

```bash
python -m pytest
```

## 项目结构

```text
ThreePhase/
├── app/                 # 应用入口、控制器与信号
├── adapters/            # UI 渲染快照
├── domain/              # 领域模型、常量、故障场景、步骤状态
├── services/            # 物理引擎、五步测试、故障管理、黑盒修复
├── ui/                  # PyQt5 主窗口、控制面板、Tab 与控件
├── tests/               # 回归测试与快照
├── README.md
└── context.md
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
  └── 五步测试 Service
```

`SimulationState` 是运行态数据源；`PhysicsEngine` 每帧更新波形、母排仲裁、断路器保护和测量值；五步测试 Service 负责记录、校验和流程推进；UI 只负责展示和采集操作。

## 五步测试流程

| 步骤 | 服务 | 核心目标 |
|------|------|----------|
| 1. 回路导通测试 | `LoopTestService` | `AA/BB/CC` 同相导通，`AB/AC/BC` 异相隔离 |
| 2. PT 电压检查 | `PtVoltageCheckService` | PT1/PT2/PT3 三相线电压在额定容差内 |
| 3. PT 相序检查 | `PtPhaseCheckService` | PT1/PT2/PT3 相序显示正序、反序或异常 |
| 4. PT 压差测试 | `PtExamService` | 比较机组侧 PT 与母排侧 PT2 的二次相电压矢量差 |
| 5. 同期功能测试 | `SyncTestService` | Gen2 自动追踪 Gen1，满足同期条件后合闸 |

第四步压差计算口径：

```python
gen_ph = gen_line / sqrt(3)
bus_ph = bus_line / sqrt(3)
same_phase = abs(gen_ph - bus_ph)
cross_phase = sqrt(gen_ph**2 + bus_ph**2 + gen_ph * bus_ph)
```

E03 的 PT3 A 相极性反接会改变压差口径：同相变为 `gen_ph + bus_ph`，跨相变为 `sqrt(gen_ph**2 + bus_ph**2 - gen_ph * bus_ph)`。

## 故障场景

| 场景 | 状态 | 故障内容 | 主要检出点 | 修复入口 |
|------|------|----------|------------|----------|
| E01 | 启用 | Gen1 A/B 相接线互换 | 步骤 1、3、4；第五步事故拦截 | 第五步事故弹窗 |
| E02 | 启用 | Gen2 B/C 相接线互换 | 步骤 1、3、4；第五步事故拦截 | G2 机端黑盒 / 事故弹窗 |
| E03 | 启用 | PT3 A 相极性反接 | 步骤 2、3、4；未修复时第五步事故拦截 | PT3 接线盒极性标识 |
| E04 | 启用 | PT3 实际变比 `11000:93` | 步骤 2、4 | 控制台 PT3 变比恢复 `11000:193` |
| E05-E14 | 启用 | Gen1/PT1 接线矩阵故障 | 步骤 1、3、4 | G1/PT1 黑盒渐进式修复 |
| E17-E21 | 启用 | PT2 母排 PT 二次侧三线接反 | 步骤 3、4 | PT2 接线盒 |
| E15-E16 | 禁用 | Gen2 过电压、强行非同期合闸 | 开发中 | 暂无 |

黑盒修复为渐进式：保存某个接线盒后会先写回运行态；只有当前场景涉及的全部可修复目标恢复正常，才会自动清除故障。

## 流程模式

| 模式 | 行为 |
|------|------|
| `teaching` | 教学模式，允许带异常继续收集证据 |
| `engineering` | 工程模式，要求当前步骤合格后才能推进 |

E01/E02 的真实修复入口保留在第五步事故弹窗；E03 优先通过 PT3 接线盒修复；E04 通过变比面板修复，不走黑盒门禁。

## 测试覆盖

当前测试集中覆盖：

- 黑盒修复编排
- E04 PT3 变比修复
- 第一步六组回路记录
- 物理引擎快照
- 第三步相序判定
- 第五步完成态稳定

常用命令：

```bash
python -m pytest
git -c core.whitespace=cr-at-eol diff --check
```
