"""Diálogos auxiliares: Sobre, Propriedades e Gerenciador de páginas."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QRadioButton, QTabWidget, QVBoxLayout, QWidget,
)

from . import __app_name__, __version__
from .document import PdfDocument, merge_pdfs
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


# ==========================================================================
# Converter PDF
# ==========================================================================

CONVERT_FORMATS = [
    ("docx", "Word (.docx)", "fa5s.file-word", "Documento editável, mantendo o layout do PDF."),
    ("xlsx", "Excel (.xlsx)", "fa5s.file-excel", "Tabelas detectadas em cada página viram planilhas."),
    ("pptx", "PowerPoint (.pptx)", "fa5s.file-powerpoint", "Uma página do PDF por slide."),
    ("html", "Página web (.html)", "fa5s.file-code", "Um único arquivo HTML com todas as páginas."),
    ("png", "Imagens (.png)", "fa5s.file-image", "Uma imagem PNG para cada página."),
    ("jpg", "Imagens (.jpg)", "fa5s.file-image", "Uma imagem JPEG para cada página."),
]


class ConvertDialog(QDialog):
    """Converte o documento atual para outro formato de arquivo."""

    def __init__(self, document: PdfDocument, parent: Optional[QWidget] = None, icon_color: str = "#e9ebf1"):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Converter PDF")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Escolha o formato de destino:"))

        self.group = QButtonGroup(self)
        for key, label, icon_name, hint in CONVERT_FORMATS:
            row = QRadioButton(label)
            row.setIcon(ficon(icon_name, icon_color))
            row.setToolTip(hint)
            row.setProperty("format_key", key)
            self.group.addButton(row)
            layout.addWidget(row)
            hint_label = QLabel(hint)
            hint_label.setObjectName("homeHint")
            hint_label.setContentsMargins(24, 0, 0, 6)
            layout.addWidget(hint_label)
        self.group.buttons()[0].setChecked(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.convert_btn = QPushButton("Converter...")
        self.convert_btn.setObjectName("primary")
        self.convert_btn.setProperty("cta", "true")
        self.convert_btn.clicked.connect(self._convert)
        buttons.addButton(self.convert_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _selected_format(self) -> str:
        checked = self.group.checkedButton()
        return checked.property("format_key") if checked else "docx"

    def _convert(self):
        fmt = self._selected_format()
        suggested = Path(self.document.path).stem if self.document.path else "documento"

        if fmt in ("png", "jpg"):
            out_dir = QFileDialog.getExistingDirectory(self, "Escolher pasta para as imagens")
            if not out_dir:
                return
            target = out_dir
        else:
            filters = {
                "docx": "Word (*.docx)", "xlsx": "Excel (*.xlsx)",
                "pptx": "PowerPoint (*.pptx)", "html": "Página web (*.html)",
            }
            target, _ = QFileDialog.getSaveFileName(
                self, "Salvar como", f"{suggested}.{fmt}", filters[fmt],
            )
            if not target:
                return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if fmt == "docx":
                self.document.convert_to_docx(target)
            elif fmt == "xlsx":
                self.document.convert_to_xlsx(target)
            elif fmt == "pptx":
                self.document.convert_to_pptx(target)
            elif fmt == "html":
                self.document.convert_to_html(target)
            else:
                self.document.convert_to_images(target, fmt=fmt)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Falha na conversão", f"Não foi possível converter:\n\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Conversão concluída", f"Arquivo salvo em:\n{target}")
        self.accept()


# ==========================================================================
# Mesclar PDF
# ==========================================================================

class MergeFilesDialog(QDialog):
    """Escolhe vários arquivos PDF, permite reordená-los e os mescla em um só."""

    def __init__(self, parent: Optional[QWidget] = None, icon_color: str = "#e9ebf1"):
        super().__init__(parent)
        self._icon_color = icon_color
        self.setWindowTitle("Mesclar PDF")
        self.resize(520, 420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Adicione os PDFs na ordem em que devem aparecer no arquivo final:"))

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setIconSize(QSize(0, 0))
        layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        add_btn = QPushButton("Adicionar arquivos...")
        add_btn.setIcon(ficon("fa5s.plus", icon_color))
        add_btn.clicked.connect(self._add_files)
        up_btn = QPushButton("Mover para cima")
        up_btn.clicked.connect(lambda: self._move(-1))
        down_btn = QPushButton("Mover para baixo")
        down_btn.clicked.connect(lambda: self._move(1))
        remove_btn = QPushButton("Remover")
        remove_btn.clicked.connect(self._remove_selected)
        row.addWidget(add_btn)
        row.addWidget(up_btn)
        row.addWidget(down_btn)
        row.addWidget(remove_btn)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.merge_btn = QPushButton("Mesclar...")
        self.merge_btn.setProperty("cta", "true")
        self.merge_btn.clicked.connect(self._merge)
        buttons.addButton(self.merge_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Adicionar PDFs", "", "Documentos PDF (*.pdf)")
        for path in paths:
            item = QListWidgetItem(ficon("fa5s.file-pdf", self._icon_color), Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.list.addItem(item)

    def _move(self, delta: int):
        row = self.list.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < self.list.count()):
            return
        item = self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentRow(target)

    def _remove_selected(self):
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)

    def _merge(self):
        paths = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if len(paths) < 2:
            QMessageBox.warning(self, "Mesclar PDF", "Adicione ao menos dois arquivos para mesclar.")
            return
        target, _ = QFileDialog.getSaveFileName(self, "Salvar PDF mesclado", "documento-mesclado.pdf", "PDF (*.pdf)")
        if not target:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            merge_pdfs(paths, target)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Falha ao mesclar", f"Não foi possível mesclar os arquivos:\n\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Mesclagem concluída", f"Arquivo salvo em:\n{target}")
        self.accept()


# ==========================================================================
# Dividir PDF
# ==========================================================================

class SplitDialog(QDialog):
    """Divide o documento atual em vários arquivos."""

    def __init__(self, document: PdfDocument, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Dividir PDF")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"O documento tem {document.page_count} página(s)."))

        self.mode_group = QButtonGroup(self)
        self.mode_one_per_page = QRadioButton("Uma página por arquivo")
        self.mode_one_per_page.setChecked(True)
        self.mode_ranges = QRadioButton("Por intervalos personalizados")
        self.mode_group.addButton(self.mode_one_per_page)
        self.mode_group.addButton(self.mode_ranges)
        layout.addWidget(self.mode_one_per_page)
        layout.addWidget(self.mode_ranges)

        self.ranges_edit = QLineEdit()
        self.ranges_edit.setPlaceholderText("Ex.: 1-3, 4-6, 7-7")
        self.ranges_edit.setEnabled(False)
        self.mode_ranges.toggled.connect(self.ranges_edit.setEnabled)
        layout.addWidget(self.ranges_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.split_btn = QPushButton("Dividir...")
        self.split_btn.setProperty("cta", "true")
        self.split_btn.clicked.connect(self._split)
        buttons.addButton(self.split_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _parse_ranges(self) -> Optional[list]:
        text = self.ranges_edit.text().strip()
        if not text:
            return None
        ranges = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start, end = int(start_s) - 1, int(end_s) - 1
            else:
                start = end = int(part) - 1
            if start < 0 or end >= self.document.page_count or start > end:
                raise ValueError(f"Intervalo inválido: “{part}”")
            ranges.append((start, end))
        return ranges or None

    def _split(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Escolher pasta de destino")
        if not out_dir:
            return

        if self.mode_one_per_page.isChecked():
            ranges = [(i, i) for i in range(self.document.page_count)]
        else:
            try:
                ranges = self._parse_ranges()
            except ValueError as exc:
                QMessageBox.warning(self, "Intervalo inválido", str(exc))
                return
            if not ranges:
                QMessageBox.warning(self, "Dividir PDF", "Informe ao menos um intervalo de páginas.")
                return

        base = Path(self.document.path).stem if self.document.path else "documento"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            parts = self.document.split_document(ranges)
            for i, data in enumerate(parts):
                start, end = ranges[i]
                suffix = f"p{start + 1}" if start == end else f"p{start + 1}-{end + 1}"
                out_path = os.path.join(out_dir, f"{base}-{suffix}.pdf")
                with open(out_path, "wb") as fh:
                    fh.write(data)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Falha ao dividir", f"Não foi possível dividir o documento:\n\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Divisão concluída", f"{len(parts)} arquivo(s) salvo(s) em:\n{out_dir}")
        self.accept()


# ==========================================================================
# Proteger PDF
# ==========================================================================

class ProtectDialog(QDialog):
    """Adiciona ou remove a senha de proteção do documento atual."""

    def __init__(self, document: PdfDocument, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Proteger PDF")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        self.mode_group = QButtonGroup(self)
        self.mode_add = QRadioButton("Adicionar senha")
        self.mode_add.setChecked(True)
        self.mode_remove = QRadioButton("Remover senha")
        self.mode_remove.setEnabled(document.is_encrypted)
        self.mode_group.addButton(self.mode_add)
        self.mode_group.addButton(self.mode_remove)
        layout.addWidget(self.mode_add)
        layout.addWidget(self.mode_remove)
        if not document.is_encrypted:
            hint = QLabel("Este documento ainda não está protegido por senha.")
            hint.setObjectName("homeHint")
            layout.addWidget(hint)

        self.form_widget = QWidget()
        form = QFormLayout(self.form_widget)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Senha:", self.password_edit)
        form.addRow("Confirmar senha:", self.confirm_edit)
        self.allow_print = QCheckBox("Permitir impressão")
        self.allow_print.setChecked(True)
        self.allow_copy = QCheckBox("Permitir copiar texto")
        self.allow_copy.setChecked(True)
        form.addRow(self.allow_print)
        form.addRow(self.allow_copy)
        layout.addWidget(self.form_widget)
        self.mode_add.toggled.connect(self.form_widget.setVisible)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.apply_btn = QPushButton("Salvar como...")
        self.apply_btn.setProperty("cta", "true")
        self.apply_btn.clicked.connect(self._apply)
        buttons.addButton(self.apply_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self):
        suggested = Path(self.document.path).stem if self.document.path else "documento"
        if self.mode_add.isChecked():
            password = self.password_edit.text()
            if not password:
                QMessageBox.warning(self, "Proteger PDF", "Informe uma senha.")
                return
            if password != self.confirm_edit.text():
                QMessageBox.warning(self, "Proteger PDF", "As senhas não coincidem.")
                return
            target, _ = QFileDialog.getSaveFileName(
                self, "Salvar PDF protegido", f"{suggested}-protegido.pdf", "PDF (*.pdf)",
            )
            if not target:
                return
            self.document.save_protected(
                target, password, allow_print=self.allow_print.isChecked(), allow_copy=self.allow_copy.isChecked(),
            )
            QMessageBox.information(self, "Concluído", f"PDF protegido salvo em:\n{target}")
        else:
            target, _ = QFileDialog.getSaveFileName(
                self, "Salvar PDF sem senha", f"{suggested}-sem-senha.pdf", "PDF (*.pdf)",
            )
            if not target:
                return
            self.document.save_unprotected(target)
            QMessageBox.information(self, "Concluído", f"PDF sem proteção salvo em:\n{target}")
        self.accept()


# ==========================================================================
# Assinar PDF (assinatura visual — traçada ou digitada)
# ==========================================================================

class SignaturePad(QWidget):
    """Área para desenhar uma assinatura à mão livre com o mouse."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(400, 160)
        self.setCursor(Qt.CrossCursor)
        self.setAttribute(Qt.WA_StaticContents)
        self._image = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
        self._image.fill(Qt.transparent)
        self._last_point: Optional[QPoint] = None
        self._has_ink = False

    def resizeEvent(self, event):
        if self._image.size() != self.size():
            new_image = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
            new_image.fill(Qt.transparent)
            painter = QPainter(new_image)
            painter.drawImage(0, 0, self._image)
            painter.end()
            self._image = new_image
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        painter.drawImage(0, 0, self._image)
        painter.setPen(QPen(QColor(210, 210, 210), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        if not self._has_ink:
            painter.setPen(QColor(170, 170, 170))
            painter.drawText(self.rect(), Qt.AlignCenter, "Assine aqui com o mouse")

    def mousePressEvent(self, event):
        self._last_point = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._last_point is None:
            return
        point = event.position().toPoint()
        painter = QPainter(self._image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(20, 30, 60), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(self._last_point, point)
        painter.end()
        self._last_point = point
        self._has_ink = True
        self.update()

    def mouseReleaseEvent(self, event):
        self._last_point = None

    def clear(self):
        self._image.fill(Qt.transparent)
        self._has_ink = False
        self.update()

    def has_ink(self) -> bool:
        return self._has_ink

    def to_png_bytes(self) -> bytes:
        from PySide6.QtCore import QBuffer, QIODevice

        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        self._image.save(buffer, "PNG")
        return bytes(buffer.data())


class SignatureDialog(QDialog):
    """Captura uma assinatura visual (traçada à mão ou digitada) para
    carimbar no documento. Não é uma assinatura digital com certificado."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Assinar PDF")
        self.setMinimumWidth(460)
        self.signature_bytes: Optional[bytes] = None
        layout = QVBoxLayout(self)

        note = QLabel(
            "Crie sua assinatura abaixo e, em seguida, clique e arraste no "
            "documento para posicioná-la. (Assinatura visual — não é uma "
            "assinatura digital com certificado.)"
        )
        note.setWordWrap(True)
        note.setObjectName("homeHint")
        layout.addWidget(note)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # -- Desenhar --
        draw_tab = QWidget()
        draw_layout = QVBoxLayout(draw_tab)
        self.pad = SignaturePad()
        draw_layout.addWidget(self.pad)
        clear_btn = QPushButton("Limpar")
        clear_btn.clicked.connect(self.pad.clear)
        draw_layout.addWidget(clear_btn, alignment=Qt.AlignLeft)
        self.tabs.addTab(draw_tab, "Desenhar")

        # -- Digitar --
        type_tab = QWidget()
        type_layout = QVBoxLayout(type_tab)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Digite seu nome")
        type_layout.addWidget(self.name_edit)
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Cursiva", "Elegante", "Simples"])
        type_layout.addWidget(self.style_combo)
        self.preview_label = QLabel()
        self.preview_label.setMinimumHeight(90)
        self.preview_label.setStyleSheet("background: white; border: 1px solid #ddd;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        type_layout.addWidget(self.preview_label)
        self.name_edit.textChanged.connect(self._update_type_preview)
        self.style_combo.currentIndexChanged.connect(self._update_type_preview)
        self.tabs.addTab(type_tab, "Digitar")

        # -- Imagem --
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)
        pick_btn = QPushButton("Escolher imagem...")
        pick_btn.clicked.connect(self._pick_image)
        image_layout.addWidget(pick_btn)
        self.image_preview = QLabel("Nenhuma imagem selecionada")
        self.image_preview.setMinimumHeight(90)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("background: white; border: 1px solid #ddd;")
        image_layout.addWidget(self.image_preview)
        self._image_path: Optional[str] = None
        self.tabs.addTab(image_tab, "Imagem")

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.ok_btn = QPushButton("Usar esta assinatura")
        self.ok_btn.setProperty("cta", "true")
        self.ok_btn.clicked.connect(self._accept_signature)
        buttons.addButton(self.ok_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_type_preview(self):
        text = self.name_edit.text().strip()
        style = self.style_combo.currentText()
        font = QFont("Segoe Script" if style == "Cursiva" else ("Brush Script MT" if style == "Elegante" else "Segoe UI"))
        font.setPointSize(28)
        font.setItalic(style != "Simples")
        image = QImage(360, 90, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(font)
        painter.setPen(QColor(20, 30, 60))
        painter.drawText(image.rect(), Qt.AlignCenter, text or "Sua assinatura")
        painter.end()
        self.preview_label.setPixmap(QPixmap.fromImage(image))

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher imagem da assinatura", "", "Imagens (*.png *.jpg *.jpeg)")
        if path:
            self._image_path = path
            self.image_preview.setPixmap(QPixmap(path).scaledToHeight(80, Qt.SmoothTransformation))

    def _accept_signature(self):
        index = self.tabs.currentIndex()
        if index == 0:
            if not self.pad.has_ink():
                QMessageBox.warning(self, "Assinar PDF", "Desenhe sua assinatura antes de continuar.")
                return
            self.signature_bytes = self.pad.to_png_bytes()
        elif index == 1:
            if not self.name_edit.text().strip():
                QMessageBox.warning(self, "Assinar PDF", "Digite seu nome antes de continuar.")
                return
            self._update_type_preview()
            from PySide6.QtCore import QBuffer, QIODevice

            image = self.preview_label.pixmap().toImage()
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, "PNG")
            self.signature_bytes = bytes(buffer.data())
        else:
            if not self._image_path:
                QMessageBox.warning(self, "Assinar PDF", "Escolha uma imagem antes de continuar.")
                return
            with open(self._image_path, "rb") as fh:
                self.signature_bytes = fh.read()
        self.accept()
