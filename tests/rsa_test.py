import unittest

from downloader.rsa import RSAUtil


class RSAUtilTest(unittest.TestCase):
    rsa_util = RSAUtil()

    def test_encrypt(self):
        print(self.rsa_util.encrypt_by_public_key('aaa'))

    def test_decrypt(self):
        rsa_text = 'ZNoduKlBQR/JZBjQT6RQGJxVjuVhCH8a1YqCDDipxApzs0F0znxQo8L3UEL0HMdf8MTl94BBjgpCd/F5fhnw3fV0bTiNbzit1UxBCtA7u5JGL1G7R7ngCIDaT+fEEoNpzbxNVD+lcIbfhNPrBMxbf86OFzSkjk6sgcAZNRxbX5M='
        self.assertEqual(
            self.rsa_util.decrypt_by_private_key(rsa_text), 'aaa')
        print(self.rsa_util.decrypt_by_private_key(rsa_text))
