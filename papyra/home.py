"""Página inicial (dashboard) do Papyra."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget,
)

from . import __app_name__
from .icons import icon as ficon

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS_DIR / "icon.svg"

MAX_CONTENT_WIDTH = 860


class ActionCard(QFrame):
    """Cartão grande e clicável para uma ação principal (Abrir, Novo...)."""

    clicked = Signal()

    def __init__(self, icon_name: str, title: str, subtitle: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._icon_name = icon_name
        self.setObjectName("homeCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(128)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        layout.addWidget(self.icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("homeCardTitle")
        layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("homeCardSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
        layout.addStretch(1)

    def set_icon_color(self, color: str):
        self.icon_label.setPixmap(ficon(self._icon_name, color).pixmap(28, 28))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecentFileRow(QFrame):
    """Uma linha clicável na lista de arquivos recentes."""

    clicked = Signal(str)
    removeRequested = Signal(str)

    def __init__(self, path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.path = path
        self.setObjectName("recentRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(12)

        self.icon_label = QLabel()
        layout.addWidget(self.icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_label = QLabel(Path(path).name)
        name_label.setObjectName("recentRowName")
        parent_dir = str(Path(path).parent)
        path_label = QLabel(parent_dir)
        path_label.setObjectName("recentRowPath")
        path_label.setToolTip(path)
        text_col.addWidget(name_label)
        text_col.addWidget(path_label)
        layout.addLayout(text_col, 1)

        self.remove_btn = QToolButton()
        self.remove_btn.setToolTip("Remover da lista de recentes")
        self.remove_btn.setAutoRaise(True)
        self.remove_btn.clicked.connect(lambda: self.removeRequested.emit(self.path))
        layout.addWidget(self.remove_btn)

    def set_icon_color(self, color: str):
        self.icon_label.setPixmap(ficon("fa5s.file-pdf", color).pixmap(20, 20))
        self.remove_btn.setIcon(ficon("fa5s.times", color))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.path)
        super().mousePressEvent(event)


class HomeWidget(QWidget):
    """Painel inicial: escolher entre abrir um PDF, criar um novo documento
    ou retomar um arquivo recente."""

    openRequested = Signal()
    newRequested = Signal()
    recentFileRequested = Signal(str)
    recentFileRemoveRequested = Signal(str)
    recentFilesCleared = Signal()

    _icon_color = "#e9ebf1"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("homeRoot")
        self._recent_paths: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("homeContent")
        scroll.setWidget(content)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 0, 40, 0)

        inner = QVBoxLayout()
        inner.setSpacing(14)
        inner_wrap = QWidget()
        inner_wrap.setMaximumWidth(MAX_CONTENT_WIDTH)
        inner_wrap.setLayout(inner)
        content_layout.addStretch(1)
        content_layout.addWidget(inner_wrap, 0)
        content_layout.addStretch(1)

        inner.addSpacing(56)

        # -- cabeçalho -------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(16)
        icon_label = QLabel()
        if ICON_PATH.exists():
            icon_label.setPixmap(QIcon(str(ICON_PATH)).pixmap(60, 60))
        header.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_label = QLabel(__app_name__)
        title_label.setObjectName("homeTitle")
        subtitle_label = QLabel("Leitor & Editor de PDF Profissional")
        subtitle_label.setObjectName("homeSubtitle")
        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)
        header.addLayout(title_col)
        header.addStretch(1)
        inner.addLayout(header)

        inner.addSpacing(30)

        section = QLabel("O que você deseja fazer?")
        section.setObjectName("homeSectionTitle")
        inner.addWidget(section)
        inner.addSpacing(8)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.card_open = ActionCard(
            "fa5s.folder-open", "Abrir PDF...",
            "Escolher um arquivo PDF existente no computador para ler ou editar.",
        )
        self.card_new = ActionCard(
            "fa5s.file-medical", "Novo documento",
            "Começar do zero, com uma página em branco pronta para editar.",
        )
        self.card_open.clicked.connect(self.openRequested)
        self.card_new.clicked.connect(self.newRequested)
        cards_row.addWidget(self.card_open)
        cards_row.addWidget(self.card_new)
        inner.addLayout(cards_row)

        hint = QLabel("Dica: você também pode arrastar um arquivo PDF para esta janela.")
        hint.setObjectName("homeHint")
        inner.addWidget(hint)

        inner.addSpacing(34)

        recent_header = QHBoxLayout()
        recent_title = QLabel("Arquivos recentes")
        recent_title.setObjectName("homeSectionTitle")
        recent_header.addWidget(recent_title)
        recent_header.addStretch(1)
        self.clear_recent_btn = QPushButton("Limpar lista")
        self.clear_recent_btn.setFlat(True)
        self.clear_recent_btn.setCursor(Qt.PointingHandCursor)
        self.clear_recent_btn.clicked.connect(self.recentFilesCleared)
        recent_header.addWidget(self.clear_recent_btn)
        inner.addLayout(recent_header)
        inner.addSpacing(8)

        self.recent_list_layout = QVBoxLayout()
        self.recent_list_layout.setSpacing(6)
        inner.addLayout(self.recent_list_layout)

        self.empty_label = QLabel("Nenhum arquivo recente ainda. Abra um PDF para começar.")
        self.empty_label.setObjectName("homeHint")
        inner.addWidget(self.empty_label)

        inner.addStretch(1)
        inner.addSpacing(40)

    # ------------------------------------------------------------------

    def set_recent_files(self, paths: list[str]):
        self._recent_paths = list(paths)
        while self.recent_list_layout.count():
            item = self.recent_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Desanexa imediatamente (deleteLater só libera no próximo
                # laço de eventos, e até lá o widget órfão continua visível).
                widget.setParent(None)
                widget.deleteLater()
        for path in paths:
            row = RecentFileRow(path)
            row.set_icon_color(self._icon_color)
            row.clicked.connect(self.recentFileRequested)
            row.removeRequested.connect(self.recentFileRemoveRequested)
            self.recent_list_layout.addWidget(row)
        self.empty_label.setVisible(not paths)
        self.clear_recent_btn.setVisible(bool(paths))

    def refresh_theme(self, icon_color: str):
        self._icon_color = icon_color
        self.card_open.set_icon_color(icon_color)
        self.card_new.set_icon_color(icon_color)
        self.set_recent_files(self._recent_paths)
