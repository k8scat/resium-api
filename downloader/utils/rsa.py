import base64

from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.PublicKey import RSA


class RSAUtil:
    privkey = None
    pubkey = None

    def __init__(self, privkey_file: str = None, pubkey_file: str = None):
        if privkey_file:
            with open(privkey_file) as f:
                self.privkey = RSA.importKey(f.read())
        if pubkey_file:
            with open(pubkey_file) as f:
                self.pubkey = RSA.importKey(f.read())

    def encrypt_by_public_key(self, message: str):
        cipher = PKCS1_cipher.new(self.pubkey)
        result = base64.b64encode(cipher.encrypt(message.encode("utf-8")))
        return result.decode("utf-8")

    def decrypt_by_private_key(self, rsa_text: str) -> str:
        cipher = PKCS1_cipher.new(self.privkey)
        result = cipher.decrypt(base64.b64decode(rsa_text), 0)
        if result == 0:
            return ""
        return result.decode("utf-8")
