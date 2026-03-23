# ThreePhase



### 高优先级: 自动同期的相位追踪仍然按线性角度差计算，没有按圆周最短角处理，±180° 附近会朝错误方向追相。
### services/_physics_arbitration.py:35 的 phase_error = generator.phase_deg - target_phase_deg 和 services/_physics_arbitration.py:239 的 _err = _target - _cur 仍然存在；但同期判定在 services/sync_test_service.py:34 是按最短圆周角差算的。控制逻辑和判定逻辑口径还是不一致。

### 中优先级: 第二步 PT 线电压检查页仍然少一条步骤显示。
### 服务层返回 9 个步骤 services/pt_voltage_check_service.py:66，但 UI 只创建了 8 个标签 ui/tabs/pt_voltage_check_tab.py:145，渲染时又用 zip 截断 ui/tabs/pt_voltage_check_tab.py:293。最后一步“记录 PT3 三相线电压”不会显示出来。
