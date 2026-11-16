@echo off
rem ===================================================================
rem  Lancer le compagnon - double-cliquer sur ce fichier.
rem  1re fois : installe tout (quelques minutes, Internet necessaire).
rem  Ensuite  : ouvre directement le compagnon (100 % hors ligne).
rem ===================================================================
setlocal
cd /d "%~dp0"
title Compagnon
echo.
echo   ==============================================
echo     COMPAGNON - lancement
echo   ==============================================
echo.

rem --- 1. Trouver Python 3.12 -----------------------------------------
set "PY="
py -3.12 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3.12"
if defined PY goto python_ok
python --version 2>nul | findstr /b /c:"Python 3.12" >nul
if not errorlevel 1 set "PY=python"
if not defined PY goto pas_de_python
:python_ok

rem --- 2. Environnement Python du projet (dossier .venv) --------------
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" goto venv_ok
echo   [1/3] Preparation de Python pour le projet...
%PY% -m venv .venv
if errorlevel 1 goto erreur
:venv_ok

rem --- 3. Bibliotheques (refait seulement si pyproject.toml a change) --
fc /b pyproject.toml .venv\pyproject.installe >nul 2>&1
if not errorlevel 1 goto biblio_ok
echo   [2/3] Installation des bibliotheques - quelques minutes la 1re fois...
"%VPY%" -m pip install --disable-pip-version-check -q -e ".[voix,dev]"
if errorlevel 1 goto erreur
copy /y pyproject.toml .venv\pyproject.installe >nul
:biblio_ok

rem --- 4. Voix francaise : livree dans le dossier voix (secours si absente)
if exist "voix\fr_FR-upmc-medium.onnx" goto voix_ok
echo   [3/3] Voix absente : telechargement, environ 140 Mo, une seule fois...
"%VPY%" -m piper.download_voices fr_FR-siwis-medium fr_FR-upmc-medium --data-dir voix
if errorlevel 1 echo   Voix non telechargee : le compagnon marchera quand meme, sans voix.
:voix_ok

rem --- 5. Lancement ----------------------------------------------------
rem  IA locale : utilisee si Ollama est installe, sinon phrases preparees.
set "OPTIONS=--ia ollama"
rem  Personnage dessine par le groupe : images dans "contenu\personnage".
if exist "contenu\personnage\neutre.png" set "OPTIONS=%OPTIONS% --personnage contenu\personnage"
if defined COMPAGNON_SANS_LANCER goto fin
echo.
echo   Ouverture du compagnon... (ne pas fermer cette fenetre noire)
echo.
"%VPY%" -m compagnon %OPTIONS% %*
if errorlevel 1 goto erreur
goto fin

:pas_de_python
echo   Python 3.12 n'est pas installe sur cet ordinateur.
echo.
where winget >nul 2>&1
if errorlevel 1 goto python_manuel
choice /c ON /m "  L'installer maintenant automatiquement ? O = oui, N = non"
if errorlevel 2 goto python_manuel
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo   Python est installe. FERMEZ cette fenetre puis relancez
echo   "Lancer le compagnon" par un double-clic.
pause
exit /b 0

:python_manuel
echo   Installez Python 3.12 depuis la page qui va s'ouvrir.
echo   IMPORTANT : cochez la case "Add python.exe to PATH" pendant l'installation.
echo   Puis relancez "Lancer le compagnon".
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 1

:erreur
echo.
echo   Un probleme est survenu. Lisez les lignes au-dessus,
echo   faites une capture d'ecran de cette fenetre et envoyez-la au groupe.
pause
exit /b 1

:fin
endlocal
