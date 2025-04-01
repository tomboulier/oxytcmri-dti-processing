from tqdm import tqdm
from oxytcmri.domain.ports.monitoring import Event, Listener, ProgressEvent


class TqdmProgressListener(Listener):
    """
    A listener that displays a progress bar using tqdm for ProgressEvent events.
    """

    def __init__(self) -> None:
        self.pbar: tqdm | None = None

    def on_event(self, event: Event) -> None:
        if not isinstance(event, ProgressEvent):
            return

        if self.pbar is None:
            self.pbar = tqdm(total=event.total)

        self.pbar.n = event.step
        self.pbar.refresh()

        if event.step >= self.pbar.total:
            self.pbar.close()
