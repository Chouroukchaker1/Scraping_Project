"""
Script simple pour ajouter la colonne source
"""
import sys
import psycopg2

# Fix encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    # Connexion directe
    conn = psycopg2.connect(
        "host=localhost port=5432 dbname=tenders_db user=tender_user password=tender_password_2024"
    )

    cursor = conn.cursor()

    # Vérifier si la colonne existe
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='tenders_haicop' AND column_name='source'
    """)

    if cursor.fetchone():
        print("✅ Colonne 'source' existe déjà")
    else:
        print("➕ Ajout de la colonne 'source'...")
        cursor.execute("""
            ALTER TABLE tenders_haicop
            ADD COLUMN source VARCHAR(255) DEFAULT 'MarchesPublicsTN'
        """)
        conn.commit()
        print("✅ Colonne 'source' ajoutée avec succès")

    # Mettre à jour les valeurs NULL
    cursor.execute("""
        UPDATE tenders_haicop
        SET source = 'MarchesPublicsTN'
        WHERE source IS NULL OR source = ''
    """)

    updated = cursor.rowcount
    conn.commit()

    print(f"✅ {updated} offres mises à jour avec source='MarchesPublicsTN'")

    # Vérifier le résultat
    cursor.execute("SELECT COUNT(*) FROM tenders_haicop WHERE source = 'MarchesPublicsTN'")
    count = cursor.fetchone()[0]
    print(f"✅ Total: {count} offres avec source='MarchesPublicsTN'")

    cursor.close()
    conn.close()

    print("\n✅ Migration terminée avec succès!")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
