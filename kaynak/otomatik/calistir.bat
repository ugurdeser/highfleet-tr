@echo off
title HighFleet - Gemini ile Otomatik Turkcelestirme
cd /d "%~dp0"

if "%GEMINI_API_KEY%"=="" (
  echo.
  echo Gemini API anahtarin tanimli degil.
  echo Ucretsiz almak icin: https://aistudio.google.com/apikey
  echo.
  set /p GEMINI_API_KEY=Anahtari buraya yapistir: 
)

:menu
echo.
echo ===============================================
echo   1  Ana menuyu oku ve cevir      (Desk1, 17 adet)
echo   2  Ana menuyu ciz               (Desk1)
echo   3  Ciktilari onayla ve uygula   (Desk1)
echo   4  TUM oyunu oku ve cevir       (103 adet)
echo   5  TUM oyunu ciz                (103 adet)
echo   6  Durum ozeti
echo   0  Cikis
echo ===============================================
set /p S=Secim: 

if "%S%"=="1" python pipeline.py --oku    --klasor Desk1
if "%S%"=="2" python pipeline.py --ciz    --klasor Desk1
if "%S%"=="3" python pipeline.py --uygula --klasor Desk1
if "%S%"=="4" python pipeline.py --oku
if "%S%"=="5" python pipeline.py --ciz
if "%S%"=="6" python pipeline.py --durum
if "%S%"=="0" goto :eof
pause
goto menu
