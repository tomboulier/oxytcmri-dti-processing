"""Unit tests for the settings module."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from oxytcmri.infrastructure.settings import Settings, ModuleSettings


class TestSettings:
    """Test cases for the Settings class."""

    @pytest.fixture
    def valid_settings_file(self):
        """Create a temporary valid settings file."""
        content = """
[database]
url = "sqlite:///test.db"
overwrite_data = true

[logs]
log_level = "DEBUG"
save_to_file = false
log_to_console = true

[paths]
base_path = "/tmp/test"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(content)
            f.flush()
            yield f.name
        # Cleanup
        Path(f.name).unlink()

    @pytest.fixture
    def invalid_settings_file(self):
        """Return a path to a non-existent settings file."""
        return "/path/that/does/not/exist.toml"

    def test_init_with_valid_file(self, valid_settings_file):
        """Test Settings initialization with a valid file."""
        settings = Settings(valid_settings_file)
        
        assert settings.filepath == Path(valid_settings_file).resolve()
        assert settings.base_dir == Path(valid_settings_file).parent.resolve()
        assert settings._dynaconf_settings is not None

    def test_init_with_invalid_file(self, invalid_settings_file):
        """Test Settings initialization with an invalid file path."""
        with pytest.raises(FileNotFoundError, match="Settings file not found"):
            Settings(invalid_settings_file)

    def test_getattr_simple_value(self, valid_settings_file):
        """Test __getattr__ for simple values."""
        settings = Settings(valid_settings_file)
        
        # Access a module that should return a ModuleSettings object
        database = settings.database
        assert isinstance(database, ModuleSettings)
        
        # Access a simple value through the module
        assert database.url == "sqlite:///test.db"
        assert database.overwrite_data is True

    def test_getattr_module_settings(self, valid_settings_file):
        """Test __getattr__ returns ModuleSettings for complex values."""
        settings = Settings(valid_settings_file)
        
        logs = settings.logs
        assert isinstance(logs, ModuleSettings)
        assert logs.log_level == "DEBUG"
        assert logs.save_to_file is False
        assert logs.log_to_console is True

    def test_getattr_nonexistent_module(self, valid_settings_file):
        """Test __getattr__ with non-existent module."""
        settings = Settings(valid_settings_file)
        
        with pytest.raises(AttributeError, match="No module 'nonexistent' in settings file"):
            _ = settings.nonexistent

    def test_setattr_special_attributes(self, valid_settings_file):
        """Test __setattr__ for special attributes."""
        settings = Settings(valid_settings_file)
        
        # These should be set directly on the object
        original_filepath = settings.filepath
        settings.filepath = Path("/some/other/path")
        assert settings.filepath == Path("/some/other/path")
        
        # Reset for cleanup
        settings.filepath = original_filepath

    def test_setattr_dynaconf_attributes(self, valid_settings_file):
        """Test __setattr__ for dynaconf attributes."""
        settings = Settings(valid_settings_file)
        
        # This should be set on the dynaconf object
        settings.new_attribute = "test_value"
        assert settings.new_attribute == "test_value"

    def test_to_toml(self, valid_settings_file):
        """Test to_toml method."""
        settings = Settings(valid_settings_file)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            output_path = f.name
        
        try:
            settings.to_toml(output_path)
            
            # Verify the file was created and contains expected content
            assert Path(output_path).exists()
            
            # Load and verify the content
            new_settings = Settings(output_path)
            assert new_settings.database.url == "sqlite:///test.db"
            
        finally:
            # Cleanup
            Path(output_path).unlink()

    def test_repr(self, valid_settings_file):
        """Test __repr__ method."""
        settings = Settings(valid_settings_file)
        
        repr_str = repr(settings)
        assert f"Settings(filename='{settings.filepath}')" == repr_str

    def test_str(self, valid_settings_file):
        """Test __str__ method."""
        settings = Settings(valid_settings_file)
        
        str_representation = str(settings)
        assert f"Settings(filename='{settings.filepath}')" in str_representation
        assert "------------------------------------------------------------------------" in str_representation
        # TOML converts to uppercase
        assert "DATABASE" in str_representation or "database" in str_representation
        assert "LOGS" in str_representation or "logs" in str_representation


class TestModuleSettings:
    """Test cases for the ModuleSettings class."""

    def test_real_settings_integration(self):
        """Integration test with real settings file."""
        content = """
[test_module]
setting1 = "value1"
setting2 = 42
setting3 = true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                settings = Settings(f.name)
                module = settings.test_module
                
                assert isinstance(module, ModuleSettings)
                assert module.setting1 == "value1"
                assert module.setting2 == 42
                assert module.setting3 is True
                
                # Test setting a new value
                module.setting4 = "new_value"
                assert module.setting4 == "new_value"
                
                # Test list_attributes
                attrs = module.list_attributes()
                assert "setting1" in attrs
                assert "setting2" in attrs
                assert "setting3" in attrs
                
            finally:
                # Cleanup
                Path(f.name).unlink()

    def test_module_settings_error_handling(self):
        """Test error handling in ModuleSettings with edge cases."""
        content = """
[empty_module]

[test_module]
existing_attr = "value"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                settings = Settings(f.name)
                
                # Test empty module
                empty_module = settings.empty_module
                attrs = empty_module.list_attributes()
                # Might contain the filepath attribute depending on implementation
                assert isinstance(attrs, list)
                
                # Test accessing non-existent attribute on test_module
                test_module = settings.test_module
                with pytest.raises(AttributeError, match="No attribute 'missing' for module 'test_module'"):
                    _ = test_module.missing
                
                # Test that existing attributes work
                assert test_module.existing_attr == "value"
                    
            finally:
                # Cleanup
                Path(f.name).unlink()

    def test_module_settings_init_and_getattr(self):
        """Test ModuleSettings init and getattr with real DynaBox."""
        content = """
[test_module]
attr1 = "value1"
attr2 = 123
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                settings = Settings(f.name)
                module = settings.test_module
                
                # Test init worked correctly
                assert module.module_name == "test_module"
                assert module.filepath == settings.filepath
                
                # Test getattr works
                assert module.attr1 == "value1"
                assert module.attr2 == 123
                
            finally:
                # Cleanup
                Path(f.name).unlink()

    def test_module_settings_setattr(self):
        """Test ModuleSettings setattr functionality."""
        content = """
[test_module]
existing = "value"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                settings = Settings(f.name)
                module = settings.test_module
                
                # Test setting a new attribute
                module.new_attr = "new_value"
                assert module.new_attr == "new_value"
                
                # Test modifying an existing attribute
                module.existing = "modified_value"
                assert module.existing == "modified_value"
                
            finally:
                # Cleanup
                Path(f.name).unlink()