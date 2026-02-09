@echo off
echo PyInstaller kontrol ediliyor...
python -m pip install pyinstaller --quiet
echo EXE olusturuluyor...
python -m PyInstaller --onefile --windowed --name "EdgeTTS-Ahmet" ^
  --hidden-import=edge_tts ^
  --hidden-import=asyncio ^
  --collect-all edge_tts ^
  main.py
echo.
if exist "dist\EdgeTTS-Ahmet.exe" (
  echo Basarili! EXE dosyasi: dist\EdgeTTS-Ahmet.exe
) else (
  echo Hata: EXE olusturulamadi.
)
pause
