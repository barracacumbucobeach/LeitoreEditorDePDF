"""Diálogos auxiliares: Sobre, Propriedades e Gerenciador de páginas."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from . import __app_name__, __version__
from .document import PdfDocument
from .icons import icon as ficon


class AboutDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Sobre o {__app_name__}")
        self.setFixedWidth(440)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"<h2 style='margin:0'>{__app_name__}</h2>")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Versão {__version__}"))

        desc = QLabel(
            "Leitor e editor de PDF profissional. Leia, navegue, dê zoom, "
            "imprima e edite texto, imagens, formas e anotações diretamente "
            "no documento — com histórico completo de desfazer e refazer."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(QLabel("Construído com Python, PySide6 (Qt) e PyMuPDF."))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PropertiesDialog(QDialog):
    def __init__(self, document: PdfDocument, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Propriedades do documento")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)

        meta = document.get_metadata()
        form = QFormLayout()
        self.title_edit = QLineEdit(meta.get("title", "") or "")
        self.author_edit = QLineEdit(meta.get("author", "") or "")
        self.subject_edit = QLineEdit(meta.get("subject", "") or "")
        self.keywords_edit = QLineEdit(meta.get("keywords", "") or "")
        form.addRow("Título:", self.title_edit)
        form.addRow("Autor:", self.author_edit)
        form.addRow("Assunto:", self.subject_edit)
        form.addRow("Palavras-chave:", self.keywords_edit)
        layout.addLayout(form)

        info_box = QGroupBox("Informações do arquivo")
        info_layout = QFormLayout(info_box)
        info_layout.addRow("Páginas:", QLabel(str(document.page_count)))
        info_layout.addRow("Formato:", QLabel(meta.get("format") or "—"))
        info_layout.addRow("Criador:", QLabel(meta.get("creator") or "—"))
        info_layout.addRow("Produtor:", QLabel(meta.get("producer") or "—"))
        info_layout.addRow("Criptografado:", QLabel("Sim" if document.is_encrypted else "Não"))
        layout.addWidget(info_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        self.document.set_metadata({
            "title": self.title_edit.text(),
            "author": self.author_edit.text(),
            "subject": self.subject_edit.text(),
            "keywords": self.keywords_edit.text(),
        })
        self.accept()


class PageManagerDialog(QDialog):
    """Gerenciador visual de páginas: reordenar, girar, duplicar, extrair..."""

    def __init__(self, document: PdfDocument, parent: Optional[QWidget] = None, icon_color: str = "#e9ebf1"):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Gerenciar páginas")
        self.resize(760, 540)
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        def add_button(text: str, iconname: str, slot):
            btn = QPushButton(text)
            btn.setIcon(ficon(iconname, icon_color))
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)
            return btn

        add_button("Página em branco", "fa5s.file", self._insert_blank)
        add_button("Inserir PDF...", "fa5s.file-import", self._insert_pdf)
        add_button("Duplicar", "fa5s.clone", self._duplicate)
        add_button("Girar ↺", "fa5s.undo", self._rotate_left)
        add_button("Girar ↻", "fa5s.redo", self._rotate_right)
        add_button("Extrair...", "fa5s.file-export", self._extract)
        add_button("Excluir", "fa5s.trash-alt", self._delete)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        hint = QLabel("Arraste as páginas para reordenar. Selecione várias com Ctrl/Shift.")
        hint.setStyleSheet("color: #9aa3b5;")
        layout.addWidget(hint)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setFlow(QListWidget.LeftToRight)
        self.list.setWrapping(True)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setMovement(QListWidget.Snap)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setIconSize(QSize(130, 170))
        self.list.setSpacing(12)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.model().rowsMoved.connect(self._apply_reorder)
        layout.addWidget(self.list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

        self.document.changed.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        self.list.blockSignals(True)
        self.list.clear()
        for i in range(self.document.page_count):
            thumb = self.document.thumbnail(i, max_dim=150)
            pix = QPixmap.fromImage(thumb)
            item = QListWidgetItem(QIcon(pix), f"{i + 1}")
            item.setData(Qt.UserRole, i)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _selected_indices(self) -> list:
        return sorted({it.data(Qt.UserRole) for it in self.list.selectedItems()})

    def _apply_reorder(self, *_args):
        order = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if order and order != list(range(len(order))):
            self.document.reorder_pages(order)

    def _insert_blank(self):
        sel = self._selected_indices()
        at = (sel[-1] + 1) if sel else None
        self.document.insert_blank_page(at)

    def _insert_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Inserir PDF", "", "PDF (*.pdf)")
        if path:
            sel = self._selected_indices()
            at = (sel[-1] + 1) if sel else None
            self.document.merge_document(path, at_index=at)

    def _duplicate(self):
        for i in reversed(self._selected_indices()):
            self.document.duplicate_page(i)

    def _rotate_left(self):
        for i in self._selected_indices():
            self.document.rotate_page(i, -90)

    def _rotate_right(self):
        for i in self._selected_indices():
            self.document.rotate_page(i, 90)

    def _delete(self):
        sel = self._selected_indices()
        if not sel:
            return
        if self.document.page_count - len(sel) < 1:
            QMessageBox.warning(self, "Não é possível excluir", "O documento precisa ter ao menos uma página.")
            return
        reply = QMessageBox.question(self, "Excluir páginas", f"Excluir {len(sel)} página(s) selecionada(s)?")
        if reply == QMessageBox.Yes:
            self.document.delete_pages(sel)

    def _extract(self):
        sel = self._selected_indices()
        if not sel:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Extrair páginas para", "", "PDF (*.pdf)")
        if path:
            self.document.extract_pages(sel, path)
            QMessageBox.information(self, "Concluído", f"{len(sel)} página(s) extraída(s) para:\n{path}")
