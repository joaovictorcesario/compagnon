@echo off
rem ===================================================================
rem  Verifier mes modifications - double-cliquer AVANT d'envoyer
rem  ses changements sur GitHub. Lance les tests automatiques du projet.
rem ===================================================================
setlocal
cd /d "%~dp0"
title Verification du compagnon
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" goto pret
echo   Lancez d'abord "Lancer le compagnon" une fois : il installe tout.
pause
exit /b 1
:pret
echo.
echo   Verification en cours (environ 10 secondes)...
echo.
"%VPY%" -m pytest -q --no-header -p no:cacheprovider
if errorlevel 1 goto probleme
echo.
echo   ==============================================
echo     TOUT EST BON : vous pouvez envoyer (Push).
echo   ==============================================
pause
exit /b 0
:probleme
echo.
echo   ==============================================
echo     ATTENTION : un test ne passe plus.
echo     Lisez les lignes "FAILED" ci-dessus : elles disent
echo     quel fichier pose probleme. N'envoyez pas encore.
echo   ==============================================
pause
exit /b 1
