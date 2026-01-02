# 🚀 Déploiement Rapide - 3 Commandes Seulement

## Pour l'Hébergeur: Tout est Prêt!

Vous n'avez **RIEN à configurer**. Toutes les tables PostgreSQL, index, et configurations sont automatiques.

---

## 🎯 Installation en 3 Étapes

### 1. Cloner le projet
```bash
git clone https://gitlab.com/tunipages-nac/extractionauto.git
cd extractionauto
git checkout development
```

### 2. Lancer Docker
```bash
docker-compose up -d
```

### 3. Vérifier (optionnel)
```bash
chmod +x verify_deployment.sh
./verify_deployment.sh
```

**C'EST TOUT! ✅**

---

## 🌐 Accès après Déploiement

### Interface Web
- **Frontend**: http://VOTRE_IP:8080
- **pgAdmin** (base de données): http://VOTRE_IP:8081
  - Login: admin@admin.com
  - Password: admin

### Base de Données
- **Host**: VOTRE_IP:5432
- **Database**: tenders_db
- **User**: tender_user
- **Password**: tender_password_2024

---

## 📊 Ce qui est Créé Automatiquement

Le fichier `backend/init.sql` crée automatiquement:

✅ **14 Tables PostgreSQL**:
- tenders_benin
- tenders_mediacongo
- tenders_relief
- tenders_tuneps
- tenders_tuneps_ao
- tenders_armp
- tenders_pnud
- tenders_banque
- tenders_boamp
- tenders_haicop
- tenders_expertise
- tenders_ppda
- jobs_niger
- jobs_somalia

✅ **Tous les Index** pour la performance

✅ **Tous les Triggers** pour updated_at automatique

✅ **Une Vue globale** `pending_tenders_all` avec toutes les offres

---

## 🔧 Commandes Utiles

### Voir les logs
```bash
docker-compose logs -f
```

### Redémarrer un service
```bash
docker restart backend_tenders
```

### Arrêter tout
```bash
docker-compose down
```

### Backup base de données
```bash
docker exec postgres_tenders pg_dump -U tender_user tenders_db > backup.sql
```

---

## 📖 Documentation Complète

Voir **DEPLOYMENT_GUIDE.md** pour:
- Structure détaillée des tables
- Variables d'environnement
- Sécurité en production
- Toutes les URLs des APIs

---

## ⚠️ Avant Production

Changez les mots de passe dans `docker-compose.yml`:
- `POSTGRES_PASSWORD`
- `PGADMIN_DEFAULT_PASSWORD`

---

## 📞 Support

- Logs: `docker-compose logs -f`
- Status: `docker ps -a`
- GitLab: https://gitlab.com/tunipages-nac/extractionauto

---

**Développé avec Claude Code** 🤖
