"""`!<command>` typed in the prompt_toolkit TUI while the agent is busy must run immediately.

The owner's `!hermes-account the41220` did nothing for an entire long agent turn: a bang
command typed while the agent runs was pushed into `_pending_input`, which the process loop
only drains after the current turn ends. Slash commands already have an inline path for the
same reason (/model, /steer, /bg); bang commands cost zero tokens and run locally, so they
get the same immediate dispatch.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tests.cli.test_cli_init import _make_cli


def _enter(cli, text):
    cli._tui_multiline_shortcuts = False
    cli._tui_enter_overlay = lambda event: False
    cli._inline_pastes = lambda buf: None
    buf = SimpleNamespace(text=text, cursor_position=len(text), reset=MagicMock())
    app = SimpleNamespace(current_buffer=buf, invalidate=MagicMock(), is_running=False, exit=MagicMock())
    cli._tui_handle_enter(SimpleNamespace(app=app))
    return buf


def test_busy_bang_runs_inline_instead_of_waiting_for_the_turn():
    cli = _make_cli()
    cli._agent_running = True
    cli._attached_images = []
    with patch.object(type(cli), "handle_bang_shell", return_value=True) as bang:
        buf = _enter(cli, "!hermes-account 2")
    bang.assert_called_once_with("!hermes-account 2")
    assert cli._pending_input.empty()
    assert cli._interrupt_queue.empty()
    buf.reset.assert_called_once()


def test_idle_bang_still_runs_inline_and_never_becomes_a_turn():
    cli = _make_cli()
    cli._agent_running = False
    cli._attached_images = []
    with patch.object(type(cli), "handle_bang_shell", return_value=True) as bang:
        _enter(cli, "!echo hi")
    bang.assert_called_once()
    assert cli._pending_input.empty()


def test_plain_prompt_while_busy_is_untouched_by_the_bang_path():
    cli = _make_cli()
    cli._agent_running = True
    cli._attached_images = []
    cli.agent = None
    with patch.object(type(cli), "handle_bang_shell") as bang:
        _enter(cli, "fix the bug!")
    bang.assert_not_called()
    assert cli._pending_input.empty() != cli._interrupt_queue.empty()
