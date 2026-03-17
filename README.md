# ThreePhase

### services/physics_engine.py 过于庞大，已经同时承载仿真、保护、测量、仲裁和部分业务语义，后续改动容易产生联动回归。
### service 会直接依赖 UI 状态，例如 services/pt_exam_service.py 读取 self._ctrl.ui._pt_target_bg.checkedId()，这让业务层不能脱离界面独立测试。
### 状态存储混合了 dataclass 和裸字典，类型边界不严格，像 loop_test_state、pt_exam_states、sync_test_state 都是 dict，长期维护容易出现字段漂移。
