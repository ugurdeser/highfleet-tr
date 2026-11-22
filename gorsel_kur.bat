@echo off
title HighFleet Turkce Yama - Gorsel Kurulumu
cd /d "%~dp0Yama\Gorseller"

echo.
echo ================================================
echo   HIGHFLEET TURKCE YAMA - GORSEL KURULUMU
echo ================================================
echo.
echo Bu adim oyunun RESME GOMULU yazilarini Turkcelestirir:
echo ana menu, posterler, paneller, uyari levhalari.
echo.
echo Python 3 ve Pillow gerekir.
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi.
    echo.
    echo Kur: https://www.python.org/downloads/
    echo Kurulum sirasinda "Add Python to PATH" kutusunu ISARETLE.
    echo Sonra bu dosyayi tekrar calistir.
    echo.
    pause
    exit /b
)

python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Pillow kurulu degil, kuruluyor...
    python -m pip install pillow
    echo.
)

python yama_uygula.py --yaz
