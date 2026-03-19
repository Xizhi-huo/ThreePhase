# ThreePhase


### 高: 万用表平滑值 EMA 在所有测量路径之间共用，会直接污染第二步、第三步、第四步的测量结果。services/_physics_measurement.py#L16 的 _whole_cycle_rms() 读写同一个 self._meter_v_ema，而它既用于第二步单体线电压，也用于第三步/第四步的两路 RMS 比较；尤其第三步/第四步里连续两次调用 services/_physics_measurement.py#L187 和 services/_physics_measurement.py#L188，第二路 RMS 会以上一路的 EMA 作为历史值，结果两路测量互相串扰。这个会直接影响 meter_voltage 和步骤 3/4 的判定，不只是显示抖动。

### 中: 第四步步骤列表仍然会把前置条件提前显示为完成，和当前真实状态不一致。services/pt_exam_service.py#L189 到 services/pt_exam_service.py#L210 里前 1 到 4 项仍然用了 ... or has_any。只要录过任意一相，接地、母排并列、万用表开启这些前置条件就会被显示成已满足，即使用户后来把状态改坏了。流程没被绕过，但步骤显示会误导。

### 中: 第一步摘要文案和实际业务门槛不一致。ui/tabs/loop_test_tab.py#L226 只要 gen1.breaker_closed and gen2.breaker_closed 就显示“两台发电机已合闸，可开始测量三相回路”，但真正业务判断要求的是 WORKING + breaker_closed，见 services/loop_test_service.py#L83 和 services/loop_test_service.py#L86。这会让摘要比真实可测条件更乐观

### 顺序直接读：

### app/main.py domain/models.py domain/test_states.py services/physics_engine.py services/_physics_arbitration.py services/_physics_protection.py 五个 *_service.py ui/main_window.py 各 tab
