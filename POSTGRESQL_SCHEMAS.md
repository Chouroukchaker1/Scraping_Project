# Documentation des Schémas PostgreSQL

## Base de données: `tenders_db`

Cette documentation décrit tous les schémas PostgreSQL utilisés dans le système d'extraction automatique d'appels d'offres.

---

## 📊 Vue d'ensemble

| Table | Description | Pays/Source | Port API |
|-------|-------------|-------------|----------|
| `tenders_benin` | Appels d'offres Bénin | Bénin | 5012 |
| `tenders_mediacongo` | Appels d'offres MediaCongo | RDC | 5003 |
| `tenders_relief` | Appels d'offres ReliefWeb | International | 5005 |
| `tenders_tuneps` | TUNEPS (Marchés publics) | Tunisie | 5001 |
| `tenders_tuneps_ao` | TUNEPS Appels d'offres | Tunisie | 5000 |
| `tenders_armp` | ARMP Madagascar | Madagascar | 5007 |
| `tenders_pnud` | PNUD/UNDP | International | 5006 |
| `tenders_banque` | Banque Mondiale | International | 5010 |
| `tenders_boamp` | BOAMP France | France | 5013 |
| `tenders_haicop` | HAICOP Tunisie | Tunisie | 5011 |
| `tenders_expertise` | Expertise France | France | 5014 |
| `tenders_ppda` | PPDA Malawi | Malawi | 5017 |
| `jobs_niger` | Emplois Niger | Niger | 5018 |
| `jobs_somalia` | Emplois Somalia | Somalia | 5019 |

---

## 1. TABLE: `tenders_benin`

**Description**: Appels d'offres du Bénin

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `ref` | VARCHAR(255) | Oui | - | Référence unique (UNIQUE) |
| `description` | TEXT | Oui | - | Description de l'appel d'offres |
| `date_publication` | VARCHAR(100) | Oui | - | Date de publication |
| `date_limite_depot` | VARCHAR(100) | Oui | - | Date limite de dépôt |
| `delai` | VARCHAR(100) | Oui | - | Délai |
| `autorite_contractante` | TEXT | Oui | - | Autorité contractante |
| `lieu_execution` | TEXT | Oui | - | Lieu d'exécution |
| `lien_pdf` | TEXT | Oui | - | Lien vers le PDF |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut: `pending`, `validated`, `failed` |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |

### Index

- `idx_benin_ref` sur `ref`
- `idx_benin_status` sur `status`
- `idx_benin_publication` sur `date_publication`

---

## 2. TABLE: `tenders_mediacongo`

**Description**: Appels d'offres MediaCongo (RDC)

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `description` | TEXT | Oui | - | Description originale |
| `description_fr` | TEXT | Oui | - | Description en français |
| `publication_date` | TIMESTAMP | Oui | - | Date de publication |
| `start_bidding_date` | TIMESTAMP | Oui | - | Date de début des soumissions |
| `expiration_date` | TIMESTAMP | Oui | - | Date d'expiration |
| `promoter` | TEXT | Oui | - | Promoteur de l'appel d'offres |
| `source_id` | INTEGER | Oui | - | ID de la source dans l'API |
| `avis_id` | INTEGER | Oui | - | ID de l'avis dans l'API |
| `external_url` | TEXT | Oui | - | URL externe |
| `montant` | VARCHAR(100) | Oui | - | Montant du marché |
| `fetched_at` | TIMESTAMP | Oui | - | Date de récupération |
| `category` | VARCHAR(100) | Oui | - | Catégorie |
| `country` | VARCHAR(100) | Oui | - | Pays |
| `nature` | VARCHAR(100) | Oui | - | Nature du marché |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `validation_date` | TIMESTAMP | Oui | - | Date de validation |
| `api_id` | INTEGER | Oui | - | ID dans l'API appeloffres.net |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |

### Index

- `idx_mediacongo_reference` sur `reference`
- `idx_mediacongo_status` sur `status`

---

## 3. TABLE: `tenders_relief`

**Description**: Appels d'offres ReliefWeb (International)

### Colonnes

Identique à `tenders_mediacongo`

### Index

- `idx_relief_reference` sur `reference`
- `idx_relief_status` sur `status`

---

## 4. TABLE: `tenders_tuneps`

**Description**: TUNEPS - Marchés publics tunisiens (Section Marchés)

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `title` | TEXT | Oui | - | Titre de l'appel d'offres |
| `description` | TEXT | Oui | - | Description |
| `full_content` | TEXT | Oui | - | Contenu complet |
| `publication_date` | TIMESTAMP | Oui | - | Date de publication |
| `expiration_date` | TIMESTAMP | Oui | - | Date d'expiration |
| `opening_date` | TIMESTAMP | Oui | - | Date d'ouverture des plis |
| `region` | VARCHAR(100) | Oui | - | Région |
| `promoter` | TEXT | Oui | - | Promoteur |
| `source_id` | INTEGER | Oui | `817` | ID source TUNEPS |
| `avis_id` | INTEGER | Oui | `2` | ID avis |
| `pays_id` | INTEGER | Oui | `219` | ID pays (Tunisie) |
| `currency_id` | INTEGER | Oui | `111` | ID devise |
| `nature` | VARCHAR(100) | Oui | `'public'` | Nature du marché |
| `external_url` | TEXT | Oui | - | URL externe |
| `pdf_url` | TEXT | Oui | - | URL du PDF |
| `cautionnement` | VARCHAR(255) | Oui | - | Cautionnement |
| `montant` | VARCHAR(255) | Oui | - | Montant |
| `batches` | JSONB | Oui | - | Lots (format JSON) |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `extraction_date` | TIMESTAMP | Oui | - | Date d'extraction |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |
| `api_id` | INTEGER | Oui | - | ID dans l'API |

### Index

- `idx_tuneps_reference` sur `reference`
- `idx_tuneps_status` sur `status`
- `idx_tuneps_publication` sur `publication_date`

---

## 5. TABLE: `tenders_tuneps_ao`

**Description**: TUNEPS - Appels d'offres tunisiens (Section /portail/offres)

### Colonnes

Identique à `tenders_tuneps`

### Index

- `idx_tuneps_ao_reference` sur `reference`
- `idx_tuneps_ao_status` sur `status`
- `idx_tuneps_ao_publication` sur `publication_date`

---

## 6. TABLE: `tenders_armp`

**Description**: ARMP Madagascar

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `description` | TEXT | Oui | - | Description originale |
| `description_fr` | TEXT | Oui | - | Description en français |
| `publication_date` | TIMESTAMP | Oui | - | Date de publication |
| `expiration_date` | TIMESTAMP | Oui | - | Date d'expiration |
| `promoter` | TEXT | Oui | - | Promoteur |
| `source_id` | INTEGER | Oui | - | ID source |
| `avis_id` | INTEGER | Oui | - | ID avis |
| `external_url` | TEXT | Oui | - | URL externe |
| `montant` | VARCHAR(255) | Oui | - | Montant |
| `nature` | VARCHAR(100) | Oui | - | Nature |
| `country` | VARCHAR(100) | Oui | `'Madagascar'` | Pays |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |
| `api_id` | INTEGER | Oui | - | ID API |

### Index

- `idx_armp_reference` sur `reference`
- `idx_armp_status` sur `status`

---

## 7. TABLE: `tenders_pnud`

**Description**: PNUD/UNDP - Marchés internationaux

### Colonnes

Identique à `tenders_armp` (sans le défaut Madagascar sur `country`)

### Index

- `idx_pnud_reference` sur `reference`
- `idx_pnud_status` sur `status`

---

## 8. TABLE: `tenders_banque`

**Description**: Banque Mondiale

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `description` | TEXT | Oui | - | Description |
| `description_fr` | TEXT | Oui | - | Description FR |
| `publication_date` | TIMESTAMP | Oui | - | Date de publication |
| `expiration_date` | TIMESTAMP | Oui | - | Date d'expiration |
| `promoter` | TEXT | Oui | - | Promoteur |
| `source_id` | INTEGER | Oui | `1464` | ID source Banque Mondiale |
| `avis_id` | INTEGER | Oui | `8` | ID avis |
| `external_url` | TEXT | Oui | - | URL externe |
| `montant` | VARCHAR(255) | Oui | - | Montant |
| `nature` | VARCHAR(100) | Oui | - | Nature |
| `country` | VARCHAR(100) | Oui | - | Pays |
| `borrower` | VARCHAR(500) | Oui | - | Emprunteur |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |
| `api_id` | INTEGER | Oui | - | ID API |

### Index

- `idx_banque_reference` sur `reference`
- `idx_banque_status` sur `status`

---

## 9. TABLE: `tenders_boamp`

**Description**: BOAMP France - Bulletin Officiel des Annonces de Marchés Publics

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `description` | TEXT | Oui | - | Description |
| `description_fr` | TEXT | Oui | - | Description FR |
| `publication_date` | TIMESTAMP | Oui | - | Date de publication |
| `expiration_date` | TIMESTAMP | Oui | - | Date d'expiration |
| `promoter` | TEXT | Oui | - | Promoteur |
| `source_id` | INTEGER | Oui | - | ID source |
| `avis_id` | INTEGER | Oui | - | ID avis |
| `external_url` | TEXT | Oui | - | URL externe |
| `montant` | VARCHAR(255) | Oui | - | Montant |
| `nature` | VARCHAR(100) | Oui | - | Nature |
| `country` | VARCHAR(100) | Oui | `'France'` | Pays |
| `business_sector` | VARCHAR(255) | Oui | - | Secteur d'activité |
| `activity` | VARCHAR(255) | Oui | - | Activité |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |
| `api_id` | INTEGER | Oui | - | ID API |

### Index

- `idx_boamp_reference` sur `reference`
- `idx_boamp_status` sur `status`

---

## 10. TABLE: `tenders_haicop`

**Description**: HAICOP Tunisie

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `description` | TEXT | Oui | - | Description |
| `description_fr` | TEXT | Oui | - | Description FR |
| `publication_date` | TIMESTAMP | Oui | - | Date de publication |
| `expiration_date` | TIMESTAMP | Oui | - | Date d'expiration |
| `promoter` | TEXT | Oui | - | Promoteur |
| `source_id` | INTEGER | Oui | `279` | ID source HAICOP |
| `avis_id` | INTEGER | Oui | - | ID avis |
| `pays_id` | INTEGER | Oui | `219` | ID pays Tunisie |
| `external_url` | TEXT | Oui | - | URL externe |
| `montant` | VARCHAR(255) | Oui | - | Montant |
| `nature` | VARCHAR(100) | Oui | - | Nature |
| `country` | VARCHAR(100) | Oui | `'Tunisie'` | Pays |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |
| `api_id` | INTEGER | Oui | - | ID API |

### Index

- `idx_haicop_reference` sur `reference`
- `idx_haicop_status` sur `status`

---

## 11. TABLE: `tenders_expertise`

**Description**: Expertise France

### Colonnes

Identique à `tenders_pnud`

### Index

- `idx_expertise_reference` sur `reference`
- `idx_expertise_status` sur `status`

---

## 12. TABLE: `tenders_ppda`

**Description**: PPDA Malawi - Public Procurement and Disposal of Assets

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) |
| `title` | TEXT | Oui | - | Titre |
| `description` | TEXT | Oui | - | Description |
| `promoter` | TEXT | Oui | - | Promoteur |
| `publication_date` | DATE | Oui | - | Date de publication |
| `expiration_date` | DATE | Oui | - | Date d'expiration |
| `document_url` | TEXT | Oui | - | URL du document |
| `country` | VARCHAR(100) | Oui | `'Malawi'` | Pays |
| `nature` | VARCHAR(100) | Oui | `'public'` | Nature |
| `type` | VARCHAR(100) | Oui | `'national'` | Type |
| `funding_source_type` | VARCHAR(100) | Oui | `'national'` | Type de financement |
| `caution` | VARCHAR(255) | Oui | `'0'` | Caution |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `validation_date` | TIMESTAMP | Oui | - | Date de validation |
| `api_id` | INTEGER | Oui | - | ID API |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |

### Index

- `idx_ppda_reference` sur `reference`
- `idx_ppda_status` sur `status`
- `idx_ppda_publication` sur `publication_date`

---

## 13. TABLE: `jobs_niger`

**Description**: Offres d'emploi Niger (NigerEmploi.com)

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) Format: `NE-{id}` |
| `title` | TEXT | Oui | - | Titre de l'emploi |
| `description` | TEXT | Oui | - | Description |
| `promoter` | TEXT | Oui | - | Recruteur/Entreprise |
| `publication_date` | DATE | Oui | - | Date de publication |
| `expiration_date` | DATE | Oui | - | Date d'expiration |
| `location` | VARCHAR(255) | Oui | - | Lieu |
| `url` | TEXT | Oui | - | URL de l'annonce |
| `country` | VARCHAR(100) | Oui | `'Niger'` | Pays |
| `category` | VARCHAR(100) | Oui | - | Catégorie |
| `contract_type` | VARCHAR(100) | Oui | - | Type de contrat |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `validation_date` | TIMESTAMP | Oui | - | Date de validation |
| `api_id` | INTEGER | Oui | - | ID API |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |

### Index

- `idx_niger_reference` sur `reference`
- `idx_niger_status` sur `status`
- `idx_niger_publication` sur `publication_date`

### Endpoints API

- `GET /jobs` - Liste des emplois
- `GET /stats` - Statistiques
- `POST /scrape` - Lancer le scraping
- `POST /validate/<reference>` - Valider un emploi
- `DELETE /delete/<reference>` - Supprimer un emploi
- `POST /delete_all` - Supprimer tous les emplois en attente

---

## 14. TABLE: `jobs_somalia`

**Description**: Offres d'emploi Somalia (SomaliaJobs.com)

### Colonnes

| Colonne | Type | Null | Défaut | Description |
|---------|------|------|--------|-------------|
| `id` | SERIAL | Non | AUTO | Identifiant unique |
| `reference` | VARCHAR(255) | Non | - | Référence unique (UNIQUE) Format: `SJ-{id}` |
| `title` | TEXT | Oui | - | Titre de l'emploi |
| `description` | TEXT | Oui | - | Description |
| `promoter` | TEXT | Oui | - | Recruteur/Entreprise |
| `publication_date` | DATE | Oui | - | Date de publication |
| `location` | VARCHAR(255) | Oui | - | Lieu |
| `url` | TEXT | Oui | - | URL de l'annonce |
| `country` | VARCHAR(100) | Oui | `'Somalia'` | Pays |
| `category` | VARCHAR(100) | Oui | - | Catégorie |
| `contract_type` | VARCHAR(100) | Oui | - | Type de contrat |
| `status` | VARCHAR(50) | Oui | `'pending'` | Statut |
| `validation_date` | TIMESTAMP | Oui | - | Date de validation |
| `api_id` | INTEGER | Oui | - | ID API (appeloffres.net staging) |
| `created_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de création |
| `updated_at` | TIMESTAMP | Oui | `CURRENT_TIMESTAMP` | Date de mise à jour |

### Index

- `idx_somalia_reference` sur `reference`
- `idx_somalia_status` sur `status`
- `idx_somalia_publication` sur `publication_date`

### Endpoints API

- `GET /jobs` - Liste des emplois
- `GET /stats` - Statistiques
- `POST /scrape` - Lancer le scraping
- `POST /validate/<reference>` - Valider et envoyer vers API staging
- `DELETE /delete/<reference>` - Supprimer un emploi
- `POST /delete_all` - Supprimer tous les emplois en attente

### Intégration API

Somalia envoie les emplois vers l'API staging: `https://be-stg.appeloffres.net/api`

- **Login**: `POST /api/auth/login`
- **Créer promoteur**: `POST /api/promoter`
- **Envoyer tender**: `POST /api/tender`

**Configuration**:
- Source ID: `1701` (Somalia Jobs)
- Country ID: `195` (Somalia)
- Avis ID: `11` (Avis standard)

---

## 🔄 Vue globale: `pending_tenders_all`

**Description**: Vue consolidée de tous les appels d'offres en attente

### Colonnes

- `source` (TEXT) - Source de l'appel d'offres
- `reference` (VARCHAR) - Référence unique
- `description` (TEXT) - Description
- `publication_date` (TEXT) - Date de publication (format texte)
- `created_at` (TIMESTAMP) - Date de création

Cette vue combine les données de toutes les tables `tenders_*` avec `status = 'pending'`.

---

## 🔧 Triggers et fonctions

### Fonction: `update_updated_at_column()`

Mise à jour automatique du timestamp `updated_at` lors d'un UPDATE.

**Appliqué sur toutes les tables** (sauf `tenders_benin`):
- `tenders_mediacongo`
- `tenders_relief`
- `tenders_tuneps`
- `tenders_tuneps_ao`
- `tenders_armp`
- `tenders_pnud`
- `tenders_banque`
- `tenders_boamp`
- `tenders_haicop`
- `tenders_expertise`
- `tenders_ppda`
- `jobs_niger`
- `jobs_somalia`

---

## 📝 Statuts possibles

### Pour les tenders

| Statut | Description |
|--------|-------------|
| `pending` | En attente de validation |
| `validated` | Validé et envoyé à l'API |
| `failed` | Échec de validation/envoi |

---

## 🗄️ Connexion à la base de données

### Configuration par défaut

```
Host: localhost
Port: 5432
Database: tenders_db
User: postgres
Password: postgres
```

### Variables d'environnement

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tenders_db
DB_USER=postgres
DB_PASSWORD=postgres
```

---

## 📊 Requêtes utiles

### Compter tous les tenders par source

```sql
SELECT 'BENIN' as source, COUNT(*) as count FROM tenders_benin
UNION ALL
SELECT 'MEDIACONGO', COUNT(*) FROM tenders_mediacongo
UNION ALL
SELECT 'RELIEF', COUNT(*) FROM tenders_relief
UNION ALL
SELECT 'TUNEPS', COUNT(*) FROM tenders_tuneps
UNION ALL
SELECT 'TUNEPS_AO', COUNT(*) FROM tenders_tuneps_ao
UNION ALL
SELECT 'ARMP', COUNT(*) FROM tenders_armp
UNION ALL
SELECT 'PNUD', COUNT(*) FROM tenders_pnud
UNION ALL
SELECT 'BANQUE', COUNT(*) FROM tenders_banque
UNION ALL
SELECT 'BOAMP', COUNT(*) FROM tenders_boamp
UNION ALL
SELECT 'HAICOP', COUNT(*) FROM tenders_haicop
UNION ALL
SELECT 'EXPERTISE', COUNT(*) FROM tenders_expertise
UNION ALL
SELECT 'PPDA', COUNT(*) FROM tenders_ppda
UNION ALL
SELECT 'NIGER JOBS', COUNT(*) FROM jobs_niger
UNION ALL
SELECT 'SOMALIA JOBS', COUNT(*) FROM jobs_somalia;
```

### Tenders en attente par source

```sql
SELECT source, COUNT(*) as pending_count
FROM pending_tenders_all
GROUP BY source
ORDER BY pending_count DESC;
```

### Derniers tenders créés

```sql
SELECT source, reference, LEFT(description, 100) as description_preview, created_at
FROM pending_tenders_all
ORDER BY created_at DESC
LIMIT 20;
```

### Statistiques par statut (exemple TUNEPS)

```sql
SELECT status, COUNT(*) as count
FROM tenders_tuneps
GROUP BY status;
```

---

## 🚀 Maintenance

### Backup de la base

```bash
docker exec postgres_tenders pg_dump -U postgres tenders_db > backup_$(date +%Y%m%d).sql
```

### Restore

```bash
docker exec -i postgres_tenders psql -U postgres tenders_db < backup_20260102.sql
```

### Nettoyer les anciens tenders (> 90 jours)

```sql
DELETE FROM tenders_tuneps WHERE created_at < NOW() - INTERVAL '90 days' AND status = 'validated';
```

---

## 📅 Dernière mise à jour

**Date**: 2026-01-02
**Version**: 1.0
**Auteur**: Système d'extraction automatique
