"""
Núcleo de domínio do Fólio Studio.

Envolve um `fitz.Document` (PyMuPDF) e expõe uma API de alto nível para
leitura, renderização e edição real de conteúdo de PDF: texto, imagens,
anotações/formas, páginas, metadados e sumário — com histórico de
desfazer/refazer baseado em snapshots binários do documento.

Regra importante ao mexer neste arquivo: objetos `fitz.Page` e `fitz.Annot`
ficam inválidos assim que a estrutura do documento muda (inserir/excluir
página, reordenar, undo/redo). Por isso nunca guardamos esses objetos —
sempre buscamos `self._doc[index]` (e o annot pelo `xref`) no momento do uso.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Union

import fitz  # PyMuPDF
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

PathOrBytes = Union[str, bytes, bytearray]


# --------------------------------------------------------------------------
# Estruturas de dados imutáveis (snapshots seguros para guardar entre chamadas)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class TextSpan:
    """Um trecho de texto (linha de uma mesma fonte/tamanho) numa página."""

    page: int
    bbox: tuple
    text: str
    font: str
    size: float
    color: int
    origin: tuple
    flags: int = 0


@dataclass(frozen=True)
class TextBlock:
    """Um parágrafo inteiro (bloco de linhas), a unidade usada para editar
    texto existente. Reaproveita o agrupamento em blocos que o próprio
    PyMuPDF já faz na extração de texto."""

    page: int
    bbox: tuple
    text: str
    font: str
    size: float
    color: int
    flags: int = 0
    from_ocr: bool = False


@dataclass(frozen=True)
class ImageInfo:
    """Uma imagem inserida numa página."""

    page: int
    bbox: tuple
    xref: int
    width: int
    height: int


@dataclass(frozen=True)
class AnnotInfo:
    """Uma anotação (realce, forma, texto livre, tinta, nota...) numa página."""

    page: int
    xref: int
    type: str
    rect: tuple
    content: str = ""


# --------------------------------------------------------------------------
# Utilitários de fonte / cor
# --------------------------------------------------------------------------

_BASE14 = {
    ("sans", False, False): "helv",
    ("sans", True, False): "hebo",
    ("sans", False, True): "heit",
    ("sans", True, True): "hebi",
    ("serif", False, False): "tiro",
    ("serif", True, False): "tibo",
    ("serif", False, True): "tiit",
    ("serif", True, True): "tibi",
    ("mono", False, False): "cour",
    ("mono", True, False): "cobo",
    ("mono", False, True): "coit",
    ("mono", True, True): "cobi",
}


def rgb_from_int(color_int: Optional[int]) -> tuple:
    """Converte a cor empacotada (sRGB inteiro) do PyMuPDF em (r, g, b) 0..1."""
    if not color_int:
        return (0.0, 0.0, 0.0)
    r = ((color_int >> 16) & 255) / 255.0
    g = ((color_int >> 8) & 255) / 255.0
    b = (color_int & 255) / 255.0
    return (r, g, b)


def int_from_rgb(rgb: tuple) -> int:
    r, g, b = (max(0, min(255, round(c * 255))) for c in rgb)
    return (r << 16) | (g << 8) | b


def pick_base_font(font_name: str, flags: int = 0) -> str:
    """Escolhe a fonte padrão (Base-14) mais próxima de uma fonte original."""
    name = (font_name or "").lower()
    bold = bool(flags & 16) or any(k in name for k in ("bold", "black", "heavy", "semibold"))
    italic = bool(flags & 2) or any(k in name for k in ("italic", "oblique"))
    mono = bool(flags & 8) or any(k in name for k in ("mono", "courier", "consolas", "menlo"))
    serif = bool(flags & 4) or any(
        k in name for k in ("times", "georgia", "serif", "garamond", "cambria", "minion", "palatino")
    )
    family = "mono" if mono else ("serif" if serif else "sans")
    return _BASE14[(family, bold, italic)]


def _extract_embedded_font(doc: "fitz.Document", page: "fitz.Page", font_name: str):
    """Tenta recuperar os bytes originais de uma fonte incorporada no PDF."""
    try:
        for xref, ext, _ftype, basefont, name, *_ in page.get_fonts(full=True):
            if not ext or ext == "n/a":
                continue
            if name == font_name or basefont == font_name:
                extracted = doc.extract_font(xref)
                buf = extracted[-1] if extracted else None
                if buf:
                    return buf, ext
    except Exception:
        pass
    return None, None


# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------

class PdfDocument(QObject):
    """Wrapper de alto nível sobre um documento PDF, com desfazer/refazer."""

    MAX_UNDO = 40

    changed = Signal()               # conteúdo/estrutura do documento mudou
    modified_changed = Signal(bool)  # estado "tem alterações não salvas" mudou

    def __init__(self, path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._doc: fitz.Document = fitz.open(path) if path else fitz.open()
        self.path: Optional[str] = path
        self._undo_stack: list[bytes] = []
        self._redo_stack: list[bytes] = []
        self._modified = False
        self.custom_title: Optional[str] = None

    # -- ciclo de vida -----------------------------------------------------

    @classmethod
    def new(cls, parent=None) -> "PdfDocument":
        return cls(path=None, parent=parent)

    @classmethod
    def open(cls, path: str, parent=None) -> "PdfDocument":
        return cls(path=path, parent=parent)

    def close(self):
        try:
            self._doc.close()
        except Exception:
            pass

    @property
    def is_new(self) -> bool:
        return self.path is None

    @property
    def modified(self) -> bool:
        return self._modified

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def __len__(self) -> int:
        return self.page_count

    @property
    def is_encrypted(self) -> bool:
        return bool(self._doc.is_encrypted)

    def authenticate(self, password: str) -> bool:
        ok = bool(self._doc.authenticate(password))
        if ok:
            self.changed.emit()
        return ok

    # -- persistência --------------------------------------------------

    def save(self, path: Optional[str] = None) -> bool:
        target = path or self.path
        if not target:
            return False
        data = self._doc.tobytes(garbage=4, deflate=True)
        with open(target, "wb") as fh:
            fh.write(data)
        self.path = target
        self._set_modified(False)
        return True

    def export_copy(self, path: str) -> str:
        data = self._doc.tobytes(garbage=4, deflate=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    # -- desfazer / refazer --------------------------------------------

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def _snapshot(self) -> Optional[bytes]:
        """Serializa o documento atual; None representa um documento vazio
        (0 páginas), estado que o PyMuPDF não consegue serializar."""
        if self._doc.page_count == 0:
            return None
        try:
            return self._doc.tobytes(garbage=0, deflate=False)
        except Exception:
            return self._doc.tobytes()

    @staticmethod
    def _restore(snapshot: Optional[bytes]) -> "fitz.Document":
        if snapshot is None:
            return fitz.open()
        return fitz.open(stream=snapshot, filetype="pdf")

    def _push_undo(self):
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        current = self._snapshot()
        previous = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._doc.close()
        self._doc = self._restore(previous)
        self._set_modified(True)
        self.changed.emit()
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        current = self._snapshot()
        nxt = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._doc.close()
        self._doc = self._restore(nxt)
        self._set_modified(True)
        self.changed.emit()
        return True

    def _mark_modified(self):
        self._set_modified(True)
        self.changed.emit()

    def _set_modified(self, value: bool):
        if self._modified != value:
            self._modified = value
            self.modified_changed.emit(value)

    # -- renderização -----------------------------------------------------

    def page_size(self, index: int) -> tuple:
        r = self._doc[index].bound()
        return (r.width, r.height)

    def render_page(self, index: int, zoom: float = 1.0) -> QImage:
        page = self._doc[index]
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        return img.copy()

    def thumbnail(self, index: int, max_dim: int = 170) -> QImage:
        w, h = self.page_size(index)
        scale = max_dim / max(w, h, 1.0)
        return self.render_page(index, zoom=scale)

    # -- texto --------------------------------------------------------------

    def text_spans(self, index: int) -> list[TextSpan]:
        page = self._doc[index]
        raw = page.get_text("dict")
        spans: list[TextSpan] = []
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    bbox = tuple(span["bbox"])
                    origin = tuple(span.get("origin", (bbox[0], bbox[3])))
                    spans.append(
                        TextSpan(
                            page=index,
                            bbox=bbox,
                            text=text,
                            font=span.get("font", ""),
                            size=float(span.get("size", 12.0)),
                            color=int(span.get("color", 0)),
                            origin=origin,
                            flags=int(span.get("flags", 0)),
                        )
                    )
        return spans

    def full_text(self, index: Optional[int] = None) -> str:
        if index is not None:
            return self._doc[index].get_text("text")
        return "\n".join(self._doc[i].get_text("text") for i in range(self.page_count))

    def replace_text(self, span: TextSpan, new_text: str, bg_color: tuple = (1, 1, 1)) -> bool:
        """Substitui um trecho de texto existente (apaga + reescreve no lugar)."""
        self._push_undo()
        page = self._doc[span.page]
        rect = fitz.Rect(span.bbox)
        self._redact(page, rect, fill=bg_color)

        color = rgb_from_int(span.color)
        fontsize = span.size
        fontbuffer, _ext = _extract_embedded_font(self._doc, page, span.font)
        fontname = None
        if fontbuffer:
            try:
                alias = f"FS{abs(hash((span.font, span.page))) % 1_000_000}"
                page.insert_font(fontname=alias, fontbuffer=fontbuffer)
                fontname = alias
            except Exception:
                fontname = None
        if not fontname:
            fontname = pick_base_font(span.font, span.flags)

        try:
            needed = fitz.get_text_length(new_text, fontname=fontname, fontsize=fontsize)
            available = rect.width * 1.02
            if needed > available > 0:
                fontsize = max(6.0, fontsize * (available / needed))
        except Exception:
            pass

        try:
            page.insert_text(span.origin, new_text, fontsize=fontsize, fontname=fontname, color=color)
        except Exception:
            fallback = pick_base_font(span.font, span.flags)
            page.insert_text(span.origin, new_text, fontsize=span.size, fontname=fallback, color=color)

        self._mark_modified()
        return True

    def _blocks_from_dict(self, index: int, raw: dict, from_ocr: bool = False) -> list["TextBlock"]:
        blocks: list[TextBlock] = []
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            lines_text = []
            dominant = None
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(s.get("text", "") for s in spans)
                if line_text.strip():
                    lines_text.append(line_text)
                if dominant is None:
                    for s in spans:
                        if s.get("text", "").strip():
                            dominant = s
                            break
            text = "\n".join(lines_text)
            if not text.strip() or dominant is None:
                continue
            blocks.append(
                TextBlock(
                    page=index,
                    bbox=tuple(block["bbox"]),
                    text=text,
                    font=dominant.get("font", ""),
                    size=float(dominant.get("size", 12.0)),
                    color=int(dominant.get("color", 0)),
                    flags=int(dominant.get("flags", 0)),
                    from_ocr=from_ocr,
                )
            )
        return blocks

    def text_blocks(self, index: int) -> list[TextBlock]:
        """Parágrafos editáveis de uma página (unidade usada pela ferramenta
        'Editar texto': clicar em qualquer linha de um parágrafo permite
        reescrever o parágrafo inteiro de uma vez)."""
        page = self._doc[index]
        raw = page.get_text("dict")
        return self._blocks_from_dict(index, raw)

    def replace_text_block(self, block: TextBlock, new_text: str, bg_color: tuple = (1, 1, 1)) -> bool:
        """Substitui um parágrafo inteiro (apaga a área e reescreve, com
        quebra de linha automática dentro dos limites originais)."""
        self._push_undo()
        page = self._doc[block.page]
        rect = fitz.Rect(block.bbox)
        self._redact(page, rect, fill=bg_color)

        color = rgb_from_int(block.color)
        fontbuffer, _ext = _extract_embedded_font(self._doc, page, block.font)
        fontname = None
        if fontbuffer:
            try:
                alias = f"FSB{abs(hash((block.font, block.page))) % 1_000_000}"
                page.insert_font(fontname=alias, fontbuffer=fontbuffer)
                fontname = alias
            except Exception:
                fontname = None
        if not fontname:
            fontname = pick_base_font(block.font, block.flags)

        text = new_text if new_text.strip() else ""
        if text:
            fontsize = block.size
            for _ in range(8):
                overflow = page.insert_textbox(rect, text, fontsize=fontsize, fontname=fontname, color=color)
                if overflow >= 0:
                    break
                fontsize = max(5.0, fontsize * 0.9)
            else:
                # última tentativa, no menor tamanho, aceitando corte se necessário
                page.insert_textbox(rect, text, fontsize=fontsize, fontname=fontname, color=color)

        self._mark_modified()
        return True

    def is_scanned_page(self, index: int) -> bool:
        """Heurística: página sem texto pesquisável mas com imagem — indício
        de página digitalizada, candidata a OCR."""
        page = self._doc[index]
        if page.get_text("text").strip():
            return False
        return bool(page.get_image_info())

    def ocr_text_blocks(self, index: int, language: str = "por+eng", dpi: int = 300) -> list[TextBlock]:
        """Reconhece o texto de uma página digitalizada via OCR (Tesseract) e
        devolve parágrafos editáveis nas mesmas coordenadas da página real.

        Não requer Tesseract instalado para o restante do programa funcionar;
        apenas esta função levanta RuntimeError se ele não estiver disponível.
        """
        page = self._doc[index]
        textpage = page.get_textpage_ocr(flags=0, language=language, dpi=dpi, full=True)
        raw = page.get_text("dict", textpage=textpage)
        return self._blocks_from_dict(index, raw, from_ocr=True)

    def search(self, query: str, page_index: Optional[int] = None) -> list[tuple]:
        results = []
        indices = [page_index] if page_index is not None else range(self.page_count)
        for i in indices:
            page = self._doc[i]
            for r in page.search_for(query):
                results.append((i, tuple(r)))
        return results

    # -- imagens --------------------------------------------------------------

    def images(self, index: int) -> list[ImageInfo]:
        page = self._doc[index]
        out = []
        for info in page.get_image_info(xrefs=True):
            out.append(
                ImageInfo(
                    page=index,
                    bbox=tuple(info["bbox"]),
                    xref=int(info.get("xref") or 0),
                    width=int(info.get("width", 0)),
                    height=int(info.get("height", 0)),
                )
            )
        return out

    def insert_image(self, index: int, rect: tuple, image_source: PathOrBytes):
        self._push_undo()
        page = self._doc[index]
        self._insert_image_raw(page, fitz.Rect(rect), image_source)
        self._mark_modified()

    def replace_image(self, img: ImageInfo, image_source: PathOrBytes):
        self._push_undo()
        page = self._doc[img.page]
        rect = fitz.Rect(img.bbox)
        self._redact(page, rect)
        self._insert_image_raw(page, rect, image_source)
        self._mark_modified()

    def delete_image(self, img: ImageInfo):
        self._push_undo()
        page = self._doc[img.page]
        self._redact(page, fitz.Rect(img.bbox))
        self._mark_modified()

    def extract_image_bytes(self, xref: int) -> bytes:
        return self._doc.extract_image(xref)["image"]

    def erase_area(self, index: int, rect: tuple, fill: tuple = (1, 1, 1)):
        """Ferramenta 'borracha': apaga permanentemente qualquer conteúdo na área."""
        self._push_undo()
        page = self._doc[index]
        self._redact(page, fitz.Rect(rect), fill=fill)
        self._mark_modified()

    @staticmethod
    def _redact(page: "fitz.Page", rect: "fitz.Rect", fill: tuple = (1, 1, 1)):
        page.add_redact_annot(rect, fill=fill)
        page.apply_redactions()

    @staticmethod
    def _insert_image_raw(page: "fitz.Page", rect: "fitz.Rect", image_source: PathOrBytes):
        if isinstance(image_source, (bytes, bytearray)):
            page.insert_image(rect, stream=bytes(image_source))
        else:
            page.insert_image(rect, filename=str(image_source))

    # -- anotações / formas ---------------------------------------------------

    def list_annots(self, index: int) -> list[AnnotInfo]:
        page = self._doc[index]
        out = []
        for a in page.annots() or []:
            out.append(
                AnnotInfo(
                    page=index,
                    xref=a.xref,
                    type=a.type[1],
                    rect=tuple(a.rect),
                    content=a.info.get("content", "") if a.info else "",
                )
            )
        return out

    def _find_annot(self, page: "fitz.Page", xref: int):
        for a in page.annots() or []:
            if a.xref == xref:
                return a
        return None

    def add_highlight(self, index: int, rect: tuple, color: tuple = (1.0, 0.92, 0.23)) -> int:
        self._push_undo()
        page = self._doc[index]
        target_rect = fitz.Rect(rect)
        words = page.get_text("words")
        quads = [
            fitz.Rect(w[0], w[1], w[2], w[3])
            for w in words
            if fitz.Rect(w[0], w[1], w[2], w[3]).intersects(target_rect)
        ]
        annot = page.add_highlight_annot(quads if quads else [target_rect])
        annot.set_colors(stroke=color)
        annot.update()
        self._mark_modified()
        return annot.xref

    def add_rect(self, index: int, rect: tuple, stroke=(0.1, 0.1, 0.1), fill=None, width: float = 1.5) -> int:
        self._push_undo()
        page = self._doc[index]
        annot = page.add_rect_annot(fitz.Rect(rect))
        annot.set_colors(stroke=stroke, fill=fill)
        annot.set_border(width=width)
        annot.update()
        self._mark_modified()
        return annot.xref

    def add_ellipse(self, index: int, rect: tuple, stroke=(0.1, 0.1, 0.1), fill=None, width: float = 1.5) -> int:
        self._push_undo()
        page = self._doc[index]
        annot = page.add_circle_annot(fitz.Rect(rect))
        annot.set_colors(stroke=stroke, fill=fill)
        annot.set_border(width=width)
        annot.update()
        self._mark_modified()
        return annot.xref

    def add_line(self, index: int, p1: tuple, p2: tuple, stroke=(0.1, 0.1, 0.1), width: float = 1.5, arrow: bool = False) -> int:
        self._push_undo()
        page = self._doc[index]
        annot = page.add_line_annot(p1, p2)
        annot.set_colors(stroke=stroke)
        annot.set_border(width=width)
        if arrow:
            annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
        annot.update()
        self._mark_modified()
        return annot.xref

    def add_ink(self, index: int, strokes: Sequence[Sequence[tuple]], color=(0.1, 0.1, 0.1), width: float = 2.0) -> int:
        self._push_undo()
        page = self._doc[index]
        annot = page.add_ink_annot(list(strokes))
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        annot.update()
        self._mark_modified()
        return annot.xref

    def add_note(self, index: int, point: tuple, text: str = "") -> int:
        self._push_undo()
        page = self._doc[index]
        annot = page.add_text_annot(point, text)
        annot.update()
        self._mark_modified()
        return annot.xref

    def add_freetext(
        self,
        index: int,
        rect: tuple,
        text: str,
        fontsize: float = 12.0,
        color: tuple = (0, 0, 0),
        fontname: str = "helv",
        fill: Optional[tuple] = None,
        align: int = 0,
    ) -> int:
        self._push_undo()
        page = self._doc[index]
        annot = page.add_freetext_annot(
            fitz.Rect(rect), text, fontsize=fontsize, fontname=fontname,
            text_color=color, fill_color=fill, align=align,
        )
        annot.update()
        self._mark_modified()
        return annot.xref

    def update_annot(self, index: int, xref: int, text: Optional[str] = None, rect: Optional[tuple] = None) -> bool:
        self._push_undo()
        page = self._doc[index]
        annot = self._find_annot(page, xref)
        if annot is None:
            self._undo_stack.pop()
            return False
        if rect is not None:
            annot.set_rect(fitz.Rect(rect))
        if text is not None:
            annot.set_info(content=text)
        annot.update()
        self._mark_modified()
        return True

    def delete_annot(self, index: int, xref: int) -> bool:
        self._push_undo()
        page = self._doc[index]
        annot = self._find_annot(page, xref)
        if annot is None:
            self._undo_stack.pop()
            return False
        page.delete_annot(annot)
        self._mark_modified()
        return True

    # -- páginas --------------------------------------------------------------

    def insert_blank_page(self, index: Optional[int] = None, width: float = 595.0, height: float = 842.0):
        self._push_undo()
        pos = self.page_count if index is None else index
        self._doc.new_page(pos, width=width, height=height)
        self._mark_modified()

    def delete_pages(self, indices: Iterable[int]):
        self._push_undo()
        for i in sorted(set(indices), reverse=True):
            self._doc.delete_page(i)
        self._mark_modified()

    def duplicate_page(self, index: int):
        self._push_undo()
        self._doc.copy_page(index, index + 1)
        self._mark_modified()

    def rotate_page(self, index: int, delta: int = 90):
        self._push_undo()
        page = self._doc[index]
        page.set_rotation((page.rotation + delta) % 360)
        self._mark_modified()

    def reorder_pages(self, new_order: Sequence[int]):
        self._push_undo()
        self._doc.select(list(new_order))
        self._mark_modified()

    def move_page(self, src: int, dst: int):
        order = list(range(self.page_count))
        order.insert(dst, order.pop(src))
        self._push_undo()
        self._doc.select(order)
        self._mark_modified()

    def extract_pages(self, indices: Sequence[int], path: Optional[str] = None):
        sub = fitz.open()
        for i in indices:
            sub.insert_pdf(self._doc, from_page=i, to_page=i)
        if path:
            sub.save(path, garbage=4, deflate=True)
            sub.close()
            return path
        data = sub.tobytes(garbage=4, deflate=True)
        sub.close()
        return data

    def split_document(self, ranges: Sequence[tuple]) -> list[bytes]:
        results = []
        for start, end in ranges:
            sub = fitz.open()
            sub.insert_pdf(self._doc, from_page=start, to_page=end)
            results.append(sub.tobytes(garbage=4, deflate=True))
            sub.close()
        return results

    def merge_document(self, source: Union[str, bytes, bytearray, "fitz.Document"], at_index: Optional[int] = None):
        self._push_undo()
        close_after = False
        if isinstance(source, fitz.Document):
            src_doc = source
        elif isinstance(source, (bytes, bytearray)):
            src_doc = fitz.open(stream=bytes(source), filetype="pdf")
            close_after = True
        else:
            src_doc = fitz.open(str(source))
            close_after = True
        start_at = -1 if at_index is None else at_index
        self._doc.insert_pdf(src_doc, start_at=start_at)
        if close_after:
            src_doc.close()
        self._mark_modified()

    # -- metadados e sumário ---------------------------------------------------

    def get_metadata(self) -> dict:
        return dict(self._doc.metadata or {})

    def set_metadata(self, meta: dict):
        self._push_undo()
        current = dict(self._doc.metadata or {})
        current.update(meta)
        self._doc.set_metadata(current)
        self._mark_modified()

    def get_toc(self) -> list:
        return self._doc.get_toc(simple=True)

    def set_toc(self, toc: list):
        self._push_undo()
        self._doc.set_toc(toc)
        self._mark_modified()

    def needs_password(self) -> bool:
        return self.is_encrypted
