from oxytcmri.domain.ports.monitoring import ProgressEvent
from oxytcmri.infrastructure.listeners import TqdmProgressListener


def test_tqdm_progress_listener_runs_without_error(capfd):
    """
    Integration test for TqdmProgressListener using real tqdm output.

    This test verifies that the TqdmProgressListener correctly displays a progress
    bar when receiving ProgressEvent instances. It does not mock any part of tqdm:
    instead, it lets tqdm render normally to standard error and checks the
    captured output to ensure that progress is being displayed.

    Notes
    -----
    - tqdm writes to stderr by default, not stdout.
    - This test focuses on ensuring the listener works "in the real world"
      (i.e., no crashes, progress appears), not on internal method calls.

    Parameters
    ----------
    capfd : pytest fixture
        Pytest fixture to capture output sent to stdout and stderr.

    Asserts
    -------
    - That the final progress display includes a string like "3/3".
    - That the string "100%" is present, indicating completion.
    """
    total_events = 3
    listener = TqdmProgressListener()

    # trigger events
    for i in range(1, total_events + 1):
        event = ProgressEvent(step=i, total=total_events)
        listener.on_event(event)

    # capture output
    # note: tqdm output writes to stderr, not stdout
    _, err = capfd.readouterr()

    # check final output
    assert f"{total_events}/{total_events}" in err
    assert "100%" in err
