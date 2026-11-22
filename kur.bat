@echo off
setlocal enabledelayedexpansion
title HighFleet Turkce Yama - Kurulum

echo.
echo ================================================
echo   HIGHFLEET TURKCE YAMA v1.0 - KURULUM
echo ================================================
echo.

set "SRC=%~dp0Yama\Data\Dialogs\english.seria_enc"
if not exist "%SRC%" (
    echo HATA: Yama dosyasi bulunamadi.
    echo Beklenen konum: %SRC%
    echo Paketi tamamen cikardigindan emin ol.
    goto :son
)

set "GAME="

echo Oyun araniyor...
for %%D in (C D E F G H) do (
    if exist "%%D:\Program Files (x86)\Steam\steamapps\common\HighFleet\Highfleet.exe" set "GAME=%%D:\Program Files (x86)\Steam\steamapps\common\HighFleet"
    if exist "%%D:\Steam\steamapps\common\HighFleet\Highfleet.exe"                     set "GAME=%%D:\Steam\steamapps\common\HighFleet"
    if exist "%%D:\SteamLibrary\steamapps\common\HighFleet\Highfleet.exe"              set "GAME=%%D:\SteamLibrary\steamapps\common\HighFleet"
    if exist "%%D:\Games\Steam\steamapps\common\HighFleet\Highfleet.exe"               set "GAME=%%D:\Games\Steam\steamapps\common\HighFleet"
    if exist "%%D:\SteamGames\steamapps\common\HighFleet\Highfleet.exe"                set "GAME=%%D:\SteamGames\steamapps\common\HighFleet"
)

if not defined GAME (
    echo.
    echo Oyun otomatik bulunamadi.
    echo Steam'de HighFleet'e sag tik ^> Yonet ^> Yerel dosyalara goz at
    echo diyerek acilan klasorun yolunu buraya yapistir.
    echo.
    set /p "GAME=HighFleet klasoru: "
)

if not exist "%GAME%\Highfleet.exe" (
    echo.
    echo HATA: Bu klasorde Highfleet.exe yok:
    echo   %GAME%
    goto :son
)

echo.
echo Oyun bulundu:
echo   %GAME%
echo.

set "DEST=%GAME%\Data\Dialogs"
if not exist "%DEST%" (
    echo HATA: Data\Dialogs klasoru yok. Oyun kurulumu bozuk olabilir.
    goto :son
)

if exist "%DEST%\english.seria_enc.orig" (
    echo Orijinal yedek zaten var, korunuyor.
) else (
    copy /y "%DEST%\english.seria_enc" "%DEST%\english.seria_enc.orig" >nul
    if errorlevel 1 (
        echo HATA: Yedek alinamadi. Bu dosyaya sag tik ^> Yonetici olarak calistir dene.
        goto :son
    )
    echo Orijinal yedeklendi: english.seria_enc.orig
)

copy /y "%SRC%" "%DEST%\english.seria_enc" >nul
if errorlevel 1 (
    echo.
    echo HATA: Kopyalama basarisiz. Oyun acik olmadigindan emin ol,
    echo sonra bu dosyaya sag tik ^> Yonetici olarak calistir dene.
    goto :son
)

echo.
echo ================================================
echo   KURULDU. Iyi oyunlar.
echo ================================================
echo.
echo Kaldirmak icin: %DEST% klasorunde
echo english.seria_enc.orig dosyasini english.seria_enc
echo olarak yeniden adlandir.

:son
echo.
pause
