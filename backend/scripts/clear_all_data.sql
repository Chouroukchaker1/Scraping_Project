-- Script pour vider toutes les tables de données
-- Exécuter ce script pour supprimer toutes les offres de toutes les sources

-- Vider la table TUNEPS Consultations
TRUNCATE TABLE tenders_tuneps RESTART IDENTITY CASCADE;

-- Vider la table TUNEPS Appels d'Offres
TRUNCATE TABLE tenders_tuneps_ao RESTART IDENTITY CASCADE;

-- Vider la table Banque Mondiale
TRUNCATE TABLE tenders_banque RESTART IDENTITY CASCADE;

-- Vider la table PNUD
TRUNCATE TABLE tenders_pnud RESTART IDENTITY CASCADE;

-- Vider la table ARMP
TRUNCATE TABLE tenders_armp RESTART IDENTITY CASCADE;

-- Vider la table BOAMP
TRUNCATE TABLE tenders_boamp RESTART IDENTITY CASCADE;

-- Vider la table Expertise France
TRUNCATE TABLE tenders_expertise RESTART IDENTITY CASCADE;

-- Vider la table HAICOP
TRUNCATE TABLE tenders_haicop RESTART IDENTITY CASCADE;

-- Afficher un message de confirmation
SELECT 'Toutes les tables ont été vidées avec succès!' AS message;
