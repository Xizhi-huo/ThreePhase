# ThreePhase

### 第 4 步“PT 二次端子压差测试”缺少真正的“已开始”门禁。pt_exam_service.py:68 的 record_pt_measurement() 没检查 started，但 UI 记录按钮直接调用它，见 pt_exam_tab.py:183。结果是不点“开始第四步测试”也能写入记录、推进流程。

### 第 5 步“同步功能测试”同样缺少“已开始”门禁。sync_test_service.py:94 的 record_sync_round() 没检查 started，UI 两个“记录轮次”按钮直接触发，见 sync_test_tab.py:150 和 sync_test_tab.py:164。这会让“开始第五步测试”失去约束意义。

### 断路器“闭合”与“真正并入一次系统”建模不一致，可能在试验位/脱开位触发本不该出现的环流、故障告警和跳闸。物理层允许非 WORKING 位置闭合，见 _physics_protection.py:158；但保护和环流逻辑大量只看 breaker_closed，见 _physics_protection.py:56 和 _physics_protection.py:85。这和业务层“WORKING + breaker_closed 才算并网”的判断不一致，会产生错误物理行为和错误显示。

### 顺序直接读：

### app/main.py domain/models.py domain/test_states.py services/physics_engine.py services/_physics_arbitration.py services/_physics_protection.py 五个 *_service.py ui/main_window.py 各 tab
