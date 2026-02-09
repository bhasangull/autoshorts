@echo off
cd /d "%~dp0"
echo Video Factory EXE olusturuluyor...
python -m pip install -r requirements.txt --quiet
if not exist "assets\fonts" mkdir "assets\fonts"
python -m PyInstaller --onefile --windowed --name "VideoFactory" ^
  --hidden-import=edge_tts ^
  --hidden-import=asyncio ^
  --hidden-import=PIL ^
  --hidden-import=PIL.Image ^
  --collect-all edge_tts ^
  --add-data "assets;assets" ^
  src/main.py
echo.
if exist "dist\VideoFactory.exe" (
  echo Basarili! EXE: dist\VideoFactory.exe
  echo FFmpeg yoksa ffmpeg.exe ve ffprobe.exe dosyalarini dist klasorune kopyalayin.
) else (
  echo Hata: EXE olusturulamadi.
)
pause
