from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_file(file_data: bytes) -> bytes:
    return fernet.encrypt(file_data)

def decrypt_file(encrypted_data: bytes) -> bytes:
    return fernet.decrypt(encrypted_data)
