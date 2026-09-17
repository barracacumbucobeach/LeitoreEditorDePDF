"""
Tema visual do Papyra.

Uma paleta única (latão/dourado sobre grafite ou marfim) aplicada de forma
consistente nos modos claro e escuro, com folha de estilos (QSS) desenhada
para parecer um produto profissional de mercado — não o visual padrão do Qt.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

DARK = {
    "bg": "#12151c",
    "bg_alt": "#0c0e13",
    "surface": "#191d27",
    "surface_alt": "#20242f",
    "surface_hover": "#262b38",
    "border": "#2b3140",
    "border_soft": "#232836",
    "text": "#eef1f7",
    "text_dim": "#9aa3b8",
    "text_faint": "#68708a",
    "accent": "#3e7bfa",
    "accent_hover": "#5c90fb",
    "accent_text": "#ffffff",
    "danger": "#f0555f",
    "success": "#3ecf8e",
    "info": "#60a5fa",
    "canvas": "#090b10",
    "selection": "#2c4a7c",
}

LIGHT = {
    "bg": "#f3f5fa",
    "bg_alt": "#eaeef7",
    "surface": "#ffffff",
    "surface_alt": "#f6f8fc",
    "surface_hover": "#eaf0fd",
    "border": "#dbe2f0",
    "border_soft": "#e6ebf5",
    "text": "#1b2233",
    "text_dim": "#5b6478",
    "text_faint": "#8b93a7",
    "accent": "#2563eb",
    "accent_hover": "#3b76f0",
    "accent_text": "#ffffff",
    "danger": "#dc4655",
    "success": "#12946a",
    "info": "#2f66c9",
    "canvas": "#dfe4ee",
    "selection": "#c7d9fb",
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

    /* ---------- Página inicial (dashboard) ---------- */
    QWidget#homeRoot, QWidget#homeContent {{
        background: {p['bg']};
    }}
    QLabel#homeTitle {{
        font-size: 25px;
        font-weight: 700;
        color: {p['text']};
    }}
    QLabel#homeSubtitle {{
        font-size: 13px;
        color: {p['text_dim']};
    }}
    QLabel#homeSectionTitle {{
        font-size: 13px;
        font-weight: 700;
        color: {p['text_dim']};
    }}
    QLabel#homeHint {{
        color: {p['text_faint']};
        font-size: 12px;
        padding: 10px 2px;
    }}
    QFrame#homeCard {{
        background: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 12px;
    }}
    QFrame#homeCard:hover {{
        background: {p['surface_hover']};
        border: 1px solid {p['accent']};
    }}
    QLabel#homeCardTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {p['text']};
    }}
    QLabel#homeCardSubtitle {{
        font-size: 12px;
        color: {p['text_dim']};
    }}
    QFrame#recentRow {{
        background: {p['surface_alt']};
        border: 1px solid {p['border_soft']};
        border-radius: 8px;
    }}
    QFrame#recentRow:hover {{
        background: {p['surface_hover']};
        border: 1px solid {p['accent']};
    }}
    QLabel#recentRowName {{
        font-weight: 600;
        color: {p['text']};
    }}
    QLabel#recentRowPath {{
        font-size: 11px;
        color: {p['text_faint']};
    }}

    /* ---------- Barra de navegação (coluna esquerda) ---------- */
    QWidget#navRail {{
        background: {p['bg_alt']};
        border-right: 1px solid {p['border']};
    }}
    QLabel#navBrand {{
        font-size: 16px;
        font-weight: 700;
        color: {p['text']};
        padding: 4px 2px;
    }}
    QLabel#navSectionLabel {{
        color: {p['text_faint']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 10px 10px 2px 10px;
    }}
    QToolButton#navItem {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 9px 10px;
        text-align: left;
        color: {p['text_dim']};
        font-weight: 500;
    }}
    QToolButton#navItem:hover {{
        background: {p['surface_hover']};
        color: {p['text']};
    }}
    QToolButton#navItem:checked {{
        background: {p['accent']};
        color: {p['accent_text']};
        font-weight: 600;
    }}

    /* ---------- Painel direito "Ferramentas de Edição" ---------- */
    QWidget#toolsPanelRoot {{
        background: {p['bg_alt']};
    }}
    QLabel#toolsPanelTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {p['text']};
        padding: 2px 2px 0 2px;
    }}
    QLabel#toolsPanelSubtitle {{
        color: {p['text_dim']};
        font-size: 12px;
        padding: 0 2px 4px 2px;
    }}
    QLabel#toolsGroupTitle {{
        color: {p['text_dim']};
        font-size: 12px;
        font-weight: 700;
        padding: 12px 2px 2px 2px;
    }}
    QToolButton#toolCard {{
        background: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 10px 8px;
        color: {p['text']};
        font-size: 11px;
        font-weight: 600;
    }}
    QToolButton#toolCard:hover {{
        background: {p['surface_hover']};
        border: 1px solid {p['accent']};
    }}
    QToolButton#toolCard:pressed {{
        background: {p['surface_alt']};
    }}
    """
