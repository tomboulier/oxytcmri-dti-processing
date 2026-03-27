"""Unit tests for the logger module."""
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from oxytcmri.infrastructure.logger import Logger
from oxytcmri.infrastructure.settings import Settings


class TestLogger:
    """Test cases for the Logger class."""

    @pytest.fixture
    def mock_settings_with_logs(self):
        """Create a mock settings object with logs configuration."""
        settings = Mock(spec=Settings)
        settings.logs = Mock()
        settings.logs.log_level = "DEBUG"
        settings.logs.save_to_file = True
        settings.logs.log_to_console = False
        return settings

    @pytest.fixture
    def mock_settings_without_logs(self):
        """Create a mock settings object without logs configuration."""
        settings = Mock(spec=Settings)
        # Remove logs attribute to trigger AttributeError
        del settings.logs
        return settings

    def test_init_with_valid_settings(self, mock_settings_with_logs):
        """Test Logger initialization with valid settings."""
        logger = Logger(mock_settings_with_logs)
        
        assert logger.settings == mock_settings_with_logs
        assert logger.log_level == "DEBUG"
        assert logger.save_to_file is True
        assert logger.log_to_console is False

    def test_init_with_missing_logs_config(self, mock_settings_without_logs):
        """Test Logger initialization when logs config is missing."""
        logger = Logger(mock_settings_without_logs)
        
        assert logger.settings == mock_settings_without_logs
        assert logger.log_level == "INFO"  # Default value
        assert logger.save_to_file is False  # Default value
        assert logger.log_to_console is True  # Default value

    def test_get_log_level_with_valid_config(self, mock_settings_with_logs):
        """Test get_log_level method with valid configuration."""
        logger = Logger(mock_settings_with_logs)
        assert logger.get_log_level() == "DEBUG"

    def test_get_log_level_with_missing_config(self, mock_settings_without_logs):
        """Test get_log_level method with missing configuration."""
        logger = Logger(mock_settings_without_logs)
        assert logger.get_log_level() == "INFO"

    def test_get_save_to_file_with_valid_config(self, mock_settings_with_logs):
        """Test get_save_to_file method with valid configuration."""
        logger = Logger(mock_settings_with_logs)
        assert logger.get_save_to_file() is True

    def test_get_save_to_file_with_missing_config(self, mock_settings_without_logs):
        """Test get_save_to_file method with missing configuration."""
        logger = Logger(mock_settings_without_logs)
        assert logger.get_save_to_file() is False

    def test_get_log_to_console_with_valid_config(self, mock_settings_with_logs):
        """Test get_log_to_console method with valid configuration."""
        logger = Logger(mock_settings_with_logs)
        assert logger.get_log_to_console() is False

    def test_get_log_to_console_with_missing_config(self, mock_settings_without_logs):
        """Test get_log_to_console method with missing configuration."""
        logger = Logger(mock_settings_without_logs)
        assert logger.get_log_to_console() is True

    @patch('oxytcmri.infrastructure.logger.logging.basicConfig')
    def test_setup_console_only(self, mock_basic_config, mock_settings_without_logs):
        """Test setup method with console logging only."""
        logger = Logger(mock_settings_without_logs)
        logger.setup()
        
        # Should be called with console handler only
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        
        assert kwargs['level'] == "INFO"
        assert kwargs['format'] == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        assert len(kwargs['handlers']) == 1
        assert isinstance(kwargs['handlers'][0], logging.StreamHandler)

    def test_setup_file_only(self):
        """Test setup method with file logging only."""
        # Setup mock settings
        settings = Mock(spec=Settings)
        settings.logs = Mock()
        settings.logs.log_level = "ERROR"
        settings.logs.save_to_file = True
        settings.logs.log_to_console = False
        
        # Create a real temporary directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_folder = Path(temp_dir) / "logs"
            logs_folder.mkdir()
            
            with patch('oxytcmri.infrastructure.logger.Path') as mock_path_class, \
                 patch('oxytcmri.infrastructure.logger.logging.basicConfig') as mock_basic_config, \
                 patch('oxytcmri.infrastructure.logger.datetime') as mock_datetime, \
                 patch('builtins.print') as mock_print:
                
                # Setup mock datetime
                mock_datetime.now.return_value.strftime.return_value = "2023-01-01_12-00-00"
                
                # Setup Path(__file__) to return a path that leads to our logs folder
                mock_file_path = MagicMock()
                mock_file_path.parents = [None, None, logs_folder.parent]
                mock_path_class.return_value = mock_file_path
                
                logger = Logger(settings)
                logger.setup()
                
                # Verify print statement for file logging without console
                mock_print.assert_called_once()
                assert "tail -f" in str(mock_print.call_args)
                
                # Should be called with file handler only
                mock_basic_config.assert_called_once()
                args, kwargs = mock_basic_config.call_args
                
                assert kwargs['level'] == "ERROR"
                assert len(kwargs['handlers']) == 1
                assert isinstance(kwargs['handlers'][0], logging.FileHandler)

    def test_setup_file_and_console(self):
        """Test setup method with both file and console logging."""
        # Setup mock settings
        settings = Mock(spec=Settings)
        settings.logs = Mock()
        settings.logs.log_level = "WARNING"
        settings.logs.save_to_file = True
        settings.logs.log_to_console = True
        
        # Create a real temporary directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_folder = Path(temp_dir) / "logs"
            logs_folder.mkdir()
            
            with patch('oxytcmri.infrastructure.logger.Path') as mock_path_class, \
                 patch('oxytcmri.infrastructure.logger.logging.basicConfig') as mock_basic_config:
                
                # Setup Path(__file__) to return a path that leads to our logs folder
                mock_file_path = MagicMock()
                mock_file_path.parents = [None, None, logs_folder.parent]
                mock_path_class.return_value = mock_file_path
                
                logger = Logger(settings)
                logger.setup()
                
                # Should be called with both handlers
                mock_basic_config.assert_called_once()
                args, kwargs = mock_basic_config.call_args
                
                assert kwargs['level'] == "WARNING"
                assert len(kwargs['handlers']) == 2
                
                # Check handler types
                handler_types = [type(handler) for handler in kwargs['handlers']]
                assert logging.StreamHandler in handler_types
                assert logging.FileHandler in handler_types

    def test_setup_file_logging_missing_logs_folder(self):
        """Test setup method when logs folder doesn't exist."""
        # Setup mock settings
        settings = Mock(spec=Settings)
        settings.logs = Mock()
        settings.logs.log_level = "INFO"
        settings.logs.save_to_file = True
        settings.logs.log_to_console = False
        
        # Create a temporary directory but don't create the logs subfolder
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('oxytcmri.infrastructure.logger.Path') as mock_path_class:
                # Setup Path(__file__) to return a path where logs folder doesn't exist
                mock_file_path = MagicMock()
                mock_file_path.parents = [None, None, Path(temp_dir)]
                mock_path_class.return_value = mock_file_path
                
                logger = Logger(settings)
                
                with pytest.raises(FileNotFoundError, match="Logs folder not found"):
                    logger.setup()

    @patch('oxytcmri.infrastructure.logger.logging.basicConfig')
    def test_setup_no_handlers(self, mock_basic_config):
        """Test setup method with no logging handlers enabled."""
        # Setup mock settings with both console and file disabled
        settings = Mock(spec=Settings)
        settings.logs = Mock()
        settings.logs.log_level = "INFO"
        settings.logs.save_to_file = False
        settings.logs.log_to_console = False
        
        logger = Logger(settings)
        logger.setup()
        
        # Should still be called but with empty handlers list
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        
        assert kwargs['level'] == "INFO"
        assert len(kwargs['handlers']) == 0