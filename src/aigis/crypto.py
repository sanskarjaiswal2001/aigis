"""Password encryption/decryption for config values using Fernet (AES-128-CBC + HMAC-SHA256).

Key management best practice:
  1. Generate a key once:  aigis --generate-key
  2. Store it in .env:     AIGIS_KEY=<key>
  3. Encrypt passwords:    aigis --encrypt-password "yourpassword"
  4. Store enc: values in config — never plaintext passwords.

The .env file must never be committed to version control.
"""

import os
import sys

_PREFIX = "enc:"


def _get_key() -> bytes:
    """Load the Fernet key from the AIGIS_KEY environment variable."""
    key = os.environ.get("AIGIS_KEY")
    if not key:
        print(
            "Error: AIGIS_KEY environment variable is not set.\n"
            "Generate a key with: aigis --generate-key\n"
            "Then add it to your .env file as: AIGIS_KEY=<key>",
            file=sys.stderr,
        )
        sys.exit(1)
    return key.encode()


def generate_key() -> str:
    """Generate a new Fernet key. Store it in .env as AIGIS_KEY."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password. Returns a string prefixed with 'enc:' for config storage."""
    from cryptography.fernet import Fernet

    f = Fernet(_get_key())
    token = f.encrypt(plaintext.encode()).decode()
    return f"{_PREFIX}{token}"


def decrypt_password(value: str) -> str:
    """Decrypt a config password value.

    If the value starts with 'enc:' it is decrypted using AIGIS_KEY.
    Plain-text values (no prefix) are returned as-is with a deprecation warning.
    """
    if not value.startswith(_PREFIX):
        print(
            "Warning: password in config is not encrypted. "
            "Encrypt it with: aigis --encrypt-password \"yourpassword\"",
            file=sys.stderr,
        )
        return value

    from cryptography.fernet import Fernet, InvalidToken

    try:
        f = Fernet(_get_key())
        return f.decrypt(value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        print(
            "Error: Failed to decrypt password — wrong AIGIS_KEY or corrupted value.",
            file=sys.stderr,
        )
        sys.exit(1)
