#!/bin/bash

# Script de vérification du déploiement
# À exécuter après docker-compose up -d

echo "======================================"
echo "🔍 Vérification du Déploiement"
echo "======================================"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour vérifier un conteneur
check_container() {
    container_name=$1
    if docker ps | grep -q "$container_name"; then
        echo -e "${GREEN}✅ $container_name${NC} - Running"
        return 0
    else
        echo -e "${RED}❌ $container_name${NC} - Not running"
        return 1
    fi
}

# Fonction pour vérifier un port
check_port() {
    port=$1
    service=$2
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✅ Port $port${NC} ($service) - Accessible"
        return 0
    else
        echo -e "${RED}❌ Port $port${NC} ($service) - Not accessible"
        return 1
    fi
}

echo "1️⃣  Vérification des Conteneurs Docker"
echo "--------------------------------------"
check_container "postgres_tenders"
check_container "backend_tenders"
check_container "frontend_tenders"
check_container "pgadmin_tenders"
echo ""

echo "2️⃣  Vérification des Ports"
echo "--------------------------------------"
check_port 5432 "PostgreSQL"
check_port 5000 "API Node.js"
check_port 5012 "Benin Scraper"
check_port 5015 "Relief Scraper"
check_port 5016 "MediaCongo Scraper"
check_port 5017 "PPDA Scraper"
check_port 5018 "Niger Scraper"
check_port 8080 "Frontend"
check_port 8081 "pgAdmin"
echo ""

echo "3️⃣  Vérification de la Base de Données"
echo "--------------------------------------"

# Vérifier la connexion PostgreSQL
if docker exec postgres_tenders pg_isready -U tender_user -d tenders_db > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL${NC} - Connexion OK"

    # Compter les tables
    table_count=$(docker exec postgres_tenders psql -U tender_user -d tenders_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" 2>/dev/null | tr -d ' ')

    if [ "$table_count" -eq "14" ]; then
        echo -e "${GREEN}✅ Tables PostgreSQL${NC} - 14 tables créées"
    else
        echo -e "${YELLOW}⚠️  Tables PostgreSQL${NC} - $table_count tables (attendu: 14)"
    fi
else
    echo -e "${RED}❌ PostgreSQL${NC} - Connexion échouée"
fi
echo ""

echo "4️⃣  Détails des Tables"
echo "--------------------------------------"
docker exec postgres_tenders psql -U tender_user -d tenders_db -c "\dt" 2>/dev/null
echo ""

echo "5️⃣  Statistiques"
echo "--------------------------------------"
docker exec postgres_tenders psql -U tender_user -d tenders_db -c "
SELECT
    'tenders_benin' as table_name, COUNT(*) as nb_rows FROM tenders_benin
UNION ALL
SELECT 'tenders_mediacongo', COUNT(*) FROM tenders_mediacongo
UNION ALL
SELECT 'tenders_relief', COUNT(*) FROM tenders_relief
UNION ALL
SELECT 'tenders_ppda', COUNT(*) FROM tenders_ppda
UNION ALL
SELECT 'jobs_niger', COUNT(*) FROM jobs_niger
UNION ALL
SELECT 'jobs_somalia', COUNT(*) FROM jobs_somalia
ORDER BY table_name;
" 2>/dev/null
echo ""

echo "======================================"
echo "🔗 URLs d'Accès"
echo "======================================"
echo -e "${GREEN}Frontend:${NC} http://localhost:8080"
echo -e "${GREEN}pgAdmin:${NC} http://localhost:8081"
echo -e "  - Email: admin@admin.com"
echo -e "  - Password: admin"
echo ""
echo -e "${GREEN}PostgreSQL:${NC} localhost:5432"
echo -e "  - Database: tenders_db"
echo -e "  - User: tender_user"
echo -e "  - Password: tender_password_2024"
echo ""

echo "======================================"
echo "✅ Vérification Terminée"
echo "======================================"
