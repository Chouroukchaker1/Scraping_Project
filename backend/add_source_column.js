// Script Node.js pour ajouter la colonne 'source' à tenders_haicop
const { Client } = require('pg');

const client = new Client({
  host: 'localhost',
  port: 5432,
  database: 'tenders_db',
  user: 'tender_user',
  password: 'tender_password_2024'
});

async function addSourceColumn() {
  try {
    await client.connect();
    console.log('✅ Connecté à PostgreSQL');

    // Vérifier si la colonne existe
    const checkResult = await client.query(`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_name='tenders_haicop' AND column_name='source'
    `);

    if (checkResult.rows.length > 0) {
      console.log('✅ Colonne "source" existe déjà');
    } else {
      console.log('➕ Ajout de la colonne "source"...');
      await client.query(`
        ALTER TABLE tenders_haicop
        ADD COLUMN source VARCHAR(255) DEFAULT 'MarchesPublicsTN'
      `);
      console.log('✅ Colonne "source" ajoutée avec succès');
    }

    // Mettre à jour les valeurs NULL ou vides
    const updateResult = await client.query(`
      UPDATE tenders_haicop
      SET source = 'MarchesPublicsTN'
      WHERE source IS NULL OR source = ''
    `);

    console.log(`✅ ${updateResult.rowCount} offres mises à jour avec source='MarchesPublicsTN'`);

    // Vérifier le résultat
    const countResult = await client.query(`
      SELECT COUNT(*) FROM tenders_haicop WHERE source = 'MarchesPublicsTN'
    `);

    console.log(`✅ Total: ${countResult.rows[0].count} offres avec source='MarchesPublicsTN'`);

    console.log('\n✅ Migration terminée avec succès!');

  } catch (err) {
    console.error('❌ Erreur:', err.message);
    console.error(err.stack);
  } finally {
    await client.end();
  }
}

addSourceColumn();
