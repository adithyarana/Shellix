from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import unicodedata


def plain(value: str) -> str:
    """Strip terminal escapes/control characters from untrusted displayed data."""
    return ''.join(
        c if (c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) < 160
                               and unicodedata.category(c) != 'Cf'))
        else f"\\u{ord(c):04x}" for c in value
    )

from shellix.core.models import AIResponse, ExecutionResult


class TerminalUI:

    def __init__(self) -> None:
        self.console = Console(markup=False, highlight=False)

        self.prompt_session: PromptSession[str] = PromptSession()

        self.prompt_style = Style.from_dict(
            {
                "prompt": "bold",
            }
        )

    def show_banner(
        self,
        *,
        os_name: str,
        shell: str,
        directory: str,
    ) -> None:
        """Display the Shellix startup screen."""

        content = (
            "⚡ Shellix - AI Terminal Assistant\n\n"
            f"OS: {plain(os_name)}\n"
            f"Shell: {plain(shell)}\n"
            f"Directory: {plain(directory)}"
        )

        self.console.print(
            Panel(
                content,
                border_style="default",
                padding=(1, 2),
            )
        )

        self.console.print()

    def get_prompt(self) -> str:
        """Read a request from the user."""

        return self.prompt_session.prompt(
            [("class:prompt", "shellix ❯ ")],
            style=self.prompt_style,
        ).strip()

    def show_request(self, request: str) -> None:
        """Display the request received from the user."""

        self.console.print()
        self.console.print(
            f"Request: {plain(request)}"
        )
        self.console.print()

    def show_info(self, message: str) -> None:
        """Display an informational message."""

        text = Text("INFO: " + plain(message))
        text.stylize("bold", 0, 5)
        self.console.print(text)

    def show_success(self, message: str) -> None:
        """Display a success message."""

        text = Text("SUCCESS: " + plain(message))
        text.stylize("bold green", 0, 8)
        self.console.print(text)

    def show_error(self, message: str) -> None:
        """Display an error message."""

        text = Text("ERROR: " + plain(message))
        text.stylize("bold red", 0, 6)
        self.console.print(text)

    def show_goodbye(self) -> None:
        """Display the exit message."""

        self.console.print()
        self.console.print("Goodbye! 👋")
        self.console.print()

    def show_ai_response(self, response: AIResponse) -> None:
        """Render the AI-generated command suggestion."""

        self.console.print()
        self.console.print("Suggested command:")
        self.console.print(
            Panel(
                Text(plain(response.command)),
                border_style="default",
            )
        )
        self.console.print(
            f"Explanation: {plain(response.explanation)}"
        )
        self.console.print(
            f"AI Risk: {response.risk_level.value}"
        )
        self.console.print()

    def confirm_command(
        self,
        *,
        command: str,
        safety_level: str,
    ) -> bool:
        """Ask the user whether the command should be executed."""

        self.console.print()

        if safety_level == "HIGH":
            self.console.print(
                "⚠ High-risk command"
            )
        elif safety_level == "CRITICAL":
            self.console.print(
                "✗ Critical command blocked"
            )
            return False

        self.console.print(
            f"Safety level: {safety_level}"
        )
        self.console.print(
            f"Command: {plain(command)}"
        )

        answer = self.prompt_session.prompt(
            "Execute this command? [y/N]: "
        ).strip().lower()

        return answer in {"y", "yes"}


    def show_execution_result(
        self,
        result: ExecutionResult,
    ) -> None:
        """Display the result of command execution."""

        self.console.print()

        if result.timed_out:
            self.show_error(
                "Command execution timed out."
            )
        elif result.success:
            self.show_success(
                f"Command completed successfully "
                f"(exit code {result.exit_code})."
            )
        else:
            self.show_error(
                f"Command failed "
                f"(exit code {result.exit_code})."
            )

        if result.stdout.strip():
            self.console.print()
            self.console.print(
                "Output:"
            )
            self.console.print(Text(plain(result.stdout.rstrip())))

        if result.stderr.strip():
            self.console.print()
            self.console.print(
                "Error:"
            )
            self.console.print(Text(plain(result.stderr.rstrip())))

    def get_errors(self) -> str:
        self.show_info("Paste terminal errors (optional). Finish with a line containing only '.'; Ctrl-C cancels.")
        lines = []
        size = 0
        while True:
            line = self.prompt_session.prompt("error> ")
            if line == '.':
                return '\n'.join(lines)
            size += len(line.encode()) + 1
            if size > 16_000:
                from shellix.fixing.project import FixError
                raise FixError("Pasted errors exceed the 16 KB limit.")
            lines.append(line)

    def confirm_send(self) -> bool:
        return self.prompt_session.prompt("Send this context to OpenRouter? [y/N]: ").strip().lower() in {'y', 'yes'}

    def choose_file(self, paths: list[str]) -> str:
        for index, path in enumerate(paths, 1):
            self.show_info(f"{index}: {path}")
        answer = self.prompt_session.prompt("File number to open in Vim (blank cancels): ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(paths):
            return paths[int(answer) - 1]
        return ''

    def review_fix(self, diagnosis: str, paths: list[str], patch: str) -> str:
        conversation = plain(diagnosis + '\n\nAffected files:\n' + '\n'.join(paths))
        patch = plain(patch)
        if not self.console.is_terminal:
            self.console.print(Panel(Text(conversation), title="Diagnosis / files", border_style="default"))
            self.console.print(Text(patch))
            answer = self.prompt_session.prompt("[a] Apply / [r] Reject / [v] Open in Vim (default Reject): ")
            return {'a': 'apply', 'v': 'vim'}.get(answer.strip().lower(), 'reject')
        from prompt_toolkit.application import Application, get_app
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout, HSplit, VSplit, DynamicContainer
        from prompt_toolkit.widgets import TextArea, Frame
        from prompt_toolkit.layout.dimension import Dimension
        left = TextArea(text=conversation, read_only=True, scrollbar=True, wrap_lines=True)
        right = TextArea(text=patch, read_only=True, scrollbar=True, wrap_lines=False)
        panes = [Frame(left, title="Conversation / diagnosis"), Frame(right, title="Unified diff")]
        wide = VSplit(panes, padding=1)
        narrow = HSplit(panes, padding=1)
        body = DynamicContainer(lambda: wide if get_app().output.get_size().columns >= 100 else narrow)
        keys = KeyBindings()
        for key, result in [('c-a', 'apply'), ('c-r', 'reject'), ('c-v', 'vim'), ('c-c', 'reject')]:
            def finish(event, choice=result):
                event.app.exit(result=choice)
            keys.add(key)(finish)
        @keys.add('tab')
        def focus(event):
            event.app.layout.focus_next()
        app = Application(layout=Layout(HSplit([
            body, TextArea(text="Ctrl-A Apply | Ctrl-R Reject | Ctrl-V Vim\nTab switch pane | arrows/page keys scroll", read_only=True, focusable=False, height=Dimension.exact(2)),
        ]), focused_element=right), key_bindings=keys, full_screen=True,
            style=Style.from_dict({'frame.border': '', 'frame.label': 'bold', 'text-area': ''}))
        return app.run()


    def get_check_command(self) -> str:
        return self.prompt_session.prompt("Optional test/check command (blank skips; separate approval follows): ").strip()
