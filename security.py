from cryptography.fernet import Fernet

KEY_FILE = ".encryption.key"

def generate_and_save_key():
    """
    Génère une nouvelle clé de chiffrement et la sauvegarde dans le fichier KEY_FILE.
    Cette opération ne doit être faite qu'une seule fois.
    """
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
    print(f"INFO: Nouvelle clé de chiffrement générée dans {KEY_FILE}.")
    return key

def load_key():
    """
    Charge la clé de chiffrement depuis le fichier KEY_FILE.
    Si le fichier n'existe pas, il en génère un nouveau.
    """
    try:
        with open(KEY_FILE, "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        print(f"AVERTISSEMENT: Fichier de clé non trouvé. Génération d'une nouvelle clé.")
        return generate_and_save_key()

def encrypt_data(data: str, key: bytes) -> bytes:
    """
    Chiffre une chaîne de caractères.
    """
    if not data:
        return b''
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode('utf-8'))
    return encrypted_data

def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """
    Déchiffre une donnée binaire vers une chaîne de caractères.
    """
    if not encrypted_data:
        return ''
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode('utf-8')

# Note pour l'équipe : L'architecte doit s'assurer que .encryption.key est ajouté à .gitignore
