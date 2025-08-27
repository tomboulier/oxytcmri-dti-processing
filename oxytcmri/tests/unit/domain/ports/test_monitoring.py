"""Unit tests for the monitoring module."""
from unittest.mock import Mock

from oxytcmri.domain.ports.monitoring import LogEvent, ProgressEvent, EventDispatcher, Listener


class TestLogEvent:
    """Test cases for the LogEvent class."""

    def test_init_with_defaults(self):
        """Test LogEvent initialization with default level."""
        event = LogEvent("Test message")
        
        assert event.message == "Test message"
        assert event.level == "INFO"

    def test_init_with_custom_level(self):
        """Test LogEvent initialization with custom level."""
        event = LogEvent("Test message", "warning")
        
        assert event.message == "Test message"
        assert event.level == "WARNING"  # Should be uppercase

    def test_init_with_uppercase_level(self):
        """Test LogEvent initialization with already uppercase level."""
        event = LogEvent("Test message", "ERROR")
        
        assert event.message == "Test message"
        assert event.level == "ERROR"


class TestProgressEvent:
    """Test cases for the ProgressEvent class."""

    def test_init(self):
        """Test ProgressEvent initialization."""
        event = ProgressEvent(5, 10)
        
        assert event.step == 5
        assert event.total == 10


class TestEventDispatcher:
    """Test cases for the EventDispatcher class."""

    def test_init(self):
        """Test EventDispatcher initialization."""
        dispatcher = EventDispatcher()
        
        assert dispatcher._listeners == []

    def test_register_listener(self):
        """Test registering a listener."""
        dispatcher = EventDispatcher()
        mock_listener = Mock(spec=Listener)
        
        dispatcher.register(mock_listener)
        
        assert mock_listener in dispatcher._listeners

    def test_dispatch_event_to_listeners(self):
        """Test dispatching an event to registered listeners."""
        dispatcher = EventDispatcher()
        mock_listener1 = Mock(spec=Listener)
        mock_listener2 = Mock(spec=Listener)
        
        dispatcher.register(mock_listener1)
        dispatcher.register(mock_listener2)
        
        event = LogEvent("Test event")
        dispatcher.dispatch(event)
        
        mock_listener1.on_event.assert_called_once_with(event)
        mock_listener2.on_event.assert_called_once_with(event)

    def test_dispatch_event_no_listeners(self):
        """Test dispatching an event when no listeners are registered."""
        dispatcher = EventDispatcher()
        event = LogEvent("Test event")
        
        # Should not raise any exceptions
        dispatcher.dispatch(event)