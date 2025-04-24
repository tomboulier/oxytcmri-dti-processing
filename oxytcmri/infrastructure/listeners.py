"""
This module provides listeners for monitoring events in the application.
"""

from tqdm import tqdm  # type: ignore

from oxytcmri.domain.ports.monitoring import Event, Listener, ProgressEvent


class TqdmProgressListener(Listener):
    """
    A listener that displays a progress bar using [tqdm](https://tqdm.github.io/) for `ProgressEvent` events.

    This class implements the Listener interface and updates a tqdm progress bar
    based on the events it receives. It initializes a progress bar when it receives
    the first ProgressEvent and updates it with the current step. When the total
    number of steps is reached, the progress bar is closed.

    Attributes
    ----------
    progress_bar : tqdm | None
        The tqdm progress bar instance. It is initialized to None and created when the first ProgressEvent is received.
    """

    def __init__(self) -> None:
        self.progress_bar: tqdm | None = None

    def on_event(self, event: Event) -> None:
        """
        Handle the event by updating the progress bar if the event is a `ProgressEvent`.

        Parameters
        ----------
        event : Event
            The event to handle.
        """
        if not isinstance(event, ProgressEvent):
            return

        if self.progress_bar is None:
            self.progress_bar = tqdm(total=event.total)

        self.progress_bar.n = event.step
        self.progress_bar.refresh()

        if event.step >= self.progress_bar.total:
            self.progress_bar.close()
