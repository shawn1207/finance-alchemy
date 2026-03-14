import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Vault:
    """A simple encryption vault for sensitive API keys."""
    
    _KEY_SALT = b'finance_alchemy_vault_salt' # In production, this should be unique and stored securely

    def __init__(self, master_password: str = None):
        # Use a provided password or fall back to a "machine-stable" identifier
        if not master_password:
            # Simple fallback for development: project directory path as a "stable" seed
            master_password = os.getcwd()
        
        self.fernet = self._derive_fernet(master_password)

    def _derive_fernet(self, password: str) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._KEY_SALT,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return a base64 encoded ciphertext."""
        if not plaintext:
            return ""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64 encoded ciphertext and return the plaintext."""
        if not ciphertext:
            return ""
        try:
            return self.fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            # If decryption fails (e.g. not encrypted), return as-is
            return ciphertext

# Global instance
_vault = Vault()

def encrypt_secret(val: str) -> str:
    return _vault.encrypt(val)

def decrypt_secret(val: str) -> str:
    return _vault.decrypt(val)
