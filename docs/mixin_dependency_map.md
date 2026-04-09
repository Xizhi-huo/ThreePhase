# Mixin 属性交叉引用扫描

最后更新：`2026-04-09`

范围：
- 宿主：`ui/main_window.py::PowerSyncUI`
- 9 个 Mixin：
  - `WidgetBuilderMixin`
  - `WaveformTabMixin`
  - `CircuitTabMixin`
  - `LoopTestTabMixin`
  - `PtVoltageCheckTabMixin`
  - `PtPhaseCheckTabMixin`
  - `PtExamTabMixin`
  - `SyncTestTabMixin`
  - `TestPanelMixin`

扫描方法：
- 使用 AST 做静态分析。
- 只统计显式 `self.xxx = ...` 赋值创建的属性。
- 只统计显式 `self.xxx` 读/写语法。
- `setattr/getattr(self, ...)`、字典内动态键、Qt 对象内部状态变化不计入显式“写”，但会在风险说明中单独标注。

## 1A. 每个 Mixin 创建的 `self.xxx` 属性

### 宿主 PowerSyncUI 创建的共享属性
- `self.ctrl`
- `self.tab_widget`
- `self.ctrl_container`
- `self.ctrl_inner`
- `self.ctrl_layout`
- `self._resize_timer`
- `self._is_resizing`
- `self._fault_dialog_open`

### WidgetBuilderMixin
- `self._cp_btn_param`
- `self._cp_btn_run`
- `self._cp_stack`
- `self._fp_btn_choose`
- `self._fp_btn_normal`
- `self._fp_btn_random`
- `self._fp_status_lbl`
- `self._gnd_bg`
- `self._mode_bg`
- `self._pre_test_flow_mode`
- `self._pre_test_preset_mode`
- `self._pre_test_scenario_id`
- `self.arbitrator_lbl`
- `self.btn_enter_test_mode`
- `self.bus_reference_lbl`
- `self.bus_status_lbl`
- `self.ctrl`
- `self.droop_cb`
- `self.fault_cb`
- `self.first_start_label`
- `self.first_start_slider`
- `self.gov_gain_label`
- `self.gov_gain_slider`
- `self.multimeter_cb`
- `self.pause_btn`
- `self.pt_blackbox_cb`
- `self.relay_lbl`
- `self.remote_start_cb`
- `self.rotate_phasor_cb`
- `self.show_gen_wires_cb`
- `self.sim_speed_label`
- `self.sim_speed_slider`
- `self.sync_gain_label`
- `self.sync_gain_slider`

### WaveformTabMixin
- `self._sync_last_metrics`
- `self.ax_a`
- `self.ax_all`
- `self.ax_b`
- `self.ax_c`
- `self.ax_p`
- `self.canvas_bus`
- `self.canvas_phasor`
- `self.canvas_wave`
- `self.fig_bus`
- `self.fig_phasor`
- `self.fig_wave`
- `self.line_all_a`
- `self.line_all_b`
- `self.line_all_c`
- `self.line_ga`
- `self.line_gb`
- `self.line_gc`
- `self.line_gen1_a`
- `self.line_gen1_b`
- `self.line_gen1_c`
- `self.line_gen2_a`
- `self.line_gen2_b`
- `self.line_gen2_c`
- `self.p_g1a`
- `self.p_g1b`
- `self.p_g1c`
- `self.p_g2a`
- `self.p_g2b`
- `self.p_g2c`
- `self.p_ga`
- `self.p_gb`
- `self.p_gc`
- `self.sync_criteria`
- `self.sync_state_hero`
- `self.sync_state_hint`
- `self.wave_bus_badge`
- `self.wave_metric_cards`
- `self.wave_mode_badge`
- `self.wave_ref_badge`
- `self.wave_sync_badge`

### CircuitTabMixin
- `self._g1_wire_artists`
- `self._g2_wire_artists`
- `self._loop_anim_offset`
- `self._psm_result_lbl`
- `self.ax_circuit`
- `self.canvas2`
- `self.fig2`
- `self.gnd_data1`
- `self.gnd_data2`
- `self.loop_anim_dots`
- `self.loop_anim_gap_l`
- `self.loop_anim_gap_r`
- `self.loop_anim_wire_ok`
- `self.loop_anim_x1`
- `self.loop_anim_x2`
- `self.multimeter_widget`
- `self.phase_seq_meter`
- `self.probe1_plot`
- `self.probe2_plot`
- `self.sw1_pack`
- `self.sw2_pack`
- `self.tbl_left`
- `self.tbl_left_title`
- `self.tbl_right`
- `self.tbl_right_title`
- `self.tbl_s1`
- `self.tbl_s1_title`
- `self.tbl_s3_left`
- `self.tbl_s3_left_title`
- `self.tbl_s3_right`
- `self.tbl_s3_right_title`
- `self.tbl_s4_left`
- `self.tbl_s4_left_title`
- `self.tbl_s4_right`
- `self.tbl_s4_right_title`
- `self.tbl_s5_left`
- `self.tbl_s5_left_title`
- `self.tbl_s5_right`
- `self.tbl_s5_right_title`
- `self.txt_bus_source`
- `self.txt_circ_flow`
- `self.txt_grounding`
- `self.txt_i1`
- `self.txt_i2`
- `self.txt_ip1`
- `self.txt_ip2`
- `self.txt_iq1`
- `self.txt_iq2`
- `self.txt_meter`
- `self.txt_pt1_v`
- `self.txt_pt2_v`
- `self.txt_pt3_v`

### LoopTestTabMixin
- `self.btn_loop_mode`
- `self.loop_test_feedback_lbl`
- `self.loop_test_meter_lbl`
- `self.loop_test_mode_banner`
- `self.loop_test_record_labels`
- `self.loop_test_step_labels`
- `self.loop_test_summary_lbl`

### PtVoltageCheckTabMixin
- `self.btn_pt_voltage_start`
- `self.pt_voltage_check_banner`
- `self.pt_voltage_feedback_lbl`
- `self.pt_voltage_meter_lbl`
- `self.pt_voltage_record_labels`
- `self.pt_voltage_step_labels`
- `self.pt_voltage_summary_lbl`

### PtPhaseCheckTabMixin
- `self.btn_pt_phase_check_mode`
- `self.pt_phase_check_feedback_lbl`
- `self.pt_phase_check_meter_lbl`
- `self.pt_phase_check_record_labels`
- `self.pt_phase_check_started_banner`
- `self.pt_phase_check_step_labels`
- `self.pt_phase_check_summary_lbl`

### PtExamTabMixin
- `self._pt_target_bg`
- `self._pt_target_rb`
- `self.btn_pt_exam_start`
- `self.pt_exam_feedback_lbl`
- `self.pt_exam_meter_lbl`
- `self.pt_exam_mode_banner`
- `self.pt_exam_record_labels`
- `self.pt_exam_step_labels`
- `self.pt_exam_summary_lbl`

### SyncTestTabMixin
- `self.btn_sync_test_start`
- `self.sync_round1_lbl`
- `self.sync_round2_lbl`
- `self.sync_test_feedback_lbl`
- `self.sync_test_live_lbl`
- `self.sync_test_mode_banner`
- `self.sync_test_step_labels`
- `self.sync_test_summary_lbl`

### TestPanelMixin
- `self._assessment_last_logged_step`
- `self._pre_step5_repair_triggered`
- `self._test_mode_active`
- `self._tp_admin_mode`
- `self._tp_fault_banner`
- `self._tp_forced_step`
- `self._tp_gen_refs`
- `self._tp_gnd_bg`
- `self._tp_gnd_rbs`
- `self._tp_mm_btn`
- `self._tp_s2_fap`
- `self._tp_s2_gnd_bg`
- `self._tp_s2_gnd_rbs`
- `self._tp_s2_ratio_rows`
- `self._tp_s3_rec_btns`
- `self._tp_s4_bg`
- `self._tp_s4_fap`
- `self._tp_s4_quick_btn`
- `self._tp_s5_fap`
- `self._tp_step_grps`
- `self.ctrl`
- `self.test_panel`
- `self.tp_btn_admin`
- `self.tp_btn_complete`
- `self.tp_btn_reset`
- `self.tp_btn_start`
- `self.tp_bus_lbl`
- `self.tp_meter_lbl`
- `self.tp_s1_fb_lbl`
- `self.tp_s1_rec_btns`
- `self.tp_s1_step_lbls`
- `self.tp_s2_fb_lbl`
- `self.tp_s2_probe_lbl`
- `self.tp_s2_rec_btns`
- `self.tp_s2_step_lbls`
- `self.tp_s3_fb_lbl`
- `self.tp_s3_step_lbls`
- `self.tp_s4_fb_lbl`
- `self.tp_s4_step_lbls`
- `self.tp_s5_bars`
- `self.tp_s5_fb_lbl`
- `self.tp_s5_remote_btn`
- `self.tp_s5_step_lbls`
- `self.tp_step_btns`

## 1B. 属性交叉引用矩阵

说明：
- `self.ctrl` 单独统计，不逐一展开调用路径。
- 下表只列“由一个模块创建、被其他模块显式访问”的共享属性。
- “访问方式”按语法统计；对 `label.setText()` 这类调用，语法上是“读属性”，但语义上仍可能改变该对象内部状态。

### `self.ctrl` 使用频率统计

| Mixin | `self.ctrl` 引用次数 |
|---|---:|
| `WidgetBuilderMixin` | 16 |
| `WaveformTabMixin` | 5 |
| `CircuitTabMixin` | 17 |
| `LoopTestTabMixin` | 14 |
| `PtVoltageCheckTabMixin` | 10 |
| `PtPhaseCheckTabMixin` | 10 |
| `PtExamTabMixin` | 20 |
| `SyncTestTabMixin` | 16 |
| `TestPanelMixin` | 116 |

### 共享属性交叉引用表

| 属性名 | 创建者 | 被哪些其他模块访问 | 访问方式 |
|---|---|---|---|
| `self.ctrl` | `main_window`（同时被 `WidgetBuilderMixin`、`TestPanelMixin` 重复赋值） | 全部 9 个 Mixin | 读；另有重复写入 |
| `self.tab_widget` | `main_window` | `WaveformTabMixin`, `CircuitTabMixin`, `LoopTestTabMixin`, `PtVoltageCheckTabMixin`, `PtPhaseCheckTabMixin`, `PtExamTabMixin`, `SyncTestTabMixin`, `TestPanelMixin` | 读 |
| `self.ctrl_layout` | `main_window` | `WidgetBuilderMixin` | 读 |
| `self.ctrl_container` | `main_window` | `TestPanelMixin` | 读 |
| `self.multimeter_cb` | `WidgetBuilderMixin` | `LoopTestTabMixin`, `PtVoltageCheckTabMixin`, `PtPhaseCheckTabMixin`, `PtExamTabMixin`, `TestPanelMixin` | 读 |
| `self.bus_status_lbl` | `WidgetBuilderMixin` | `CircuitTabMixin` | 读 |
| `self.bus_reference_lbl` | `WidgetBuilderMixin` | `CircuitTabMixin` | 读 |
| `self.arbitrator_lbl` | `WidgetBuilderMixin` | `CircuitTabMixin` | 读 |
| `self.relay_lbl` | `WidgetBuilderMixin` | `CircuitTabMixin` | 读 |
| `self.ax_circuit` | `CircuitTabMixin` | `WidgetBuilderMixin` | 读 |
| `self.canvas2` | `CircuitTabMixin` | `main_window` | 读 |
| `self.phase_seq_meter` | `CircuitTabMixin` | `TestPanelMixin` | 读 |
| `self.test_panel` | `TestPanelMixin` | `main_window` | 读 |

### 共享热点属性

被 `>= 3` 个 Mixin 访问的热点属性：

| 属性名 | 创建者 | 被访问 Mixin 数 | 备注 |
|---|---|---:|---|
| `self.ctrl` | `main_window` | 9 | 整条 UI 继承链的共同入口；也是最大耦合源 |
| `self.tab_widget` | `main_window` | 8 | 所有 Tab 切换都依赖它 |
| `self.multimeter_cb` | `WidgetBuilderMixin` | 5 | 第一步到第四步以及测试总面板都依赖它 |

## 1C. Mixin 解耦难度评估

评估口径：
- 低：只依赖 `self.ctrl` / `self.tab_widget`，不读取其他 Mixin 显式创建的属性
- 中：读取 1-3 个其他模块创建的属性
- 高：读取 >= 4 个其他模块创建的属性，或存在显式写入式交叉引用

| Mixin | 交叉属性数（不含 `ctrl`/`tab_widget`） | 结论 | 说明 |
|---|---:|---|---|
| `WaveformTabMixin` | 0 | 低 | 只依赖 `self.ctrl` 与 `self.tab_widget` |
| `SyncTestTabMixin` | 0 | 低 | 结构自洽，适合作为组合式组件试点 |
| `LoopTestTabMixin` | 1 | 中 | 依赖 `self.multimeter_cb` |
| `PtVoltageCheckTabMixin` | 1 | 中 | 依赖 `self.multimeter_cb` |
| `PtPhaseCheckTabMixin` | 1 | 中 | 依赖 `self.multimeter_cb` |
| `PtExamTabMixin` | 1 | 中 | 依赖 `self.multimeter_cb`，但 `self.ctrl` 调用较多 |
| `WidgetBuilderMixin` | 2 | 中 | 依赖 `self.ctrl_layout`、`self.ax_circuit`，本身还是共享控件来源 |
| `TestPanelMixin` | 3 | 中（工程上接近高） | 只按交叉属性计为中，但体量最大、`self.ctrl` 使用 116 次，实际拆分难度高 |
| `CircuitTabMixin` | 4 | 高 | 读取 `WidgetBuilderMixin` 创建的 4 个状态标签，跨 Mixin UI 依赖最重 |

### 推荐 Phase 3 迁移顺序（从易到难）

1. `WaveformTabMixin`
2. `SyncTestTabMixin`
3. `LoopTestTabMixin`
4. `PtVoltageCheckTabMixin`
5. `PtPhaseCheckTabMixin`
6. `PtExamTabMixin`
7. `WidgetBuilderMixin`
8. `TestPanelMixin`
9. `CircuitTabMixin`

迁移理由：
- 前 6 个更接近“单页组件”；
- `WidgetBuilderMixin` 是共享控件源，不能太早拆；
- `TestPanelMixin` 虽然显式交叉属性不算最多，但体量和 `self.ctrl` 耦合极重，必须晚拆；
- `CircuitTabMixin` 同时承担绘图、仪表、记录表和顶部状态标签渲染，是最重的 UI 交汇点。

## 1D. 关键风险标注

### 拆分高风险点

1. **`self.ctrl` 存在多处重复赋值**
   - 创建/赋值位置：`main_window`、`WidgetBuilderMixin`、`TestPanelMixin`
   - 风险：这是当前 UI 继承链里唯一明确的“写入式交叉引用”热点；后续转组合时必须先统一 `ctrl` 注入方式。

2. **`CircuitTabMixin` 依赖 `WidgetBuilderMixin` 的 4 个状态标签**
   - `self.bus_status_lbl`
   - `self.bus_reference_lbl`
   - `self.arbitrator_lbl`
   - `self.relay_lbl`
   - 风险：`CircuitTabMixin` 的渲染结果要写到控制面板创建的标签对象里，拆分时必须先改成显式接口或状态桥接。

3. **`TestPanelMixin` 同时依赖控制容器、万用表开关和相序仪**
   - `self.ctrl_container`（宿主创建）
   - `self.multimeter_cb`（`WidgetBuilderMixin` 创建）
   - `self.phase_seq_meter`（`CircuitTabMixin` 创建）
   - 风险：测试总面板不是独立页面，而是跨越“控制面板 + 电路页 + 测试流程”的粘合层。

### TestPanelMixin 与其他 Tab 共用的关键属性

| 共享属性 | 创建者 | 被谁共用 | 风险 |
|---|---|---|---|
| `self.multimeter_cb` | `WidgetBuilderMixin` | `LoopTestTabMixin`, `PtVoltageCheckTabMixin`, `PtPhaseCheckTabMixin`, `PtExamTabMixin`, `TestPanelMixin` | 测试步骤和总面板都围绕同一个开关联动 |
| `self.tab_widget` | `main_window` | 几乎所有 Tab Mixin + `TestPanelMixin` | 所有流程跳转都绑在宿主对象上 |
| `self.phase_seq_meter` | `CircuitTabMixin` | `TestPanelMixin` | 第三步测试要直接操作电路页上的相序仪 |

### 额外说明

- 本扫描**没有**覆盖 `setattr/getattr(self, ...)` 这类动态属性；`WidgetBuilderMixin` 中存在一批动态生成的发电机控件属性，这是后续组合化时的隐藏风险。
- 本扫描的“写入式交叉引用”只按 `self.xxx = ...` 统计。像 `self.bus_status_lbl.setText(...)` 这种对共享控件内部状态的改变，在语法上仍然表现为“读共享属性”，但工程语义上仍属于耦合点。
