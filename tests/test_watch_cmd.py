import types
from unittest.mock import MagicMock, patch, call

from stackwatch.fetcher import StackState
from stackwatch.commands.watch_cmd import cmd_watch


def _args(**kwargs):
    defaults = dict(
        stack_name="my-stack",
        region=None,
        profile=None,
        interval=5,
        no_color=True,
    )
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def make_state(status="CREATE_COMPLETE", params=None, resources=None):
    return StackState(
        name="my-stack",
        status=status,
        parameters=params or {},
        outputs={},
        resources=resources or {},
    )


def _run_watch(states, args=None):
    """Drive cmd_watch by exhausting `states`, then raising KeyboardInterrupt."""
    if args is None:
        args = _args()

    side_effects = list(states) + [KeyboardInterrupt()]

    with patch("stackwatch.commands.watch_cmd.fetch_stack", side_effect=side_effects), \
         patch("stackwatch.commands.watch_cmd.time.sleep"):
        return cmd_watch(args)


def test_returns_0_on_keyboard_interrupt():
    result = _run_watch([make_state()])
    assert result == 0


def test_prints_initial_status(capsys):
    _run_watch([make_state(status="UPDATE_COMPLETE")])
    out = capsys.readouterr().out
    assert "initial" in out
    assert "UPDATE_COMPLETE" in out


def test_no_change_message(capsys):
    state = make_state()
    _run_watch([state, state])
    out = capsys.readouterr().out
    assert "no change" in out


def test_diff_printed_on_status_change(capsys):
    s1 = make_state(status="UPDATE_IN_PROGRESS")
    s2 = make_state(status="UPDATE_COMPLETE")
    _run_watch([s1, s2])
    out = capsys.readouterr().out
    assert "UPDATE_COMPLETE" in out or "UPDATE_IN_PROGRESS" in out


def test_none_stack_prints_no_data(capsys):
    _run_watch([None])
    out = capsys.readouterr().out
    assert "my-stack" in out


def test_sleep_called_with_interval():
    args = _args(interval=10)
    with patch("stackwatch.commands.watch_cmd.fetch_stack", side_effect=[make_state(), KeyboardInterrupt()]), \
         patch("stackwatch.commands.watch_cmd.time.sleep") as mock_sleep:
        cmd_watch(args)
    mock_sleep.assert_called_with(10)


def test_sleep_called_between_polls():
    """Verify sleep is called once per poll cycle, not just on the final iteration."""
    states = [make_state(), make_state(), make_state()]
    args = _args(interval=7)
    side_effects = states + [KeyboardInterrupt()]

    with patch("stackwatch.commands.watch_cmd.fetch_stack", side_effect=side_effects), \
         patch("stackwatch.commands.watch_cmd.time.sleep") as mock_sleep:
        cmd_watch(args)

    assert mock_sleep.call_count == len(states)
    mock_sleep.assert_called_with(7)
