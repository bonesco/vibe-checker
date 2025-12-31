"""Token encryption and decryption utilities using Fernet symmetric encryption"""

from cryptography.fernet import Fernet
from src.config import config


def encrypt_token(token: str) -> str:
    """
    Encrypt a Slack token for secure storage in database

    Args:
        token: Plain text token to encrypt

    Returns:
        Encrypted token as string
    """
    f = Fernet(config.ENCRYPTION_KEY.encode())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a Slack token from database

    Args:
        encrypted_token: Encrypted token string

    Returns:
        Decrypted plain text token
    """
    f = Fernet(config.ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_token.encode()).decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key

    Returns:
        New encryption key as string

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode()
