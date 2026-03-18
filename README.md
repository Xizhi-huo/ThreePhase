# ThreePhase

### 高: 下垂控制的电压幅值限幅还停留在旧低压模型，开启后会把高压系统直接压到 200到400V。当前系统常量里母排目标幅值已经是约 8573V，但 _apply_droop_control() 仍然把 gen.amp 硬夹到 200~400，一旦机组已并到母排，PT 电压、同期判断和环流都会被带偏。domain/constants.py (line 24) domain/constants.py (line 28) services/_physics_protection.py (line 72)

### 高: 第 2 步 PT 相序检查可以被后续流程绕过。record_pt_measurement() 只要求完成第 1 步，没有校验 is_pt_phase_check_complete()；record_sync_round() 也只要求第 1 步和 PT 压差记录完成。结果是用户可以直接做第 3/4 步，而不经过第 2 步的相序核验，这和流程定义不一致。services/pt_exam_service.py (line 94) services/sync_test_service.py (line 44) services/sync_test_service.py (line 94)

### 高: PT3 反送电建模忽略了断路器位置，只要 Gen2.breaker_closed 就把 PT3 当成母排反送电。相序检查页和测量映射都只看“已合闸”，没要求 WORKING 位置，所以在“试验位/脱开位”下也可能测出 PT3 有母排电压并通过第 2 步，这个物理逻辑是错的。services/pt_phase_check_service.py (line 38) services/pt_phase_check_service.py (line 80) app/main.py (line 117) services/_physics_measurement.py (line 33)

### 中: “完成第 X 步测试”基本没有参与真正的流程解锁。第 1/2/3 步的 finalize_*() 只是把 .completed 置真，但后续解锁和合闸前置检查主要看“记录是否齐全”，不看 .completed。这会导致用户不点“完成”也能继续推进流程，确认按钮变成了展示态而不是约束态。services/loop_test_service.py (line 132) services/loop_test_service.py (line 136) services/pt_phase_check_service.py (line 149) services/pt_exam_service.py (line 256) app/main.py (line 288)
