"""Encryption service for Circle Core Framework.

Provides secure data encryption with multiple algorithm support and envelope encryption.
"""

import base64
import json
import os
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .key_manager import KeyManager


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""

    AES_GCM = "aes-gcm"  # AES in GCM mode (authenticated encryption)
    AES_CBC = "aes-cbc"  # AES in CBC mode with HMAC
    RSA = "rsa"  # RSA asymmetric encryption


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""

    ciphertext: bytes
    algorithm: EncryptionAlgorithm
    key_id: Optional[str] = None
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None
    aad: Optional[bytes] = None  # Additional authenticated data


class EncryptionService:
    """Service for encrypting and decrypting data.

    This class provides a secure interface for encrypting and decrypting data
    using various algorithms and key management strategies.
    """

    def __init__(
        self, 
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_GCM,
        key_manager: Optional[KeyManager] = None
    ):
        """Initialize the encryption service.

        Args:
            algorithm: Default encryption algorithm
            key_manager: Optional key manager instance
        """
        self.algorithm = algorithm
        self.key_manager = key_manager or KeyManager()

    def encrypt(
        self, 
        data: Union[bytes, str], 
        algorithm: Optional[EncryptionAlgorithm] = None,
        aad: Optional[bytes] = None,
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """Encrypt data using the specified algorithm.

        Args:
            data: Data to encrypt (bytes or string)
            algorithm: Optional encryption algorithm (defaults to service default)
            aad: Additional authenticated data for AEAD modes
            key_id: Optional key ID to use (defaults to active key)

        Returns:
            EncryptedData object containing the encrypted data and metadata
        """
        # Convert string to bytes if needed
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data

        # Use default algorithm if none specified
        algorithm = algorithm or self.algorithm

        # Get the encryption key
        key_id, key = self.key_manager.get_key(key_id)

        # Encrypt the data based on the algorithm
        if algorithm == EncryptionAlgorithm.AES_GCM:
            # Generate a random 96-bit IV for GCM
            iv = os.urandom(12)
            
            # Encrypt the data
            ciphertext = self._encrypt_aes_gcm(data_bytes, key, iv, aad)
            
            # Return the encrypted data
            return EncryptedData(
                ciphertext=ciphertext,
                algorithm=algorithm,
                key_id=key_id,
                iv=iv,
                aad=aad
            )
        
        elif algorithm == EncryptionAlgorithm.AES_CBC:
            # Generate a random 128-bit IV for CBC
            iv = os.urandom(16)
            
            # Encrypt the data
            ciphertext, tag = self._encrypt_aes_cbc(data_bytes, key, iv)
            
            # Return the encrypted data
            return EncryptedData(
                ciphertext=ciphertext,
                algorithm=algorithm,
                key_id=key_id,
                iv=iv,
                tag=tag
            )
        
        elif algorithm == EncryptionAlgorithm.RSA:
            # No IV needed for RSA
            ciphertext = self._encrypt_rsa(data_bytes, key)
            
            # Return the encrypted data
            return EncryptedData(
                ciphertext=ciphertext,
                algorithm=algorithm,
                key_id=key_id
            )
        
        else:
            raise ValueError(f"Unsupported encryption algorithm: {algorithm}")

    def decrypt(
        self, 
        encrypted_data: EncryptedData,
        aad: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt data using the specified algorithm.

        Args:
            encrypted_data: EncryptedData object containing the encrypted data and metadata
            aad: Additional authenticated data for AEAD modes (must match what was used for encryption)

        Returns:
            Decrypted data as bytes
        """
        # Get the key from the key manager
        key_id, key = self.key_manager.get_key(encrypted_data.key_id)

        # Use the provided aad or the one from the encrypted data
        aad = aad or encrypted_data.aad

        # Decrypt based on the algorithm
        if encrypted_data.algorithm == EncryptionAlgorithm.AES_GCM:
            if encrypted_data.iv is None:
                raise ValueError("Missing IV for AES-GCM decryption")
                
            return self._decrypt_aes_gcm(
                encrypted_data.ciphertext, 
                key, 
                encrypted_data.iv, 
                aad
            )
        
        elif encrypted_data.algorithm == EncryptionAlgorithm.AES_CBC:
            if encrypted_data.iv is None:
                raise ValueError("Missing IV for AES-CBC decryption")
            if encrypted_data.tag is None:
                raise ValueError("Missing HMAC tag for AES-CBC decryption")
                
            return self._decrypt_aes_cbc(
                encrypted_data.ciphertext, 
                key, 
                encrypted_data.iv, 
                encrypted_data.tag
            )
        
        elif encrypted_data.algorithm == EncryptionAlgorithm.RSA:
            return self._decrypt_rsa(encrypted_data.ciphertext, key)
        
        else:
            raise ValueError(f"Unsupported encryption algorithm: {encrypted_data.algorithm}")

    def _encrypt_aes_gcm(
        self, 
        data: bytes, 
        key: bytes, 
        iv: bytes, 
        aad: Optional[bytes] = None
    ) -> bytes:
        """Encrypt data using AES-GCM.

        Args:
            data: Data to encrypt
            key: Encryption key
            iv: Initialization vector
            aad: Additional authenticated data

        Returns:
            Encrypted data
        """
        aesgcm = AESGCM(key)
        return aesgcm.encrypt(iv, data, aad)

    def _decrypt_aes_gcm(
        self, 
        ciphertext: bytes, 
        key: bytes, 
        iv: bytes, 
        aad: Optional[bytes] = None
    ) -> bytes:
        """Decrypt data using AES-GCM.

        Args:
            ciphertext: Encrypted data
            key: Encryption key
            iv: Initialization vector
            aad: Additional authenticated data

        Returns:
            Decrypted data
        """
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(iv, ciphertext, aad)

    def _encrypt_aes_cbc(
        self, 
        data: bytes, 
        key: bytes, 
        iv: bytes
    ) -> Tuple[bytes, bytes]:
        """Encrypt data using AES-CBC with HMAC.

        Args:
            data: Data to encrypt
            key: Encryption key
            iv: Initialization vector

        Returns:
            Tuple of (ciphertext, hmac_tag)
        """
        # Split the key for encryption and HMAC
        enc_key = key[:16]  # First half for encryption
        hmac_key = key[16:]  # Second half for HMAC

        # Pad the data to a multiple of the block size
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()

        # Create the cipher
        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Encrypt the data
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Create HMAC of IV and ciphertext
        h = hmac.HMAC(hmac_key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        tag = h.finalize()

        return ciphertext, tag

    def _decrypt_aes_cbc(
        self, 
        ciphertext: bytes, 
        key: bytes, 
        iv: bytes, 
        tag: bytes
    ) -> bytes:
        """Decrypt data using AES-CBC with HMAC.

        Args:
            ciphertext: Encrypted data
            key: Encryption key
            iv: Initialization vector
            tag: HMAC tag

        Returns:
            Decrypted data
        """
        # Split the key for encryption and HMAC
        enc_key = key[:16]  # First half for encryption
        hmac_key = key[16:]  # Second half for HMAC

        # Verify the HMAC
        h = hmac.HMAC(hmac_key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        h.verify(tag)  # Will raise InvalidSignature if verification fails

        # Create the cipher
        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt the data
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Unpad the data
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded_data) + unpadder.finalize()

    def _encrypt_rsa(
        self, 
        data: bytes, 
        public_key_pem: bytes
    ) -> bytes:
        """Encrypt data using RSA.

        Args:
            data: Data to encrypt
            public_key_pem: RSA public key PEM

        Returns:
            Encrypted data
        """
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        # Load the public key
        public_key = load_pem_public_key(public_key_pem, backend=default_backend())

        # Encrypt the data
        ciphertext = public_key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return ciphertext

    def _decrypt_rsa(
        self, 
        ciphertext: bytes, 
        private_key_pem: bytes
    ) -> bytes:
        """Decrypt data using RSA.

        Args:
            ciphertext: Encrypted data
            private_key_pem: RSA private key PEM

        Returns:
            Decrypted data
        """
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        # Load the private key
        private_key = load_pem_private_key(
            private_key_pem, 
            password=None, 
            backend=default_backend()
        )

        # Decrypt the data
        plaintext = private_key.decrypt(
            ciphertext,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return plaintext

    def encrypt_envelope(
        self, 
        data: Union[bytes, str], 
        algorithm: Optional[EncryptionAlgorithm] = None
    ) -> Dict[str, str]:
        """Encrypt data using envelope encryption.

        This method generates a data encryption key (DEK), encrypts the data with the DEK,
        and then encrypts the DEK with a key encryption key (KEK) from the key manager.

        Args:
            data: Data to encrypt
            algorithm: Encryption algorithm to use

        Returns:
            Dictionary containing the encrypted data and metadata
        """
        # Convert string to bytes if needed
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data

        # Use default algorithm if none specified
        algorithm = algorithm or self.algorithm

        # Generate a data encryption key (DEK)
        dek = secrets.token_bytes(32)

        # Encrypt the data with the DEK
        iv = os.urandom(12 if algorithm == EncryptionAlgorithm.AES_GCM else 16)
        
        if algorithm == EncryptionAlgorithm.AES_GCM:
            encrypted_data = self._encrypt_aes_gcm(data_bytes, dek, iv)
        elif algorithm == EncryptionAlgorithm.AES_CBC:
            encrypted_data, tag = self._encrypt_aes_cbc(data_bytes, dek, iv)
        else:
            raise ValueError(f"Unsupported algorithm for envelope encryption: {algorithm}")

        # Get the key encryption key (KEK) from the key manager
        kek_id, kek = self.key_manager.get_key()

        # Encrypt the DEK with the KEK
        if algorithm == EncryptionAlgorithm.AES_GCM:
            dek_iv = os.urandom(12)
            encrypted_dek = self._encrypt_aes_gcm(dek, kek, dek_iv)
            
            # Format the envelope
            envelope = {
                "algorithm": algorithm.value,
                "key_id": kek_id,
                "encrypted_dek": base64.b64encode(encrypted_dek).decode('utf-8'),
                "dek_iv": base64.b64encode(dek_iv).decode('utf-8'),
                "iv": base64.b64encode(iv).decode('utf-8'),
                "ciphertext": base64.b64encode(encrypted_data).decode('utf-8')
            }
        elif algorithm == EncryptionAlgorithm.AES_CBC:
            dek_iv = os.urandom(16)
            encrypted_dek, dek_tag = self._encrypt_aes_cbc(dek, kek, dek_iv)
            
            # Format the envelope
            envelope = {
                "algorithm": algorithm.value,
                "key_id": kek_id,
                "encrypted_dek": base64.b64encode(encrypted_dek).decode('utf-8'),
                "dek_iv": base64.b64encode(dek_iv).decode('utf-8'),
                "dek_tag": base64.b64encode(dek_tag).decode('utf-8'),
                "iv": base64.b64encode(iv).decode('utf-8'),
                "ciphertext": base64.b64encode(encrypted_data).decode('utf-8'),
                "tag": base64.b64encode(tag).decode('utf-8') if 'tag' in locals() else None
            }
        
        return envelope

    def decrypt_envelope(self, envelope: Dict[str, str]) -> bytes:
        """Decrypt data using envelope encryption.

        Args:
            envelope: Dictionary containing the encrypted data and metadata

        Returns:
            Decrypted data
        """
        # Parse the envelope
        algorithm = EncryptionAlgorithm(envelope["algorithm"])
        key_id = envelope["key_id"]
        encrypted_dek = base64.b64decode(envelope["encrypted_dek"])
        dek_iv = base64.b64decode(envelope["dek_iv"])
        iv = base64.b64decode(envelope["iv"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
        
        # Get the key encryption key (KEK) from the key manager
        _, kek = self.key_manager.get_key(key_id)
        
        # Decrypt the DEK
        if algorithm == EncryptionAlgorithm.AES_GCM:
            dek = self._decrypt_aes_gcm(encrypted_dek, kek, dek_iv)
            
            # Decrypt the data
            return self._decrypt_aes_gcm(ciphertext, dek, iv)
        elif algorithm == EncryptionAlgorithm.AES_CBC:
            dek_tag = base64.b64decode(envelope["dek_tag"])
            tag = base64.b64decode(envelope["tag"]) if envelope.get("tag") else None
            
            # Decrypt the DEK
            dek = self._decrypt_aes_cbc(encrypted_dek, kek, dek_iv, dek_tag)
            
            # Decrypt the data
            return self._decrypt_aes_cbc(ciphertext, dek, iv, tag)
        else:
            raise ValueError(f"Unsupported algorithm for envelope decryption: {algorithm}")

    def encrypt_file(
        self, 
        input_path: str, 
        output_path: str, 
        use_envelope: bool = True,
        algorithm: Optional[EncryptionAlgorithm] = None,
        chunk_size: int = 64 * 1024  # 64 KB chunks
    ) -> Dict[str, str]:
        """Encrypt a file.

        Args:
            input_path: Path to the file to encrypt
            output_path: Path to write the encrypted file
            use_envelope: Whether to use envelope encryption
            algorithm: Encryption algorithm to use
            chunk_size: Size of chunks to read and encrypt

        Returns:
            Dictionary with encryption metadata
        """
        # Use default algorithm if none specified
        algorithm = algorithm or self.algorithm
        
        # Only GCM and CBC are supported for file encryption
        if algorithm not in (EncryptionAlgorithm.AES_GCM, EncryptionAlgorithm.AES_CBC):
            raise ValueError(f"Unsupported algorithm for file encryption: {algorithm}")
            
        # For envelope encryption, we'll generate a DEK
        if use_envelope:
            dek = secrets.token_bytes(32)
            key_id, kek = self.key_manager.get_key()
        else:
            key_id, dek = self.key_manager.get_key()
        
        # Initialize metadata
        metadata = {
            "algorithm": algorithm.value,
            "envelope": use_envelope,
            "key_id": key_id if not use_envelope else None,
        }
        
        # For CBC mode, we need to keep track of the HMAC
        hmac_key = None
        h = None
        if algorithm == EncryptionAlgorithm.AES_CBC:
            enc_key = dek[:16]  # First half for encryption
            hmac_key = dek[16:]  # Second half for HMAC
            h = hmac.HMAC(hmac_key, hashes.SHA256(), backend=default_backend())
        
        # Generate IV
        iv = os.urandom(12 if algorithm == EncryptionAlgorithm.AES_GCM else 16)
        metadata["iv"] = base64.b64encode(iv).decode('utf-8')
        
        # For GCM mode
        aesgcm = None
        if algorithm == EncryptionAlgorithm.AES_GCM:
            aesgcm = AESGCM(dek)
        
        # For CBC mode
        cipher = None
        encryptor = None
        padder = None
        if algorithm == EncryptionAlgorithm.AES_CBC:
            cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            # Add IV to HMAC
            h.update(iv)
        
        # Open input and output files
        with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            # Write file header with metadata
            if use_envelope:
                # Encrypt DEK with KEK
                dek_iv = os.urandom(12 if algorithm == EncryptionAlgorithm.AES_GCM else 16)
                if algorithm == EncryptionAlgorithm.AES_GCM:
                    encrypted_dek = self._encrypt_aes_gcm(dek, kek, dek_iv)
                    metadata["encrypted_dek"] = base64.b64encode(encrypted_dek).decode('utf-8')
                    metadata["dek_iv"] = base64.b64encode(dek_iv).decode('utf-8')
                else:  # CBC
                    encrypted_dek, dek_tag = self._encrypt_aes_cbc(dek, kek, dek_iv)
                    metadata["encrypted_dek"] = base64.b64encode(encrypted_dek).decode('utf-8')
                    metadata["dek_iv"] = base64.b64encode(dek_iv).decode('utf-8')
                    metadata["dek_tag"] = base64.b64encode(dek_tag).decode('utf-8')
            
            # Write metadata to file header (as JSON)
            header = json.dumps(metadata).encode('utf-8')
            header_length = len(header).to_bytes(4, byteorder='big')
            outfile.write(header_length)
            outfile.write(header)
            
            # Process the file in chunks
            while True:
                chunk = infile.read(chunk_size)
                if not chunk:
                    break
                
                # Last chunk needs padding for CBC
                is_last_chunk = len(chunk) < chunk_size
                
                if algorithm == EncryptionAlgorithm.AES_GCM:
                    # Each chunk gets a unique nonce derived from IV and counter
                    chunk_number = outfile.tell().to_bytes(8, byteorder='big')
                    chunk_iv = iv + chunk_number[-4:]  # Use last 4 bytes for counter
                    encrypted_chunk = aesgcm.encrypt(chunk_iv, chunk, None)
                    # Write chunk length and IV suffix
                    outfile.write(len(encrypted_chunk).to_bytes(4, byteorder='big'))
                    outfile.write(chunk_iv[-4:])  # Only need to write the counter part
                elif algorithm == EncryptionAlgorithm.AES_CBC:
                    if is_last_chunk:
                        # Pad the last chunk
                        padded_chunk = padder.update(chunk) + padder.finalize()
                    else:
                        # No padding needed for intermediate chunks
                        padded_chunk = chunk
                    
                    # Encrypt the chunk
                    encrypted_chunk = encryptor.update(padded_chunk)
                    
                    # Update HMAC
                    h.update(encrypted_chunk)
                
                # Write the encrypted chunk
                outfile.write(encrypted_chunk)
            
            # Finalize CBC encryption
            if algorithm == EncryptionAlgorithm.AES_CBC:
                final_block = encryptor.finalize()
                if final_block:
                    outfile.write(final_block)
                    h.update(final_block)
                
                # Write HMAC tag
                tag = h.finalize()
                outfile.write(tag)
                metadata["tag_length"] = len(tag)
        
        return metadata

    def decrypt_file(
        self, 
        input_path: str, 
        output_path: str, 
        chunk_size: int = 64 * 1024  # 64 KB chunks
    ) -> None:
        """Decrypt a file.

        Args:
            input_path: Path to the encrypted file
            output_path: Path to write the decrypted file
            chunk_size: Size of chunks to read and decrypt
        """
        # Read file header
        with open(input_path, 'rb') as infile:
            # Read header length
            header_length_bytes = infile.read(4)
            header_length = int.from_bytes(header_length_bytes, byteorder='big')
            
            # Read header
            header = infile.read(header_length)
            metadata = json.loads(header.decode('utf-8'))
            
            # Parse metadata
            algorithm = EncryptionAlgorithm(metadata["algorithm"])
            use_envelope = metadata.get("envelope", False)
            
            # Get the decryption key
            if use_envelope:
                # Get KEK
                key_id = metadata["key_id"]
                _, kek = self.key_manager.get_key(key_id)
                
                # Decrypt DEK
                encrypted_dek = base64.b64decode(metadata["encrypted_dek"])
                dek_iv = base64.b64decode(metadata["dek_iv"])
                
                if algorithm == EncryptionAlgorithm.AES_GCM:
                    dek = self._decrypt_aes_gcm(encrypted_dek, kek, dek_iv)
                else:  # CBC
                    dek_tag = base64.b64decode(metadata["dek_tag"])
                    dek = self._decrypt_aes_cbc(encrypted_dek, kek, dek_iv, dek_tag)
            else:
                # Use key directly
                key_id = metadata["key_id"]
                _, dek = self.key_manager.get_key(key_id)
            
            # Get IV
            iv = base64.b64decode(metadata["iv"])
            
            # For CBC mode
            enc_key = None
            hmac_key = None
            cipher = None
            decryptor = None
            unpadder = None
            if algorithm == EncryptionAlgorithm.AES_CBC:
                enc_key = dek[:16]  # First half for encryption
                hmac_key = dek[16:]  # Second half for HMAC
                cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            
            # For GCM mode
            aesgcm = None
            if algorithm == EncryptionAlgorithm.AES_GCM:
                aesgcm = AESGCM(dek)
            
            # For CBC, we need to read the whole file to verify HMAC
            if algorithm == EncryptionAlgorithm.AES_CBC:
                # Remember file position after header
                start_pos = infile.tell()
                
                # Get file size
                infile.seek(0, 2)  # Seek to end
                file_size = infile.tell()
                
                # Calculate HMAC tag position
                tag_length = metadata.get("tag_length", 32)  # Default to 32 bytes
                tag_pos = file_size - tag_length
                
                # Verify HMAC
                infile.seek(start_pos)
                h = hmac.HMAC(hmac_key, hashes.SHA256(), backend=default_backend())
                
                # Add IV to HMAC
                h.update(iv)
                
                # Read and update HMAC (excluding tag)
                bytes_read = 0
                while bytes_read < (tag_pos - start_pos):
                    read_size = min(chunk_size, tag_pos - start_pos - bytes_read)
                    chunk = infile.read(read_size)
                    if not chunk:
                        break
                    h.update(chunk)
                    bytes_read += len(chunk)
                
                # Read tag
                tag = infile.read(tag_length)
                
                # Verify tag
                h.verify(tag)
                
                # Reset file position
                infile.seek(start_pos)
            
            # Open output file
            with open(output_path, 'wb') as outfile:
                # Process the file in chunks
                if algorithm == EncryptionAlgorithm.AES_GCM:
                    while True:
                        # Read chunk length
                        length_bytes = infile.read(4)
                        if not length_bytes or len(length_bytes) < 4:
                            break
                        
                        chunk_length = int.from_bytes(length_bytes, byteorder='big')
                        
                        # Read counter suffix
                        counter_suffix = infile.read(4)
                        
                        # Read encrypted chunk
                        encrypted_chunk = infile.read(chunk_length)
                        if not encrypted_chunk:
                            break
                        
                        # Reconstruct IV with counter
                        chunk_iv = iv[:-4] + counter_suffix
                        
                        # Decrypt chunk
                        decrypted_chunk = aesgcm.decrypt(chunk_iv, encrypted_chunk, None)
                        
                        # Write decrypted chunk
                        outfile.write(decrypted_chunk)
                else:  # CBC
                    # For CBC, we need to read the whole ciphertext (excluding tag)
                    bytes_to_read = tag_pos - start_pos
                    bytes_read = 0
                    
                    while bytes_read < bytes_to_read:
                        read_size = min(chunk_size, bytes_to_read - bytes_read)
                        encrypted_chunk = infile.read(read_size)
                        if not encrypted_chunk:
                            break
                        
                        # Decrypt chunk
                        decrypted_chunk = decryptor.update(encrypted_chunk)
                        bytes_read += len(encrypted_chunk)
                        
                        # For the last chunk, we need to unpad
                        if bytes_read >= bytes_to_read:
                            # Add the finalizer
                            decrypted_chunk += decryptor.finalize()
                            # Unpad
                            decrypted_chunk = unpadder.update(decrypted_chunk) + unpadder.finalize()
                        
                        # Write decrypted chunk
                        outfile.write(decrypted_chunk)
