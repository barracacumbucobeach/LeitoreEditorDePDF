"""Janela principal do Fólio Studio."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction, QActionGroup, QCloseEvent, QColor, QDragEnterEvent, QDropEvent,
    QIcon, QKeySequence, QPixmap,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDockWidget, QDoubleSpinBox, QFileDialog,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPushButton, QSizePolicy, QSpinBox, QTabWidget, QToolBar, QToolButton, QVBoxLayout,
    QWidget,
)

from . import __app_name__, __organization__, __version__
from .dialogs import AboutDialog, PageManagerDialog, PropertiesDialog
from .document import PdfDocument
from .icons import icon as ficon
from .sidebar import DocumentSidebar
from .theme import icon_color, stylesheet
from .tools import TOOL_LABELS, TOOL_TOOLTIPS, Tool
from .view import PdfView, print_document

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS_DIR / "icon.svg"

TOOL_SPECS = [
    (Tool.SELECT, "fa5s.mouse-pointer", "Ctrl+1"),
    (Tool.EDIT_TEXT, "fa5s.i-cursor", "Ctrl+2"),
    (Tool.ADD_TEXT, "fa5s.font", "Ctrl+3"),
    (Tool.HIGHLIGHT, "fa5s.highlighter", "Ctrl+4"),
    (Tool.RECT, "fa5s.square", "Ctrl+5"),
    (Tool.ELLIPSE, "fa5s.circle", "Ctrl+6"),
    (Tool.LINE, "fa5s.slash", "Ctrl+7"),
    (Tool.ARROW, "fa5s.arrow-right", "Ctrl+8"),
    (Tool.INK, "fa5s.pen", "Ctrl+9"),
    (Tool.IMAGE, "fa5s.image", ""),
    (Tool.NOTE, "fa5s.sticky-note", ""),
    (Tool.ERASER, "fa5s.eraser", ""),
]


class ColorButton(QToolButton):
    colorChanged = Signal(QColor)

    def __init__(self, initial: QColor, tooltip: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = initial
        self.setToolTip(tooltip)
        self.setFixedSize(30, 26)
        self.clicked.connect(self._pick)
        self._update_icon()

    def _update_icon(self):
        pix = QPixmap(18, 18)
        pix.fill(self._color)
        self.setIcon(QIcon(pix))
        self.setIconSize(QSize(16, 16))

    def color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor):
        self._color = color
        self._update_icon()

    def _pick(self):
        color = QColorDialog.getColor(self._color, self, "Escolher cor", QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.set_color(color)
            self.colorChanged.emit(color)


class FindBar(QWidget):
    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        row = QHBoxLayout()
        layout.addLayout(row)

        row.addWidget(QLabel("Localizar:"))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Digite para buscar no documento…")
        row.addWidget(self.edit, 1)

        self.result_label = QLabel("")
        self.result_label.setMinimumWidth(90)
        row.addWidget(self.result_label)

        self.prev_btn = QPushButton("Anterior")
        self.next_btn = QPushButton("Próximo")
        self.close_btn = QPushButton("Fechar")
        row.addWidget(self.prev_btn)
        row.addWidget(self.next_btn)
        row.addWidget(self.close_btn)

        self.close_btn.clicked.connect(self.closed)
        self.edit.returnPressed.connect(self.next_btn.click)


class FolioMainWindow(QMainWindow):
    MAX_RECENT = 10

    def __init__(self):
        super().__init__()
        QApplication.setOrganizationName(__organization__)
        QApplication.setApplicationName(__app_name__)
        self.settings = QSettings()
        self._dark_theme = self.settings.value("theme/dark", True)
        if isinstance(self._dark_theme, str):
            self._dark_theme = self._dark_theme.lower() == "true"
        self._untitled_count = 0
        self._edit_mode = False

        self.setWindowTitle(__app_name__)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1440, 920)
        self.setAcceptDrops(True)

        self._icon_actions: list[tuple[QAction, str]] = []
        self._build_actions()
        self._build_menus()
        self._build_toolbars()
        self._build_central()
        self._build_docks()
        self._build_statusbar()
        self._apply_theme()
        self._update_recent_menu()
        self._on_tab_changed(-1)

        self.new_document()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------

    def _act(self, text, icon_name=None, shortcut=None, checkable=False, tip=None, slot=None):
        action = QAction(text, self)
        if icon_name:
            action.setIcon(ficon(icon_name, icon_color(self._dark_theme)))
            self._icon_actions.append((action, icon_name))
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.setCheckable(checkable)
        if tip:
            action.setStatusTip(tip)
            action.setToolTip(tip)
        if slot:
            action.triggered.connect(slot)
        return action

    def _build_actions(self):
        # Arquivo
        self.act_new = self._act("Novo", "fa5s.file", "Ctrl+N", tip="Novo documento", slot=self.new_document)
        self.act_open = self._act("Abrir...", "fa5s.folder-open", "Ctrl+O", tip="Abrir PDF", slot=self.open_document_dialog)
        self.act_save = self._act("Salvar", "fa5s.save", "Ctrl+S", tip="Salvar", slot=self.save_current)
        self.act_save_as = self._act("Salvar como...", "fa5s.file-export", "Ctrl+Shift+S", tip="Salvar como", slot=self.save_current_as)
        self.act_properties = self._act("Propriedades...", "fa5s.info-circle", slot=self.show_properties)
        self.act_print = self._act("Imprimir...", "fa5s.print", "Ctrl+P", tip="Imprimir", slot=self.print_current)
        self.act_print_preview = self._act("Visualizar impressão...", "fa5s.eye", slot=self.print_preview_current)
        self.act_close_tab = self._act("Fechar aba", None, "Ctrl+W", slot=lambda: self.close_tab(self.tabs.currentIndex()))
        self.act_quit = self._act("Sair", None, "Ctrl+Q", slot=self.close)

        # Editar
        self.act_undo = self._act("Desfazer", "fa5s.undo", "Ctrl+Z", tip="Desfazer", slot=lambda: self._with_doc(lambda d: d.undo()))
        self.act_redo = self._act("Refazer", "fa5s.redo", "Ctrl+Y", tip="Refazer", slot=lambda: self._with_doc(lambda d: d.redo()))
        self.act_delete_selection = self._act("Excluir selecionado", "fa5s.trash-alt", "Delete", slot=self._delete_selection)
        self.act_find = self._act("Localizar...", "fa5s.search", "Ctrl+F", slot=self.show_find_bar)

        # Exibir
        self.act_zoom_in = self._act("Ampliar", "fa5s.search-plus", "Ctrl++", slot=lambda: self._with_view(lambda v: v.zoom_in()))
        self.act_zoom_out = self._act("Reduzir", "fa5s.search-minus", "Ctrl+-", slot=lambda: self._with_view(lambda v: v.zoom_out()))
        self.act_zoom_reset = self._act("Zoom 100%", None, "Ctrl+0", slot=lambda: self._with_view(lambda v: v.zoom_reset()))
        self.act_fit_width = self._act("Ajustar à largura", "fa5s.arrows-alt-h", slot=lambda: self._with_view(lambda v: v.fit_width()))
        self.act_fit_page = self._act("Ajustar à página", "fa5s.expand", slot=lambda: self._with_view(lambda v: v.fit_page()))
        self.act_toggle_theme = self._act("Alternar tema claro/escuro", "fa5s.adjust", slot=self.toggle_theme)
        self.act_toggle_sidebar = self._act("Painel lateral", "fa5s.columns", checkable=True, slot=self._toggle_sidebar)
        self.act_toggle_sidebar.setChecked(True)

        self.act_prev_page = self._act("Página anterior", "fa5s.chevron-up", "PgUp", slot=lambda: self._with_view(lambda v: v.prev_page()))
        self.act_next_page = self._act("Próxima página", "fa5s.chevron-down", "PgDown", slot=lambda: self._with_view(lambda v: v.next_page()))

        # Página
        self.act_page_manager = self._act("Gerenciar páginas...", "fa5s.th-large", slot=self._open_page_manager)
        self.act_insert_blank = self._act("Inserir página em branco", "fa5s.file", slot=lambda: self._with_doc(lambda d: d.insert_blank_page(self._current_view().current_page + 1)))
        self.act_delete_page = self._act("Excluir página atual", "fa5s.trash", slot=self._delete_current_page)
        self.act_rotate_left = self._act("Girar página ↺", "fa5s.undo", slot=lambda: self._with_doc(lambda d: d.rotate_page(self._current_view().current_page, -90)))
        self.act_rotate_right = self._act("Girar página ↻", "fa5s.redo", slot=lambda: self._with_doc(lambda d: d.rotate_page(self._current_view().current_page, 90)))
        self.act_ocr = self._act(
            "Reconhecer texto (OCR)...", "fa5s.glasses",
            tip="Reconhecer o texto de uma página digitalizada para poder editá-la",
            slot=lambda: self._with_view(lambda v: v.run_ocr_current_page()),
        )

        # Ajuda
        self.act_about = self._act(f"Sobre o {__app_name__}", None, slot=self._show_about)

        # Modo de edição — por padrão o documento abre somente para leitura;
        # as ferramentas de edição só aparecem depois de ativado.
        self.act_edit_mode = self._act(
            "Editar PDF", "fa5s.pen-nib", "Ctrl+E", checkable=True,
            tip="Ativar as ferramentas de edição (o documento abre em modo de leitura)",
            slot=self._toggle_edit_mode,
        )

        # Ferramentas de edição
        self.tool_actions: dict[Tool, QAction] = {}
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        for tool, icon_name, shortcut in TOOL_SPECS:
            action = self._act(TOOL_LABELS[tool], icon_name, shortcut, checkable=True,
                                tip=TOOL_TOOLTIPS[tool], slot=lambda checked, t=tool: checked and self._set_tool(t))
            self.tool_group.addAction(action)
            self.tool_actions[tool] = action
        self.tool_actions[Tool.SELECT].setChecked(True)

    def _build_menus(self):
        menubar = self.menuBar()

        m_file = menubar.addMenu("&Arquivo")
        m_file.addAction(self.act_new)
        m_file.addAction(self.act_open)
        self.recent_menu = m_file.addMenu("Abrir recente")
        m_file.addSeparator()
        m_file.addAction(self.act_save)
        m_file.addAction(self.act_save_as)
        m_file.addSeparator()
        m_file.addAction(self.act_properties)
        m_file.addSeparator()
        m_file.addAction(self.act_print_preview)
        m_file.addAction(self.act_print)
        m_file.addSeparator()
        m_file.addAction(self.act_close_tab)
        m_file.addAction(self.act_quit)

        m_edit = menubar.addMenu("&Editar")
        m_edit.addAction(self.act_undo)
        m_edit.addAction(self.act_redo)
        m_edit.addSeparator()
        m_edit.addAction(self.act_delete_selection)
        m_edit.addSeparator()
        m_edit.addAction(self.act_find)

        m_view = menubar.addMenu("Exi&bir")
        m_view.addAction(self.act_zoom_in)
        m_view.addAction(self.act_zoom_out)
        m_view.addAction(self.act_zoom_reset)
        m_view.addAction(self.act_fit_width)
        m_view.addAction(self.act_fit_page)
        m_view.addSeparator()
        m_view.addAction(self.act_prev_page)
        m_view.addAction(self.act_next_page)
        m_view.addSeparator()
        m_view.addAction(self.act_toggle_sidebar)
        m_view.addAction(self.act_toggle_theme)
        m_view.addSeparator()
        m_view.addAction(self.act_edit_mode)

        m_insert = menubar.addMenu("&Inserir")
        for tool, _icon, _sc in TOOL_SPECS:
            m_insert.addAction(self.tool_actions[tool])

        m_page = menubar.addMenu("Pá&gina")
        m_page.addAction(self.act_page_manager)
        m_page.addSeparator()
        m_page.addAction(self.act_insert_blank)
        m_page.addAction(self.act_rotate_left)
        m_page.addAction(self.act_rotate_right)
        m_page.addAction(self.act_delete_page)
        m_page.addSeparator()
        m_page.addAction(self.act_ocr)

        m_help = menubar.addMenu("Aj&uda")
        m_help.addAction(self.act_about)

    def _build_toolbars(self):
        tb_main = QToolBar("Principal", self)
        tb_main.setObjectName("mainToolBar")
        tb_main.setMovable(False)
        tb_main.setIconSize(QSize(18, 18))
        tb_main.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(tb_main)
        for a in (self.act_new, self.act_open, self.act_save, self.act_print):
            tb_main.addAction(a)
        tb_main.addSeparator()
        for a in (self.act_undo, self.act_redo):
            tb_main.addAction(a)
        tb_main.addSeparator()
        tb_main.addAction(self.act_toggle_sidebar)
        tb_main.addAction(self.act_find)
        tb_main.addSeparator()

        tb_main.addAction(self.act_zoom_out)
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(90)
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%", "300%"])
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.activated.connect(self._zoom_combo_changed)
        self.zoom_combo.lineEdit().returnPressed.connect(lambda: self._zoom_combo_changed(-1))
        tb_main.addWidget(self.zoom_combo)
        tb_main.addAction(self.act_zoom_in)
        tb_main.addAction(self.act_fit_width)
        tb_main.addAction(self.act_fit_page)
        tb_main.addSeparator()
        tb_main.addAction(self.act_toggle_theme)

        # Espaçador empurra o botão de modo para a direita, bem visível.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb_main.addWidget(spacer)

        self.edit_mode_btn = QToolButton()
        self.edit_mode_btn.setDefaultAction(self.act_edit_mode)
        self.edit_mode_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.edit_mode_btn.setObjectName("editModeButton")
        self.edit_mode_btn.setCursor(Qt.PointingHandCursor)
        tb_main.addWidget(self.edit_mode_btn)

        # Paleta de ferramentas (só visível em modo de edição), com nome sob
        # cada ícone para não deixar dúvida sobre a função de cada botão.
        self.tb_tools = QToolBar("Ferramentas", self)
        self.tb_tools.setObjectName("toolsToolBar")
        self.tb_tools.setMovable(False)
        self.tb_tools.setIconSize(QSize(20, 20))
        self.tb_tools.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.LeftToolBarArea, self.tb_tools)
        self.tb_tools.setOrientation(Qt.Vertical)
        for tool, _icon, _sc in TOOL_SPECS:
            self.tb_tools.addAction(self.tool_actions[tool])
        self.tb_tools.setVisible(False)

        # Barra de estilo (cor, preenchimento, espessura, fonte) — também só
        # aparece em modo de edição.
        self.tb_style = QToolBar("Estilo", self)
        self.tb_style.setObjectName("styleToolBar")
        self.tb_style.setMovable(False)
        self.tb_style.setIconSize(QSize(16, 16))
        self.addToolBarBreak()
        self.addToolBar(self.tb_style)

        self.tb_style.addWidget(QLabel("  Cor do traço: "))
        self.stroke_color_btn = ColorButton(QColor(212, 69, 69), "Cor do traço/contorno")
        self.stroke_color_btn.colorChanged.connect(self._stroke_color_changed)
        self.tb_style.addWidget(self.stroke_color_btn)

        self.tb_style.addWidget(QLabel("  Preenchimento: "))
        self.fill_color_btn = ColorButton(QColor(255, 255, 255, 0), "Cor de preenchimento das formas")
        self.fill_color_btn.colorChanged.connect(self._fill_color_changed)
        self.tb_style.addWidget(self.fill_color_btn)
        self.fill_none_btn = QPushButton("Sem preenchimento")
        self.fill_none_btn.setFixedHeight(26)
        self.fill_none_btn.setToolTip("Remover a cor de preenchimento das formas")
        self.fill_none_btn.clicked.connect(self._clear_fill_color)
        self.tb_style.addWidget(self.fill_none_btn)

        self.tb_style.addWidget(QLabel("  Cor do realce: "))
        self.highlight_color_btn = ColorButton(QColor(255, 235, 59), "Cor do realce de texto")
        self.highlight_color_btn.colorChanged.connect(self._highlight_color_changed)
        self.tb_style.addWidget(self.highlight_color_btn)

        self.tb_style.addWidget(QLabel("  Espessura do traço: "))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.5, 30.0)
        self.width_spin.setSingleStep(0.5)
        self.width_spin.setValue(2.0)
        self.width_spin.setToolTip("Espessura da linha/contorno, em pontos")
        self.width_spin.valueChanged.connect(self._width_changed)
        self.tb_style.addWidget(self.width_spin)

        self.tb_style.addWidget(QLabel("  Tamanho da fonte: "))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(4, 200)
        self.font_size_spin.setValue(13)
        self.font_size_spin.setToolTip("Tamanho da fonte para texto novo")
        self.font_size_spin.valueChanged.connect(self._font_size_changed)
        self.tb_style.addWidget(self.font_size_spin)
        self.tb_style.setVisible(False)

    def _build_central(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.find_bar = FindBar()
        self.find_bar.setVisible(False)
        self.find_bar.closed.connect(self.hide_find_bar)
        self.find_bar.edit.textChanged.connect(self._live_search)
        self.find_bar.next_btn.clicked.connect(lambda: self._with_view(lambda v: v.next_search_result()))
        self.find_bar.prev_btn.clicked.connect(lambda: self._with_view(lambda v: v.prev_search_result()))
        layout.addWidget(self.find_bar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

        self.setCentralWidget(container)

    def _build_docks(self):
        self.sidebar = DocumentSidebar()
        self.sidebar.pageActivated.connect(lambda i: self._with_view(lambda v: v.goto_page(i)))
        self.sidebar.contextMenuRequestedFor.connect(self._show_page_context_menu)

        self.dock = QDockWidget("Navegação", self)
        self.dock.setObjectName("navigationDock")
        self.dock.setWidget(self.sidebar)
        self.dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        self.dock.visibilityChanged.connect(self.act_toggle_sidebar.setChecked)

    def _build_statusbar(self):
        sb = self.statusBar()

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedWidth(70)
        self.page_spin.editingFinished.connect(self._page_spin_changed)
        sb.addPermanentWidget(QLabel("Página:"))
        sb.addPermanentWidget(self.page_spin)
        self.page_count_label = QLabel("de 1")
        sb.addPermanentWidget(self.page_count_label)

        sb.addPermanentWidget(QLabel("   "))
        self.tool_label = QLabel(TOOL_LABELS[Tool.SELECT])
        sb.addPermanentWidget(self.tool_label)

        sb.addPermanentWidget(QLabel("   "))
        self.modified_label = QLabel("")
        sb.addPermanentWidget(self.modified_label)

        sb.showMessage(f"{__app_name__} {__version__} pronto.", 4000)

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------

    def _apply_theme(self):
        QApplication.instance().setStyleSheet(stylesheet(self._dark_theme))
        self._refresh_icons()

    def _refresh_icons(self):
        color = icon_color(self._dark_theme)
        for action, name in self._icon_actions:
            action.setIcon(ficon(name, color))

    def toggle_theme(self):
        self._dark_theme = not self._dark_theme
        self.settings.setValue("theme/dark", self._dark_theme)
        self._apply_theme()

    # ------------------------------------------------------------------
    # Gestão de abas / documentos
    # ------------------------------------------------------------------

    def _current_view(self) -> Optional[PdfView]:
        return self.tabs.currentWidget()

    def _current_doc(self) -> Optional[PdfDocument]:
        view = self._current_view()
        return view.document if view else None

    def _with_view(self, func):
        view = self._current_view()
        if view is not None:
            func(view)

    def _with_doc(self, func):
        doc = self._current_doc()
        if doc is not None:
            func(doc)

    def _add_document_tab(self, document: PdfDocument, title: str):
        view = PdfView(document)
        view.set_edit_mode(self._edit_mode)
        view.pageChanged.connect(lambda i, v=view: self._on_page_changed(v, i))
        view.zoomChanged.connect(lambda z, v=view: self._on_zoom_changed(v, z))
        view.selectionChanged.connect(lambda hit: self.act_delete_selection.setEnabled(hit is not None))
        view.statusMessage.connect(lambda msg: self.statusBar().showMessage(msg, 3000))
        document.modified_changed.connect(lambda m, d=document: self._refresh_tab_title(d))
        document.changed.connect(lambda d=document: self._refresh_tab_title(d))

        index = self.tabs.addTab(view, title)
        self.tabs.setCurrentIndex(index)
        self._refresh_tab_title(document)
        return view

    def _refresh_tab_title(self, document: PdfDocument):
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            if view.document is document:
                name = Path(document.path).name if document.path else (document.custom_title or "Sem título")
                mark = " •" if document.modified else ""
                self.tabs.setTabText(i, name + mark)
                self.tabs.setTabToolTip(i, document.path or name)
                if view is self._current_view():
                    self.setWindowTitle(f"{name}{mark} — {__app_name__}")
                    self.modified_label.setText("Alterações não salvas" if document.modified else "")
                break

    def new_document(self):
        self._untitled_count += 1
        document = PdfDocument.new()
        document.insert_blank_page()
        document._set_modified(False)
        document.custom_title = f"Sem título {self._untitled_count}"
        self._add_document_tab(document, document.custom_title)

    def open_document_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir PDF", "", "Documentos PDF (*.pdf)")
        if path:
            self.open_document(path)

    def open_document(self, path: str):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Arquivo não encontrado", f"Não foi possível encontrar:\n{path}")
            return
        try:
            document = PdfDocument.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao abrir", f"Não foi possível abrir o arquivo:\n{exc}")
            return

        while document.needs_password():
            password, ok = QInputDialog.getText(
                self, "Documento protegido", "Este PDF está protegido. Digite a senha:",
                QLineEdit.Password,
            )
            if not ok:
                document.close()
                return
            if not document.authenticate(password):
                QMessageBox.warning(self, "Senha incorreta", "A senha informada está incorreta.")

        document.custom_title = Path(path).name
        self._add_document_tab(document, document.custom_title)
        self._add_recent(path)

    def close_tab(self, index: int) -> bool:
        view = self.tabs.widget(index)
        if view is None:
            return True
        document = view.document
        if document.modified:
            name = Path(document.path).name if document.path else document.custom_title
            reply = QMessageBox.question(
                self, "Alterações não salvas",
                f"Deseja salvar as alterações em “{name}” antes de fechar?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if reply == QMessageBox.Cancel:
                return False
            if reply == QMessageBox.Save:
                if not self._save_document(document):
                    return False
        self.tabs.removeTab(index)
        document.close()
        if self.tabs.count() == 0:
            self.new_document()
        return True

    def _on_tab_changed(self, _index: int):
        view = self._current_view()
        has_doc = view is not None
        for action in (self.act_save, self.act_save_as, self.act_print, self.act_print_preview,
                       self.act_properties, self.act_undo, self.act_redo, self.act_find,
                       self.act_zoom_in, self.act_zoom_out, self.act_fit_page, self.act_fit_width):
            action.setEnabled(has_doc)
        for action in (self.act_page_manager, self.act_insert_blank, self.act_delete_page,
                       self.act_rotate_left, self.act_rotate_right, self.act_ocr):
            action.setEnabled(has_doc and self._edit_mode)
        if not has_doc:
            self.sidebar.set_document(None)
            self.setWindowTitle(__app_name__)
            self._update_mode_status()
            return
        self.sidebar.set_document(view.document)
        self.sidebar.set_current_page(view.current_page)
        self.page_spin.setMaximum(max(1, view.document.page_count))
        self.page_spin.setValue(view.current_page + 1)
        self.page_count_label.setText(f"de {view.document.page_count}")
        self._refresh_tab_title(view.document)
        self._sync_zoom_label(view.zoom)
        self.hide_find_bar()
        self._update_mode_status()

    def _on_page_changed(self, view: PdfView, index: int):
        if view is self._current_view():
            self.page_spin.blockSignals(True)
            self.page_spin.setMaximum(max(1, view.document.page_count))
            self.page_spin.setValue(index + 1)
            self.page_spin.blockSignals(False)
            self.page_count_label.setText(f"de {view.document.page_count}")
            self.sidebar.set_current_page(index)

    def _on_zoom_changed(self, view: PdfView, zoom: float):
        if view is self._current_view():
            self._sync_zoom_label(zoom)

    def _sync_zoom_label(self, zoom: float):
        self.zoom_combo.blockSignals(True)
        self.zoom_combo.setCurrentText(f"{round(zoom * 100)}%")
        self.zoom_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Ações de arquivo
    # ------------------------------------------------------------------

    def save_current(self):
        doc = self._current_doc()
        if doc is not None:
            self._save_document(doc)

    def save_current_as(self):
        doc = self._current_doc()
        if doc is not None:
            self._save_document(doc, force_dialog=True)

    def _save_document(self, document: PdfDocument, force_dialog: bool = False) -> bool:
        target = document.path
        if force_dialog or not target:
            suggested = document.path or f"{getattr(document, 'custom_title', 'documento')}.pdf"
            target, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", suggested, "PDF (*.pdf)")
            if not target:
                return False
            if not target.lower().endswith(".pdf"):
                target += ".pdf"
        try:
            document.save(target)
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao salvar", f"Não foi possível salvar o arquivo:\n{exc}")
            return False
        self._add_recent(target)
        self._refresh_tab_title(document)
        self.statusBar().showMessage(f"Salvo em {target}", 4000)
        return True

    def show_properties(self):
        doc = self._current_doc()
        if doc is not None:
            PropertiesDialog(doc, self).exec()

    def print_current(self):
        doc = self._current_doc()
        if doc is None:
            return
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            if not print_document(doc, printer):
                QMessageBox.warning(self, "Impressão", "Não foi possível imprimir o documento.")

    def print_preview_current(self):
        doc = self._current_doc()
        if doc is None:
            return
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: print_document(doc, p))
        preview.exec()

    # ------------------------------------------------------------------
    # Ferramentas / estilo
    # ------------------------------------------------------------------

    def _set_tool(self, tool: Tool):
        for i in range(self.tabs.count()):
            self.tabs.widget(i).set_tool(tool)
        self._update_mode_status()

    def _toggle_edit_mode(self, checked: bool):
        self._edit_mode = checked
        self.tb_tools.setVisible(checked)
        self.tb_style.setVisible(checked)
        for tool_action in self.tool_actions.values():
            tool_action.setEnabled(checked)
        if checked:
            self.tool_actions[Tool.SELECT].setChecked(True)
        for i in range(self.tabs.count()):
            self.tabs.widget(i).set_edit_mode(checked)
        self._on_tab_changed(self.tabs.currentIndex())

    def _update_mode_status(self):
        if not self._edit_mode:
            self.tool_label.setText("Modo leitura — clique em “Editar PDF” para editar")
            return
        view = self._current_view()
        label = TOOL_LABELS.get(view.tool, "") if view else ""
        self.tool_label.setText(f"Editando: {label}" if label else "Modo de edição")

    def _stroke_color_changed(self, color: QColor):
        self._with_view(lambda v: setattr(v.tool_options, "stroke_color", (color.redF(), color.greenF(), color.blueF())))

    def _fill_color_changed(self, color: QColor):
        rgb = None if color.alpha() == 0 else (color.redF(), color.greenF(), color.blueF())
        self._with_view(lambda v: setattr(v.tool_options, "fill_color", rgb))

    def _clear_fill_color(self):
        transparent = QColor(255, 255, 255, 0)
        self.fill_color_btn.set_color(transparent)
        self._with_view(lambda v: setattr(v.tool_options, "fill_color", None))

    def _highlight_color_changed(self, color: QColor):
        self._with_view(lambda v: setattr(v.tool_options, "highlight_color", (color.redF(), color.greenF(), color.blueF())))

    def _width_changed(self, value: float):
        self._with_view(lambda v: setattr(v.tool_options, "line_width", value))

    def _font_size_changed(self, value: int):
        self._with_view(lambda v: setattr(v.tool_options, "font_size", float(value)))

    def _delete_selection(self):
        self._with_view(lambda v: v.delete_selection())

    # ------------------------------------------------------------------
    # Zoom / navegação
    # ------------------------------------------------------------------

    def _zoom_combo_changed(self, _index: int):
        text = self.zoom_combo.currentText().replace("%", "").strip()
        try:
            value = float(text) / 100.0
        except ValueError:
            return
        self._with_view(lambda v: v.set_zoom(value))

    def _page_spin_changed(self):
        self._with_view(lambda v: v.goto_page(self.page_spin.value() - 1))

    def _toggle_sidebar(self, checked: bool):
        self.dock.setVisible(checked)

    # ------------------------------------------------------------------
    # Busca
    # ------------------------------------------------------------------

    def show_find_bar(self):
        self.find_bar.setVisible(True)
        self.find_bar.edit.setFocus()
        self.find_bar.edit.selectAll()

    def hide_find_bar(self):
        self.find_bar.setVisible(False)
        self._with_view(lambda v: v.clear_search())

    def _live_search(self, text: str):
        view = self._current_view()
        if view is None:
            return
        if not text:
            view.clear_search()
            self.find_bar.result_label.setText("")
            return
        count = view.search(text)
        self.find_bar.result_label.setText(f"{count} resultado(s)" if count else "Nenhum resultado")

    # ------------------------------------------------------------------
    # Páginas
    # ------------------------------------------------------------------

    def _open_page_manager(self):
        doc = self._current_doc()
        if doc is not None:
            PageManagerDialog(doc, self, icon_color=icon_color(self._dark_theme)).exec()

    def _delete_current_page(self):
        view = self._current_view()
        doc = self._current_doc()
        if view is None or doc is None:
            return
        if doc.page_count <= 1:
            QMessageBox.warning(self, "Não é possível excluir", "O documento precisa ter ao menos uma página.")
            return
        doc.delete_pages([view.current_page])

    def _show_page_context_menu(self, indices: list, global_pos):
        doc = self._current_doc()
        if doc is None:
            return
        color = icon_color(self._dark_theme)
        menu = QMenu(self)
        act_del = menu.addAction(ficon("fa5s.trash-alt", color), "Excluir")
        act_rot_l = menu.addAction(ficon("fa5s.undo", color), "Girar ↺")
        act_rot_r = menu.addAction(ficon("fa5s.redo", color), "Girar ↻")
        act_dup = menu.addAction(ficon("fa5s.clone", color), "Duplicar")
        act_extract = menu.addAction(ficon("fa5s.file-export", color), "Extrair para novo arquivo...")
        chosen = menu.exec(global_pos)
        if chosen == act_del:
            if doc.page_count - len(indices) < 1:
                QMessageBox.warning(self, "Não é possível excluir", "O documento precisa ter ao menos uma página.")
                return
            doc.delete_pages(indices)
        elif chosen == act_rot_l:
            for i in indices:
                doc.rotate_page(i, -90)
        elif chosen == act_rot_r:
            for i in indices:
                doc.rotate_page(i, 90)
        elif chosen == act_dup:
            for i in reversed(indices):
                doc.duplicate_page(i)
        elif chosen == act_extract:
            path, _ = QFileDialog.getSaveFileName(self, "Extrair páginas para", "", "PDF (*.pdf)")
            if path:
                doc.extract_pages(indices, path)

    # ------------------------------------------------------------------
    # Arquivos recentes
    # ------------------------------------------------------------------

    def _recent_files(self) -> list:
        value = self.settings.value("recent/files", [])
        if isinstance(value, str):
            value = [value]
        return list(value or [])

    def _add_recent(self, path: str):
        files = [f for f in self._recent_files() if f != path]
        files.insert(0, path)
        files = files[: self.MAX_RECENT]
        self.settings.setValue("recent/files", files)
        self._update_recent_menu()

    def _update_recent_menu(self):
        self.recent_menu.clear()
        files = [f for f in self._recent_files() if os.path.exists(f)]
        if not files:
            empty = self.recent_menu.addAction("(vazio)")
            empty.setEnabled(False)
            return
        for path in files:
            action = self.recent_menu.addAction(Path(path).name)
            action.setToolTip(path)
            action.triggered.connect(lambda _checked=False, p=path: self.open_document(p))
        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("Limpar lista")
        clear_action.triggered.connect(self._clear_recent)

    def _clear_recent(self):
        self.settings.setValue("recent/files", [])
        self._update_recent_menu()

    # ------------------------------------------------------------------
    # Diversos
    # ------------------------------------------------------------------

    def _show_about(self):
        AboutDialog(self).exec()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.open_document(path)

    def closeEvent(self, event: QCloseEvent):
        # Percorremos uma cópia estável dos widgets: fechar uma aba desloca os
        # índices das demais, então não podemos iterar por índice diretamente.
        views = [self.tabs.widget(i) for i in range(self.tabs.count())]
        for view in views:
            document = view.document
            if document.modified:
                index = self.tabs.indexOf(view)
                if index == -1:
                    continue
                self.tabs.setCurrentIndex(index)
                if not self.close_tab(index):
                    event.ignore()
                    return
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        event.accept()
