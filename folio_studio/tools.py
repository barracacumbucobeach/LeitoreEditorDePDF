"""Ferramentas de edição disponíveis no visualizador de PDF."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class Tool(Enum):
    SELECT = auto()      # selecionar, mover e redimensionar objetos
    EDIT_TEXT = auto()    # editar um texto já existente no documento
    ADD_TEXT = auto()     # inserir uma nova caixa de texto
    HIGHLIGHT = auto()    # realçar texto
    RECT = auto()         # retângulo
    ELLIPSE = auto()      # elipse / círculo
    LINE = auto()         # linha reta
    ARROW = auto()        # linha com seta
    INK = auto()          # desenho livre (caneta)
    IMAGE = auto()        # inserir imagem
    NOTE = auto()         # nota adesiva
    ERASER = auto()       # apagar (borracha / branqueamento)


DRAG_RECT_TOOLS = {Tool.HIGHLIGHT, Tool.RECT, Tool.ELLIPSE, Tool.ERASER, Tool.ADD_TEXT, Tool.IMAGE}
DRAG_LINE_TOOLS = {Tool.LINE, Tool.ARROW}

TOOL_LABELS = {
    Tool.SELECT: "Selecionar",
    Tool.EDIT_TEXT: "Editar texto",
    Tool.ADD_TEXT: "Texto",
    Tool.HIGHLIGHT: "Realce",
    Tool.RECT: "Retângulo",
    Tool.ELLIPSE: "Elipse",
    Tool.LINE: "Linha",
    Tool.ARROW: "Seta",
    Tool.INK: "Caneta",
    Tool.IMAGE: "Imagem",
    Tool.NOTE: "Nota",
    Tool.ERASER: "Borracha",
}

TOOL_TOOLTIPS = {
    Tool.SELECT: "Selecionar — escolher, mover, redimensionar ou excluir um objeto",
    Tool.EDIT_TEXT: "Editar texto — clique num parágrafo existente para reescrevê-lo",
    Tool.ADD_TEXT: "Texto — desenhe uma caixa para adicionar um novo texto",
    Tool.HIGHLIGHT: "Realce — arraste sobre um trecho para realçá-lo",
    Tool.RECT: "Retângulo — desenhe um retângulo",
    Tool.ELLIPSE: "Elipse — desenhe uma elipse ou círculo",
    Tool.LINE: "Linha — desenhe uma linha reta",
    Tool.ARROW: "Seta — desenhe uma linha com ponta de seta",
    Tool.INK: "Caneta — desenho livre à mão",
    Tool.IMAGE: "Imagem — insira uma foto ou figura a partir de um arquivo",
    Tool.NOTE: "Nota adesiva — adicione um comentário em forma de nota",
    Tool.ERASER: "Borracha — apaga permanentemente o conteúdo de uma área",
}


@dataclass
class ToolOptions:
    """Preferências atuais de estilo para as ferramentas de desenho/texto."""

    stroke_color: tuple = (0.83, 0.27, 0.27)     # vermelho suave
    fill_color: tuple | None = None
    highlight_color: tuple = (1.0, 0.92, 0.23)   # amarelo
    line_width: float = 2.0
    font_family: str = "helv"
    font_size: float = 13.0
    font_color: tuple = (0.05, 0.05, 0.05)

    def with_stroke(self, rgb: tuple) -> "ToolOptions":
        self.stroke_color = rgb
        return self
