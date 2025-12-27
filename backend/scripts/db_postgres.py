"""
Module helper pour PostgreSQL - Remplace MongoDB
Utilisé par tous les scrapers
"""
import os
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from contextlib import contextmanager

# Configuration PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tenders_db")
DB_USER = os.getenv("DB_USER", "tender_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tender_password_2024")


@contextmanager
def get_db_connection():
    """Context manager pour connexion PostgreSQL"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    try:
        yield conn
    finally:
        conn.close()


class PostgreSQLHelper:
    """Helper class pour opérations PostgreSQL communes"""

    @staticmethod
    def insert_tenders(table_name, data_list, fields_mapping):
        """
        Insert tenders into PostgreSQL table

        Args:
            table_name: nom de la table (ex: 'tenders_benin')
            data_list: liste de dictionnaires à insérer
            fields_mapping: dict mapping {nom_champ_postgres: nom_champ_dict}

        Returns:
            nombre de lignes insérées
        """
        if not data_list:
            return 0

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Préparer les valeurs
            values = []
            for item in data_list:
                row = tuple(item.get(fields_mapping[field], '') for field in fields_mapping.keys())
                values.append(row)

            # Construire la requête
            fields = ', '.join(fields_mapping.keys())
            placeholders = ', '.join(['%s'] * len(fields_mapping))

            # Détecter la colonne unique pour ON CONFLICT
            unique_field = 'reference' if 'reference' in fields_mapping else 'ref'

            query = f"""
                INSERT INTO {table_name} ({fields})
                VALUES ({placeholders})
                ON CONFLICT ({unique_field}) DO NOTHING
            """

            cursor.executemany(query, values)
            inserted_count = cursor.rowcount
            conn.commit()
            cursor.close()

            return inserted_count

    @staticmethod
    def insert_one(table_name, data_dict):
        """Insert un seul record"""
        import json
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Liste des champs communs
            fields = ['reference', 'description', 'description_fr', 'publication_date',
                     'expiration_date', 'promoter', 'source_id', 'avis_id', 'external_url',
                     'montant', 'nature', 'country', 'status']

            values = [
                data_dict.get('reference'),
                data_dict.get('description'),
                data_dict.get('description_fr'),
                data_dict.get('publicationDate') or data_dict.get('publication_date'),
                data_dict.get('expirationDate') or data_dict.get('expiration_date'),
                data_dict.get('promoter'),
                data_dict.get('sourceId') or data_dict.get('source_id'),
                data_dict.get('avisId') or data_dict.get('avis_id'),
                data_dict.get('external_url'),
                data_dict.get('montant'),
                data_dict.get('nature', 'public'),
                data_dict.get('country') or data_dict.get('pays'),
                data_dict.get('status', 'pending')
            ]

            placeholders = ','.join(['%s'] * len(fields))
            query = f"""
                INSERT INTO {table_name} ({','.join(fields)})
                VALUES ({placeholders})
                ON CONFLICT (reference) DO NOTHING
                RETURNING id
            """

            try:
                cursor.execute(query, values)
                result = cursor.fetchone()
                conn.commit()
                cursor.close()
                return result[0] if result else None
            except Exception as e:
                conn.rollback()
                cursor.close()
                raise e

    @staticmethod
    def get_all(table_name, status=None):
        """Get all records from table"""
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if status:
                cursor.execute(f"SELECT * FROM {table_name} WHERE status = %s ORDER BY created_at DESC", (status,))
            else:
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY created_at DESC")

            results = cursor.fetchall()
            cursor.close()
            return results

    @staticmethod
    def count(table_name, status=None):
        """Count records"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE status = %s", (status,))
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")

            count = cursor.fetchone()[0]
            cursor.close()
            return count

    @staticmethod
    def delete(table_name, record_id):
        """Delete record by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE id = %s", (record_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            return deleted_count

    @staticmethod
    def update_status(table_name, record_id, new_status):
        """Update status of a record"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {table_name} SET status = %s WHERE id = %s",
                (new_status, record_id)
            )
            updated_count = cursor.rowcount
            conn.commit()
            cursor.close()
            return updated_count

    @staticmethod
    def get_existing_references(table_name):
        """Get set of existing references"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Essayer 'reference' puis 'ref'
            try:
                cursor.execute(f"SELECT reference FROM {table_name}")
                results = cursor.fetchall()
                cursor.close()
                return {row[0] for row in results if row[0]}
            except:
                cursor.execute(f"SELECT ref FROM {table_name}")
                results = cursor.fetchall()
                cursor.close()
                return {row[0] for row in results if row[0]}
