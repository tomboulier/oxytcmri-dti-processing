from tqdm import tqdm
from oxytcmri.domain.ports.monitoring import Event, Listener, ProgressEvent


class TqdmProgressListener(Listener):
    """
    A listener that displays a progress bar using tqdm for ProgressEvent events.

    Parameters
    ----------
    total : int
        The total number of steps to complete.
    """

    def __init__(self, total: int) -> None:
        self.pbar = tqdm(total=total)

    def on_event(self, event: Event) -> None:
        if isinstance(event, ProgressEvent):
            self.pbar.n = event.step
            self.pbar.refresh()
            if event.step >= self.pbar.total:
                self.pbar.close()
