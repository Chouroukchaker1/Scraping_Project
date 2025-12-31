-- Script SQL pour ajouter la colonne 'source' à la table tenders_haicop
-- Exécutez ce script dans pgAdmin ou via psql

-- Ajouter la colonne 'source' si elle n'existe pas
ALTER TABLE tenders_haicop
ADD COLUMN IF NOT EXISTS source VARCHAR(255) DEFAULT 'MarchesPublicsTN';

-- Mettre à jour les offres existantes qui n'ont pas de source
UPDATE tenders_haicop
SET source = 'MarchesPublicsTN'
WHERE source IS NULL OR source = '';

-- Vérifier le résultat
SELECT COUNT(*) as total_offres,
       COUNT(CASE WHEN source = 'MarchesPublicsTN' THEN 1 END) as offres_avec_source
FROM tenders_haicop;
