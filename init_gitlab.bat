@echo off
echo ========================================
echo INITIALISATION DU DEPOT GITLAB
echo ========================================
echo.
echo Etape 1: Ouvrir GitLab dans votre navigateur...
start https://gitlab.com/tunipages-nac/extractionauto
echo.
echo Etape 2: Connectez-vous avec:
echo Email: chourouk.chaker@tunipages.tn
echo Mot de passe: bouba2022*
echo.
echo Etape 3: Une fois connecté, cliquez sur le bouton:
echo "Initialize repository with a README"
echo.
echo Etape 4: Appuyez sur une touche quand c'est fait...
pause
echo.
echo Etape 5: Envoi du code vers GitLab...
cd "c:\Users\lenovo\Desktop\extractionautomatic"
git push -u origin initial
echo.
echo ========================================
echo TERMINE!
echo ========================================
pause
