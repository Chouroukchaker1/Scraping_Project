"""
Script pour ajouter la colonne 'source' à la table tenders_haicop si elle n'existe pas
"""
import psycopg2

DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "tenders_db"
DB_USER = "tender_user"
DB_PASSWORD = "tender_password_2024"
TABLE_NAME = "tenders_haicop"

def add_source_column():
    """Ajoute la colonne source si elle n'existe pas"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        # Vérifier si la colonne existe
        cursor.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{TABLE_NAME}' AND column_name = 'source'
        """)

        if cursor.fetchone():
            print(f"La colonne 'source' existe deja dans {TABLE_NAME}")
        else:
            print(f"Ajout de la colonne 'source' dans {TABLE_NAME}...")

            cursor.execute(f"""
                ALTER TABLE {TABLE_NAME}
                ADD COLUMN source VARCHAR(255) DEFAULT 'MarchesPublicsTN'
            """)

            conn.commit()
            print(f"Colonne 'source' ajoutee avec succes")

        # Mettre à jour les offres existantes qui n'ont pas de source
        cursor.execute(f"""
            UPDATE {TABLE_NAME}
            SET source = 'MarchesPublicsTN'
            WHERE source IS NULL OR source = ''
        """)

        updated_count = cursor.rowcount
        conn.commit()

        print(f"Mise a jour de {updated_count} offres avec source='MarchesPublicsTN'")

        cursor.close()
        conn.close()

        print("Verification terminee avec succes!")

    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_source_column()
