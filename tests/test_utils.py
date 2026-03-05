"""
Tests for utility functions: timezone, logging, limiter.
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestTimezoneHelpers:
    """Comprehensive timezone utility tests."""

    def test_now_utc_no_tzinfo(self):
        from utils.timezone import now_utc
        assert now_utc().tzinfo is None

    def test_now_utc_close_to_system_utc(self):
        from utils.timezone import now_utc
        system_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        diff = abs((now_utc() - system_utc).total_seconds())
        assert diff < 2

    def test_now_tashkent_has_tzinfo(self):
        from utils.timezone import now_tashkent
        assert now_tashkent().tzinfo is not None

    def test_tashkent_tz_offset_is_5(self):
        from utils.timezone import TASHKENT_TZ
        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=TASHKENT_TZ)
        offset = dt.utcoffset()
        assert offset == timedelta(hours=5)

    def test_to_tashkent_with_naive(self):
        from utils.timezone import to_tashkent
        naive = datetime(2026, 1, 1, 10, 0, 0)
        result = to_tashkent(naive)
        assert result.hour == 15  # 10 + 5

    def test_to_tashkent_with_aware_utc(self):
        from utils.timezone import to_tashkent
        aware = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        result = to_tashkent(aware)
        assert result.hour == 15

    def test_make_naive_utc_from_tashkent(self):
        from utils.timezone import make_naive_utc, TASHKENT_TZ
        tash = datetime(2026, 1, 1, 15, 0, 0, tzinfo=TASHKENT_TZ)
        result = make_naive_utc(tash)
        assert result.tzinfo is None
        assert result.hour == 10  # 15 - 5

    def test_make_naive_utc_from_naive_passthrough(self):
        from utils.timezone import make_naive_utc
        naive = datetime(2026, 1, 1, 12, 0, 0)
        result = make_naive_utc(naive)
        assert result == naive


class TestStructlogSetup:
    """Test that structlog configures without errors."""

    def test_configure_does_not_raise(self):
        from utils.logging import configure_structlog
        configure_structlog()  # Should not throw

    def test_get_logger_returns_logger(self):
        from utils.logging import get_logger
        logger = get_logger("test")
        assert logger is not None

    def test_logger_can_log(self):
        from utils.logging import get_logger
        logger = get_logger("test_log")
        # Should not throw
        logger.info("test message", key="value")


class TestI18n:
    """Test i18n.py backend translations."""

    def test_translations_has_three_languages(self):
        from i18n import TRANSLATIONS
        assert "ru" in TRANSLATIONS
        assert "uz" in TRANSLATIONS
        assert "en" in TRANSLATIONS

    def test_all_languages_have_same_keys(self):
        from i18n import TRANSLATIONS
        ru_keys = set(TRANSLATIONS["ru"].keys())
        uz_keys = set(TRANSLATIONS["uz"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        # All languages should have the same keys
        assert ru_keys == uz_keys, f"Missing in uz: {ru_keys - uz_keys}"
        assert ru_keys == en_keys, f"Missing in en: {ru_keys - en_keys}"

    def test_translate_function(self):
        from i18n import t, set_language
        set_language("ru")
        assert t("cancel") != ""  # Should return something, not empty


class TestConstants:
    """Test constants module."""

    def test_constants_importable(self):
        import constants
        # Should have some attributes
        assert hasattr(constants, '__file__')
