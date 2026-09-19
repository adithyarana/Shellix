from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from shellix.core.models import AIResponse, ExecutionResult


class TerminalUI:

    def __init__(self) -> None:
        self.console = Console()

        self.prompt_session: PromptSession[str] = PromptSession()

        self.prompt_style = Style.from_dict(
            {
                "prompt": "bold cyan",
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
            "[bold cyan]⚡ Shellix[/bold cyan] - AI Terminal Assistant\n\n"
            f"[bold]OS:[/bold] {os_name}\n"
            f"[bold]Shell:[/bold] {shell}\n"
            f"[bold]Directory:[/bold] {directory}"
        )

        self.console.print(
            Panel(
                content,
                border_style="cyan",
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
            f"[bold]Request:[/bold] {request}"
        )
        self.console.print()

    def show_info(self, message: str) -> None:
        """Display an informational message."""

        self.console.print(f"[cyan]ℹ[/cyan] {message}")

    def show_success(self, message: str) -> None:
        """Display a success message."""

        self.console.print(f"[green]✓[/green] {message}")

    def show_error(self, message: str) -> None:
        """Display an error message."""

        self.console.print(f"[red]✗[/red] {message}")

    def show_goodbye(self) -> None:
        """Display the exit message."""

        self.console.print()
        self.console.print("[cyan]Goodbye! 👋[/cyan]")
        self.console.print()

    def show_ai_response(self, response: AIResponse) -> None:
        """Render the AI-generated command suggestion."""

        self.console.print()
        self.console.print("[bold]Suggested command:[/bold]")
        self.console.print(
            Panel(
                response.command,
                border_style="green",
            )
        )
        self.console.print(
            f"[bold]Explanation:[/bold] {response.explanation}"
        )
        self.console.print(
            f"[bold]AI Risk:[/bold] {response.risk_level.value}"
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
                "[bold yellow]⚠ High-risk command[/bold yellow]"
            )
        elif safety_level == "CRITICAL":
            self.console.print(
                "[bold red]✗ Critical command blocked[/bold red]"
            )
            return False

        self.console.print(
            f"[bold]Safety level:[/bold] {safety_level}"
        )
        self.console.print(
            f"[bold]Command:[/bold] {command}"
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
                "[bold]Output:[/bold]"
            )
            self.console.print(result.stdout.rstrip())

        if result.stderr.strip():
            self.console.print()
            self.console.print(
                "[bold red]Error:[/bold]"
            )
            self.console.print(result.stderr.rstrip())