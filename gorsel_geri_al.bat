@echo off
title HighFleet Turkce Yama - Gorselleri Geri Al
cd /d "%~dp0Yama\Gorseller"
echo.
echo Gorseller orijinal haline dondurulecek.
echo (Metin yamasi etkilenmez.)
echo.
pause
python yama_uygula.py --geri-al
