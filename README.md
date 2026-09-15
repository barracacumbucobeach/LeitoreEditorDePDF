# Papyra — Leitor & Editor de PDF Profissional

**Papyra** é um leitor e editor de PDF de desktop, multiplataforma, com
edição real de conteúdo: texto, imagens, formas e anotações diretamente no
documento — não apenas visualização.

O nome remete a *papiro*, um dos primeiros suportes de escrita da história —
uma referência direta ao documento, ao ato de escrever e editar, e ao próprio
PDF (*Portable Document Format*) como o "papiro digital" de hoje.

## Principais recursos

**Página inicial (dashboard)**

Ao abrir o programa, uma página inicial recebe o usuário com as opções
principais em destaque: **Abrir PDF...**, **Novo documento** e a lista de
**arquivos recentes** (clicáveis, com opção de remover individualmente ou
limpar tudo). A qualquer momento é possível voltar a ela pelo botão de casa
na barra de ferramentas, pelo menu Arquivo, ou com `Ctrl+Home`.

**Modo Visualizar / Editar**

O documento sempre abre em **modo leitura** — um leitor de PDF comum, sem
nenhuma ferramenta de edição visível ou ativa, para evitar alterações
acidentais. Clique no botão **"Editar PDF"**, no canto superior direito (ou
`Ctrl+E`), para revelar a paleta de ferramentas (com nome escrito embaixo de
cada ícone) e a barra de estilo. Voltar ao modo leitura oculta tudo de novo.

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
- **Editar texto existente**: com a ferramenta "Editar texto" ativa, todos os
  parágrafos da página ficam contornados, mostrando o que pode ser clicado.
  Clique em qualquer um para reescrever o **parágrafo inteiro** de uma vez
  (não apenas uma linha) — o Papyra reaproveita a fonte original incorporada
  no arquivo quando possível, ou escolhe a fonte padrão mais próxima.
  Pressione `Ctrl+Enter` para confirmar, `Esc` para cancelar, ou apenas
  clique fora da caixa
- **OCR em páginas digitalizadas**: ao tentar editar uma página sem texto
  pesquisável (um PDF digitalizado ou uma imagem escaneada), o programa
  oferece reconhecer o texto automaticamente via OCR (requer o
  [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) instalado no
  sistema — veja abaixo). Depois do OCR, o texto reconhecido pode ser editado
  normalmente. Também é possível disparar o OCR manualmente pelo menu
  Página → "Reconhecer texto (OCR)..."
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

### OCR — instalando o Tesseract (opcional)

O reconhecimento de texto em páginas digitalizadas usa o mecanismo
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract) através do
PyMuPDF. Ele **não vem embutido** no Papyra — sem ele, o programa funciona
normalmente, só a opção de OCR fica indisponível (com um aviso explicando
como instalar).

- **Windows**: instale o Tesseract (build da UB-Mannheim, com os idiomas
  "Portuguese" marcados na instalação):
  https://github.com/UB-Mannheim/tesseract/wiki — e garanta que a pasta de
  instalação esteja no `PATH` do sistema.
- **Linux**: `sudo apt install tesseract-ocr tesseract-ocr-por`
- **macOS**: `brew install tesseract tesseract-lang`

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

## Gerando o executável (.exe) para Windows

O empacotamento usa o [PyInstaller](https://pyinstaller.org/), que **precisa
ser executado no Windows** (ele não faz compilação cruzada a partir do
Linux/Mac). O projeto já traz um `.spec` pronto e um script que automatiza
tudo.

**Opção 1 — script automático**

Copie a pasta do projeto para uma máquina Windows com Python 3.11+ instalado
e dê duplo clique em `build_windows.bat` (ou rode-o pelo `cmd`/PowerShell na
raiz do projeto). Ele cria um ambiente virtual, instala as dependências e
gera o executável.

**Opção 2 — comandos manuais**

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements-build.txt
pyinstaller --noconfirm papyra.spec
```

Em ambos os casos, o resultado fica em:

```
dist\Papyra\Papyra.exe
```

Essa pasta `dist\Papyra\` inteira é o que deve ser distribuído (o `.exe`
sozinho não funciona fora dela). Para gerar um único arquivo `.exe`
autocontido (inicialização um pouco mais lenta), troque o `.spec` por:

```bat
pyinstaller --noconfirm --onefile --windowed --name Papyra --icon assets\icon.ico --add-data "assets;assets" main.py
```

## Estrutura do projeto

```
main.py                     Ponto de entrada da aplicação
papyra/
  document.py                Núcleo: abrir/salvar, edição de texto/imagens/
                              anotações/páginas, desfazer/refazer, busca,
                              metadados e sumário (sobre PyMuPDF)
  view.py                    Visualizador/editor (QGraphicsView): zoom,
                              rolagem contínua, ferramentas de edição,
                              impressão
  tools.py                   Definição das ferramentas de edição
  home.py                    Página inicial (dashboard)
  sidebar.py                 Painéis de miniaturas e sumário
  dialogs.py                 Diálogos: Sobre, Propriedades, Gerenciar páginas
  main_window.py             Janela principal: menus, barras de ferramentas,
                              abas, atalhos, arquivos recentes
  theme.py                   Paleta de cores e folha de estilos (QSS)
  icons.py                   Ícones vetoriais
assets/icon.svg               Ícone da aplicação
```

## Atalhos principais

| Ação | Atalho |
|---|---|
| Página inicial | `Ctrl+Home` |
| Novo / Abrir / Salvar / Salvar como | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` |
| Ativar/desativar modo de edição | `Ctrl+E` |
| Imprimir | `Ctrl+P` |
| Desfazer / Refazer | `Ctrl+Z` / `Ctrl+Y` |
| Localizar | `Ctrl+F` |
| Ampliar / Reduzir / 100% | `Ctrl++` / `Ctrl+-` / `Ctrl+0` |
| Ferramentas de edição (em modo de edição) | `Ctrl+1`…`Ctrl+9` |
| Confirmar texto digitado / cancelar | `Ctrl+Enter` / `Esc` |
| Excluir objeto selecionado | `Delete` |
| Zoom com a roda do mouse | `Ctrl` + roda do mouse |
| Arrastar a página | Botão do meio do mouse |
