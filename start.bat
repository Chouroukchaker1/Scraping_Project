@echo off
echo ========================================
echo  Plateforme d'Extraction d'Appels d'Offres
echo  Script de demarrage automatique
echo ========================================
echo.

REM Verifier si Docker est installe
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou n'est pas dans le PATH
    echo Installez Docker Desktop depuis: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Verifier si docker-compose est disponible
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] docker-compose n'est pas disponible
    pause
    exit /b 1
)

REM Verifier si le fichier .env existe
if not exist ".env" (
    echo [INFO] Fichier .env introuvable. Creation depuis .env.example...
    copy .env.example .env
    echo.
    echo [ATTENTION] Fichier .env cree !
    echo Veuillez editer le fichier .env et modifier au minimum:
    echo   - JWT_SECRET (obligatoire pour la securite)
    echo   - API_EMAIL et API_PASSWORD (si vous utilisez l'API externe)
    echo.
    echo Appuyez sur une touche apres avoir edite .env...
    pause
    notepad .env
)

echo.
echo [INFO] Demarrage des services Docker...
echo.

REM Arreter les anciens containers s'ils existent
docker-compose down 2>nul

REM Demarrer les services
docker-compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] Echec du demarrage des services
    echo Verifiez les logs avec: docker-compose logs
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Services demarres avec succes !
echo ========================================
echo.
echo Attente de 15 secondes pour que tout demarre...
timeout /t 15 /nobreak >nul

echo.
echo Verification du statut des services...
docker-compose ps

echo.
echo ========================================
echo  Application prete !
echo ========================================
echo.
echo URLs d'acces:
echo   Frontend:    http://localhost
echo   Backend API: http://localhost:5000
echo   MongoDB:     localhost:27017
echo.
echo Commandes utiles:
echo   - Voir les logs:     docker-compose logs -f
echo   - Arreter:           docker-compose down
echo   - Redemarrer:        docker-compose restart
echo.
echo Appuyez sur une touche pour ouvrir l'application dans le navigateur...
pause >nul

start http://localhost

echo.
echo Application ouverte ! Pour arreter, fermez cette fenetre ou utilisez Ctrl+C
echo.
pause
