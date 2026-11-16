@echo off
rem Windows'ta yerel derleme: Python 3.10+ ve Inno Setup 6 gerekli.
cd /d "%~dp0"
if not exist .buildenv py -3 -m venv .buildenv || exit /b 1
.buildenv\Scripts\python -m pip install -q -r requirements.txt pyinstaller || exit /b 1
.buildenv\Scripts\pyinstaller --noconfirm --distpath dist --workpath build\pyi packaging\voicechanger.spec || exit /b 1
if not exist build\vbcable\VBCABLE_Setup_x64.exe (
  powershell -NoProfile -Command "New-Item -ItemType Directory -Force build\vbcable | Out-Null; Invoke-WebRequest https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack46.zip -OutFile build\vbcable.zip; Expand-Archive -Force build\vbcable.zip build\vbcable" || exit /b 1
)
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
%ISCC% packaging\installer.iss || exit /b 1
echo.
echo Hazir: dist klasorundeki DnDVoiceChanger_Setup_*.exe
