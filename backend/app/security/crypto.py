from cryptography.fernet import Fernet
from app.config import settings
import base64

def get_fernet_cipher() -> Fernet:
    key = settings.FERNET_MASTER_KEY
    # Ensure key is valid 32-byte base64url encoded
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Fallback derive deterministic urlsafe base64 if user gave a raw passphrase
        raw = key.encode("utf-8")[:32].ljust(32, b"0")
        encoded_key = base64.urlsafe_b64encode(raw)
        return Fernet(encoded_key)

def encrypt_credential(secret_value: str) -> str:
    """Encrypt a secret credential before persisting to MongoDB."""
    if not secret_value:
        return ""
    cipher = get_fernet_cipher()
    encrypted_bytes = cipher.encrypt(secret_value.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_credential(encrypted_value: str) -> str:
    """Decrypt a secret credential in-memory when making external calls."""
    if not encrypted_value:
        return ""
    cipher = get_fernet_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_value.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
