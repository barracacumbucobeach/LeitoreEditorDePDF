"""
Tema visual do Fólio Studio.

Uma paleta única (latão/dourado sobre grafite ou marfim) aplicada de forma
consistente nos modos claro e escuro, com folha de estilos (QSS) desenhada
para parecer um produto profissional de mercado — não o visual padrão do Qt.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

DARK = {
    "bg": "#191c22",
    "bg_alt": "#14161b",
    "surface": "#20242c",
    "surface_alt": "#262b35",
    "surface_hover": "#2c313d",
    "border": "#333a47",
    "border_soft": "#2a2f3a",
    "text": "#e9ebf1",
    "text_dim": "#9aa3b5",
    "text_faint": "#6b7385",
    "accent": "#d3a44c",
    "accent_hover": "#e6b862",
    "accent_text": "#1a1d24",
    "danger": "#e5636b",
    "success": "#4bd0a0",
    "info": "#6ea8fe",
    "canvas": "#0e0f13",
    "selection": "#3a5a8c",
}

LIGHT = {
    "bg": "#f2f1ec",
    "bg_alt": "#e9e7df",
    "surface": "#ffffff",
    "surface_alt": "#f6f5f1",
    "surface_hover": "#eee9db",
    "border": "#dcd6c4",
    "border_soft": "#e6e1d2",
    "text": "#232420",
    "text_dim": "#5c5d52",
    "text_faint": "#8b8c7f",
    "accent": "#9c6f13",
    "accent_hover": "#b3811a",
    "accent_text": "#ffffff",
    "danger": "#c23b41",
    "success": "#1f8f66",
    "info": "#2f66c9",
    "canvas": "#d9d6cb",
    "selection": "#bcd2f3",
}


def palette(dark: bool) -> dict:
    return DARK if dark else LIGHT


def qcolor(dark: bool, key: str) -> QColor:
    return QColor(palette(dark)[key])


def icon_color(dark: bool) -> str:
    """Cor apropriada para ícones monocromáticos (qtawesome) no tema atual."""
    return palette(dark)["text"]


def stylesheet(dark: bool) -> str:
    p = palette(dark)
    return f"""
    * {{
        outline: none;
        font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif;
    }}

    QMainWindow, QDialog {{
        background: {p['bg']};
        color: {p['text']};
    }}

    QWidget {{
        color: {p['text']};
        selection-background-color: {p['selection']};
        selection-color: {p['text']};
    }}

    /* ---------- Barra de menus ---------- */
    QMenuBar {{
        background: {p['bg_alt']};
        color: {p['text']};
        border-bottom: 1px solid {p['border']};
        padding: 2px 4px;
        spacing: 2px;
    }}
    QMenuBar::item {{
        padding: 5px 10px;
        border-radius: 5px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background: {p['surface_hover']};
    }}
    QMenu {{
        background: {p['surface']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::separator {{
        height: 1px;
        background: {p['border']};
        margin: 6px 8px;
    }}
    QMenu::item {{
        padding: 6px 28px 6px 14px;
        border-radius: 6px;
        margin: 1px;
    }}
    QMenu::item:selected {{
        background: {p['accent']};
        color: {p['accent_text']};
    }}
    QMenu::icon {{
        padding-left: 6px;
    }}

    /* ---------- Barra de ferramentas ---------- */
    QToolBar {{
        background: {p['bg_alt']};
        border: none;
        border-bottom: 1px solid {p['border']};
        padding: 6px 8px;
        spacing: 4px;
    }}
    QToolBar::separator {{
        background: {p['border']};
        width: 1px;
        margin: 6px 6px;
    }}
    QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 7px;
        padding: 6px;
        color: {p['text']};
    }}
    QToolButton:hover {{
        background: {p['surface_hover']};
        border: 1px solid {p['border']};
    }}
    QToolButton:pressed {{
        background: {p['surface_alt']};
    }}
    QToolButton:checked {{
        background: {p['accent']};
        color: {p['accent_text']};
        border: 1px solid {p['accent']};
    }}
    QToolButton::menu-indicator {{ width: 0; }}

    /* ---------- Botão de alternância Visualizar / Editar ---------- */
    QToolButton#editModeButton {{
        background: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 14px;
        padding: 6px 16px 6px 12px;
        margin: 2px 4px;
        font-weight: 600;
        color: {p['text']};
    }}
    QToolButton#editModeButton:hover {{
        background: {p['surface_hover']};
    }}
    QToolButton#editModeButton:checked {{
        background: {p['accent']};
        color: {p['accent_text']};
        border: 1px solid {p['accent']};
    }}

    /* ---------- Paleta de ferramentas (lateral) ---------- */
    QToolBar#toolsToolBar {{
        spacing: 3px;
        padding: 8px 4px;
    }}
    QToolBar#toolsToolBar QToolButton {{
        min-width: 76px;
        max-width: 76px;
        padding: 6px 2px;
        font-size: 11px;
    }}
    QToolBar#styleToolBar {{
        padding: 4px 10px;
    }}

    /* ---------- Barra de status ---------- */
    QStatusBar {{
        background: {p['bg_alt']};
        color: {p['text_dim']};
        border-top: 1px solid {p['border']};
    }}
    QStatusBar::item {{ border: none; }}

    /* ---------- Abas de documentos ---------- */
    QTabWidget::pane {{
        border: none;
        background: {p['bg']};
        top: -1px;
    }}
    QTabBar {{
        background: {p['bg_alt']};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {p['text_dim']};
        padding: 8px 18px;
        margin: 0px;
        border: none;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {p['text']};
        border-bottom: 2px solid {p['accent']};
        background: {p['bg']};
    }}
    QTabBar::tab:hover:!selected {{
        color: {p['text']};
        background: {p['surface_hover']};
    }}
    QTabBar::close-button {{
        image: none;
    }}

    /* ---------- Painéis / listas laterais ---------- */
    QDockWidget {{
        color: {p['text']};
        titlebar-close-icon: none;
        border: none;
    }}
    QDockWidget::title {{
        background: {p['bg_alt']};
        padding: 8px 10px;
        border-bottom: 1px solid {p['border']};
        font-weight: 600;
    }}

    QListWidget, QTreeWidget {{
        background: {p['surface']};
        border: none;
        color: {p['text']};
        padding: 4px;
    }}
    QListWidget::item, QTreeWidget::item {{
        border-radius: 6px;
        padding: 6px;
        margin: 2px 0;
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {p['accent']};
        color: {p['accent_text']};
    }}
    QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{
        background: {p['surface_hover']};
    }}

    /* ---------- Área de rolagem / tela do documento ---------- */
    QScrollArea, QAbstractScrollArea {{
        background: {p['canvas']};
        border: none;
    }}
    QGraphicsView {{
        background: {p['canvas']};
        border: none;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 13px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']};
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['text_faint']}; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 13px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p['border']};
        min-width: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p['text_faint']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

    /* ---------- Controles ---------- */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
        background: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 5px 8px;
        color: {p['text']};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
        border: 1px solid {p['accent']};
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {p['surface']};
        border: 1px solid {p['border']};
        selection-background-color: {p['accent']};
        selection-color: {p['accent_text']};
        outline: none;
    }}

    QPushButton {{
        background: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        padding: 7px 16px;
        color: {p['text']};
    }}
    QPushButton:hover {{ background: {p['surface_hover']}; }}
    QPushButton:pressed {{ background: {p['border_soft']}; }}
    QPushButton:disabled {{ color: {p['text_faint']}; }}
    QPushButton#primary, QPushButton[cta="true"] {{
        background: {p['accent']};
        color: {p['accent_text']};
        border: 1px solid {p['accent']};
        font-weight: 600;
    }}
    QPushButton#primary:hover, QPushButton[cta="true"]:hover {{
        background: {p['accent_hover']};
        border: 1px solid {p['accent_hover']};
    }}

    QCheckBox, QRadioButton {{ spacing: 8px; color: {p['text']}; }}
    QGroupBox {{
        border: 1px solid {p['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {p['text_dim']};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {p['border']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {p['accent']};
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: {p['accent']};
        border-radius: 2px;
    }}

    QSplitter::handle {{
        background: {p['border']};
    }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical {{ height: 1px; }}

    QToolTip {{
        background: {p['surface_alt']};
        color: {p['text']};
        border: 1px solid {p['border']};
        padding: 4px 8px;
        border-radius: 5px;
    }}

    QLabel#pageBadge {{
        background: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 3px 10px;
        color: {p['text_dim']};
    }}

    QProgressBar {{
        background: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        text-align: center;
        color: {p['text']};
    }}
    QProgressBar::chunk {{
        background: {p['accent']};
        border-radius: 6px;
    }}
    """
