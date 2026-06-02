"""凭证安全存储模块。

提供跨平台的密钥存储能力。优先级：
1. Windows: Windows Credential Manager（加密存储）
2. 非 Windows + keyring 已安装: keyring 后端
3. 回退: Base64 编码的明文文件（~/.devlearnerai/api_key.txt）

公开接口: save_secret()、load_secret()、delete_secret()。
"""

import base64
import ctypes
import logging
import stat
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import keyring as _keyring

    _HAS_KEYRING = True
except ImportError:
    _HAS_KEYRING = False


if sys.platform == "win32":
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2
    ERROR_NOT_FOUND = 1168

    LPBYTE = ctypes.POINTER(wintypes.BYTE)

    class CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
        _fields_ = [
            ("Keyword", wintypes.LPWSTR),
            ("Flags", wintypes.DWORD),
            ("ValueSize", wintypes.DWORD),
            ("Value", LPBYTE),
        ]

    PCREDENTIAL_ATTRIBUTEW = ctypes.POINTER(CREDENTIAL_ATTRIBUTEW)

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", LPBYTE),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", PCREDENTIAL_ATTRIBUTEW),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    PCREDENTIALW = ctypes.POINTER(CREDENTIALW)

    advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
    CredWriteW = advapi32.CredWriteW
    CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    CredWriteW.restype = wintypes.BOOL

    CredReadW = advapi32.CredReadW
    CredReadW.argtypes = [
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(PCREDENTIALW),
    ]
    CredReadW.restype = wintypes.BOOL

    CredDeleteW = advapi32.CredDeleteW
    CredDeleteW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    CredDeleteW.restype = wintypes.BOOL

    CredFree = advapi32.CredFree
    CredFree.argtypes = [ctypes.c_void_p]
    CredFree.restype = None


def save_secret(target: str, secret: str, username: str = "DevLearnerAI") -> None:
    if sys.platform != "win32":
        if _HAS_KEYRING:
            _keyring.set_password("DevLearnerAI", target, secret)
            return
        logger.warning(
            "keyring not installed; falling back to base64-encoded file storage "
            "for API key at ~/.devlearnerai/api_key.txt"
        )
        fallback_path = Path.home() / ".devlearnerai" / "api_key.txt"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_text(base64.b64encode(secret.encode("utf-8")).decode("ascii"), encoding="utf-8")
        # Restrict file permissions to owner-only (Unix); no-op on Windows
        try:
            fallback_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            pass
        return

    blob = secret.encode("utf-16-le")
    blob_buffer = ctypes.create_string_buffer(blob)
    credential = CREDENTIALW()
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.UserName = username
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(blob_buffer, LPBYTE)

    if not CredWriteW(ctypes.byref(credential), 0):
        error = ctypes.get_last_error()
        raise OSError(error, f"Failed to store secret for {target}")


def load_secret(target: str) -> Optional[str]:
    if sys.platform != "win32":
        if _HAS_KEYRING:
            return _keyring.get_password("DevLearnerAI", target)
        fallback_path = Path.home() / ".devlearnerai" / "api_key.txt"
        if not fallback_path.exists():
            return None
        raw = fallback_path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        try:
            return base64.b64decode(raw).decode("utf-8")
        except Exception:
            logger.debug("Base64 解码失败，返回原始文本")
            return raw

    credential = PCREDENTIALW()
    if not CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(credential)):
        error = ctypes.get_last_error()
        if error == ERROR_NOT_FOUND:
            return None
        raise OSError(error, f"Failed to read secret for {target}")

    try:
        blob = ctypes.string_at(credential.contents.CredentialBlob, credential.contents.CredentialBlobSize)
        return blob.decode("utf-16-le")
    finally:
        CredFree(credential)


def delete_secret(target: str) -> bool:
    if sys.platform != "win32":
        if _HAS_KEYRING:
            try:
                _keyring.delete_password("DevLearnerAI", target)
                return True
            except _keyring.errors.PasswordDeleteError:
                return False
        fallback_path = Path.home() / ".devlearnerai" / "api_key.txt"
        if fallback_path.exists():
            fallback_path.unlink()
            return True
        return False

    if CredDeleteW(target, CRED_TYPE_GENERIC, 0):
        return True

    error = ctypes.get_last_error()
    if error == ERROR_NOT_FOUND:
        return False
    raise OSError(error, f"Failed to delete secret for {target}")
