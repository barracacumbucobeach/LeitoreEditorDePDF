"""
Visualizador/editor de páginas de PDF.

`PdfView` é uma `QGraphicsView` com rolagem contínua entre páginas, zoom
suave, e um conjunto de ferramentas de edição (texto, imagens, realces,
formas, tinta livre, notas e borracha) que operam diretamente sobre o
`PdfDocument`. A cena usa coordenadas de pixel na resolução atual de zoom:
um ponto PDF `(x, y)` de uma página corresponde ao ponto de cena
`item.pos() + (x*zoom, y*zoom)`.
"""

from __future__ import annotations

import bisect
from typing import Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QFileDialog, QGraphicsDropShadowEffect, QGraphicsLineItem, QGraphicsPathItem,
    QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QTextEdit,
    QWidget,
)

from .document import ImageInfo, PdfDocument, TextSpan
from .tools import DRAG_LINE_TOOLS, DRAG_RECT_TOOLS, Tool, ToolOptions

PAGE_GAP = 20
SIDE_MARGIN = 40
MIN_ZOOM = 0.15
MAX_ZOOM = 8.0
SELECTION_COLOR = "#d3a44c"


class PageItem(QGraphicsPixmapItem):
    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.rendered = False
        self.setTransformationMode(Qt.SmoothTransformation)


class InlineTextEdit(QTextEdit):
    """Editor de texto flutuante embutido na cena para editar/inserir texto."""

    committed = Signal(str)
    cancelled = Signal()

    def __init__(self, initial_text: str = ""):
        super().__init__()
        self.setAcceptRichText(False)
        self.setFrameStyle(0)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setPlainText(initial_text)
        cursor = self.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.setTextCursor(cursor)
        self._committed = False

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self._commit()
            return
        if event.key() == Qt.Key_Escape:
            self._committed = True
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self._commit()
        super().focusOutEvent(event)

    def _commit(self):
        if self._committed:
            return
        self._committed = True
        self.committed.emit(self.toPlainText())


class PdfView(QGraphicsView):
    """Área de leitura e edição de um documento PDF."""

    pageChanged = Signal(int)
    zoomChanged = Signal(float)
    documentEdited = Signal()
    selectionChanged = Signal(object)
    statusMessage = Signal(str)

    def __init__(self, document: PdfDocument, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setDragMode(QGraphicsView.NoDrag)

        self.document = document
        self.zoom = 1.0
        self.tool = Tool.SELECT
        self.tool_options = ToolOptions()

        self._page_items: list[PageItem] = []
        self._page_positions: list[float] = []
        self._page_heights: list[float] = []
        self._current_page = 0
        self._layout_sig = None

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_visible)

        self._drag_start_scene: Optional[QPointF] = None
        self._drag_start_info = None
        self._rubber_item: Optional[QGraphicsRectItem] = None

        self._line_preview: Optional[QGraphicsLineItem] = None
        self._ink_path_item: Optional[QGraphicsPathItem] = None
        self._ink_scene_points: Optional[list] = None
        self._ink_page: Optional[int] = None

        self._selection = None
        self._selection_item: Optional[QGraphicsRectItem] = None
        self._resize_handle_item: Optional[QGraphicsRectItem] = None
        self._drag_mode: Optional[str] = None
        self._drag_anchor_scene: Optional[QPointF] = None
        self._drag_orig_rect_scene: Optional[QRectF] = None

        self._search_results: list = []
        self._search_markers: list = []
        self._search_index = -1

        self._panning = False
        self._pan_start = None

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.document.changed.connect(self._on_document_changed)

        self.rebuild_layout()
        self.set_tool(Tool.SELECT)

    # ------------------------------------------------------------------
    # Layout / renderização
    # ------------------------------------------------------------------

    def _layout_signature(self):
        return tuple(
            tuple(round(v, 1) for v in self.document.page_size(i))
            for i in range(self.document.page_count)
        )

    def rebuild_layout(self):
        self._reset_transient_items()
        self.scene().clear()
        self._page_items = []
        self._page_positions = []
        self._page_heights = []

        sizes = [self.document.page_size(i) for i in range(self.document.page_count)]
        max_w = max((w * self.zoom for w, _ in sizes), default=0.0)

        y = PAGE_GAP
        for i, (w, h) in enumerate(sizes):
            pw, ph = w * self.zoom, h * self.zoom
            item = PageItem(i)
            placeholder = QPixmap(max(1, int(pw)), max(1, int(ph)))
            placeholder.fill(QColor("#ffffff"))
            item.setPixmap(placeholder)
            item.rendered = False
            item.setPos((max_w - pw) / 2, y)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(22)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 130))
            item.setGraphicsEffect(shadow)

            self.scene().addItem(item)
            self._page_items.append(item)
            self._page_positions.append(y)
            self._page_heights.append(ph)
            y += ph + PAGE_GAP

        self.scene().setSceneRect(-SIDE_MARGIN, 0, max_w + 2 * SIDE_MARGIN, max(y, 200))
        self._layout_sig = self._layout_signature()
        self._schedule_render(immediate=True)
        self._update_current_page()

    def _on_document_changed(self):
        sig = self._layout_signature()
        if sig != self._layout_sig:
            current = self._current_page
            self.rebuild_layout()
            self.goto_page(current)
        else:
            for item in self._page_items:
                item.rendered = False
            self._reset_transient_items()
            self._render_visible()
        self.documentEdited.emit()

    def _reset_transient_items(self):
        self._selection = None
        self._selection_item = None
        self._resize_handle_item = None
        self._drag_mode = None
        self._search_markers = []
        self._search_results = []
        self._search_index = -1
        self._rubber_item = None
        self._line_preview = None
        self._ink_path_item = None
        self._ink_scene_points = None

    def _schedule_render(self, immediate: bool = False):
        if immediate:
            self._render_visible()
        else:
            self._render_timer.start(35)

    def _on_scroll(self, *_args):
        self._schedule_render()
        self._update_current_page()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_render()

    def _page_index_at_y(self, y: float) -> int:
        if not self._page_positions:
            return 0
        idx = bisect.bisect_right(self._page_positions, y) - 1
        return max(0, min(idx, len(self._page_positions) - 1))

    def _visible_page_range(self):
        if not self._page_items:
            return 0, -1
        top = self.mapToScene(self.viewport().rect().topLeft()).y()
        bottom = self.mapToScene(self.viewport().rect().bottomLeft()).y()
        first = max(0, self._page_index_at_y(top) - 1)
        last = min(len(self._page_items) - 1, self._page_index_at_y(bottom) + 1)
        return first, last

    def _render_visible(self):
        if not self._page_items:
            return
        first, last = self._visible_page_range()
        for i in range(first, last + 1):
            item = self._page_items[i]
            if not item.rendered:
                img = self.document.render_page(i, zoom=self.zoom)
                item.setPixmap(QPixmap.fromImage(img))
                item.rendered = True

    def _update_current_page(self):
        center = self.mapToScene(self.viewport().rect().center()).y()
        idx = self._page_index_at_y(center)
        if idx != self._current_page:
            self._current_page = idx
            self.pageChanged.emit(idx)

    @property
    def current_page(self) -> int:
        return self._current_page

    # ------------------------------------------------------------------
    # Zoom / navegação
    # ------------------------------------------------------------------

    def set_zoom(self, zoom: float):
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        if abs(zoom - self.zoom) < 1e-4 or not self._page_items:
            self.zoom = zoom
            return
        anchor_scene = self.mapToScene(self.viewport().rect().center())
        page_idx = self._page_index_at_y(anchor_scene.y())
        rel_y = (anchor_scene.y() - self._page_positions[page_idx]) / max(1.0, self._page_heights[page_idx])

        self.zoom = zoom
        self.rebuild_layout()

        if page_idx < len(self._page_positions):
            target_y = self._page_positions[page_idx] + rel_y * self._page_heights[page_idx]
            self.centerOn(self.sceneRect().center().x(), target_y)
        self.zoomChanged.emit(self.zoom)

    def zoom_in(self):
        self.set_zoom(self.zoom * 1.15)

    def zoom_out(self):
        self.set_zoom(self.zoom / 1.15)

    def zoom_reset(self):
        self.set_zoom(1.0)

    def fit_width(self):
        if not self._page_items:
            return
        w, _ = self.document.page_size(self._current_page)
        available = self.viewport().width() - 2 * SIDE_MARGIN
        if w > 0 and available > 0:
            self.set_zoom(available / w)

    def fit_page(self):
        if not self._page_items:
            return
        w, h = self.document.page_size(self._current_page)
        available_w = self.viewport().width() - 2 * SIDE_MARGIN
        available_h = self.viewport().height() - 2 * PAGE_GAP
        if w > 0 and h > 0 and available_w > 0 and available_h > 0:
            self.set_zoom(min(available_w / w, available_h / h))

    def goto_page(self, index: int):
        if not self._page_positions:
            return
        index = max(0, min(index, len(self._page_positions) - 1))
        self.verticalScrollBar().setValue(int(self._page_positions[index]) - PAGE_GAP // 2)

    def next_page(self):
        self.goto_page(self._current_page + 1)

    def prev_page(self):
        self.goto_page(self._current_page - 1)

    # ------------------------------------------------------------------
    # Ferramentas
    # ------------------------------------------------------------------

    _CURSORS = {
        Tool.SELECT: Qt.ArrowCursor,
        Tool.EDIT_TEXT: Qt.IBeamCursor,
        Tool.ADD_TEXT: Qt.IBeamCursor,
        Tool.HIGHLIGHT: Qt.CrossCursor,
        Tool.RECT: Qt.CrossCursor,
        Tool.ELLIPSE: Qt.CrossCursor,
        Tool.LINE: Qt.CrossCursor,
        Tool.ARROW: Qt.CrossCursor,
        Tool.INK: Qt.CrossCursor,
        Tool.IMAGE: Qt.CrossCursor,
        Tool.NOTE: Qt.PointingHandCursor,
        Tool.ERASER: Qt.CrossCursor,
    }

    def set_tool(self, tool: Tool):
        self.tool = tool
        self._clear_selection()
        self.viewport().setCursor(QCursor(self._CURSORS.get(tool, Qt.ArrowCursor)))

    # -- mapeamento de coordenadas --------------------------------------

    def _scene_to_pdf(self, scene_pos: QPointF):
        if not self._page_items:
            return None
        idx = self._page_index_at_y(scene_pos.y())
        item = self._page_items[idx]
        local = item.mapFromScene(scene_pos)
        if not item.boundingRect().adjusted(-4, -4, 4, 4).contains(local):
            return None
        return idx, (local.x() / self.zoom, local.y() / self.zoom)

    def _pdf_rect_to_scene(self, page_idx: int, bbox) -> QRectF:
        item = self._page_items[page_idx]
        x0, y0, x1, y1 = bbox
        top_left = item.mapToScene(QPointF(x0 * self.zoom, y0 * self.zoom))
        bottom_right = item.mapToScene(QPointF(x1 * self.zoom, y1 * self.zoom))
        return QRectF(top_left, bottom_right).normalized()

    def _scene_rect_to_pdf(self, page_idx: int, rect_scene: QRectF) -> tuple:
        item = self._page_items[page_idx]
        local = item.mapRectFromScene(rect_scene).intersected(item.boundingRect())
        return (
            local.left() / self.zoom,
            local.top() / self.zoom,
            local.right() / self.zoom,
            local.bottom() / self.zoom,
        )

    # ------------------------------------------------------------------
    # Eventos de mouse
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)

        scene_pos = self.mapToScene(event.pos())

        if self.tool == Tool.SELECT:
            self._handle_select_press(scene_pos)
            return

        info = self._scene_to_pdf(scene_pos)

        if self.tool == Tool.EDIT_TEXT:
            if info:
                self._start_edit_text(*info)
            return

        if self.tool == Tool.NOTE:
            if info:
                self._commit_note(*info)
            return

        if self.tool in DRAG_LINE_TOOLS:
            if info:
                self._drag_start_scene = scene_pos
                self._drag_start_info = info
                pen = QPen(QColor.fromRgbF(*self.tool_options.stroke_color))
                pen.setWidthF(max(1.0, self.tool_options.line_width))
                self._line_preview = QGraphicsLineItem(QLineF(scene_pos, scene_pos))
                self._line_preview.setPen(pen)
                self._line_preview.setZValue(950)
                self.scene().addItem(self._line_preview)
            return

        if self.tool == Tool.INK:
            if info:
                self._ink_page = info[0]
                self._ink_scene_points = [scene_pos]
                pen = QPen(QColor.fromRgbF(*self.tool_options.stroke_color))
                pen.setWidthF(max(1.0, self.tool_options.line_width))
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
                self._ink_path_item = QGraphicsPathItem()
                self._ink_path_item.setPen(pen)
                path = QPainterPath(scene_pos)
                self._ink_path_item.setPath(path)
                self._ink_path_item.setZValue(950)
                self.scene().addItem(self._ink_path_item)
            return

        if self.tool in DRAG_RECT_TOOLS:
            if info:
                self._drag_start_scene = scene_pos
                self._drag_start_info = info
                pen = QPen(QColor(SELECTION_COLOR))
                pen.setStyle(Qt.DashLine)
                pen.setWidth(2)
                self._rubber_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
                self._rubber_item.setPen(pen)
                self._rubber_item.setBrush(QBrush(QColor(211, 164, 76, 45)))
                self._rubber_item.setZValue(950)
                self.scene().addItem(self._rubber_item)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())

        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            return

        if self._drag_mode and self._selection is not None:
            self._update_selection_drag(scene_pos)
            return

        if self._rubber_item is not None and self._drag_start_scene is not None:
            self._rubber_item.setRect(QRectF(self._drag_start_scene, scene_pos).normalized())
            return

        if self._line_preview is not None and self._drag_start_scene is not None:
            self._line_preview.setLine(QLineF(self._drag_start_scene, scene_pos))
            return

        if self._ink_path_item is not None and self._ink_scene_points is not None:
            self._ink_scene_points.append(scene_pos)
            path = self._ink_path_item.path()
            path.lineTo(scene_pos)
            self._ink_path_item.setPath(path)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.viewport().setCursor(QCursor(self._CURSORS.get(self.tool, Qt.ArrowCursor)))
            return

        if self._drag_mode and self._selection is not None:
            self._commit_selection_transform()
            self._drag_mode = None
            self._drag_anchor_scene = None
            self._drag_orig_rect_scene = None
            return

        if self._rubber_item is not None:
            rect_scene = self._rubber_item.rect()
            page_idx = self._drag_start_info[0] if self._drag_start_info else None
            self._remove_item_safely(self._rubber_item)
            self._rubber_item = None
            self._drag_start_scene = None
            self._drag_start_info = None
            if page_idx is not None:
                self._commit_drag_tool(page_idx, rect_scene)
            return

        if self._line_preview is not None:
            end_scene = self.mapToScene(event.pos())
            start_scene = self._drag_start_scene
            page_idx = self._drag_start_info[0] if self._drag_start_info else None
            self._remove_item_safely(self._line_preview)
            self._line_preview = None
            self._drag_start_scene = None
            self._drag_start_info = None
            if page_idx is not None and start_scene is not None:
                self._commit_line(page_idx, start_scene, end_scene)
            return

        if self._ink_path_item is not None:
            self._commit_ink()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.tool == Tool.SELECT and self._selection is not None:
            sel = self._selection
            if sel["kind"] == "annot" and sel["type"] == "FreeText":
                self._edit_freetext(sel)
                return
            if sel["kind"] == "image":
                self.replace_selected_image()
                return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self._selection is not None:
            self.delete_selection()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _remove_item_safely(item):
        if item is None or item.scene() is None:
            return
        try:
            item.scene().removeItem(item)
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    # Confirmação das ferramentas de desenho
    # ------------------------------------------------------------------

    def _commit_drag_tool(self, page_idx: int, rect_scene: QRectF):
        if rect_scene.width() < 3 and rect_scene.height() < 3:
            return
        pdf_rect = self._scene_rect_to_pdf(page_idx, rect_scene)
        if pdf_rect[2] - pdf_rect[0] < 1 and pdf_rect[3] - pdf_rect[1] < 1:
            return
        opts = self.tool_options

        if self.tool == Tool.HIGHLIGHT:
            self.document.add_highlight(page_idx, pdf_rect, color=opts.highlight_color)
        elif self.tool == Tool.RECT:
            self.document.add_rect(page_idx, pdf_rect, stroke=opts.stroke_color, fill=opts.fill_color, width=opts.line_width)
        elif self.tool == Tool.ELLIPSE:
            self.document.add_ellipse(page_idx, pdf_rect, stroke=opts.stroke_color, fill=opts.fill_color, width=opts.line_width)
        elif self.tool == Tool.ERASER:
            self.document.erase_area(page_idx, pdf_rect)
        elif self.tool == Tool.ADD_TEXT:
            self._start_add_text(page_idx, pdf_rect)
        elif self.tool == Tool.IMAGE:
            self._pick_and_insert_image(page_idx, pdf_rect)

    def _commit_line(self, page_idx: int, start_scene: QPointF, end_scene: QPointF):
        item = self._page_items[page_idx]
        p1 = item.mapFromScene(start_scene)
        p2 = item.mapFromScene(end_scene)
        if (p1 - p2).manhattanLength() < 3:
            return
        pdf_p1 = (p1.x() / self.zoom, p1.y() / self.zoom)
        pdf_p2 = (p2.x() / self.zoom, p2.y() / self.zoom)
        opts = self.tool_options
        self.document.add_line(page_idx, pdf_p1, pdf_p2, stroke=opts.stroke_color, width=opts.line_width, arrow=(self.tool == Tool.ARROW))

    def _commit_ink(self):
        page_idx = self._ink_page
        points = self._ink_scene_points or []
        self._remove_item_safely(self._ink_path_item)
        self._ink_path_item = None
        self._ink_scene_points = None
        self._ink_page = None
        if page_idx is None or len(points) < 2:
            return
        item = self._page_items[page_idx]
        pdf_points = []
        for sp in points:
            local = item.mapFromScene(sp)
            pdf_points.append((local.x() / self.zoom, local.y() / self.zoom))
        opts = self.tool_options
        self.document.add_ink(page_idx, [pdf_points], color=opts.stroke_color, width=opts.line_width)

    def _commit_note(self, page_idx: int, pdf_pt: tuple):
        self.document.add_note(page_idx, pdf_pt, "")

    # ------------------------------------------------------------------
    # Edição de texto (inline)
    # ------------------------------------------------------------------

    def _open_inline_editor(self, page_idx, bbox, initial_text, font_px, color_rgb, on_commit):
        rect_scene = self._pdf_rect_to_scene(page_idx, bbox)
        editor = InlineTextEdit(initial_text)
        font = QFont()
        font.setPixelSize(max(9, int(font_px)))
        editor.setFont(font)
        color = QColor.fromRgbF(*color_rgb)
        editor.setStyleSheet(
            f"QTextEdit {{ background: #ffffff; color: {color.name()}; "
            f"border: 2px solid {SELECTION_COLOR}; padding: 1px; }}"
        )
        proxy = self.scene().addWidget(editor)
        proxy.setZValue(1000)
        proxy.setPos(rect_scene.topLeft())
        width = max(rect_scene.width() + 20, 80)
        height = max(rect_scene.height() + 10, font.pixelSize() + 16)
        proxy.resize(width, height)
        editor.setFocus()

        def finish(text):
            self._remove_item_safely(proxy)
            editor.deleteLater()
            on_commit(text)

        def cancel():
            self._remove_item_safely(proxy)
            editor.deleteLater()

        editor.committed.connect(finish)
        editor.cancelled.connect(cancel)

    def _start_edit_text(self, page_idx: int, pdf_pt: tuple):
        px, py = pdf_pt
        target = None
        for span in self.document.text_spans(page_idx):
            x0, y0, x1, y1 = span.bbox
            if x0 - 2 <= px <= x1 + 2 and y0 - 2 <= py <= y1 + 2:
                target = span
        if target is None:
            self.statusMessage.emit("Nenhum texto encontrado neste ponto.")
            return

        color = self._rgb_from_int(target.color)

        def commit(text):
            if text != target.text:
                self.document.replace_text(target, text)

        self._open_inline_editor(page_idx, target.bbox, target.text, target.size * self.zoom, color, commit)

    def _start_add_text(self, page_idx: int, pdf_rect: tuple):
        opts = self.tool_options

        def commit(text):
            if text.strip():
                self.document.add_freetext(
                    page_idx, pdf_rect, text, fontsize=opts.font_size,
                    color=opts.font_color, fontname=opts.font_family,
                )

        self._open_inline_editor(page_idx, pdf_rect, "", opts.font_size * self.zoom, opts.font_color, commit)

    def _edit_freetext(self, sel: dict):
        def commit(text):
            self.document.update_annot(sel["page"], sel["xref"], text=text)

        self._open_inline_editor(sel["page"], sel["pdf_rect"], sel.get("content", ""), 13 * self.zoom, (0, 0, 0), commit)

    @staticmethod
    def _rgb_from_int(color_int: int) -> tuple:
        if not color_int:
            return (0.0, 0.0, 0.0)
        r = ((color_int >> 16) & 255) / 255.0
        g = ((color_int >> 8) & 255) / 255.0
        b = (color_int & 255) / 255.0
        return (r, g, b)

    # ------------------------------------------------------------------
    # Imagens
    # ------------------------------------------------------------------

    def _pick_and_insert_image(self, page_idx: int, pdf_rect: tuple):
        path, _ = QFileDialog.getOpenFileName(
            self, "Inserir imagem", "", "Imagens (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if not path:
            return
        self.document.insert_image(page_idx, pdf_rect, path)

    def replace_selected_image(self):
        if not self._selection or self._selection["kind"] != "image":
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Substituir imagem", "", "Imagens (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if not path:
            return
        sel = self._selection
        img = ImageInfo(page=sel["page"], bbox=sel["pdf_rect"], xref=sel["xref"], width=0, height=0)
        self.document.replace_image(img, path)
        self._clear_selection()

    # ------------------------------------------------------------------
    # Ferramenta Selecionar
    # ------------------------------------------------------------------

    def _handle_select_press(self, scene_pos: QPointF):
        if self._selection is not None:
            if self._resize_handle_item is not None and self._resize_handle_item.contains(
                self._resize_handle_item.mapFromScene(scene_pos)
            ):
                self._drag_mode = "resize"
                self._drag_anchor_scene = scene_pos
                self._drag_orig_rect_scene = QRectF(self._selection["rect"])
                return
            if self._selection_item is not None and self._selection_item.contains(
                self._selection_item.mapFromScene(scene_pos)
            ):
                self._drag_mode = "move"
                self._drag_anchor_scene = scene_pos
                self._drag_orig_rect_scene = QRectF(self._selection["rect"])
                return

        info = self._scene_to_pdf(scene_pos)
        if info is None:
            self._clear_selection()
            return
        hit = self._hit_test(*info)
        if hit is None:
            self._clear_selection()
        else:
            self._select(hit)

    def _hit_test(self, page_idx: int, pdf_pt: tuple):
        px, py = pdf_pt
        for a in reversed(self.document.list_annots(page_idx)):
            x0, y0, x1, y1 = a.rect
            if x0 - 2 <= px <= x1 + 2 and y0 - 2 <= py <= y1 + 2:
                return {"kind": "annot", "page": page_idx, "xref": a.xref, "type": a.type,
                        "content": a.content, "pdf_rect": a.rect}
        for img in reversed(self.document.images(page_idx)):
            x0, y0, x1, y1 = img.bbox
            if x0 <= px <= x1 and y0 <= py <= y1:
                return {"kind": "image", "page": page_idx, "xref": img.xref, "pdf_rect": img.bbox}
        return None

    def _select(self, hit: dict):
        self._clear_selection()
        page_idx = hit["page"]
        rect_scene = self._pdf_rect_to_scene(page_idx, hit["pdf_rect"])

        pen = QPen(QColor(SELECTION_COLOR))
        pen.setStyle(Qt.DashLine)
        pen.setWidth(2)
        item = QGraphicsRectItem(rect_scene)
        item.setPen(pen)
        item.setBrush(Qt.NoBrush)
        item.setZValue(900)
        self.scene().addItem(item)

        handle = QGraphicsRectItem(rect_scene.right() - 6, rect_scene.bottom() - 6, 12, 12)
        handle.setPen(QPen(QColor("#1a1d24")))
        handle.setBrush(QBrush(QColor(SELECTION_COLOR)))
        handle.setZValue(901)
        self.scene().addItem(handle)

        self._selection = {**hit, "rect": rect_scene}
        self._selection_item = item
        self._resize_handle_item = handle
        self.selectionChanged.emit(hit)

    def _clear_selection(self):
        self._remove_item_safely(self._selection_item)
        self._remove_item_safely(self._resize_handle_item)
        self._selection_item = None
        self._resize_handle_item = None
        had_selection = self._selection is not None
        self._selection = None
        if had_selection:
            self.selectionChanged.emit(None)

    def _update_selection_drag(self, scene_pos: QPointF):
        delta = scene_pos - self._drag_anchor_scene
        if self._drag_mode == "move":
            new_rect = self._drag_orig_rect_scene.translated(delta)
        else:
            br = self._drag_orig_rect_scene.bottomRight() + delta
            min_x = self._drag_orig_rect_scene.left() + 12
            min_y = self._drag_orig_rect_scene.top() + 12
            new_rect = QRectF(self._drag_orig_rect_scene.topLeft(), QPointF(max(min_x, br.x()), max(min_y, br.y())))
        self._selection_item.setRect(new_rect)
        self._resize_handle_item.setRect(new_rect.right() - 6, new_rect.bottom() - 6, 12, 12)
        self._selection["rect"] = new_rect

    def _commit_selection_transform(self):
        sel = self._selection
        if sel is None:
            return
        page_idx = sel["page"]
        new_pdf_rect = self._scene_rect_to_pdf(page_idx, sel["rect"])
        if sel["kind"] == "annot":
            self.document.update_annot(page_idx, sel["xref"], rect=new_pdf_rect)
        else:
            try:
                img_bytes = self.document.extract_image_bytes(sel["xref"])
            except Exception:
                img_bytes = None
            old_img = ImageInfo(page=page_idx, bbox=sel["pdf_rect"], xref=sel["xref"], width=0, height=0)
            self.document.delete_image(old_img)
            if img_bytes:
                self.document.insert_image(page_idx, new_pdf_rect, img_bytes)
        self._clear_selection()

    def delete_selection(self):
        if self._selection is None:
            return
        sel = self._selection
        if sel["kind"] == "annot":
            self.document.delete_annot(sel["page"], sel["xref"])
        else:
            img = ImageInfo(page=sel["page"], bbox=sel["pdf_rect"], xref=sel["xref"], width=0, height=0)
            self.document.delete_image(img)
        self._clear_selection()

    # ------------------------------------------------------------------
    # Busca de texto
    # ------------------------------------------------------------------

    def search(self, query: str) -> int:
        self.clear_search()
        if not query:
            return 0
        self._search_results = self.document.search(query)
        for page_idx, rect in self._search_results:
            rect_scene = self._pdf_rect_to_scene(page_idx, rect)
            marker = QGraphicsRectItem(rect_scene)
            marker.setBrush(QBrush(QColor(255, 213, 79, 110)))
            marker.setPen(QPen(Qt.NoPen))
            marker.setZValue(500)
            self.scene().addItem(marker)
            self._search_markers.append(marker)
        self._search_index = -1
        if self._search_results:
            self.next_search_result()
        return len(self._search_results)

    def next_search_result(self):
        if not self._search_results:
            return
        self._search_index = (self._search_index + 1) % len(self._search_results)
        self._focus_search_result()

    def prev_search_result(self):
        if not self._search_results:
            return
        self._search_index = (self._search_index - 1) % len(self._search_results)
        self._focus_search_result()

    def _focus_search_result(self):
        page_idx, rect = self._search_results[self._search_index]
        rect_scene = self._pdf_rect_to_scene(page_idx, rect)
        self.centerOn(rect_scene.center())
        marker = self._search_markers[self._search_index]
        marker.setBrush(QBrush(QColor(255, 140, 0, 180)))
        QTimer.singleShot(500, lambda m=marker: self._reset_marker_color(m))

    @staticmethod
    def _reset_marker_color(marker):
        try:
            marker.setBrush(QBrush(QColor(255, 213, 79, 110)))
        except RuntimeError:
            pass

    def clear_search(self):
        for m in self._search_markers:
            self._remove_item_safely(m)
        self._search_markers = []
        self._search_results = []
        self._search_index = -1


def print_document(document: PdfDocument, printer) -> bool:
    """Imprime todas as páginas do documento no `QPrinter` fornecido."""
    from PySide6.QtGui import QPainter as _QPainter

    painter = _QPainter()
    if not painter.begin(printer):
        return False
    try:
        page_rect = printer.pageRect(printer.Unit.DevicePixel)
    except Exception:
        page_rect = QRectF(0, 0, printer.width(), printer.height())

    first = True
    for i in range(document.page_count):
        if not first:
            if not printer.newPage():
                break
        first = False
        dpi = printer.resolution() or 150
        zoom = max(0.3, min(6.0, dpi / 72.0))
        img: QImage = document.render_page(i, zoom=zoom)
        if img.width() == 0 or img.height() == 0:
            continue
        scale = min(page_rect.width() / img.width(), page_rect.height() / img.height())
        draw_w = img.width() * scale
        draw_h = img.height() * scale
        x = page_rect.x() + (page_rect.width() - draw_w) / 2
        y = page_rect.y() + (page_rect.height() - draw_h) / 2
        painter.drawImage(QRectF(x, y, draw_w, draw_h), img)
    painter.end()
    return True
