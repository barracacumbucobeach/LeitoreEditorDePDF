@echo off
REM Gera o executavel do Folio Studio para Windows.
REM Execute este script dentro de uma janela do "cmd" ou PowerShell no Windows,
REM na pasta raiz do projeto (onde este arquivo esta).

setlocal

echo === Folio Studio - build do .exe ===

REM 1) Cria e ativa um ambiente virtual, se ainda nao existir
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
)
call venv\Scripts\activate.bat

REM 2) Instala as dependencias do app + o PyInstaller
echo Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM 3) Gera o executavel usando o spec do projeto
echo Empacotando com PyInstaller...
pyinstaller --noconfirm folio_studio.spec

echo.
echo Concluido! O executavel esta em: dist\FolioStudio\FolioStudio.exe
pause
