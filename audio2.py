import base64
import requests
import mimetypes
import random
import os
import hashlib
import hmac
from Crypto.Cipher import AES

# Ensure necessary directories exist
os.makedirs('./tmp', exist_ok=True)
os.makedirs('./decoded', exist_ok=True)

def download_file(url, filename):
    response = requests.get(url, allow_redirects=True)
    response.raise_for_status()
    with open(filename, 'wb') as file:
        file.write(response.content)

def hkdf(key, length, app_info=b""):
    key = hmac.new(b"\0" * 32, key, hashlib.sha256).digest()
    key_stream = b""
    key_block = b""
    block_index = 1
    while len(key_stream) < length:
        key_block = hmac.new(key, msg=key_block + app_info + chr(block_index).encode("utf-8"), digestmod=hashlib.sha256).digest()
        block_index += 1
        key_stream += key_block
    return key_stream[:length]

def aes_unpad(s):
    return s[:-ord(s[len(s) - 1:])]

def aes_decrypt(key, ciphertext, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext)
    return aes_unpad(plaintext)

def decrypt_media_file(media_key, encrypted_file_path, output_file_path, app_info):
    media_key_expanded = hkdf(base64.b64decode(media_key), 112, app_info)
    iv = media_key_expanded[:16]
    cipher_key = media_key_expanded[16:48]

    with open(encrypted_file_path, 'rb') as file:
        media_data = file.read()

    file_data = media_data[:-10]  # Remove the last 10 bytes (MAC)
    decrypted_data = aes_decrypt(cipher_key, file_data, iv)

    with open(output_file_path, 'wb') as file:
        file.write(decrypted_data)

def download_and_decrypt(payload):
    media_key = payload['mediaKey']
    url = payload['url']
    message_type = payload['messageType']
    app_info = bytes(payload['whatsappTypeMessageToDecode'], encoding='utf-8')
    mimetype = payload['mimetype'].split(';')[0]

    filename = payload.get('filename') or str(random.getrandbits(128))
    file_extension = mimetypes.guess_extension(mimetype)
    complete_filename = f'{filename}{file_extension}'

    print(f'filename: {filename}\nmediaKey: {media_key}\nurl: {url}\nmessageType: {message_type}\nwhatsappTypeMessageToDecode: {app_info}\nmimetype: {mimetype}\nextension: {file_extension}')

    encrypted_file_path = f'tmp/{filename}.enc'
    output_file_path = f'decoded/{complete_filename}'

    # Download the encrypted file
    download_file(url, encrypted_file_path)

    # Decrypt the media file
    decrypt_media_file(media_key, encrypted_file_path, output_file_path, app_info)

    print(f"Decrypted [{message_type}] [{complete_filename}]")

# Sample payload
payload_audio = {
    'url': 'https://mmg.whatsapp.net/v/t62.7117-24/12098171_1990187224829771_6235292153998745965_n.enc?ccb=11-4&oh=01_Q5AaIIqcRuzK9WBBJFgLwndXVaRW-cB0EbmFsAwZ_Jn4GFmD&oe=675A1646&_nc_sid=5e03e0&mms3=true',
    'mediaKey': 'v68ThsgiLLQJTk3yKJMVDfyVlDC5BU3QnfQoyFpzci4=',
    'messageType': 'audioMessage',
    'whatsappTypeMessageToDecode': 'WhatsApp Audio Keys',
    'mimetype': 'audio/ogg; codecs=opus'
}

download_and_decrypt(payload_audio)