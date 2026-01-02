-- ============================================================================
-- Script pour Ajouter la Table GIZ Manquante
-- ============================================================================
-- À exécuter sur une base de données existante qui n'a que 14 tables
--
-- Utilisation:
-- docker exec -it postgres_tenders psql -U tender_user -d tenders_db -f backend/add_giz_table.sql
-- ============================================================================

\echo '======================================'
\echo 'AJOUT TABLE GIZ'
\echo '======================================'
\echo ''

-- Vérifier si la table existe déjà
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tenders_giz') THEN
        RAISE NOTICE '⚠️  La table tenders_giz existe déjà!';
    ELSE
        RAISE NOTICE '✅ La table tenders_giz n''existe pas, création en cours...';
    END IF;
END $$;

-- ============================================================================
-- Créer la table GIZ
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_giz (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    date_publication TIMESTAMP,
    date_limite TIMESTAMP,
    promoter TEXT DEFAULT 'GIZ',
    type VARCHAR(255),
    pays VARCHAR(255),
    source_id INTEGER DEFAULT 1760,
    avis_id INTEGER DEFAULT 1,
    project_id VARCHAR(255),
    lien_details TEXT,
    pdf_links JSONB,
    lots JSONB,
    secteur_activite VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    validation_date TIMESTAMP,
    api_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX IF NOT EXISTS idx_giz_reference ON tenders_giz(reference);
CREATE INDEX IF NOT EXISTS idx_giz_status ON tenders_giz(status);
CREATE INDEX IF NOT EXISTS idx_giz_publication ON tenders_giz(date_publication);

-- Trigger pour updated_at
DROP TRIGGER IF EXISTS update_tenders_giz_updated_at ON tenders_giz;
CREATE TRIGGER update_tenders_giz_updated_at
    BEFORE UPDATE ON tenders_giz
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

\echo ''
\echo '✅ Table tenders_giz créée avec succès!'
\echo ''

-- ============================================================================
-- Mettre à jour la vue pending_tenders_all
-- ============================================================================
\echo 'Mise à jour de la vue pending_tenders_all...'

DROP VIEW IF EXISTS pending_tenders_all;

CREATE OR REPLACE VIEW pending_tenders_all AS
SELECT 'BENIN' as source, ref as reference, description, date_publication::text as publication_date, created_at
FROM tenders_benin WHERE status = 'pending'
UNION ALL
SELECT 'MEDIACONGO' as source, reference, description, publication_date::text, created_at
FROM tenders_mediacongo WHERE status = 'pending'
UNION ALL
SELECT 'RELIEF' as source, reference, description, publication_date::text, created_at
FROM tenders_relief WHERE status = 'pending'
UNION ALL
SELECT 'TUNEPS' as source, reference, description, publication_date::text, created_at
FROM tenders_tuneps WHERE status = 'pending'
UNION ALL
SELECT 'TUNEPS_AO' as source, reference, description, publication_date::text, created_at
FROM tenders_tuneps_ao WHERE status = 'pending'
UNION ALL
SELECT 'ARMP' as source, reference, description, publication_date::text, created_at
FROM tenders_armp WHERE status = 'pending'
UNION ALL
SELECT 'PNUD' as source, reference, description, publication_date::text, created_at
FROM tenders_pnud WHERE status = 'pending'
UNION ALL
SELECT 'BANQUE' as source, reference, description, publication_date::text, created_at
FROM tenders_banque WHERE status = 'pending'
UNION ALL
SELECT 'BOAMP' as source, reference, description, publication_date::text, created_at
FROM tenders_boamp WHERE status = 'pending'
UNION ALL
SELECT 'HAICOP' as source, reference, description, publication_date::text, created_at
FROM tenders_haicop WHERE status = 'pending'
UNION ALL
SELECT 'EXPERTISE' as source, reference, description, publication_date::text, created_at
FROM tenders_expertise WHERE status = 'pending'
UNION ALL
SELECT 'PPDA' as source, reference, description, publication_date::text, created_at
FROM tenders_ppda WHERE status = 'pending'
UNION ALL
SELECT 'GIZ' as source, reference, description, date_publication::text, created_at
FROM tenders_giz WHERE status = 'pending';

\echo '✅ Vue pending_tenders_all mise à jour!'
\echo ''

-- ============================================================================
-- Vérification finale
-- ============================================================================
\echo 'Vérification finale...'
\echo ''

-- Compter les tables
SELECT COUNT(*) as total_tables
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';

\echo ''
\echo '======================================'
\echo '✅ MIGRATION TERMINÉE'
\echo '======================================'
\echo 'La table tenders_giz a été ajoutée.'
\echo 'Total des tables: 15'
\echo '======================================'
