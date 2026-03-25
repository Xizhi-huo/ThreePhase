"""
domain/fault_scenarios.py
故障场景元数据字典。

每个场景键值对应一个教学故障场景，包含：
  - title        : 显示名称
  - category     : 故障大类（I 接线 / II 运行 / III 数值 / IV 危险操作）
  - label        : 大类中文标签
  - description  : 故障原因说明（面向管理员/教师）
  - symptom      : 学员可观察到的现象（面向学员报告）
  - affected_steps: 受影响的步骤列表（1-5）
  - detection_step: 首个可检测到故障的步骤
  - danger_level : 'recoverable'（可恢复）或 'accident'（事故级别）
  - params       : 故障注入参数（由控制器读取）
  - repair_prompt: 虚拟修复确认对话框文案
"""

SCENARIOS: dict = {
    '': {
        'title': '正常场景（无故障）',
        'category': None,
        'label': '正常',
        'description': '标准流程，无任何故障注入。',
        'symptom': '所有测量值均正常。',
        'affected_steps': [],
        'detection_step': None,
        'danger_level': 'recoverable',
        'params': {},
        'repair_prompt': '',
    },

    'E01': {
        'title': 'E01 — Gen1 A/B 相接线对调',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen1 机端 A 相与 B 相端子接线对调：A 端子接了 B 相绕组，B 端子接了 A 相绕组。'
            '导致 PT1 相序显示异常（ACB 逆序），第一步 AA/BB 回路断路，第四步压差矩阵异常。'
        ),
        'symptom': (
            '第一步：AA 回路 ∞Ω（断路），BB 回路 ∞Ω（断路），CC 回路正常。\n'
            '第三步：PT1 相序仪显示 ACB（逆序）。\n'
            '第四步：PT1_A↔PT2_B 压差 ≈ 0V，PT1_A↔PT2_A 压差 ≈ 146V。'
        ),
        'affected_steps': [1, 3, 4],
        'detection_step': 1,
        'danger_level': 'recoverable',
        'params': {
            'pt1_phase_order': ['B', 'A', 'C'],   # PT1 端子 A→B相, B→A相, C→C相
            'g1_loop_swap': ('A', 'B'),             # G1 回路测试相序交换对
        },
        'repair_prompt': (
            '已定位故障：Gen1 机端 A/B 相接线对调。\n\n'
            '修复方法：将 Gen1 接线盒内 A 相与 B 相端子重新对调接回原位。\n\n'
            '点击【确认修复】继续测试流程。'
        ),
    },

    'E02': {
        'title': 'E02 — Gen2 B/C 相接线对调',
        'category': 'I',
        'label': '接线错误',
        'description': (
            'Gen2 机端 B 相与 C 相端子接线对调：B 端子接了 C 相绕组，C 端子接了 B 相绕组。'
            '导致 PT3 相序逆序，第一步 BB/CC 回路断路，第四步压差矩阵异常。'
        ),
        'symptom': (
            '第一步：BB 回路 ∞Ω（断路），CC 回路 ∞Ω（断路），AA 回路正常。\n'
            '第三步：PT3 相序仪显示 ACB（逆序）。\n'
            '第四步：PT3_B↔PT2_C 压差 ≈ 0V，PT3_B↔PT2_B 压差 ≈ 146V。'
        ),
        'affected_steps': [1, 3, 4],
        'detection_step': 1,
        'danger_level': 'recoverable',
        'params': {
            'pt3_phase_order': ['A', 'C', 'B'],   # PT3 端子 A→A相, B→C相, C→B相
            'g2_loop_swap': ('B', 'C'),             # G2 回路测试相序交换对
        },
        'repair_prompt': (
            '已定位故障：Gen2 机端 B/C 相接线对调。\n\n'
            '修复方法：将 Gen2 接线盒内 B 相与 C 相端子重新对调接回原位。\n\n'
            '点击【确认修复】继续测试流程。'
        ),
    },

    'E03': {
        'title': 'E03 — PT3 A 相极性反接',
        'category': 'II',
        'label': '运行条件错误',
        'description': (
            'PT3 A 相二次端子极性反接（K/k 端子对调）：A 端子实际输出 −VA。'
            '第四步 PT3_A 行所有压差均异常：AA 组显示约 212V，AB/AC 组显示约 106V。'
        ),
        'symptom': (
            '第二步：PT3 单体线电压正常（RMS 不受极性影响）。\n'
            '第四步：PT3_A↔PT2_A ≈ 212V（应≈0V）；\n'
            '         PT3_A↔PT2_B ≈ 106V（应≈146V）；\n'
            '         PT3_A↔PT2_C ≈ 106V（应≈146V）。\n'
            'PT3_B/C 行数据正常。'
        ),
        'affected_steps': [4],
        'detection_step': 4,
        'danger_level': 'recoverable',
        'params': {
            'pt3_a_reversed': True,   # PT3 A 相二次侧极性反接
        },
        'repair_prompt': (
            '已定位故障：PT3 A 相二次端子极性反接。\n\n'
            '修复方法：将 PT3 A 相二次端子 K/k 对调，恢复正确极性。\n\n'
            '点击【确认修复】继续测试流程。'
        ),
    },

    'E04': {
        'title': 'E04 — PT3 变比铭牌参数错误',
        'category': 'III',
        'label': '数值异常',
        'description': (
            'PT3 实际变比为 75（铭牌额定值 57 = 11000/193）。'
            '导致 PT3 二次线电压测量值偏低（约 140V，额定约 184V），超出 ±15% 容差下限。'
        ),
        'symptom': (
            '第二步：PT3 线电压读数约 140V（正常约 184V），显示红色【异常】标志。\n'
            '第四步：所有 PT3_X↔PT2_Y 压差均偏小（因 PT3 二次侧电压偏低）。'
        ),
        'affected_steps': [2, 4],
        'detection_step': 2,
        'danger_level': 'recoverable',
        'params': {
            'pt3_ratio': 75.0,   # PT3 故障变比（正常值约 57.0）
        },
        'repair_prompt': (
            '已定位故障：PT3 变比铭牌参数录入错误，实际变比为 75，非额定 57。\n\n'
            '修复方法：核查 PT3 铭牌，更正变比参数至实测值 75，或更换匹配额定变比的 PT3。\n\n'
            '点击【确认修复】继续测试流程（系统将使用正确变比重新计算）。'
        ),
    },

    'E05': {
        'title': 'E05 — Gen2 电压调节器故障（过电压）',
        'category': 'III',
        'label': '数值异常',
        'description': (
            'Gen2 电压调节器故障，运行电压固定在 13000V（正常额定 10500V），'
            '电压偏差约 +23.8%，超出并网电压容差 ±4.8%（±500V）。'
            '第四步同相压差偏大，第五步同期检查无法通过电压幅值校核。'
        ),
        'symptom': (
            '第二步：PT3 线电压约 228V（正常约 184V），显示红色【异常】。\n'
            '第四步：PT3_A↔PT2_A ≈ 71V（应≈0V），所有同相压差均偏大。\n'
            '第五步：同步仪电压差超出容差，仲裁器无法完成幅值同步。'
        ),
        'affected_steps': [2, 4, 5],
        'detection_step': 2,
        'danger_level': 'recoverable',
        'params': {
            'gen2_amp': 13000.0,   # Gen2 注入后锁定的异常电压幅值（V）
        },
        'repair_prompt': (
            '已定位故障：Gen2 电压调节器故障，运行电压偏高约 13000V（超出额定 +23.8%）。\n\n'
            '修复方法：检修 Gen2 电压调节器（AVR），恢复至额定 10500V 输出。\n\n'
            '点击【确认修复】继续测试流程（Gen2 电压将恢复至额定值）。'
        ),
    },

    'E06': {
        'title': 'E06 — 强行并网（非同期合闸危险操作）',
        'category': 'IV',
        'label': '危险操作',
        'description': (
            'Gen2 自动相位追踪功能失效：仲裁器无法捕获相角，导致自动同期无法完成。'
            '正确操作：学员应识别异常并拒绝合闸，上报故障。'
            '危险操作：若强行点击「非同期合闸」按钮，将触发短路冲击电流事故模拟。'
        ),
        'symptom': (
            '第五步：Gen2 相位追踪停止，相角差无法收敛至 0°，同步仪相位差持续振荡。\n'
            '仲裁器显示「Gen2 相角追踪故障，无法自动同期！」\n'
            '若强行合闸：触发短路冲击电流，断路器跳闸，系统产生事故报告。'
        ),
        'affected_steps': [5],
        'detection_step': 5,
        'danger_level': 'accident',
        'params': {
            'phase_track_disabled': True,   # 禁止 Gen2 自动相位追踪
        },
        'repair_prompt': (
            '⚠️ 危险操作警告 ⚠️\n\n'
            '检测到非同期合闸操作！Gen2 与母排相位差过大时强行合闸，'
            '将产生巨大冲击电流，可能损坏发电机绕组与断路器触头。\n\n'
            '实际系统中此操作将导致继电保护跳闸并触发事故报告。\n\n'
            '正确做法：Gen2 相位追踪故障时，应停机检修追踪模块，\n'
            '严禁在相位差未收敛时强行合闸。\n\n'
            '点击【确认】查看事故模拟结果。'
        ),
    },
}
