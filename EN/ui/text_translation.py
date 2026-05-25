"""Runtime UI text translation helpers."""

from __future__ import annotations

import re
from typing import Any, Callable

from PyQt5 import QtCore, QtGui, QtWidgets


_INSTALLED = False
_COMBO_ORIGINAL_ROLE = int(QtCore.Qt.UserRole) + 4201
_HAN_RE = re.compile(r"[\u4e00-\u9fff]+")


_EXACT = {
    "小电阻接地": "Low-resistance grounding",
    "断开": "Disconnected",
    "直接接地": "Solid grounding",
    "脱开位置": "Disconnected position",
    "试验位置": "Test position",
    "工作位置": "Service position",
    "隔离母排": "Isolated bus",
    "孤岛运行": "Islanded operation",
    "并网运行": "Grid-tied operation",
    "黑启动": "Black start",
    "正常": "Normal",
    "异常": "Abnormal",
    "通过": "Pass",
    "未通过": "Fail",
    "未记录": "Not recorded",
    "未接": "Not connected",
    "未导通": "Open circuit",
    "无": "None",
    "工作": "Service",
    "脱开": "Disconnected",
    "试验": "Test",
    "停机": "Stopped",
    "运行": "Running",
    "起机": "Start",
    "合闸": "Close",
    "分闸": "Open",
    "断路": "Open",
    "手动": "Manual",
    "自动": "Auto",
    "正序": "Positive sequence",
    "反序": "Reverse sequence",
    "逆序": "Reverse sequence",
    "同相": "In phase",
    "跨相": "Cross phase",
    "有功": "Active power",
    "无功": "Reactive power",
    "平衡": "Balanced",
    "接近": "Near",
    "放大": "Diverging",
    "收敛": "Converging",
    "持平": "Flat",
    "停止": "Stopped",
    "正序 ↻": "Positive sequence ↻",
    "反序 ↺": "Reverse sequence ↺",
}


_REPLACEMENTS = {
    "三相电并网仿真教学系统": "Three-phase Grid Synchronization Training Simulator",
    "实时波形与同期表": "Live Waveforms and Synchroscope",
    "母排拓扑与环流监测": "Bus Topology and Circulating-current Monitor",
    "第一步：回路连通性测试": "Step 1: Circuit Continuity Test",
    "第二步：PT 单体线电压检查": "Step 2: PT Line-voltage Check",
    "第二步：PT线电压检查": "Step 2: PT Line-voltage Check",
    "第二步：PT 电压校准": "Step 2: PT Voltage Calibration",
    "第三步：PT 相序检查": "Step 3: PT Phase-sequence Check",
    "第三步：PT相序检查": "Step 3: PT Phase-sequence Check",
    "第四步：PT 二次端子压差测试": "Step 4: PT Secondary-terminal Voltage-difference Test",
    "第四步：PT二次端子压差测试": "Step 4: PT Secondary-terminal Voltage-difference Test",
    "第五步：同步功能测试": "Step 5: Synchronization Function Test",
    "合闸前测试模式": "Pre-close Test Mode",
    "合闸前测试": "Pre-close Test",
    "隔离母排合闸前": "Before Closing the Isolated Bus",
    "测试步骤": "Test Steps",
    "实时状态": "Live Status",
    "实时同步状态": "Live Synchronization Status",
    "操作提示": "Operation Tip",
    "当前步骤": "Current Step",
    "流程模式": "Flow Mode",
    "教学/工程": "Teaching/Engineering",
    "教学模式": "Teaching Mode",
    "考核模式": "Assessment Mode",
    "考核成绩单": "Assessment Scorecard",
    "考核结果报告": "Assessment Result Report",
    "随机故障判定": "Random Fault Identification",
    "随机故障考核": "Random Fault Assessment",
    "随机出题方式": "Random Scenario Mode",
    "指定场景": "Specified Scenario",
    "正常模式": "Normal Mode",
    "随机故障": "Random Fault",
    "故障训练场景": "Fault Training Scenario",
    "教师预设": "Instructor Preset",
    "已选": "Selected",
    "无故障注入": "No fault injected",
    "无故障": "No fault",
    "标准流程": "Standard procedure",
    "所有测量值均正常": "All measurements are normal",
    "流程纪律": "Process Discipline",
    "异常识别与故障定位": "Abnormality Recognition and Fault Location",
    "黑盒修复": "Black-box Repair",
    "效率与规范性": "Efficiency and Compliance",
    "步骤进入顺序": "Step Entry Order",
    "完成本步尝试次数": "Step Completion Attempts",
    "门禁拦截次数": "Interlock Blocks",
    "闭环门禁触发次数": "Closed-loop Interlock Triggers",
    "测量记录总数": "Total Measurement Records",
    "无效测量次数": "Invalid Measurements",
    "打开黑盒": "Opened Black Box",
    "黑盒交换次数": "Black-box Swaps",
    "错误确认次数": "Wrong Confirmations",
    "首次发现异常步骤": "First Abnormality Step",
    "故障修复时间": "Fault Repair Time",
    "严重误操作次数": "Serious Misoperations",
    "总分": "Total Score",
    "总耗时": "Total Time",
    "否决原因": "Veto Reason",
    "分项汇总": "Category Summary",
    "详细计分点": "Detailed Scoring Items",
    "过程统计": "Process Statistics",
    "额外扣分说明": "Extra Penalty Notes",
    "学员判定故障": "Student Fault Selection",
    "判定结果": "Identification Result",
    "实际故障": "Actual Fault",
    "额外扣分合计": "Total Extra Penalty",
    "类别": "Category",
    "编号": "ID",
    "计分点": "Scoring Item",
    "结果": "Result",
    "满分": "Max",
    "实得": "Score",
    "说明": "Notes",
    "场景": "Scenario",
    "模式": "Mode",
    "完成时间": "Finished At",
    "部分扣分": "Partial Deduction",
    "存在扣分项": "Deductions Found",
    "表现稳定": "Stable Performance",
    "需要重点关注": "Needs Attention",
    "关闭": "Close",
    "知道了": "OK",
    "确认修复": "Confirm Repair",
    "保存接线": "Save Wiring",
    "重置默认": "Reset Defaults",
    "提交判定并生成成绩单": "Submit Selection and Generate Scorecard",
    "请选择故障场景": "Select a Fault Scenario",
    "请先选择一个故障场景": "Select a fault scenario first",
    "当前考核尚未闭环": "Current Assessment Is Not Closed",
    "仍有接线故障未修复": "Wiring Fault Still Unrepaired",
    "当前流程尚未闭环": "Current Process Is Not Closed",
    "当前已记录的异常现象": "Recorded Abnormal Symptoms",
    "物理接线检查 / 手动修复": "Physical Wiring Inspection / Manual Repair",
    "开盖查线": "Open Cover and Inspect Wiring",
    "机端接线检查": "Generator-terminal Wiring Check",
    "接线盒检查": "Junction-box Check",
    "控制柜负载分配接线检查": "Load-share Cabinet Wiring Check",
    "控制柜负载分配接线": "Load-share Cabinet Wiring",
    "打开控制柜": "Open Control Cabinet",
    "负载分配接线检查": "Load-share Wiring Check",
    "当前状态": "Current Status",
    "两侧控制柜接线一致": "Both control cabinets match",
    "两侧控制柜接线不一致": "Control-cabinet wiring mismatch",
    "仅 Gen1 接入": "Only Gen1 connected",
    "仅 Gen2 接入": "Only Gen2 connected",
    "未接线": "Not wired",
    "已接端子": "Connected terminals",
    "上方绕组": "Upper windings",
    "下方接线柱": "Lower terminals",
    "仅查看": "View only",
    "只读": "Read-only",
    "可交互修复": "Interactive repair",
    "可互换": "Swappable",
    "可切换极性": "Polarity switchable",
    "不可直接修复": "Direct repair not allowed",
    "当前物理状态": "Current physical state",
    "母排一次侧输入": "Bus primary-side input",
    "二次侧输出": "Secondary output",
    "测量端口": "Measurement port",
    "一次侧输入": "Primary input",
    "实际输出": "Actual output",
    "实际来相": "Actual incoming phase",
    "极性": "Polarity",
    "变压器铁芯": "Transformer Core",
    "黑盒": "Black Box",
    "一次侧结果": "Primary-side Result",
    "二次侧测量端口": "Secondary Measurement Ports",
    "一次侧输入电缆": "Primary Input Cable",
    "内闭绕组": "Internal Windings",
    "输出接线柱": "Output Terminals",
    "相序仪": "Phase-sequence Meter",
    "顺时针": "Clockwise",
    "逆时针": "Counterclockwise",
    "待接线": "Waiting for wiring",
    "未接入": "Not connected",
    "接待线": "Waiting for wiring",
    "接入": "Connect",
    "断开": "Disconnect",
    "三点接线": "three-point wiring",
    "相序结果": "phase-sequence result",
    "相序正确": "Phase sequence correct",
    "相序错误": "Phase sequence wrong",
    "接线有误": "wiring error",
    "正在接线中": "is being wired",
    "结果尚未就绪": "result is not ready",
    "切换到": "switched to",
    "母排拓扑页": "bus topology page",
    "波形/相量页": "waveform/phasor page",
    "打开母排拓扑页": "Open Bus Topology",
    "打开波形/相量页": "Open Waveform/Phasor View",
    "开启/关闭万用表": "Toggle Multimeter",
    "开启 / 关闭万用表": "Toggle Multimeter",
    "拿取万用表": "Pick Up Multimeter",
    "万用表未开启": "Multimeter is off",
    "万用表": "Multimeter",
    "表笔": "probe",
    "红/黑": "red/black",
    "红表笔": "red probe",
    "黑表笔": "black probe",
    "当前表笔": "Current probes",
    "未放置": "not placed",
    "等待放置黑表笔": "waiting for black probe",
    "探针": "probe",
    "蜂鸣": "beep",
    "无蜂鸣": "no beep",
    "通断挡": "continuity mode",
    "通断测试": "continuity test",
    "回路连通性测试": "Circuit Continuity Test",
    "回路检查模式": "circuit-check mode",
    "回路检查": "Circuit Check",
    "回路测试": "Circuit Test",
    "回路测量记录": "Circuit Measurement Records",
    "回路数据": "circuit data",
    "回路": "circuit",
    "导通": "continuity",
    "断路": "open circuit",
    "隔离": "isolated",
    "异相": "cross-phase",
    "同相": "same-phase",
    "测点": "test point",
    "测试对象": "Test Target",
    "快速记录": "Quick Record",
    "快捷记录": "Quick Record",
    "记录当前表笔位置": "Record Current Probe Position",
    "记录当前": "Record Current",
    "记录测试结果": "Record Test Results",
    "记录第一轮": "Record Round 1",
    "记录第二轮": "Record Round 2",
    "记录全部": "Record All",
    "记录 ": "Record ",
    "已记录": "Recorded",
    "尚未记录": "not recorded",
    "数据已锁定": "data locked",
    "请继续": "continue",
    "请先": "please first",
    "请按步骤": "Follow the steps",
    "请在": "Please use",
    "点击": "click",
    "继续": "continue",
    "剩余项目": "remaining items",
    "全部记录": "all records",
    "重置本步": "Reset Step",
    "重置回路测试": "Reset Circuit Test",
    "重置线电压检查": "Reset Line-voltage Check",
    "重置相序检查": "Reset Phase-sequence Check",
    "重置同步测试": "Reset Synchronization Test",
    "完成第一步测试": "Complete Step 1",
    "完成第二步测试": "Complete Step 2",
    "完成第三步测试": "Complete Step 3",
    "完成第五步测试": "Complete Step 5",
    "完成本步": "Complete Step",
    "完成本步 ✓": "Complete Step ✓",
    "开始测试": "Start Test",
    "开始第一步测试": "Start Step 1",
    "开始第二步测试": "Start Step 2",
    "开始第三步测试": "Start Step 3",
    "开始第五步测试": "Start Step 5",
    "退出测试": "Exit Test",
    "退出第二步测试": "Exit Step 2",
    "退出第三步测试": "Exit Step 3",
    "退出第五步测试": "Exit Step 5",
    "进入回路检查模式": "Enter Circuit-check Mode",
    "退出回路检查模式": "Exit Circuit-check Mode",
    "管理员": "Admin",
    "母排": "Bus",
    "母线": "Bus",
    "死母线": "Dead bus",
    "死母线投入延时": "Dead-bus close delay",
    "参考基准": "Reference",
    "参考源": "Reference Source",
    "基准": "Reference",
    "供电": "powered",
    "无电": "de-energized",
    "带电": "energized",
    "独立供电": "standalone supply",
    "并联运行": "parallel operation",
    "建立母排基准": "establish bus reference",
    "无参考源": "No reference source",
    "当前无母排参考": "No current bus reference",
    "母线状态": "Bus Status",
    "运行模式": "Operating Mode",
    "机组状态": "Generator Status",
    "机组": "generator",
    "发电机": "Generator",
    "电网供电": "grid powered",
    "外部电网": "external grid",
    "远程启动信号": "Remote Start Signal",
    "闭合全局": "Close global",
    "触发自动模式": "trigger auto mode",
    "开启自动": "Enable Auto",
    "关闭自动": "Disable Auto",
    "同步功能测试": "Synchronization Function Test",
    "同步误差监测": "Synchronization Error Monitor",
    "同期判定面板": "Synchronization Decision Panel",
    "同期判定": "Synchronization Decision",
    "同期条件": "Synchronization Conditions",
    "当前可否合闸": "Ready to Close",
    "允许合闸": "Close Allowed",
    "可合闸": "ready to close",
    "未就绪": "Not Ready",
    "接近就绪": "Nearly Ready",
    "已同步": "Synchronized",
    "同步中": "Synchronizing",
    "等待收敛": "Waiting for convergence",
    "三值收敛": "All three values converged",
    "两轮同步测试": "two synchronization rounds",
    "第一轮": "Round 1",
    "第二轮": "Round 2",
    "最终": "Final",
    "互换角色": "swap roles",
    "自动同步": "auto synchronization",
    "同步跟踪": "synchronization tracking",
    "同步功能验证": "synchronization function verification",
    "自动合闸逻辑": "auto-close logic",
    "同期装置": "synchronizer",
    "非同期合闸": "out-of-sync closing",
    "非同期冲击电流": "out-of-sync inrush current",
    "波形": "waveform",
    "相量": "phasor",
    "相量图": "phasor diagram",
    "三相实时波形": "Three-phase Live Waveforms",
    "母线总览": "Bus Overview",
    "次级趋势信息": "secondary trend information",
    "相位关系": "phase relationship",
    "窗口角度": "Window Angle",
    "电压": "Voltage",
    "频率": "Frequency",
    "幅值": "Amplitude",
    "相位": "Phase",
    "频差": "frequency difference",
    "压差": "voltage difference",
    "相角差": "phase-angle difference",
    "角差": "angle difference",
    "相对参考频率": "Frequency vs Reference",
    "相对参考电压": "Voltage vs Reference",
    "相对参考相角": "Phase Angle vs Reference",
    "当前机组方式": "Current Generator Mode",
    "趋势": "Trend",
    "待评估": "Pending",
    "条件正在收敛": "conditions are converging",
    "仍不满足": "still does not meet",
    "继续调整或等待自动收敛": "continue adjustment or wait for auto convergence",
    "第二个采样点": "second sample point",
    "开始判断收敛方向": "start judging convergence direction",
    "PT 单体线电压检查": "PT Line-voltage Check",
    "PT 线电压检查": "PT Line-voltage Check",
    "PT 电压校准": "PT Voltage Calibration",
    "PT 变比参数": "PT Ratio Parameters",
    "PT 二次端子压差": "PT Secondary-terminal Voltage Difference",
    "PT 二次端子": "PT secondary terminals",
    "PT 二次侧": "PT secondary side",
    "PT 一次侧": "PT primary side",
    "二次侧": "secondary side",
    "一次侧": "primary side",
    "二次": "secondary",
    "一次": "primary",
    "变比": "ratio",
    "铭牌参数": "nameplate parameter",
    "额定值": "rated value",
    "额定": "rated",
    "实际硬件": "actual hardware",
    "物理测量": "physical measurement",
    "线电压": "line voltage",
    "相电压": "phase voltage",
    "电压校准": "Voltage Calibration",
    "电压检查": "Voltage Check",
    "电压读数": "voltage reading",
    "二次侧电压": "secondary-side voltage",
    "输出电压": "output voltage",
    "压差矩阵": "voltage-difference matrix",
    "压差测量": "voltage-difference measurement",
    "压差考核": "Voltage-difference Assessment",
    "电压异常": "voltage abnormality",
    "严重偏低": "seriously low",
    "偏低": "low",
    "偏高": "high",
    "已达到": "reached",
    "暂无有效": "no valid",
    "测量项": "Measurement",
    "状态": "Status",
    "相序检查": "Phase-sequence Check",
    "相序仪显示": "phase-sequence meter shows",
    "相序仪旋转方向": "phase-sequence meter rotation direction",
    "旋转方向": "rotation direction",
    "接入相序仪": "connect phase-sequence meter",
    "相序判断": "phase-sequence judgment",
    "相序异常": "phase-sequence abnormality",
    "相位不匹配": "phase mismatch",
    "极性反接": "polarity reversed",
    "极性未修复": "polarity unrepaired",
    "正负极颠倒": "positive/negative polarity reversed",
    "输出反相": "output inverted",
    "恢复正确极性": "restore correct polarity",
    "对调": "swapped",
    "接反": "reversed",
    "换位": "swap",
    "接线错误": "wiring error",
    "接线故障": "wiring fault",
    "接线": "wiring",
    "端子": "terminal",
    "端子排": "terminal block",
    "接线盒": "junction box",
    "测量端": "measurement terminal",
    "机端": "generator terminal",
    "高压侧": "high-voltage side",
    "中性点": "neutral point",
    "接地系统": "grounding system",
    "小电阻": "low resistance",
    "直接接地": "solid grounding",
    "未接地": "ungrounded",
    "悬浮脱开": "floating disconnected",
    "漂移电位": "floating potential",
    "短路隐患": "short-circuit risk",
    "寄生回路": "parasitic circuit",
    "完整通路": "complete path",
    "机械合闸": "mechanically closed",
    "恢复小电阻接地": "restore low-resistance grounding",
    "断开中性点小电阻": "disconnect the neutral low resistance",
    "断开中性点接地": "disconnect neutral grounding",
    "手动工作模式": "manual service mode",
    "工作模式": "operating mode",
    "切至手动": "switch to manual",
    "切至工作位置": "switch to service position",
    "断路器断开": "breaker open",
    "断路器自动脱扣": "breaker auto-tripped",
    "断路器": "breaker",
    "开关柜": "switchgear",
    "PCC模式": "PCC Mode",
    "PCC 模式": "PCC Mode",
    "调速增益": "Governor Gain",
    "同步增益": "Sync Gain",
    "仿真全局时间流速": "Global Simulation Time Scale",
    "速度": "Speed",
    "核心参数整定": "Core Parameter Setup",
    "继电保护系统": "Relay Protection System",
    "继电保护监控中": "Relay protection monitoring",
    "保护": "Protection",
    "监控中": "monitoring",
    "跳闸阈值": "trip threshold",
    "阈值": "threshold",
    "跳闸": "trip",
    "脱扣": "trip",
    "环流": "circulating current",
    "机组间无环流": "No inter-generator circulating current",
    "机组间未形成直接环流回路": "No direct circulating-current loop between generators",
    "环流过大": "excessive circulating current",
    "短路电流": "short-circuit current",
    "下垂控制": "droop control",
    "功率电流": "power current",
    "熔断停止": "fused and stopped",
    "物理帧更新连续失败": "physics frame update failed consecutively",
    "阶段": "stage",
    "请检查控制台错误日志": "check the console error log",
    "暂停整个物理空间": "Pause Entire Physics Space",
    "恢复物理时空": "Resume Physics Space",
    "紧急一键强行合闸": "Emergency Force Close",
    "显示发电机与母排之间的连线": "Show lines between generators and bus",
    "取消勾选": "uncheck",
    "黑盒模式": "black-box mode",
    "当前流程模式": "current flow mode",
    "要求先排除故障并复测合格": "requires fault removal and passing retest first",
    "当前流程中的黑盒检查区": "black-box inspection area in the current flow",
    "后续流程": "subsequent flow",
    "后续步骤": "subsequent steps",
    "第五步前统一进行检修": "perform unified repair before Step 5",
    "故障训练模式已启用": "Fault training mode is enabled",
    "已发现异常证据": "Abnormal evidence found",
    "故障已修复": "Fault repaired",
    "剩余步骤": "remaining steps",
    "正常流程": "normal process",
    "检修": "repair",
    "排查": "troubleshoot",
    "发现并定位异常": "find and locate abnormalities",
    "发现异常": "abnormality found",
    "故障": "fault",
    "错误": "error",
    "正确": "correct",
    "虚假正常": "false normal",
    "虚假为": "falsely",
    "隐性故障": "hidden fault",
    "完全隐性错误": "fully hidden error",
    "迷惑性强": "highly misleading",
    "唯一可靠判据": "only reliable criterion",
    "唯一有效检测": "only effective detection",
    "唯一出路": "only way out",
    "单相核相的盲区": "blind spot of single-phase phase comparison",
    "单相核相": "single-phase phase comparison",
    "核相": "phase comparison",
    "跨相位差": "cross-phase difference",
    "相位差": "phase difference",
    "相互抵消": "mutually cancel",
    "相消": "cancel out",
    "净效果": "net effect",
    "测量端净相序": "net phase sequence at measurement terminals",
    "三处错误": "three errors",
    "三级复合": "three-level composite",
    "复合故障": "composite fault",
    "两处跨层错误": "two cross-layer errors",
    "两处同层错误": "two same-layer errors",
    "不同换位": "different swaps",
    "相同换位": "same swap",
    "三轮换": "three-phase rotation",
    "整体轮换": "overall phase rotation",
    "奇数次": "odd number of",
    "逆序": "reverse sequence",
    "正序轮换": "positive-sequence rotation",
    "定位需拆检": "location requires disassembly inspection",
    "需物理拆检": "requires physical disassembly inspection",
    "物理拆检": "physical disassembly inspection",
    "打开 PT2 接线盒": "open the PT2 junction box",
    "打开 PT2": "open PT2",
    "打开": "open",
    "恢复正序": "restore positive sequence",
    "恢复为 ABC 正序": "restore to ABC positive sequence",
    "恢复至额定值": "restore to rated value",
    "恢复": "restore",
    "重新测量": "measure again",
    "重新记录": "record again",
    "重新完成": "complete again",
    "重新调整": "adjust again",
    "重新绕制": "rewind",
    "更换": "replace",
    "修复方法": "Repair method",
    "修复步骤": "Repair steps",
    "已定位故障": "Fault located",
    "已定位隐性故障": "Hidden fault located",
    "已定位三级复合故障": "Three-level composite fault located",
    "故障已清除": "fault cleared",
    "全部接线均已修复": "all wiring has been repaired",
    "接线已修复": "wiring repaired",
    "接线已保存": "wiring saved",
    "请关闭黑盒后返回外部测试流程复测": "close the black box and return to the external test flow for retest",
    "请关闭黑盒后重新测量": "close the black box and measure again",
    "此处": "this location",
    "其他位置": "other locations",
    "提交": "submit",
    "前两步提前打开 PT 黑盒次数": "PT black-box openings during first two steps",
    "提前打开 PT 黑盒": "opened PT black box early",
    "高危违规": "high-risk violation",
    "额外扣": "extra deduction",
    "随机故障最终场景判定错误": "random-fault final scenario identified incorrectly",
    "存在严重误操作": "serious misoperation exists",
    "闭环": "closed loop",
    "尚未完成": "not completed",
    "暂不能": "cannot yet",
    "不允许": "not allowed",
    "可以": "can",
    "不能": "cannot",
    "需先": "must first",
    "需要": "need",
    "无需": "not required",
    "不再": "no longer",
    "统一": "unified",
    "当前": "current",
    "全部": "all",
    "所有": "all",
    "每个": "each",
    "具体": "specific",
    "具体说明": "details",
    "前四步": "first four steps",
    "前两步": "first two steps",
    "第一步": "Step 1",
    "第二步": "Step 2",
    "第三步": "Step 3",
    "第四步": "Step 4",
    "第五步": "Step 5",
    "第 ": "Step ",
    " 项": " items",
    " 组": " groups",
    " 轮": " round",
    " 次": " times",
    " 分": " points",
    "步": "step",
    "轮次": "Round",
    "两轮": "two rounds",
    "三组": "three groups",
    "九组": "nine groups",
    "三相": "three-phase",
    "三项": "three items",
    "六组": "six groups",
    "十八组": "18 groups",
    "全部18组": "all 18 groups",
    "各三组": "three groups each",
    "各三相": "three phases each",
    "共九组": "nine groups total",
    "共两轮": "two rounds total",
    "需按顺序完成": "must be completed in order",
    "按顺序完成": "complete in order",
    "按相位": "by phase",
    "逐相": "phase by phase",
    "逐项": "item by item",
    "分别": "separately",
    "依次": "in sequence",
    "状态栏": "status bar",
    "顶部": "top",
    "侧": "side",
    "相": "phase",
    "项": "item",
    "组": "group",
    "端": "terminal",
    "页": "page",
    "表": "meter",
    "值": "value",
    "无效": "invalid",
    "有效": "valid",
    "高压": "high voltage",
    "损坏": "damage",
    "危险": "Danger",
    "警告": "Warning",
    "致命事故警告": "Fatal Accident Warning",
    "事故模拟结果": "accident simulation result",
    "损坏机组": "damage the generator set",
    "严禁": "strictly forbidden",
    "正确做法": "Correct action",
    "模拟中无保护器": "no protection device in the simulation",
    "实际系统将立即跳闸": "a real system would trip immediately",
    "炸毁": "destroyed",
    "爆炸": "explosion",
    "强行并网": "force grid connection",
    "强行合闸": "force closing",
    "故障分析": "fault analysis",
    "故障定位": "fault location",
    "疑似": "suspected",
    "严重异常": "serious abnormality",
    "异常导通": "abnormal continuity",
    "异常断路": "abnormal open circuit",
    "异常标志": "abnormal flag",
    "不符合期望": "does not meet expectation",
    "符合预期": "meets expectation",
    "期望": "expected",
    "判读": "interpretation",
    "不足": "insufficient",
    "完整": "complete",
    "不完整": "incomplete",
    "规范": "compliant",
    "不规范": "non-compliant",
    "操作顺序": "operation order",
    "记录顺序": "record order",
    "接线选择": "wiring selection",
    "结果判读": "result interpretation",
    "异常识别": "abnormality recognition",
    "形成有效判断": "formed a valid judgment",
    "形成判断": "formed a judgment",
    "直到系统门禁拦截后才意识到": "recognized only after system interlock blocked it",
    "正常场景": "normal scenario",
    "标准流程": "standard flow",
    "故障场景": "fault scenario",
    "运行条件错误": "operating-condition error",
    "数值异常": "numeric abnormality",
    "接线错误": "wiring error",
    "参数错误": "parameter error",
    "实际变比": "actual ratio",
    "控制台": "console",
    "录入": "entered",
    "计算": "calculate",
    "显示红色": "shown in red",
    "显示": "shows",
    "含": "contains",
    "不含": "does not include",
    "绕组": "winding",
    "源": "source",
    "自": "from",
    "向": "to",
    "与": "and",
    "或": "or",
    "及": "and",
    "为": "is",
    "后": "after",
    "前": "before",
    "内": "inside",
    "中": "in",
    "上": "upper",
    "下": "lower",
    "左": "left",
    "右": "right",
    "由": "by",
    "将": "will",
    "把": "set",
    "且": "and",
    "均": "all",
    "仍": "still",
    "尚": "still",
    "先": "first",
    "再": "then",
    "已": "already",
    "未": "not",
    "无": "no",
    "有": "has",
    "若": "if",
    "并": "and",
    "只": "only",
    "仅": "only",
    "可": "can",
    "会": "will",
    "让": "let",
    "使": "make",
    "因": "because",
    "导致": "causes",
    "等同于": "equivalent to",
    "完全相同": "identical",
    "完全一致": "identical",
    "完全通过": "all passed",
    "正常约": "normally about",
    "约": "about",
    "应": "should be",
    "偏差": "deviation",
    "下限": "lower limit",
    "容差": "tolerance",
    "严重": "serious",
    "高": "high",
    "低": "low",
    "大": "large",
    "小": "small",
    "首台投入": "first unit connected",
    "待命": "standby",
    "待机": "standby",
    "等待": "waiting",
    "准备投入": "ready to connect to",
    "正在捕获相角打同期": "capturing phase angle for synchronization",
    "达标": "qualified",
    "延时": "delay",
    "仲裁器": "Arbitrator",
    "仲裁": "Arbitration",
    "故障训练": "Fault Training",
    "管理": "management",
    "系统运行模式": "System Operating Mode",
    "待开发": "planned",
    "窗口": "window",
    "正文": "body",
    "报告": "report",
    "列表": "list",
    "表格": "table",
    "相序": "phase sequence",
    "正序": "positive sequence",
    "反序": "reverse sequence",
    "逆序": "reverse sequence",
    "正常": "normal",
    "异常": "abnormal",
    "通过": "pass",
    "不通过": "fail",
    "未通过": "fail",
    "有功": "active power",
    "无功": "reactive power",
    "平衡": "balanced",
    "手动": "manual",
    "自动": "auto",
    "工作位": "service position",
    "试验位": "test position",
    "脱开位": "disconnected position",
    "请": "please ",
    "请先": "Please",
    "请继续": "Continue",
    "的": " ",
    "在": " in ",
    "至": "to",
    "从": "from",
    "以": "using ",
    "属于": "is",
    "达到": "reach",
    "基本": "basic",
    "要求": "requirement",
    "及格线": "passing line",
    "整体": "overall",
    "优秀": "excellent",
    "若干": "several",
    "扣分点": "deduction items",
    "另有": "also has",
    "指定": "specified",
    "准确": "accurate",
    "判断": "judgment",
    "流程": "process",
    "过程": "process",
    "结束时": "at the end",
    "物理引擎": "physics engine",
    "已熔断停止": "has stopped after repeated failures",
    "连续失败": "consecutive failures",
    "连接": "connection",
    "已连接": "connected",
    "未连接": "not connected",
    "合法": "valid",
    "鼠标": "mouse",
    "点击两个端子": "click two terminals",
    "点击": "click",
    "查看": "view",
    "确认": "confirm",
    "完成": "complete",
    "测试": "test",
    "检查": "check",
    "记录": "record",
    "测量": "measure",
    "选择": "select",
    "比较": "compare",
    "放置": "place",
    "对准": "aligned with",
    "对应": "corresponding",
    "其余": "remaining",
    "重置": "reset",
    "重测": "retest",
    "修正": "correct",
    "纠正": "correct",
    "收集": "collect",
    "更多数据": "more data",
    "证据": "evidence",
    "分析": "analysis",
    "启动": "start",
    "开启": "turn on",
    "闭合": "close",
    "闭合开关": "close the switch",
    "不要起机": "do not start the engine",
    "两台": "both",
    "都": "both",
    "只有在": "only in",
    "才能": "can",
    "执行": "execute",
    "切换": "switch",
    "起机条件不满足": "Start conditions are not met",
    "不允许合闸": "not allowed to close",
    "合闸前步骤未完成": "pre-close steps incomplete",
    "合闸前": "before closing",
    "锁定": "locked",
    "当前机组不允许合闸": "Current generator is not allowed to close",
    "闭合远程启动信号": "close the remote start signal",
    "运行中": "running",
    "干扰": "interfere with",
    "自身电池": "internal battery",
    "靠自身电池": "using its internal battery",
    "注入微小电流": "injects a small current",
    "微小电流": "small current",
    "是否连通": "whether the circuit is continuous",
    "防止": "prevent",
    "被测": "measured",
    "进行": "perform",
    "演示": "demo",
    "通路": "continuity path",
    "不通": "open",
    "无电压": "no voltage",
    "检测到": "detected",
    "满足": "satisfied",
    "模拟闭合": "simulated closed",
    "触头闭合": "contacts closed",
    "引擎停机失压": "engine stopped and voltage was lost",
    "并网运行": "grid-connected operation",
    "建立": "establish",
    "无法": "unable to",
    "为基准": "as reference",
    "正反正": "normal-reversed-normal",
    "正正反": "normal-normal-reversed",
    "正反反": "normal-reversed-reversed",
    "反反反": "reversed-reversed-reversed",
    "反正反": "reversed-normal-reversed",
    "反反正": "reversed-reversed-normal",
    "不同": "different",
    "同对": "same swap of",
    "反接": "reversed connection",
    "双反": "two reversals",
    "绿灯": "green indicator",
    "循环": "cycle",
    "外部观测": "external observation",
    "现象": "symptom",
    "区别": "difference",
    "学员": "trainee",
    "放松警惕": "be less alert",
    "联合指向": "jointly point to",
    "联合诊断": "joint diagnosis",
    "直测": "direct measurement",
    "内部": "internal",
    "内部变压": "internal transformation",
    "接出时": "when brought out",
    "互换": "interchanged",
    "呈": "appears as",
    "两次": "two",
    "两错": "two errors",
    "四步": "four steps",
    "功能性": "functional",
    "只有": "only",
    "复接": "reconnect",
    "暴露": "expose",
    "本身": "itself",
    "假象": "illusion",
    "恰好吻合": "happen to match",
    "必须": "must",
    "揭示": "reveals",
    "陷阱": "trap",
    "盲区": "blind spot",
    "循环": "cycle",
    "不变": "unchanged",
    "存在": "exists",
    "对比": "comparison",
    "失配": "mismatch",
    "隐蔽性极高": "highly hidden",
    "破绽": "clue",
    "端同相": "terminal same-phase",
    "侧均": "sides both",
    "数值": "value",
    "被相消欺骗": "masked by cancellation",
    "应立即": "should immediately",
    "产生": "produce",
    "错误相位": "wrong phase",
    "位置": "position",
    "收敛至": "converges to",
    "反相": "opposite phase",
    "事故": "accident",
    "确认修复": "Confirm Repair",
    "确认": "Confirm",
    "接回原位": "restore to the original position",
    "不符": "does not match",
    "超出": "exceeds",
    "使用正确变比重新计算": "recalculate using the correct ratio",
    "受": "affected by",
    "影响": "effect",
    "标志": "flag",
    "控制柜": "control cabinet",
    "接入": "connect",
    "未接入": "not connected",
    "白色圆圈": "white circle",
    "黑色圆点": "black dot",
    "任何": "any",
    "注入": "injection",
    "同": "same",
    "合闸": "close",
    "参考": "reference",
    "重新": "again",
    "输出": "output",
    "保持": "keep",
    "并入": "connect to",
    "入": "connect",
    "起机": "start engine",
    "但": "but",
    "接地": "grounding",
    "不": "not",
    "和": "and",
    "提供": "provide",
    "线": "line",
    "各": "each",
    "形成": "form",
    "修复": "repair",
    "时": "when",
    "开始": "start",
    "项目": "items",
    "目": "",
    "作为": "as",
    "作": "as",
    "步骤一": "Step 1",
    "步骤二": "Step 2",
    "步骤三": "Step 3",
    "步骤四": "Step 4",
    "步骤五": "Step 5",
    "步骤": "step",
    "骤": "step",
    "矢量": "vector",
    "进入顺序": "entry order",
    "进入": "enter",
    "两": "two",
    "考核": "assessment",
    "放在": "place on",
    "放": "place",
    "实时": "live",
    "同期": "synchronization",
    "停机": "stop engine",
    "按": "according to",
    "同名": "same-name",
    "用": "use",
    "需": "must",
    "检测": "detect",
    "发现": "found",
    "该": "this",
    "组合": "combination",
    "合": "combine",
    "后续操作": "later operations",
    "续操作": "later operations",
    "缺失": "missing",
    "门禁": "interlock",
    "操作": "operation",
    "切": "switch",
    "追踪": "tracking",
    "是": "is",
    "通断": "continuity",
    "不合闸": "do not close",
    "命中": "hit",
    "收敛": "converge",
    "关": "close",
    "接了": "is connected to",
    "置": "position",
    "三": "three",
    "然后": "then",
    "然": "then",
    "不一致": "inconsistent",
    "复核": "review",
    "偏离": "deviates from",
    "调整": "adjust",
    "补充": "add",
    "控制": "control",
    "共发生": "occurred",
    "识别": "identify",
    "设备": "device",
    "三个": "three",
    "致命": "fatal",
    "网操作": "grid-connection operation",
    "跟踪": "tracking",
    "参考角": "reference angle",
    "角参考": "angle reference",
    "发生": "occur",
    "持续": "continuous",
    "强": "strong",
    "全": "all",
    "外部": "external",
    "合成": "compose",
    "误判": "misjudge",
    "合格": "qualified",
    "覆盖": "cover",
    "核": "phase-check",
    "错位": "misalignment",
    "须": "must",
    "测": "measure",
    "分": "points",
    "开路": "open circuit",
    "之间": "between",
    "落": "falls",
    "九": "nine",
    "控制器": "controller",
    "同一": "same",
    "偏离目标": "deviates from target",
    "修复路径合理": "repair path is reasonable",
    "累计": "cumulative",
    "违规操作": "violating operations",
    "额外": "extra",
    "个目标": "targets",
    "个": "",
    "操作折返": "operation backtracking",
    "交换": "swap",
    "违规推进尝试": "invalid advance attempts",
    "越级": "skipped step",
    "识别能力": "recognition ability",
    "定位到": "located",
    "识别到": "identified",
    "不承担本": "does not carry this",
    "关键": "key",
    "匹配": "match",
    "成功": "success",
    "结束条件": "finish conditions",
    "获得": "obtained",
    "如需进一步": "if further",
    "如需进一": "if further",
    "但系统不": "but the system does not",
    "提示": "tip",
    "报": "report",
    "数据": "data",
    "系统": "system",
    "三处": "three locations",
    "物理": "physical",
    "定位": "locate",
    "角": "angle",
    "到": "to",
    "运": "run",
    "连线": "connection",
    "接": "connect",
    "写入": "written",
    "范围": "range",
    "顺序进入": "ordered entry",
    "门禁拦截": "interlock block",
    "层级": "level",
    "根据": "based on",
    "紧急停机": "emergency shutdown",
    "动作后果": "Action consequence",
    "动作": "action",
    "果": "result",
    "巨大": "huge",
    "巨": "huge",
    "定子": "stator",
    "大轴": "shaft",
    "轴": "shaft",
    "受损": "damaged",
    "损": "damage",
    "工程": "engineering",
    "机": "machine",
    "考核提示": "Assessment Tip",
    "观察": "observe",
    "差": "difference",
    "直接": "direct",
    "前提": "Prerequisite",
    "提": "prerequisite",
    "本": "this",
    "网": "grid",
    "允许": "allow",
    "功能": "function",
    "短路": "short circuit",
    "可见": "visible",
    "见": "visible",
    "否": "No",
    "反": "reverse",
    "四": "four",
    "五": "five",
    "一": "one",
    "完": "complete",
    "推进": "advance",
    "出": "out",
    "条件": "condition",
    "指令": "command",
    "跨": "cross",
    "瞬间": "instant",
    "控": "control",
    "仪": "meter",
    "能": "can",
    "唯一": "only",
    "错": "error",
    "现": "appear",
    "参数": "parameters",
    "合理": "reasonable",
    "理": "reasonable",
    "依赖": "depend on",
    "良好": "good",
    "出现": "occur",
    "回到": "return to",
    "回": "return",
    "当": "when",
    "顺序": "sequence",
    "才": "only then",
    "非": "non",
    "发出": "issue",
    "实": "actual",
    "预警": "warning",
    "标红": "marked red",
    "保密": "confidential",
    "连通": "continuous",
    "验证": "verify",
    "退出": "exit",
    "排": "row",
    "自身": "self",
    "身": "self",
    "双": "double",
    "看": "view",
    "监视": "monitor",
    "情况": "condition",
    "绘制": "draw",
    "示": "show",
    "调节": "adjust",
    "点": "point",
    "偏": "deviation",
    "其": "its",
    "节点": "node",
    "样虚假": "also false",
    "区": "area",
    "隐性": "hidden",
    "互": "mutual",
    "抵消": "cancel",
    "这": "this",
    "变": "change",
    "观": "observe",
    "还": "still",
    "平移": "shift",
    "显": "show",
    "处": "location",
    "查": "inspect",
    "虚假": "false",
    "于": "at",
    "位于": "located at",
    "而非": "rather than",
    "错互消": "errors cancel each other",
    "叠加": "stack",
    "程": "process",
    "矩阵出现": "matrix shows",
    "容易": "easy to",
    "了": "",
    "清除": "cleared",
    "正": "positive",
    "选": "select",
    "确保": "ensure",
    "来": "source",
    "处于": "is in",
    "面板": "panel",
    "对": "for",
    "设置": "set",
    "设": "set",
    "绝不可": "must never",
    "绝": "never",
    "修改": "modify",
    "其建压": "its voltage is established",
    "压": "voltage",
    "追赶": "tracking",
    "路径": "path",
    "性": "",
    "求一致": "match requirements",
    "偏长": "longer than expected",
    "明显偏长": "significantly longer than expected",
    "超标": "exceeds the limit",
    "理想水平": "ideal level",
    "次数偏多": "too many times",
    "效率": "efficiency",
    "遵守": "comply with",
    "严格遵守": "strictly comply with",
    "停留": "hold",
    "推进尝试": "advance attempt",
    "主动": "actively",
    "才意识": "only then realized",
    "漏": "missing",
    "过早": "too early",
    "尝试": "attempt",
    "拦截": "blocked",
    "拆检": "disassembly inspection",
    "新": "new",
    "详细事故分析": "Detailed Accident Analysis",
    "详细": "detailed",
    "间短路": "phase-to-phase short circuit",
    "行": "row",
    "列": "column",
}


_PUNCT_TRANSLATION = str.maketrans(
    {
        "，": ", ",
        "。": ".",
        "；": "; ",
        "：": ": ",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "「": '"',
        "」": '"',
        "“": '"',
        "”": '"',
        "、": "/",
        "？": "?",
        "！": "!",
        "—": "-",
        "～": "~",
        "　": " ",
        "…": "...",
    }
)


_ORDERED_REPLACEMENTS = sorted(_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True)


def has_han(text: str) -> bool:
    return bool(_HAN_RE.search(text))


def _visible_replacement(target: str) -> str:
    if not target:
        return target
    if target[0].isalnum() and target[-1].isalnum():
        return f" {target} "
    return target


def ui_text(text: Any) -> Any:
    if not isinstance(text, str) or not has_han(text):
        return text
    if text in _EXACT:
        return _EXACT[text]

    translated = text
    for source, target in _ORDERED_REPLACEMENTS:
        if source in translated:
            translated = translated.replace(source, _visible_replacement(target))
    if translated in _EXACT:
        translated = _EXACT[translated]

    translated = translated.translate(_PUNCT_TRANSLATION)
    translated = re.sub(r"\s+,", ",", translated)
    translated = re.sub(r"\s+([:;.!?])", r"\1", translated)
    translated = re.sub(r"([(\[])\s+", r"\1", translated)
    translated = re.sub(r"\s+([)\]])", r"\1", translated)
    translated = re.sub(r" {2,}", " ", translated)
    translated = translated.replace("Step 1:", "Step 1:")
    translated = translated.replace("Step 2:", "Step 2:")
    translated = translated.replace("Step 3:", "Step 3:")
    translated = translated.replace("Step 4:", "Step 4:")
    translated = translated.replace("Step 5:", "Step 5:")
    translated = translated.strip()
    if translated and translated[0].islower():
        translated = translated[0].upper() + translated[1:]

    if has_han(translated):
        # Last-resort safety: never allow Han characters to reach the visible UI.
        translated = _HAN_RE.sub("item", translated)
        translated = re.sub(r" {2,}", " ", translated).strip()
    return translated


def _patch_text_method(cls: type, name: str) -> None:
    original = getattr(cls, name, None)
    if original is None or getattr(original, "_ui_translation_patched", False):
        return

    def wrapper(self, text, *args, **kwargs):
        return original(self, ui_text(text), *args, **kwargs)

    wrapper._ui_translation_patched = True  # type: ignore[attr-defined]
    try:
        setattr(cls, name, wrapper)
    except Exception:
        pass


def _patch_constructor(cls: type) -> None:
    original = getattr(cls, "__init__", None)
    if original is None or getattr(original, "_ui_translation_patched", False):
        return

    def wrapper(self, *args, **kwargs):
        args = list(args)
        if args and isinstance(args[0], str):
            args[0] = ui_text(args[0])
        return original(self, *args, **kwargs)

    wrapper._ui_translation_patched = True  # type: ignore[attr-defined]
    try:
        setattr(cls, "__init__", wrapper)
    except Exception:
        pass


def _patch_static_message_box(name: str) -> None:
    original = getattr(QtWidgets.QMessageBox, name, None)
    if original is None or getattr(original, "_ui_translation_patched", False):
        return

    def wrapper(parent, title, text, *args, **kwargs):
        return original(parent, ui_text(title), ui_text(text), *args, **kwargs)

    wrapper._ui_translation_patched = True  # type: ignore[attr-defined]
    try:
        setattr(QtWidgets.QMessageBox, name, staticmethod(wrapper))
    except Exception:
        pass


def _patch_qcombobox() -> None:
    cls = QtWidgets.QComboBox
    if getattr(cls, "_ui_translation_patched", False):
        return

    original_add_item = cls.addItem
    original_add_items = cls.addItems
    original_current_text = cls.currentText
    original_set_current_text = cls.setCurrentText

    def add_item(self, *args):
        if len(args) >= 2 and isinstance(args[1], str):
            original = args[1]
            new_args = list(args)
            new_args[1] = ui_text(original)
            result = original_add_item(self, *new_args)
        elif args and isinstance(args[0], str):
            original = args[0]
            new_args = list(args)
            new_args[0] = ui_text(original)
            result = original_add_item(self, *new_args)
        else:
            return original_add_item(self, *args)
        self.setItemData(self.count() - 1, original, _COMBO_ORIGINAL_ROLE)
        return result

    def add_items(self, texts):
        for text in texts:
            self.addItem(text)

    def current_text(self):
        idx = self.currentIndex()
        original = self.itemData(idx, _COMBO_ORIGINAL_ROLE)
        return original if isinstance(original, str) else original_current_text(self)

    def set_current_text(self, text):
        for idx in range(self.count()):
            original = self.itemData(idx, _COMBO_ORIGINAL_ROLE)
            if text == original or text == self.itemText(idx):
                self.setCurrentIndex(idx)
                return
        return original_set_current_text(self, ui_text(text))

    cls.addItem = add_item
    cls.addItems = add_items
    cls.currentText = current_text
    cls.setCurrentText = set_current_text
    cls._ui_translation_patched = True


def _patch_qtabwidget() -> None:
    cls = QtWidgets.QTabWidget
    if getattr(cls, "_ui_translation_patched", False):
        return

    original_add_tab = cls.addTab
    original_insert_tab = cls.insertTab
    original_set_tab_text = cls.setTabText

    def add_tab(self, *args):
        args = list(args)
        for i, value in enumerate(args):
            if isinstance(value, str):
                args[i] = ui_text(value)
                break
        return original_add_tab(self, *args)

    def insert_tab(self, *args):
        args = list(args)
        for i, value in enumerate(args):
            if i > 0 and isinstance(value, str):
                args[i] = ui_text(value)
                break
        return original_insert_tab(self, *args)

    def set_tab_text(self, index, text):
        return original_set_tab_text(self, index, ui_text(text))

    cls.addTab = add_tab
    cls.insertTab = insert_tab
    cls.setTabText = set_tab_text
    cls._ui_translation_patched = True


def _patch_qformlayout() -> None:
    cls = QtWidgets.QFormLayout
    original_add_row = getattr(cls, "addRow", None)
    if original_add_row is None or getattr(original_add_row, "_ui_translation_patched", False):
        return

    def add_row(self, *args):
        args = list(args)
        if args and isinstance(args[0], str):
            args[0] = ui_text(args[0])
        return original_add_row(self, *args)

    add_row._ui_translation_patched = True  # type: ignore[attr-defined]
    try:
        cls.addRow = add_row
    except Exception:
        pass


def _patch_qpainter() -> None:
    original = getattr(QtGui.QPainter, "drawText", None)
    if original is None or getattr(original, "_ui_translation_patched", False):
        return

    def draw_text(self, *args):
        args = list(args)
        for idx in range(len(args) - 1, -1, -1):
            if isinstance(args[idx], str):
                args[idx] = ui_text(args[idx])
                break
        return original(self, *args)

    draw_text._ui_translation_patched = True  # type: ignore[attr-defined]
    try:
        QtGui.QPainter.drawText = draw_text
    except Exception:
        pass


def _patch_matplotlib() -> None:
    try:
        from matplotlib.axes import Axes
        from matplotlib.text import Text
    except Exception:
        return

    if not getattr(Text, "_ui_translation_patched", False):
        original_text_init = Text.__init__
        original_set_text = Text.set_text

        def text_init(self, *args, **kwargs):
            if "text" in kwargs:
                kwargs["text"] = ui_text(kwargs["text"])
            args = list(args)
            if len(args) >= 3 and isinstance(args[2], str):
                args[2] = ui_text(args[2])
            return original_text_init(self, *args, **kwargs)

        def set_text(self, text):
            return original_set_text(self, ui_text(text))

        Text.__init__ = text_init
        Text.set_text = set_text
        Text._ui_translation_patched = True

    for name in ("set_title", "set_xlabel", "set_ylabel"):
        _patch_text_method(Axes, name)

    original_axes_text = getattr(Axes, "text", None)
    if original_axes_text is not None and not getattr(original_axes_text, "_ui_translation_patched", False):

        def axes_text(self, *args, **kwargs):
            args = list(args)
            if len(args) >= 3 and isinstance(args[2], str):
                args[2] = ui_text(args[2])
            if "s" in kwargs:
                kwargs["s"] = ui_text(kwargs["s"])
            return original_axes_text(self, *args, **kwargs)

        axes_text._ui_translation_patched = True  # type: ignore[attr-defined]
        try:
            Axes.text = axes_text
        except Exception:
            pass


def install_runtime_text_translation() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    for cls in (
        QtWidgets.QLabel,
        QtWidgets.QPushButton,
        QtWidgets.QGroupBox,
        QtWidgets.QRadioButton,
        QtWidgets.QCheckBox,
        QtWidgets.QTableWidgetItem,
        QtWidgets.QTreeWidgetItem,
        QtWidgets.QListWidgetItem,
    ):
        _patch_constructor(cls)

    for cls in (
        QtWidgets.QWidget,
        QtWidgets.QAbstractButton,
        QtWidgets.QLabel,
        QtWidgets.QGroupBox,
        QtWidgets.QLineEdit,
        QtWidgets.QTextEdit,
        QtWidgets.QPlainTextEdit,
        QtWidgets.QTableWidgetItem,
        QtWidgets.QTreeWidgetItem,
        QtWidgets.QListWidgetItem,
        QtWidgets.QStatusBar,
    ):
        for name in (
            "setText",
            "setTitle",
            "setWindowTitle",
            "setPlaceholderText",
            "setToolTip",
            "setStatusTip",
            "setWhatsThis",
            "setPlainText",
            "setHtml",
            "append",
            "showMessage",
        ):
            _patch_text_method(cls, name)

    for action_cls in (getattr(QtWidgets, "QAction", None), getattr(QtGui, "QAction", None)):
        if action_cls is not None:
            _patch_constructor(action_cls)
            for name in ("setText", "setToolTip", "setStatusTip", "setWhatsThis"):
                _patch_text_method(action_cls, name)

    for name in ("warning", "critical", "information", "question", "about"):
        _patch_static_message_box(name)

    _patch_qcombobox()
    _patch_qtabwidget()
    _patch_qformlayout()
    _patch_qpainter()
    _patch_matplotlib()

    _INSTALLED = True
