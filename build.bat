@echo off
echo PyInstaller kontrol ediliyor...
python -m pip install pyinstaller --quiet
echo AutoShorts EXE olusturuluyor...
python -m PyInstaller --noconfirm VideoFactory.spec
echo.
if exist "dist\AutoShorts.exe" (
  echo Basarili! EXE: dist\AutoShorts.exe
) else (
  echo Hata: EXE olusturulamadi.
)
pause
