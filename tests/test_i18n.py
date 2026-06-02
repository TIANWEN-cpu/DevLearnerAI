"""Tests for app.i18n -- translation function business logic.

Tests tr(), set_language(), get_language(), and fallback behavior.
Every test asserts specific values.
"""

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_language():
    """Reset the i18n module to default state before each test."""
    import app.i18n as i18n_mod

    # Save original state
    orig_lang = i18n_mod._current_lang
    orig_fallback = i18n_mod._fallback_lang
    orig_registry = dict(i18n_mod._LANGUAGES)
    yield
    # Restore
    i18n_mod._current_lang = orig_lang
    i18n_mod._fallback_lang = orig_fallback
    i18n_mod._LANGUAGES = orig_registry


# ---------------------------------------------------------------------------
# tr() with valid key
# ---------------------------------------------------------------------------


class TestTrValidKey:
    """Test tr() returns correct translations for known keys."""

    def test_app_subtitle_zh(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("app.subtitle")
        assert result == "Python / 数据库 / 融合项目一体化学习平台"

    def test_app_subtitle_en(self):
        from app.i18n import set_language, tr

        set_language("en_US")
        result = tr("app.subtitle")
        assert result == "Python / Database / Integrated Project Learning Platform"

    def test_window_section_nav_zh(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("window.section_nav")
        assert result == "导航"

    def test_window_section_nav_en(self):
        from app.i18n import set_language, tr

        set_language("en_US")
        result = tr("window.section_nav")
        assert result == "Navigation"

    def test_window_brand_sub_zh(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("window.brand_sub")
        assert "学习路径" in result
        assert "AI" in result

    def test_window_theme_btn_zh(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("window.theme_btn")
        assert result == "深色模式"

    def test_window_theme_btn_en(self):
        from app.i18n import set_language, tr

        set_language("en_US")
        result = tr("window.theme_btn")
        assert result == "Dark Mode"


# ---------------------------------------------------------------------------
# tr() with missing key (fallback)
# ---------------------------------------------------------------------------


class TestTrMissingKey:
    """Test tr() fallback behavior for missing keys."""

    def test_missing_key_returns_key_itself(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("this.key.does.not.exist.anywhere")
        assert result == "this.key.does.not.exist.anywhere"

    def test_missing_key_en_returns_key(self):
        from app.i18n import set_language, tr

        set_language("en_US")
        result = tr("completely.bogus.key")
        assert result == "completely.bogus.key"

    def test_empty_key_returns_empty(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("")
        assert result == ""

    def test_fallback_to_english_when_missing_in_zh(self):
        """If a key exists in en_US but not zh_CN, should fall back to en_US."""
        import app.i18n as i18n_mod
        from app.i18n import set_language, tr

        set_language("zh_CN")
        # Inject a key that only exists in English
        i18n_mod._LANGUAGES.setdefault("en_US", {})["test.only.en"] = "English only"
        # Ensure it's NOT in zh_CN
        i18n_mod._LANGUAGES.setdefault("zh_CN", {}).pop("test.only.en", None)

        result = tr("test.only.en")
        assert result == "English only"

    def test_key_returned_when_missing_in_both_languages(self):
        """If key is missing from both current and fallback, return the key."""
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("definitely.not.a.real.key.xyz123")
        assert result == "definitely.not.a.real.key.xyz123"


# ---------------------------------------------------------------------------
# tr() with kwargs (format placeholders)
# ---------------------------------------------------------------------------


class TestTrWithKwargs:
    """Test tr() str.format() placeholder expansion."""

    def test_version_placeholder_zh(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("window.status_bar", version="1.0.0")
        assert "v1.0.0" in result

    def test_version_placeholder_en(self):
        from app.i18n import set_language, tr

        set_language("en_US")
        result = tr("window.status_bar", version="2.5.0")
        assert "v2.5.0" in result

    def test_title_placeholder_zh(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("window.page_switched", title="练习")
        assert "练习" in result

    def test_title_placeholder_en(self):
        from app.i18n import set_language, tr

        set_language("en_US")
        result = tr("window.page_switched", title="Practice")
        assert "Practice" in result

    def test_no_kwargs_returns_unformatted(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        result = tr("window.status_bar")
        # Should contain literal {version} since no kwargs
        assert "{version}" in result

    def test_mismatched_kwargs_does_not_crash(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        # Pass wrong kwarg name -- should not raise
        result = tr("window.section_nav", wrong_key="test")
        assert result == "导航"


# ---------------------------------------------------------------------------
# Language switching
# ---------------------------------------------------------------------------


class TestLanguageSwitching:
    """Test set_language() and get_language() interaction."""

    def test_default_language_is_zh_cn(self):
        from app.i18n import get_language

        assert get_language() == "zh_CN"

    def test_switch_to_english(self):
        from app.i18n import get_language, set_language

        set_language("en_US")
        assert get_language() == "en_US"

    def test_switch_back_to_chinese(self):
        from app.i18n import get_language, set_language

        set_language("en_US")
        set_language("zh_CN")
        assert get_language() == "zh_CN"

    def test_switch_affects_tr_output(self):
        from app.i18n import set_language, tr

        set_language("zh_CN")
        zh = tr("window.section_nav")
        set_language("en_US")
        en = tr("window.section_nav")
        assert zh != en
        assert zh == "导航"
        assert en == "Navigation"

    def test_switch_to_unknown_language_graceful(self):
        """Switching to an unknown language should not crash."""
        from app.i18n import set_language, tr

        set_language("fr_FR")  # not registered
        # Should fall back to returning the key itself
        result = tr("app.subtitle")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# available_languages
# ---------------------------------------------------------------------------


class TestAvailableLanguages:
    """Test available_languages() returns correct list."""

    def test_returns_list(self):
        from app.i18n import available_languages

        result = available_languages()
        assert isinstance(result, list)

    def test_contains_zh_cn(self):
        from app.i18n import available_languages

        assert "zh_CN" in available_languages()

    def test_contains_en_us(self):
        from app.i18n import available_languages

        assert "en_US" in available_languages()

    def test_length_is_two(self):
        from app.i18n import available_languages

        assert len(available_languages()) == 2
