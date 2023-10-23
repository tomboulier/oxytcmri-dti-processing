# tests.py

from oxytcmri import settings


class TestSettings:
    """Test suite for verifying the behavior of the settings module"""
    def test_read_test_variable(self):
        """Verify that the "test_variable" in the [test] section
        of the  settings file "settings.toml" is read correctly"""
        assert settings.test.test_variable == "test_value"

    def test_read_test_secret(self):
        """Verify that the "test_secret" in the [test] section
        of the secret settings file ".secrets.toml" is read correctly"""
        assert settings.test.test_secret == "test_secret_value"
