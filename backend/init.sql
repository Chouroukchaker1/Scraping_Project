-- Script d'initialisation PostgreSQL pour le système de tenders
-- Migration complète de MongoDB vers PostgreSQL

-- ============================================================================
-- TABLE BENIN
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_benin (
    id SERIAL PRIMARY KEY,
    ref VARCHAR(255) UNIQUE,
    description TEXT,
    date_publication VARCHAR(100),
    date_limite_depot VARCHAR(100),
    delai VARCHAR(100),
    autorite_contractante TEXT,
    lieu_execution TEXT,
    lien_pdf TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_benin_ref ON tenders_benin(ref);
CREATE INDEX IF NOT EXISTS idx_benin_status ON tenders_benin(status);
CREATE INDEX IF NOT EXISTS idx_benin_publication ON tenders_benin(date_publication);

-- ============================================================================
-- TABLE MEDIACONGO
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_mediacongo (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    start_bidding_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER,
    avis_id INTEGER,
    external_url TEXT,
    montant VARCHAR(100),
    fetched_at TIMESTAMP,
    category VARCHAR(100),
    country VARCHAR(100),
    nature VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    validation_date TIMESTAMP,
    api_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mediacongo_reference ON tenders_mediacongo(reference);
CREATE INDEX IF NOT EXISTS idx_mediacongo_status ON tenders_mediacongo(status);

-- ============================================================================
-- TABLE RELIEF
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_relief (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    start_bidding_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER,
    avis_id INTEGER,
    external_url TEXT,
    montant VARCHAR(100),
    fetched_at TIMESTAMP,
    category VARCHAR(100),
    country VARCHAR(100),
    nature VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    validation_date TIMESTAMP,
    api_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_relief_reference ON tenders_relief(reference);
CREATE INDEX IF NOT EXISTS idx_relief_status ON tenders_relief(status);

-- ============================================================================
-- TABLE TUNEPS (APPELS D'OFFRES)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_tuneps (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    full_content TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    opening_date TIMESTAMP,
    region VARCHAR(100),
    promoter TEXT,
    source_id INTEGER DEFAULT 817,
    avis_id INTEGER DEFAULT 2,
    pays_id INTEGER DEFAULT 219,
    currency_id INTEGER DEFAULT 111,
    nature VARCHAR(100) DEFAULT 'public',
    external_url TEXT,
    pdf_url TEXT,
    cautionnement VARCHAR(255),
    montant VARCHAR(255),
    batches JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    extraction_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tuneps_reference ON tenders_tuneps(reference);
CREATE INDEX IF NOT EXISTS idx_tuneps_status ON tenders_tuneps(status);
CREATE INDEX IF NOT EXISTS idx_tuneps_publication ON tenders_tuneps(publication_date);

-- ============================================================================
-- TABLE TUNEPS AO (APPELS D'OFFRES /portail/offres)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_tuneps_ao (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    full_content TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    opening_date TIMESTAMP,
    region VARCHAR(100),
    promoter TEXT,
    source_id INTEGER DEFAULT 817,
    avis_id INTEGER DEFAULT 2,
    pays_id INTEGER DEFAULT 219,
    currency_id INTEGER DEFAULT 111,
    nature VARCHAR(100) DEFAULT 'public',
    external_url TEXT,
    pdf_url TEXT,
    cautionnement VARCHAR(255),
    montant VARCHAR(255),
    batches JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    extraction_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tuneps_ao_reference ON tenders_tuneps_ao(reference);
CREATE INDEX IF NOT EXISTS idx_tuneps_ao_status ON tenders_tuneps_ao(status);
CREATE INDEX IF NOT EXISTS idx_tuneps_ao_publication ON tenders_tuneps_ao(publication_date);

-- ============================================================================
-- TABLE ARMP (Madagascar)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_armp (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER,
    avis_id INTEGER,
    external_url TEXT,
    montant VARCHAR(255),
    nature VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Madagascar',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_armp_reference ON tenders_armp(reference);
CREATE INDEX IF NOT EXISTS idx_armp_status ON tenders_armp(status);

-- ============================================================================
-- TABLE PNUD (UNDP)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_pnud (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER,
    avis_id INTEGER,
    external_url TEXT,
    montant VARCHAR(255),
    nature VARCHAR(100),
    country VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_pnud_reference ON tenders_pnud(reference);
CREATE INDEX IF NOT EXISTS idx_pnud_status ON tenders_pnud(status);

-- ============================================================================
-- TABLE BANQUE MONDIALE (World Bank)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_banque (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER DEFAULT 1464,
    avis_id INTEGER DEFAULT 8,
    external_url TEXT,
    montant VARCHAR(255),
    nature VARCHAR(100),
    country VARCHAR(100),
    borrower VARCHAR(500),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_banque_reference ON tenders_banque(reference);
CREATE INDEX IF NOT EXISTS idx_banque_status ON tenders_banque(status);

-- ============================================================================
-- TABLE BOAMP (France Marchés)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_boamp (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER,
    avis_id INTEGER,
    external_url TEXT,
    montant VARCHAR(255),
    nature VARCHAR(100),
    country VARCHAR(100) DEFAULT 'France',
    business_sector VARCHAR(255),
    activity VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_boamp_reference ON tenders_boamp(reference);
CREATE INDEX IF NOT EXISTS idx_boamp_status ON tenders_boamp(status);

-- ============================================================================
-- TABLE HAICOP (Tunisie)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_haicop (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER DEFAULT 279,
    avis_id INTEGER,
    pays_id INTEGER DEFAULT 219,
    external_url TEXT,
    montant VARCHAR(255),
    nature VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Tunisie',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_haicop_reference ON tenders_haicop(reference);
CREATE INDEX IF NOT EXISTS idx_haicop_status ON tenders_haicop(status);

-- ============================================================================
-- TABLE EXPERTISE FRANCE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_expertise (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_fr TEXT,
    publication_date TIMESTAMP,
    expiration_date TIMESTAMP,
    promoter TEXT,
    source_id INTEGER,
    avis_id INTEGER,
    external_url TEXT,
    montant VARCHAR(255),
    nature VARCHAR(100) DEFAULT 'public',
    country VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_expertise_reference ON tenders_expertise(reference);
CREATE INDEX IF NOT EXISTS idx_expertise_status ON tenders_expertise(status);

-- ============================================================================
-- TABLE PPDA (Public Procurement Malawi)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders_ppda (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    promoter TEXT,
    publication_date DATE,
    expiration_date DATE,
    document_url TEXT,
    country VARCHAR(100) DEFAULT 'Malawi',
    nature VARCHAR(100) DEFAULT 'public',
    type VARCHAR(100) DEFAULT 'national',
    funding_source_type VARCHAR(100) DEFAULT 'national',
    caution VARCHAR(255) DEFAULT '0',
    status VARCHAR(50) DEFAULT 'pending',
    validation_date TIMESTAMP,
    api_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ppda_reference ON tenders_ppda(reference);
CREATE INDEX IF NOT EXISTS idx_ppda_status ON tenders_ppda(status);
CREATE INDEX IF NOT EXISTS idx_ppda_publication ON tenders_ppda(publication_date);

-- ============================================================================
-- VUE GLOBALE - Toutes les offres en attente
-- ============================================================================
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
FROM tenders_ppda WHERE status = 'pending';

-- ============================================================================
-- FONCTION TRIGGER pour mise à jour automatique du timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Appliquer les triggers sur toutes les tables
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE 'tenders_%'
        AND table_name != 'tenders_benin'  -- Benin n'a pas updated_at
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_%s_updated_at ON %I', tbl, tbl);
        EXECUTE format('CREATE TRIGGER update_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()', tbl, tbl);
    END LOOP;
END $$;

-- ============================================================================
-- STATISTIQUES D'INITIALISATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'PostgreSQL Database Initialized!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - tenders_benin';
    RAISE NOTICE '  - tenders_mediacongo';
    RAISE NOTICE '  - tenders_relief';
    RAISE NOTICE '  - tenders_tuneps';
    RAISE NOTICE '  - tenders_tuneps_ao';
    RAISE NOTICE '  - tenders_armp';
    RAISE NOTICE '  - tenders_pnud';
    RAISE NOTICE '  - tenders_banque';
    RAISE NOTICE '  - tenders_boamp';
    RAISE NOTICE '  - tenders_haicop';
    RAISE NOTICE '  - tenders_expertise';
    RAISE NOTICE '  - tenders_ppda';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'View created: pending_tenders_all';
    RAISE NOTICE '========================================';
END $$;
