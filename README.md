# Fólio Studio — Leitor & Editor de PDF Profissional

**Fólio Studio** é um leitor e editor de PDF de desktop, multiplataforma, com
edição real de conteúdo: texto, imagens, formas e anotações diretamente no
documento — não apenas visualização.

O nome vem de *fólio*: a folha numerada de um manuscrito ou livro. É também
uma referência direta ao PDF (*Portable Document Format*) — o "fólio digital"
de hoje.

## Principais recursos

**Leitura**
- Rolagem contínua entre páginas, com renderização sob demanda (rápida mesmo
  em documentos grandes)
- Zoom suave (roda do mouse + Ctrl, atalhos, campo de porcentagem), ajustar à
  largura/à página
- Painel de miniaturas das páginas e painel de sumário (marcadores/TOC)
- Busca de texto com realce dos resultados e navegação entre ocorrências
- Múltiplos documentos em abas
- Abertura de PDFs protegidos por senha
- Impressão e pré-visualização de impressão

**Edição**
- **Editar texto existente**: clique em qualquer trecho de texto do PDF e
  edite-o no lugar — o Fólio Studio reaproveita a fonte original incorporada
  no arquivo quando possível, ou escolhe a fonte padrão mais próxima
- **Imagens**: inserir, substituir, mover, redimensionar e excluir imagens do
  documento
- **Anotações e formas**: realce de texto, retângulo, elipse, linha, seta,
  caneta (desenho livre), caixa de texto, nota adesiva
- **Borracha**: apaga permanentemente qualquer conteúdo de uma área
  (baseada em redação/*redaction* real do PDF, não apenas uma cobertura visual)
- **Gerenciador de páginas**: adicionar, excluir, girar, duplicar, reordenar
  (arrastar e soltar), extrair páginas para um novo arquivo e inserir páginas
  de outro PDF (mesclar)
- **Propriedades do documento**: título, autor, assunto, palavras-chave
- **Desfazer/Refazer** completo para qualquer operação de edição
- Temas claro e escuro

## Tecnologia

- **Python 3.11+**
- **PySide6** (Qt 6) para a interface
- **PyMuPDF** (`pymupdf`/`fitz`) para leitura e edição de baixo nível do PDF
- **qtawesome** para os ícones vetoriais
- **Pillow** como apoio para manipulação de imagens

## Como executar

```bash
pip install -r requirements.txt
python main.py
```

Para abrir um arquivo diretamente:

```bash
python main.py caminho/para/arquivo.pdf
```

## Estrutura do projeto

```
main.py                     Ponto de entrada da aplicação
folio_studio/
  document.py                Núcleo: abrir/salvar, edição de texto/imagens/
                              anotações/páginas, desfazer/refazer, busca,
                              metadados e sumário (sobre PyMuPDF)
  view.py                    Visualizador/editor (QGraphicsView): zoom,
                              rolagem contínua, ferramentas de edição,
                              impressão
  tools.py                   Definição das ferramentas de edição
  sidebar.py                 Painéis de miniaturas e sumário
  dialogs.py                 Diálogos: Sobre, Propriedades, Gerenciar páginas
  main_window.py              Janela principal: menus, barras de ferramentas,
                              abas, atalhos, arquivos recentes
  theme.py                    Paleta de cores e folha de estilos (QSS)
  icons.py                    Ícones vetoriais
assets/icon.svg               Ícone da aplicação
```

## Atalhos principais

| Ação | Atalho |
|---|---|
| Novo / Abrir / Salvar / Salvar como | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` |
| Imprimir | `Ctrl+P` |
| Desfazer / Refazer | `Ctrl+Z` / `Ctrl+Y` |
| Localizar | `Ctrl+F` |
| Ampliar / Reduzir / 100% | `Ctrl++` / `Ctrl+-` / `Ctrl+0` |
| Ferramentas de edição | `Ctrl+1`…`Ctrl+9` |
| Excluir objeto selecionado | `Delete` |
| Girar visualização com o mouse | `Ctrl` + roda do mouse (zoom) |
| Arrastar a página | Botão do meio do mouse |
