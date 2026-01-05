import sqlite3
from sqlite3 import Error

DB_FILE = "tealium_manager.db"

def create_connection():
    """Crée une connexion à la base de données SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Error as e:
        print(f"Erreur de connexion à la base de données: {e}")
    return conn

def create_tables(conn):
    """Crée les tables nécessaires si elles n'existent pas."""
    try:
        cursor = conn.cursor()
        # Table pour les configurations générales (email, clé API chiffrée)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value BLOB
            );
        """)
        # Table pour stocker les profils découverts et leur état de sélection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                is_selected INTEGER NOT NULL DEFAULT 0,
                UNIQUE(account_name, profile_name)
            );
        """)
        # Table pour mettre en cache les détails des révisions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revisions (
                revision_id TEXT NOT NULL,
                account TEXT NOT NULL,
                profile TEXT NOT NULL,
                details_json TEXT NOT NULL,
                PRIMARY KEY (revision_id, account, profile)
            );
        """)
        conn.commit()
        print("INFO: Tables de la base de données vérifiées/créées.")
    except Error as e:
        print(f"Erreur lors de la création des tables: {e}")

def init_database():
    """Initialise la base de données et les tables."""
    conn = create_connection()
    if conn:
        create_tables(conn)
        conn.close()

# --- Fonctions CRUD ---

def save_setting(key: str, value):
    """Sauvegarde un paramètre (clé-valeur). Gère str et bytes."""
    conn = create_connection()
    if not conn: return

    try:
        sql = "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        cursor = conn.cursor()
        cursor.execute(sql, (key, value))
        conn.commit()
    except Error as e:
        print(f"Erreur lors de la sauvegarde du paramètre '{key}': {e}")
    finally:
        conn.close()

def load_setting(key: str):
    """Charge un paramètre. Retourne la valeur ou None."""
    conn = create_connection()
    if not conn: return None
    
    try:
        sql = "SELECT value FROM settings WHERE key = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (key,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        print(f"Erreur lors du chargement du paramètre '{key}': {e}")
        return None
    finally:
        conn.close()

def save_profiles(profiles_data: list):
    """
    Sauvegarde une liste de profils. Met à jour 'is_selected' si le profil existe déjà.
    profiles_data est une liste de tuples: (account_name, profile_name, is_selected)
    """
    conn = create_connection()
    if not conn: return

    try:
        # Utilise ON CONFLICT pour gérer les cas où le profil existe déjà (UPSERT)
        sql = """
            INSERT INTO profiles (account_name, profile_name, is_selected)
            VALUES (?, ?, ?)
            ON CONFLICT(account_name, profile_name) 
            DO UPDATE SET is_selected = excluded.is_selected;
        """
        cursor = conn.cursor()
        cursor.executemany(sql, profiles_data)
        conn.commit()
    except Error as e:
        print(f"Erreur lors de la sauvegarde des profils: {e}")
    finally:
        conn.close()

def load_profiles_by_account(account_name: str) -> list:
    """Charge les profils (nom, is_selected) pour un compte donné."""
    conn = create_connection()
    if not conn: return []

    try:
        sql = "SELECT profile_name, is_selected FROM profiles WHERE account_name = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (account_name,))
        return cursor.fetchall() # Retourne une liste de tuples (profile_name, is_selected)
    except Error as e:
        print(f"Erreur lors du chargement des profils pour '{account_name}': {e}")
        return []
    finally:
        conn.close()

def unselect_all_profiles():
    """Met le flag is_selected à 0 pour tous les profils."""
    conn = create_connection()
    if not conn: return
    
    try:
        sql = "UPDATE profiles SET is_selected = 0"
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
    except Error as e:
        print(f"Erreur lors de la désélection de tous les profils: {e}")
    finally:
        conn.close()

def load_all_selected_profiles() -> list:
    """Charge tous les profils où is_selected = 1."""
    conn = create_connection()
    if not conn: return []

    try:
        sql = "SELECT account_name, profile_name FROM profiles WHERE is_selected = 1"
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall() # Retourne une liste de tuples (account_name, profile_name)
    except Error as e:
        print(f"Erreur lors du chargement des profils sélectionnés: {e}")
        return []
    finally:
        conn.close()

# --- Fonctions pour le cache des révisions ---

def save_revisions_details(revisions_data: list):
    """
    Sauvegarde les détails de plusieurs révisions dans la table de cache.
    revisions_data est une liste de tuples: (revision_id, account, profile, details_json)
    """
    conn = create_connection()
    if not conn: return

    try:
        # On ignore les IDs qui existent déjà
        sql = "INSERT OR IGNORE INTO revisions (revision_id, account, profile, details_json) VALUES (?, ?, ?, ?)"
        cursor = conn.cursor()
        cursor.executemany(sql, revisions_data)
        conn.commit()
        print(f"INFO: {cursor.rowcount} nouvelles révisions sauvegardées en cache.")
    except Error as e:
        print(f"Erreur lors de la sauvegarde des détails de révisions: {e}")
    finally:
        conn.close()

def get_cached_revision_ids(account: str, profile: str) -> set:
    """Récupère l'ensemble des IDs de révision déjà en cache pour un contexte."""
    conn = create_connection()
    if not conn: return set()

    try:
        sql = "SELECT revision_id FROM revisions WHERE account = ? AND profile = ?"
        cursor = conn.cursor()
        cursor.execute(sql, (account, profile))
        return {row[0] for row in cursor.fetchall()}
    except Error as e:
        print(f"Erreur lors de la récupération des IDs de révision en cache: {e}")
        return set()
    finally:
        conn.close()

def get_cached_revisions_details_by_date(account: str, profile: str, start_date: str, end_date: str) -> list:
    """
    Charge les détails des révisions en cache pour une plage de dates.
    Les dates sont au format YYYYMMDD.
    """
    conn = create_connection()
    if not conn: return []

    try:
        # On filtre sur le revision_id qui est un timestamp YYYYMMDD...
        sql = "SELECT details_json FROM revisions WHERE account = ? AND profile = ? AND revision_id >= ? AND revision_id <= ? ORDER BY revision_id DESC"
        # On ajoute '235959' à la date de fin pour inclure toute la journée
        cursor = conn.cursor()
        cursor.execute(sql, (account, profile, f"{start_date}000000", f"{end_date}235959"))
        return [row[0] for row in cursor.fetchall()]
    except Error as e:
        print(f"Erreur lors du chargement des révisions en cache par date: {e}")
        return []
    finally:
        conn.close()

def get_cached_revisions_details(account: str, profile: str) -> list:
    """Charge tous les détails des révisions en cache pour un profil."""
    conn = create_connection()
    if not conn: return []

    try:
        sql = "SELECT details_json FROM revisions WHERE account = ? AND profile = ? ORDER BY revision_id DESC"
        cursor = conn.cursor()
        cursor.execute(sql, (account, profile))
        return [row[0] for row in cursor.fetchall()]
    except Error as e:
        print(f"Erreur lors du chargement des révisions en cache: {e}")
        return []
    finally:
        conn.close()

def clear_revisions_cache():
    """Vide complètement la table de cache des révisions."""
    conn = create_connection()
    if not conn: return
    
    try:
        sql = "DELETE FROM revisions"
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        print(f"INFO: Cache des révisions vidé ({cursor.rowcount} lignes supprimées).")
    except Error as e:
        print(f"Erreur lors du vidage du cache des révisions: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    # Pour initialiser la base de données manuellement
    print("Initialisation de la base de données...")
    init_database()
    print("Base de données prête.")