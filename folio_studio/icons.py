"""Ícones vetoriais (Font Awesome via qtawesome) usados na interface."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtGui import QIcon

try:
    import qtawesome as qta

    _HAS_QTA = True
except Exception:  # pragma: no cover - ambiente sem qtawesome
    _HAS_QTA = False


@lru_cache(maxsize=256)
def icon(name: str, color: str = "#e9ebf1") -> QIcon:
    """Retorna um QIcon do conjunto Font Awesome 5 (ex.: 'fa5s.save')."""
    if not _HAS_QTA:
        return QIcon()
    try:
        return qta.icon(name, color=color)
    except Exception:
        return QIcon()
