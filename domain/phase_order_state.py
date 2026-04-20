from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _default_phase_orders() -> Dict[str, List[str]]:
    return {
        "PT1": ["A", "B", "C"],
        "PT2": ["A", "B", "C"],
        "PT3": ["A", "B", "C"],
    }


def _default_order() -> List[str]:
    return ["A", "B", "C"]


@dataclass
class PhaseOrderState:
    pt_phase_orders: Dict[str, List[str]] = field(default_factory=_default_phase_orders)
    g1_blackbox_order: List[str] = field(default_factory=_default_order)
    g2_blackbox_order: List[str] = field(default_factory=_default_order)
    pt1_pri_blackbox_order: List[str] = field(default_factory=_default_order)
    pt1_sec_blackbox_order: List[str] = field(default_factory=_default_order)
    pt_blackbox_mode: bool = False

    @classmethod
    def default(cls) -> "PhaseOrderState":
        return cls()

    def _overwrite_phase(self, pt_name: str, values: List[str]) -> None:
        target = self.pt_phase_orders.get(pt_name)
        if isinstance(target, list):
            target[:] = list(values)
        else:
            self.pt_phase_orders[pt_name] = list(values)

    def reset_pt_phase_orders(self) -> None:
        for pt_name, values in _default_phase_orders().items():
            self._overwrite_phase(pt_name, values)

    def reshuffle_pt_phase_orders(self, rng: Optional[random.Random] = None) -> None:
        shuffler = rng if rng is not None else random
        for pt_name in ("PT1", "PT2", "PT3"):
            order = _default_order()
            shuffler.shuffle(order)
            self._overwrite_phase(pt_name, order)

    def reset_blackbox_orders(self) -> None:
        normal = _default_order()
        self.g1_blackbox_order[:] = normal
        self.g2_blackbox_order[:] = normal
        self.pt1_pri_blackbox_order[:] = normal
        self.pt1_sec_blackbox_order[:] = normal

    def set_g2_terminal_fault(self, enabled: bool) -> None:
        self.g2_blackbox_order[:] = ["A", "C", "B"] if enabled else _default_order()

    def apply_g2_blackbox_to_pt3(self) -> None:
        """派生: PT3 ← g2_blackbox_order（整列覆盖）。"""
        self._overwrite_phase("PT3", self.g2_blackbox_order)

    def apply_pt1_blackbox_to_pt_phases(self, pt1_net_order: List[str]) -> None:
        """派生: PT2 ← g1_blackbox_order；PT1 ← pt1_net_order。"""
        self._overwrite_phase("PT2", self.g1_blackbox_order)
        self._overwrite_phase("PT1", pt1_net_order)

    def on_pt_blackbox_toggle(self, checked: bool) -> None:
        self.pt_blackbox_mode = bool(checked)
        if checked:
            self.reshuffle_pt_phase_orders()
            return
        self.reset_pt_phase_orders()

    def get_pt_blackbox_mode(self) -> bool:
        return bool(self.pt_blackbox_mode)
