# monitoring.py

from abc import ABC, abstractmethod
from typing import Any


class Event(ABC):
    """
    Base class for all events emitted by the system.
    """
    pass


class ProgressEvent(Event):
    """
    Event indicating progress in a long-running process.

    Parameters
    ----------
    step : int
        The current step.
    total : int
        The total number of steps.
    """
    def __init__(self, step: int, total: int) -> None:
        self.step: int = step
        self.total: int = total


class LogEvent(Event):
    """
    Event representing a log message.

    Parameters
    ----------
    message : str
        The message to log.
    level : str
        The log level ('INFO', 'DEBUG', 'WARNING', 'ERROR').
    """
    def __init__(self, message: str, level: str = "INFO") -> None:
        self.message: str = message
        self.level: str = level.upper()


class Listener(ABC):
    """
    Abstract interface for any object that listens to events.
    """

    @abstractmethod
    def on_event(self, event: Event) -> None:
        """
        React to an emitted event.

        Parameters
        ----------
        event : Event
            The emitted event instance.
        """


class EventDispatcher:
    """
    Central hub for dispatching events to registered listeners.

    Attributes
    ----------
    _listeners : list[Listener]
        The registered listeners that will receive all events.
    """

    def __init__(self) -> None:
        self._listeners: list[Listener] = []

    def register(self, listener: Listener) -> None:
        """
        Add a listener to receive future events.

        Parameters
        ----------
        listener : Listener
            A listener instance implementing on_event().
        """
        self._listeners.append(listener)

    def dispatch(self, event: Event) -> None:
        """
        Dispatch an event to all registered listeners.

        Parameters
        ----------
        event : Event
            An event instance to send to all listeners.
        """
        for listener in self._listeners:
            listener.on_event(event)
