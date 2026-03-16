# ThreePhase


## 高: 预合闸联锁只检查了“第一步回路测试”，没有把后续 PT 相序和 PT 压差纳入阻断条件，所以完成第一步后，WORKING 位手动合闸仍可继续推进，绕过后续流程。app/main.py (line 247) 里 get_preclose_flow_blockers() 只返回 loop_blockers，而 app/main.py (line 279) 的 toggle_breaker() 完全依赖它做阻断。这和“四步流程”设计不自洽。

## 高: “同步测试完成”仍然被定义成“两轮记录完成”，而不是“用户点击完成第四步”。services/sync_test_service.py (line 161) 的 is_sync_test_complete() 只看 round1_done 和 round2_done，但 services/sync_test_service.py (line 170) 又单独维护 completed=True。同时物理层自动合闸恢复逻辑依赖前者，services/physics_engine.py (line 514)；结果是用户还没点“完成第四步测试”，系统已经按“测试完成”恢复正常自动合闸，状态语义冲突。

## 中: PT 压差相关的合闸阻断会把用户跳到错误页面。当前 tab 顺序是 0 波形 / 1 电路 / 2 回路 / 3 PT相序 / 4 PT压差 / 5 同步，但 app/main.py (line 266) 在“当前机组不允许合闸”时跳的是 setCurrentIndex(3)，实际落到 PT 相序页，不是 PT 压差页。用户会被带到错误上下文。

## 中: 第二步 PT 相序检查的 UI 文案和真实校验条件冲突，用户按界面说明操作会进入不可通过的状态。页面说明要求“起机 Gen2，不合闸”，见 ui/tabs/pt_phase_check_tab.py；但当前实际服务逻辑要求 gen2.running == True 且 gen2.breaker_closed == False 才能记录，services/pt_phase_check_service.py (line 54) 和 services/pt_phase_check_service.py (line 85)。这和你之前另一版“停机+反送电测 PT3”的规则又不一致，说明第二步的业务定义本身还没稳定，当前存在流程语义漂移。
