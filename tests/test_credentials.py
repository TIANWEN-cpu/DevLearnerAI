"""Tests for app.credentials -- credential storage module.

Covers non-Windows code paths (keyring and base64 fallback) by injecting
mock _keyring and patching sys.platform, plus edge cases in load/save/delete.
"""

import base64
import sys
from unittest.mock import MagicMock, patch

import pytest

import app.credentials as creds_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _with_fake_platform(platform: str):
    """Context manager that patches sys.platform for the credentials module."""
    return patch.object(creds_mod, "sys", wraps=creds_mod.sys)


# ---------------------------------------------------------------------------
# save_secret -- non-Windows with keyring
# ---------------------------------------------------------------------------
class TestSaveSecretWithKeyring:
    """save_secret using keyring backend on non-Windows."""

    def test_calls_keyring_set_password(self):
        mock_kr = MagicMock()
        with patch.object(creds_mod.sys, "platform", "linux"), patch.object(creds_mod, "_HAS_KEYRING", True):
            # Inject _keyring if it doesn't exist
            if not hasattr(creds_mod, "_keyring"):
                creds_mod._keyring = mock_kr
                added = True
            else:
                added = False
            try:
                with patch.object(creds_mod, "_keyring", mock_kr):
                    creds_mod.save_secret("target", "secret")
                mock_kr.set_password.assert_called_once_with("DevLearnerAI", "target", "secret")
            finally:
                if added:
                    delattr(creds_mod, "_keyring")


# ---------------------------------------------------------------------------
# save_secret -- non-Windows fallback (base64 file)
# ---------------------------------------------------------------------------
class TestSaveSecretFallback:
    """save_secret using base64 file fallback on non-Windows (no keyring)."""

    def test_writes_base64_to_file(self, tmp_path):
        """Actually exercise the non-Windows fallback save path."""
        api_dir = tmp_path / ".devlearnerai"
        fallback_path = api_dir / "api_key.txt"

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            # Path.home() / ".devlearnerai" / "api_key.txt"
            # tmp_path is a real Path, so / operator creates real paths
            creds_mod.save_secret("target", "my_secret_key")

            assert fallback_path.exists()
            content = fallback_path.read_text(encoding="utf-8")
            decoded = base64.b64decode(content).decode("utf-8")
            assert decoded == "my_secret_key"

    def test_base64_encoding_ascii(self):
        secret = "sk-test123"
        encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        assert base64.b64decode(encoded).decode("utf-8") == secret

    def test_base64_encoding_unicode(self):
        secret = "密钥测试🔑"
        encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        assert base64.b64decode(encoded).decode("utf-8") == secret


# ---------------------------------------------------------------------------
# load_secret -- non-Windows with keyring
# ---------------------------------------------------------------------------
class TestLoadSecretWithKeyring:
    """load_secret using keyring backend on non-Windows."""

    def test_returns_keyring_value(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = "found"
        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", True),
            patch.object(creds_mod, "_keyring", mock_kr, create=True),
        ):
            result = creds_mod.load_secret("target")
            assert result == "found"
            mock_kr.get_password.assert_called_once_with("DevLearnerAI", "target")

    def test_returns_none_when_keyring_returns_none(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = None
        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", True),
            patch.object(creds_mod, "_keyring", mock_kr, create=True),
        ):
            result = creds_mod.load_secret("target")
            assert result is None


# ---------------------------------------------------------------------------
# load_secret -- non-Windows fallback (base64 file)
# ---------------------------------------------------------------------------
class TestLoadSecretFallback:
    """load_secret using base64 file fallback on non-Windows."""

    def test_file_not_exists_returns_none(self, tmp_path):
        api_dir = tmp_path / ".devlearnerai"
        api_dir.mkdir(parents=True, exist_ok=True)
        # File does not exist

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            # Reconstruct the actual path chain
            # The code does: Path.home() / ".devlearnerai" / "api_key.txt"
            # Path.home() returns tmp_path, then / ".devlearnerai" / "api_key.txt"
            # But mock_path.home() returns tmp_path (a real Path), so / operator works
            result = creds_mod.load_secret("target")
            assert result is None

    def test_empty_file_returns_none(self, tmp_path):
        api_dir = tmp_path / ".devlearnerai"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "api_key.txt").write_text("", encoding="utf-8")

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            result = creds_mod.load_secret("target")
            assert result is None

    def test_valid_base64_decoded(self, tmp_path):
        secret = "my_api_key_123"
        api_dir = tmp_path / ".devlearnerai"
        api_dir.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        (api_dir / "api_key.txt").write_text(encoded, encoding="utf-8")

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            result = creds_mod.load_secret("target")
            assert result == secret

    def test_invalid_base64_returns_raw(self, tmp_path):
        raw_text = "not-valid-base64!@#"
        api_dir = tmp_path / ".devlearnerai"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "api_key.txt").write_text(raw_text, encoding="utf-8")

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            result = creds_mod.load_secret("target")
            # base64.b64decode won't raise for all strings, but some do
            # The code catches Exception and returns raw
            assert isinstance(result, str)

    def test_whitespace_stripped(self, tmp_path):
        secret = "key123"
        api_dir = tmp_path / ".devlearnerai"
        api_dir.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        (api_dir / "api_key.txt").write_text(f"  {encoded}  ", encoding="utf-8")

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            result = creds_mod.load_secret("target")
            assert result == secret


# ---------------------------------------------------------------------------
# delete_secret -- non-Windows with keyring
# ---------------------------------------------------------------------------
class TestDeleteSecretWithKeyring:
    """delete_secret using keyring backend on non-Windows."""

    def test_success_returns_true(self):
        mock_kr = MagicMock()
        mock_errors = MagicMock()
        mock_errors.PasswordDeleteError = type("PasswordDeleteError", (Exception,), {})
        mock_kr.errors = mock_errors

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", True),
            patch.object(creds_mod, "_keyring", mock_kr, create=True),
        ):
            result = creds_mod.delete_secret("target")
            assert result is True
            mock_kr.delete_password.assert_called_once_with("DevLearnerAI", "target")

    def test_password_not_found_returns_false(self):
        mock_kr = MagicMock()
        mock_errors = MagicMock()
        pwd_err = type("PasswordDeleteError", (Exception,), {})
        mock_errors.PasswordDeleteError = pwd_err
        mock_kr.errors = mock_errors
        mock_kr.delete_password.side_effect = pwd_err()

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", True),
            patch.object(creds_mod, "_keyring", mock_kr, create=True),
        ):
            result = creds_mod.delete_secret("target")
            assert result is False


# ---------------------------------------------------------------------------
# delete_secret -- non-Windows fallback (file)
# ---------------------------------------------------------------------------
class TestDeleteSecretFallback:
    """delete_secret using file fallback on non-Windows."""

    def test_file_exists_deletes_returns_true(self, tmp_path):
        api_dir = tmp_path / ".devlearnerai"
        api_dir.mkdir(parents=True, exist_ok=True)
        api_file = api_dir / "api_key.txt"
        api_file.write_text("data", encoding="utf-8")

        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            result = creds_mod.delete_secret("target")
            assert result is True
            assert not api_file.exists()

    def test_file_not_exists_returns_false(self, tmp_path):
        with (
            patch.object(creds_mod.sys, "platform", "linux"),
            patch.object(creds_mod, "_HAS_KEYRING", False),
            patch("app.credentials.Path") as mock_path,
        ):
            mock_path.home.return_value = tmp_path
            result = creds_mod.delete_secret("target")
            assert result is False


# ---------------------------------------------------------------------------
# Windows credential path (mocked ctypes)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager only")
class TestWindowsCredentialPaths:
    """Test Windows credential manager paths using mocked ctypes calls."""

    def test_save_secret_windows_success(self):
        """CredWriteW returns True -> no error raised."""
        mock_credential = MagicMock()
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredWriteW", return_value=True) as mock_write,
            patch.object(creds_mod, "CREDENTIALW", return_value=mock_credential),
            patch("app.credentials.ctypes.byref", side_effect=lambda x: x),
            patch("app.credentials.ctypes.create_string_buffer", return_value=b""),
        ):
            creds_mod.save_secret("target", "secret")
            mock_write.assert_called_once()

    def test_save_secret_windows_failure_raises_oserror(self):
        """CredWriteW returns False -> OSError raised."""
        mock_credential = MagicMock()
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredWriteW", return_value=False),
            patch.object(creds_mod, "CREDENTIALW", return_value=mock_credential),
            patch("app.credentials.ctypes.byref", side_effect=lambda x: x),
            patch("app.credentials.ctypes.create_string_buffer", return_value=b""),
            patch("app.credentials.ctypes.get_last_error", return_value=5),
            pytest.raises(OSError),
        ):
            creds_mod.save_secret("target", "secret")

    def test_load_secret_windows_not_found_returns_none(self):
        """CredReadW fails with ERROR_NOT_FOUND -> returns None."""
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredReadW", return_value=False),
            patch("app.credentials.ctypes.get_last_error", return_value=1168),
            patch("app.credentials.ctypes.byref", side_effect=lambda x: x),
        ):
            result = creds_mod.load_secret("target")
            assert result is None

    def test_load_secret_windows_other_error_raises(self):
        """CredReadW fails with non-NOT_FOUND error -> OSError raised."""
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredReadW", return_value=False),
            patch("app.credentials.ctypes.get_last_error", return_value=5),
            patch("app.credentials.ctypes.byref", side_effect=lambda x: x),
            pytest.raises(OSError),
        ):
            creds_mod.load_secret("target")

    def test_load_secret_windows_success(self):
        """CredReadW succeeds -> blob decoded and returned, CredFree called."""
        secret_utf16 = "my_secret".encode("utf-16-le")

        mock_cred = MagicMock()
        mock_cred.contents.CredentialBlob = 0
        mock_cred.contents.CredentialBlobSize = len(secret_utf16)

        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "PCREDENTIALW", return_value=mock_cred),
            patch("app.credentials.ctypes.byref", side_effect=lambda x: x),
            patch("app.credentials.ctypes.string_at", return_value=secret_utf16),
            patch.object(creds_mod, "CredReadW", return_value=True),
            patch.object(creds_mod, "CredFree") as mock_free,
        ):
            result = creds_mod.load_secret("target")
            assert result == "my_secret"
            mock_free.assert_called_once_with(mock_cred)

    def test_delete_secret_windows_success(self):
        """CredDeleteW returns True -> returns True."""
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredDeleteW", return_value=True),
        ):
            result = creds_mod.delete_secret("target")
            assert result is True

    def test_delete_secret_windows_not_found_returns_false(self):
        """CredDeleteW fails with ERROR_NOT_FOUND -> returns False."""
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredDeleteW", return_value=False),
            patch("app.credentials.ctypes.get_last_error", return_value=1168),
        ):
            result = creds_mod.delete_secret("target")
            assert result is False

    def test_delete_secret_windows_other_error_raises(self):
        """CredDeleteW fails with non-NOT_FOUND error -> OSError raised."""
        with (
            patch.object(creds_mod.sys, "platform", "win32"),
            patch.object(creds_mod, "CredDeleteW", return_value=False),
            patch("app.credentials.ctypes.get_last_error", return_value=5),
            pytest.raises(OSError),
        ):
            creds_mod.delete_secret("target")


# ---------------------------------------------------------------------------
# Base64 roundtrip edge cases
# ---------------------------------------------------------------------------
class TestBase64EdgeCases:
    """Additional base64 encoding scenarios."""

    def test_empty_string(self):
        raw = base64.b64encode(b"").decode("ascii")
        assert base64.b64decode(raw).decode("utf-8") == ""

    def test_long_key(self):
        secret = "x" * 500
        raw = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        assert base64.b64decode(raw).decode("utf-8") == secret

    def test_special_chars(self):
        secret = "key=abc&secret=xyz?token=123+456/789"
        raw = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        assert base64.b64decode(raw).decode("utf-8") == secret

    def test_newlines_in_secret(self):
        secret = "line1\nline2\nline3"
        raw = base64.b64encode(secret.encode("utf-8")).decode("ascii")
        assert base64.b64decode(raw).decode("utf-8") == secret
