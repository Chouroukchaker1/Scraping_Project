@echo off
echo ========================================
echo Ajout colonne 'source' dans tenders_haicop
echo ========================================

psql -U tender_user -d tenders_db -f fix_haicop_source.sql

if %errorlevel% equ 0 (
    echo.
    echo ✅ Script execute avec succes!
) else (
    echo.
    echo ❌ Erreur lors de l'execution du script
)

pause
