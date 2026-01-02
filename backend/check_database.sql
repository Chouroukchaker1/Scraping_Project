-- ============================================================================
-- Script de Vérification de la Base de Données
-- ============================================================================
-- À exécuter pour vérifier que toutes les tables sont bien créées
--
-- Utilisation:
-- docker exec -it postgres_tenders psql -U tender_user -d tenders_db -f check_database.sql
-- Ou depuis psql: \i check_database.sql
-- ============================================================================

\echo '======================================'
\echo 'VÉRIFICATION BASE DE DONNÉES'
\echo '======================================'
\echo ''

\echo '1. Informations Générales'
\echo '--------------------------------------'
SELECT version();
\echo ''

\echo '2. Liste des Tables (14 attendues)'
\echo '--------------------------------------'
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
\echo ''

\echo '3. Nombre Total de Tables'
\echo '--------------------------------------'
SELECT COUNT(*) as total_tables
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';
\echo ''

\echo '4. Index Créés'
\echo '--------------------------------------'
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
\echo ''

\echo '5. Statistiques par Table'
\echo '--------------------------------------'
-- Benin
SELECT
    'tenders_benin' as table_name,
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'validated') as validated
FROM tenders_benin
UNION ALL
-- MediaCongo
SELECT
    'tenders_mediacongo',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_mediacongo
UNION ALL
-- Relief
SELECT
    'tenders_relief',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_relief
UNION ALL
-- TUNEPS
SELECT
    'tenders_tuneps',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_tuneps
UNION ALL
-- TUNEPS AO
SELECT
    'tenders_tuneps_ao',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_tuneps_ao
UNION ALL
-- ARMP
SELECT
    'tenders_armp',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_armp
UNION ALL
-- PNUD
SELECT
    'tenders_pnud',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_pnud
UNION ALL
-- Banque
SELECT
    'tenders_banque',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_banque
UNION ALL
-- BOAMP
SELECT
    'tenders_boamp',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_boamp
UNION ALL
-- HAICOP
SELECT
    'tenders_haicop',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_haicop
UNION ALL
-- Expertise
SELECT
    'tenders_expertise',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_expertise
UNION ALL
-- PPDA
SELECT
    'tenders_ppda',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_ppda
UNION ALL
-- GIZ
SELECT
    'tenders_giz',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM tenders_giz
UNION ALL
-- Niger
SELECT
    'jobs_niger',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM jobs_niger
UNION ALL
-- Somalia
SELECT
    'jobs_somalia',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'pending'),
    COUNT(*) FILTER (WHERE status = 'validated')
FROM jobs_somalia
ORDER BY table_name;
\echo ''

\echo '6. Colonnes de chaque Table'
\echo '--------------------------------------'
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name LIKE 'tenders_%' OR table_name LIKE 'jobs_%'
ORDER BY table_name, ordinal_position;
\echo ''

\echo '7. Triggers Actifs'
\echo '--------------------------------------'
SELECT
    event_object_table as table_name,
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table;
\echo ''

\echo '8. Vue Globale'
\echo '--------------------------------------'
SELECT COUNT(*) as total_pending_all_sources
FROM pending_tenders_all;
\echo ''

\echo '9. Dernières Offres Ajoutées (5 plus récentes)'
\echo '--------------------------------------'
SELECT
    source,
    reference,
    LEFT(description, 50) as description_preview,
    publication_date,
    created_at
FROM pending_tenders_all
ORDER BY created_at DESC
LIMIT 5;
\echo ''

\echo '10. Résumé Final'
\echo '--------------------------------------'
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    trigger_count INTEGER;
    total_rows INTEGER;
BEGIN
    -- Compter les tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE';

    -- Compter les index
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public';

    -- Compter les triggers
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers
    WHERE trigger_schema = 'public';

    -- Compter total des lignes (approximation)
    SELECT SUM(n_tup_ins) INTO total_rows
    FROM pg_stat_user_tables
    WHERE schemaname = 'public';

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RÉSUMÉ DE LA BASE DE DONNÉES';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables créées: % (attendu: 15)', table_count;
    RAISE NOTICE 'Index créés: %', index_count;
    RAISE NOTICE 'Triggers actifs: %', trigger_count;
    RAISE NOTICE 'Total lignes insérées: %', COALESCE(total_rows, 0);
    RAISE NOTICE '========================================';

    IF table_count = 15 THEN
        RAISE NOTICE '✅ Base de données correctement configurée!';
    ELSE
        RAISE WARNING '⚠️ Nombre de tables incorrect (attendu: 15, trouvé: %)', table_count;
    END IF;
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
END $$;

\echo ''
\echo '======================================'
\echo 'VÉRIFICATION TERMINÉE'
\echo '======================================'
