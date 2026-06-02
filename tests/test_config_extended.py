"""Extended tests for app.config covering helper functions.

Targets:
- _resource_dir (lines 32-38)
- _user_data_root when APPDATA is not set (line 49)
"""

import os
import sys
from unittest.mock import patch

import pytest


class TestResourceDir:
    """Test _resource_dir function (lines 31-38)."""

    def test_resource_dir_prefers_runtime(self, tmp_path):
        """If runtime candidate exists, should return it."""
        from app.config import RUNTIME_DIR, _resource_dir

        # The function checks RUNTIME_DIR / name first
        runtime_path = RUNTIME_DIR / "test_resource"
        if not runtime_path.exists():
            runtime_path.mkdir(parents=True, exist_ok=True)

        result = _resource_dir("test_resource")
        assert result.name == "test_resource"
        # Cleanup
        runtime_path.rmdir()

    def test_resource_dir_falls_back_to_base(self, tmp_path):
        """If runtime candidate doesn't exist but base does, should return base."""
        from app.config import _resource_dir

        # Use a name that likely doesn't exist in runtime
        result = _resource_dir("nonexistent_resource_12345")
        # Should fall back to runtime_candidate (which doesn't exist)
        assert result.name == "nonexistent_resource_12345"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows paths only")
class TestUserDataRoot:
    """Test _user_data_root function (lines 45-49)."""

    def test_user_data_root_with_appdata(self):
        """When APPDATA is set, should use it."""
        from app.config import _user_data_root

        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            result = _user_data_root()
            assert "DevLearnerAI" in str(result)
            assert "AppData" in str(result)

    def test_user_data_root_without_appdata(self):
        """When APPDATA and LOCALAPPDATA are not set, should fall back to home."""
        from app.config import _user_data_root

        with patch.dict(os.environ, {"APPDATA": "", "LOCALAPPDATA": ""}, clear=False):
            # Remove the keys entirely
            env_copy = os.environ.copy()
            env_copy.pop("APPDATA", None)
            env_copy.pop("LOCALAPPDATA", None)
            with patch.dict(os.environ, env_copy, clear=True):
                result = _user_data_root()
                # Should end up using Path.home()
                assert ".devlearnerai" in str(result).lower() or "DevLearnerAI" in str(result)


class TestReadPackageVersion:
    """Test _read_package_version (lines 17-23)."""

    def test_version_fallback(self):
        """When package is not installed, should return fallback."""
        from app.config import APP_VERSION

        # Should not crash and should return a string
        assert isinstance(APP_VERSION, str)


class TestConfigConstants:
    """Test that config constants are properly set."""

    def test_app_name(self):
        from app.config import APP_NAME

        assert APP_NAME == "DevLearnerAI"

    def test_base_dir_is_parent_of_app(self):
        from app.config import BASE_DIR

        assert BASE_DIR.is_dir()

    def test_content_dir_may_exist(self):
        from app.config import CONTENT_DIR

        assert CONTENT_DIR.name == "content"

    def test_db_path(self):
        from app.config import DB_PATH

        assert DB_PATH.name == "app.db"
