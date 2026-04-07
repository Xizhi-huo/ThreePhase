from PyQt5 import QtWidgets


def refresh_styles(*widgets):
    for widget in widgets:
        if widget is None:
            continue
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()


def set_props(widget, **props):
    for key, value in props.items():
        widget.setProperty(key, value)
    refresh_styles(widget)


def apply_step_shell(tab_outer, scroll, tab, header, desc, banner, *, banner_tone="info"):
    set_props(tab_outer, stepPage=True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    set_props(tab, stepPage=True)
    set_props(header, stepHeader=True)
    set_props(desc, stepDescription=True)
    set_props(banner, stepBanner=True, tone=banner_tone)


def apply_button_tone(owner, button, tone="primary", *, hero=False, secondary=False, muted=False):
    owner._apply_button_tone(
        button,
        tone,
        hero=hero,
        secondary=secondary,
        muted=muted,
    )


def set_live_text(widget, tone="neutral"):
    set_props(widget, liveText=True, tone=tone)


def set_record_value(widget, tone="neutral"):
    set_props(widget, recordValue=True, tone=tone)


def set_step_item(widget, text, done, started):
    widget.setText(("√ " if done else "□ ") + text)
    set_props(widget, stepListItem=True, tone="success" if done else ("active" if started else "muted"))
