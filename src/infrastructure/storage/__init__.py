"""
Storage services for Circle Core Framework.
Provides unified storage interfaces with multiple backends and encryption support.
"""

from .interface import StorageBackend, StorageObject, StorageMetadata
from .file_storage import FileSystemStorage
from .encryption import EncryptedStorageWrapper
from .manager import StorageManager

__all__ = [
    'StorageBackend',
    'StorageObject',
    'StorageMetadata',
    'FileSystemStorage',
    'EncryptedStorageWrapper',
    'StorageManager'
]
