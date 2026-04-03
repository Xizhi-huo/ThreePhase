from PyQt5 import QtCore, QtGui, QtWidgets


class DemoWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Three-Phase UI Demo - PyQt")
        self.resize(980, 640)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #f4f1ea;
                color: #1f2a31;
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }
            QFrame#Shell {
                background: #fffdf8;
                border: 1px solid #d7cfc2;
                border-radius: 24px;
            }
            QFrame.card {
                background: #fbf7ef;
                border: 1px solid #dbd2c4;
                border-radius: 18px;
            }
            QLabel.title {
                font-size: 30px;
                font-weight: 700;
            }
            QLabel.caption {
                color: #746b61;
            }
            QLabel.h2 {
                font-size: 18px;
                font-weight: 700;
            }
            QLabel.metric {
                font-size: 26px;
                font-weight: 700;
            }
            QPushButton.primary {
                background: #1f7a5c;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 18px;
                font-weight: 700;
            }
            QPushButton.secondary {
                background: #efe6d6;
                color: #2a353d;
                border: 1px solid #d0c4b0;
                border-radius: 12px;
                padding: 12px 18px;
                font-weight: 700;
            }
            QListWidget {
                background: transparent;
                border: none;
                padding: 0;
            }
            QListWidget::item {
                background: #fff;
                border: 1px solid #e2d9ca;
                border-radius: 12px;
                margin-bottom: 8px;
                padding: 10px 12px;
            }
            """
        )

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        shell = QtWidgets.QFrame(objectName="Shell")
        root.addWidget(shell)

        shell_layout = QtWidgets.QVBoxLayout(shell)
        shell_layout.setContentsMargins(28, 28, 28, 28)
        shell_layout.setSpacing(20)

        top = QtWidgets.QHBoxLayout()
        shell_layout.addLayout(top)

        title_box = QtWidgets.QVBoxLayout()
        top.addLayout(title_box, 1)

        title = QtWidgets.QLabel("Three-Phase Training Console")
        title.setProperty("class", "title")
        title.setObjectName("")
        title.setStyleSheet("font-size: 30px; font-weight: 700;")
        title_box.addWidget(title)

        caption = QtWidgets.QLabel("A simple desktop card layout built with PyQt5 widgets.")
        caption.setProperty("class", "caption")
        caption.setStyleSheet("color: #746b61;")
        title_box.addWidget(caption)

        mode_chip = self._chip("Engineering Mode", "#dbeee5", "#1f7a5c")
        top.addWidget(mode_chip, 0, QtCore.Qt.AlignTop)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        shell_layout.addLayout(grid)

        grid.addWidget(self._summary_card(), 0, 0)
        grid.addWidget(self._steps_card(), 0, 1)
        grid.addWidget(self._actions_card(), 1, 0)
        grid.addWidget(self._log_card(), 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    def _chip(self, text: str, bg: str, fg: str) -> QtWidgets.QLabel:
        chip = QtWidgets.QLabel(text)
        chip.setAlignment(QtCore.Qt.AlignCenter)
        chip.setFixedHeight(38)
        chip.setContentsMargins(14, 0, 14, 0)
        chip.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 19px; "
            "padding: 0 14px; font-weight: 700;"
        )
        return chip

    def _card_shell(self, title_text: str, subtitle: str) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setProperty("class", "card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QtWidgets.QLabel(title_text)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        note = QtWidgets.QLabel(subtitle)
        note.setWordWrap(True)
        note.setStyleSheet("color: #746b61;")
        layout.addWidget(note)
        return card

    def _summary_card(self) -> QtWidgets.QFrame:
        card = self._card_shell("Session Snapshot", "Current scene and quick metrics.")
        layout = card.layout()

        metric_row = QtWidgets.QHBoxLayout()
        metric_row.addWidget(self._metric("E12", "fault scene"))
        metric_row.addWidget(self._metric("3 / 5", "step"))
        metric_row.addWidget(self._metric("02:18", "elapsed"))
        layout.addLayout(metric_row)
        return card

    def _metric(self, value: str, label: str) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        box = QtWidgets.QVBoxLayout(frame)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)

        value_label = QtWidgets.QLabel(value)
        value_label.setStyleSheet("font-size: 26px; font-weight: 700;")
        box.addWidget(value_label)

        label_widget = QtWidgets.QLabel(label)
        label_widget.setStyleSheet("color: #746b61;")
        box.addWidget(label_widget)
        return frame

    def _steps_card(self) -> QtWidgets.QFrame:
        card = self._card_shell("Step Progress", "A compact, modern-looking progress block.")
        layout = card.layout()

        for idx, text, done in [
            (1, "Loop test completed", True),
            (2, "Voltage inspection completed", True),
            (3, "Phase sequence inspection in progress", False),
        ]:
            row = QtWidgets.QHBoxLayout()
            row.addWidget(self._chip(str(idx), "#1f7a5c" if done else "#efe6d6", "white" if done else "#7b6d58"))
            label = QtWidgets.QLabel(text)
            row.addWidget(label, 1)
            state = QtWidgets.QLabel("Done" if done else "Open")
            state.setStyleSheet("color: #746b61; font-weight: 700;")
            row.addWidget(state)
            layout.addLayout(row)
        return card

    def _actions_card(self) -> QtWidgets.QFrame:
        card = self._card_shell("Actions", "The current PyQt implementation relies on native widgets and layouts.")
        layout = card.layout()

        buttons = QtWidgets.QHBoxLayout()
        start = QtWidgets.QPushButton("Open Blackbox")
        start.setProperty("class", "primary")
        start.setStyleSheet(
            "background: #1f7a5c; color: white; border: none; border-radius: 12px; padding: 12px 18px; font-weight: 700;"
        )
        buttons.addWidget(start)

        report = QtWidgets.QPushButton("Generate Report")
        report.setProperty("class", "secondary")
        report.setStyleSheet(
            "background: #efe6d6; color: #2a353d; border: 1px solid #d0c4b0; border-radius: 12px; padding: 12px 18px; font-weight: 700;"
        )
        buttons.addWidget(report)
        layout.addLayout(buttons)
        return card

    def _log_card(self) -> QtWidgets.QFrame:
        card = self._card_shell("Event Log", "A simple list to mirror the same content in the React demo.")
        layout = card.layout()

        items = QtWidgets.QListWidget()
        items.addItems(
            [
                "14:09  Detected mismatch on PT1 secondary output.",
                "14:10  User opened PT1 blackbox.",
                "14:12  Step 3 measurements updated.",
                "14:13  Waiting for wiring correction.",
            ]
        )
        layout.addWidget(items)
        return card


def main() -> None:
    app = QtWidgets.QApplication([])
    app.setWindowIcon(QtGui.QIcon())
    win = DemoWindow()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
