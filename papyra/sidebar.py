"""Painéis laterais: miniaturas de páginas e sumário (marcadores)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QLabel, QListWidget, QListWidgetItem, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .document import PdfDocument


class ThumbnailPanel(QListWidget):
    """Lista de miniaturas das páginas, com navegação e menu de contexto."""

    pageActivated = Signal(int)
    contextMenuRequestedFor = Signal(list, object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ListMode)
        self.setFlow(QListWidget.TopToBottom)
        self.setWrapping(False)
        self.setResizeMode(QListWidget.Adjust)
        self.setIconSize(QSize(150, 200))
        self.setSpacing(8)
        self.setUniformItemSizes(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemClicked.connect(self._on_item_clicked)

        self.document: Optional[PdfDocument] = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh)
        self._syncing = False

    def set_document(self, document: Optional[PdfDocument]):
        if self.document is not None:
            try:
                self.document.changed.disconnect(self._schedule_refresh)
            except (RuntimeError, TypeError):
                pass
        self.document = document
        if document is not None:
            document.changed.connect(self._schedule_refresh)
        self.refresh()

    def _schedule_refresh(self):
        self._refresh_timer.start(350)

    def refresh(self):
        self.clear()
        if self.document is None:
            return
        for i in range(self.document.page_count):
            thumb = self.document.thumbnail(i, max_dim=160)
            pix = QPixmap.fromImage(thumb)
            item = QListWidgetItem(QIcon(pix), f"Página {i + 1}")
            item.setData(Qt.UserRole, i)
            item.setTextAlignment(Qt.AlignHCenter)
            self.addItem(item)

    def set_current_page(self, index: int):
        if self._syncing:
            return
        if 0 <= index < self.count():
            self._syncing = True
            self.setCurrentRow(index)
            self.scrollToItem(self.item(index), QAbstractItemView.PositionAtCenter)
            self._syncing = False

    def _on_item_clicked(self, item: QListWidgetItem):
        self.pageActivated.emit(item.data(Qt.UserRole))

    def _on_context_menu(self, pos):
        indices = sorted({it.data(Qt.UserRole) for it in self.selectedItems()})
        if not indices:
            return
        self.contextMenuRequestedFor.emit(indices, self.mapToGlobal(pos))


class BookmarksPanel(QTreeWidget):
    """Sumário / marcadores (TOC) do documento."""

    pageActivated = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.itemClicked.connect(self._on_item_clicked)
        self.document: Optional[PdfDocument] = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh)

    def set_document(self, document: Optional[PdfDocument]):
        if self.document is not None:
            try:
                self.document.changed.disconnect(self._schedule_refresh)
            except (RuntimeError, TypeError):
                pass
        self.document = document
        if document is not None:
            document.changed.connect(self._schedule_refresh)
        self.refresh()

    def _schedule_refresh(self):
        self._refresh_timer.start(350)

    def refresh(self):
        self.clear()
        if self.document is None:
            return
        toc = self.document.get_toc()
        if not toc:
            placeholder = QTreeWidgetItem(["Este documento não possui sumário."])
            placeholder.setDisabled(True)
            self.addTopLevelItem(placeholder)
            return
        stack: list = [(0, self.invisibleRootItem())]
        for level, title, page in toc:
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.UserRole, max(0, page - 1))
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()
            stack[-1][1].addChild(item)
            stack.append((level, item))
        self.expandAll()

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        page = item.data(0, Qt.UserRole)
        if page is not None:
            self.pageActivated.emit(page)


class DocumentSidebar(QTabWidget):
    """Painel lateral com abas de Miniaturas e Sumário."""

    pageActivated = Signal(int)
    contextMenuRequestedFor = Signal(list, object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.thumbnails = ThumbnailPanel()
        self.bookmarks = BookmarksPanel()
        self.addTab(self.thumbnails, "Miniaturas")
        self.addTab(self.bookmarks, "Sumário")
        self.thumbnails.pageActivated.connect(self.pageActivated)
        self.bookmarks.pageActivated.connect(self.pageActivated)
        self.thumbnails.contextMenuRequestedFor.connect(self.contextMenuRequestedFor)

    def set_document(self, document: Optional[PdfDocument]):
        self.thumbnails.set_document(document)
        self.bookmarks.set_document(document)

    def set_current_page(self, index: int):
        self.thumbnails.set_current_page(index)
