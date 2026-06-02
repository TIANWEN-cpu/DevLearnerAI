"""Internationalization (i18n) module for DevLearner AI.

Provides a translation function ``tr()`` that looks up keys in the active
language dictionary.  Languages are registered as modules under
``app.i18n`` (e.g. ``zh_CN``, ``en_US``).

Usage::

    from app.i18n import tr

    label.setText(tr("dashboard.welcome"))

The active language is read from ``app.config.LANGUAGE`` (default ``zh_CN``).
Switch at runtime via ``set_language("en_US")``.
"""

from __future__ import annotations

import importlib
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ── Built-in language registry ────────────────────────────────────────────────

_LANGUAGES: Dict[str, Dict[str, str]] = {}
_current_lang: str = "zh_CN"
_fallback_lang: str = "en_US"


def _ensure_loaded(lang: str) -> None:
    """Lazy-load a language module on first use."""
    if lang in _LANGUAGES:
        return
    try:
        mod = importlib.import_module(f"app.i18n.{lang}")
        _LANGUAGES[lang] = getattr(mod, "TRANSLATIONS", {})
    except ModuleNotFoundError:
        logger.warning("Translation module app.i18n.%s not found", lang)
        _LANGUAGES[lang] = {}
    except Exception:
        logger.warning("Failed to load translations for %s", lang, exc_info=True)
        _LANGUAGES[lang] = {}


def tr(key: str, **kwargs) -> str:
    """Return the translated string for *key* in the current language.

    If the key is missing from the current language, fall back to the
    fallback language (English).  If still missing, return the key itself.

    Positional placeholders in the value are expanded via ``str.format()``
    using *kwargs*::

        tr("practice.score_detail", score=85, label="good")
    """
    _ensure_loaded(_current_lang)

    value = _LANGUAGES.get(_current_lang, {}).get(key)
    if value is None:
        _ensure_loaded(_fallback_lang)
        value = _LANGUAGES.get(_fallback_lang, {}).get(key)
    if value is None:
        value = key  # last resort: return the key

    if kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass  # leave value as-is if placeholders don't match
    return value


def set_language(lang: str) -> None:
    """Switch the active language at runtime.

    Args:
        lang: Language code, e.g. ``"zh_CN"`` or ``"en_US"``.
    """
    global _current_lang
    _current_lang = lang
    _ensure_loaded(lang)
    logger.info("Language switched to %s", lang)


def get_language() -> str:
    """Return the current language code."""
    return _current_lang


def available_languages() -> list[str]:
    """Return a list of known language codes."""
    return ["zh_CN", "en_US"]
