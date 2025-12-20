#!/bin/bash

# Script de démarrage automatique pour Linux/Mac
# Plateforme d'Extraction d'Appels d'Offres

set -e

echo "========================================"
echo " Plateforme d'Extraction d'Appels d'Offres"
echo " Script de démarrage automatique"
echo "========================================"
echo ""

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "[ERREUR] Docker n'est pas installé"
    echo "Installez Docker depuis: https://docs.docker.com/get-docker/"
    exit 1
fi

# Vérifier si docker-compose est disponible
if ! command -v docker-compose &> /dev/null; then
    echo "[ERREUR] docker-compose n'est pas disponible"
    echo "Installez docker-compose depuis: https://docs.docker.com/compose/install/"
    exit 1
fi

# Vérifier si le fichier .env existe
if [ ! -f ".env" ]; then
    echo "[INFO] Fichier .env introuvable. Création depuis .env.example..."
    cp .env.example .env
    echo ""
    echo "[ATTENTION] Fichier .env créé !"
    echo "Veuillez éditer le fichier .env et modifier au minimum:"
    echo "  - JWT_SECRET (obligatoire pour la sécurité)"
    echo "  - API_EMAIL et API_PASSWORD (si vous utilisez l'API externe)"
    echo ""
    read -p "Appuyez sur Entrée après avoir édité .env..."

    # Ouvrir l'éditeur par défaut
    ${EDITOR:-nano} .env
fi

echo ""
echo "[INFO] Démarrage des services Docker..."
echo ""

# Arrêter les anciens containers s'ils existent
docker-compose down 2>/dev/null || true

# Démarrer les services
docker-compose up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERREUR] Échec du démarrage des services"
    echo "Vérifiez les logs avec: docker-compose logs"
    exit 1
fi

echo ""
echo "========================================"
echo " Services démarrés avec succès !"
echo "========================================"
echo ""
echo "Attente de 15 secondes pour que tout démarre..."
sleep 15

echo ""
echo "Vérification du statut des services..."
docker-compose ps

echo ""
echo "========================================"
echo " Application prête !"
echo "========================================"
echo ""
echo "URLs d'accès:"
echo "  Frontend:    http://localhost"
echo "  Backend API: http://localhost:5000"
echo "  MongoDB:     localhost:27017"
echo ""
echo "Commandes utiles:"
echo "  - Voir les logs:     docker-compose logs -f"
echo "  - Arrêter:           docker-compose down"
echo "  - Redémarrer:        docker-compose restart"
echo ""

# Ouvrir le navigateur (selon l'OS)
if command -v xdg-open &> /dev/null; then
    echo "Ouverture de l'application dans le navigateur..."
    xdg-open http://localhost &>/dev/null &
elif command -v open &> /dev/null; then
    echo "Ouverture de l'application dans le navigateur..."
    open http://localhost &>/dev/null &
fi

echo ""
echo "Application démarrée ! Pour arrêter, utilisez: docker-compose down"
echo ""
