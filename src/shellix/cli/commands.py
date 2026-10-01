from __future__ import annotations
from typing import Optional
import sys
import typer
from typer.core import TyperGroup
from pydantic import ValidationError
from shellix.config.manager import ConfigManager, ConfigurationError, Settings
from shellix.ai.openrouter import OpenRouterProvider, AIRequestError
from shellix.ai.service import AIService
from shellix.cli.ui import TerminalUI
from shellix.core.session import SessionManager
from shellix.safety.validator import SafetyValidator
from shellix.executor.executor import CommandExecutor


class ShellixCLI:
    def __init__(
        self,
        ui: TerminalUI,
        session: SessionManager,
        ai_service: AIService,
        safety_validator: SafetyValidator,
        executor: CommandExecutor,
    ) -> None:
        self.ui = ui
        self.session = session
        self.ai_service = ai_service
        self.safety_validator = safety_validator
        self.executor = executor

    def run(self, initial_prompt: Optional[str] = None) -> None:
        """Start Shellix."""

        context = self.session.get_terminal_context()

        self.ui.show_banner(
            os_name=context.os,
            shell=context.shell,
            directory=context.current_directory,
        )

        if initial_prompt:
            self.handle_request(initial_prompt)
            return

        self.run_interactive_mode()

    def run_interactive_mode(self) -> None:
        while True:
            try:
                request = self.ui.get_prompt()

                if not request:
                    continue

                if self.is_exit_command(request):
                    self.ui.show_goodbye()
                    return

                self.handle_request(request)

            except KeyboardInterrupt:
                self.ui.show_goodbye()
                return

            except EOFError:
                self.ui.show_goodbye()
                return

            except Exception as exc:
                self.ui.show_error(str(exc))

    def handle_request(self, request: str) -> None:
        """Process a user request and execute approved commands."""

        context = self.session.get_terminal_context()

        self.ui.show_info("Thinking...")

        response = self.ai_service.generate_command(
            prompt=request,
            context=context,
        )

        safety_result = self.safety_validator.validate(
            response.command
        )

        self.ui.show_ai_response(response)

        self.ui.show_info(
            f"Shellix Safety: {safety_result.level.value}"
        )

        for reason in safety_result.reasons:
            self.ui.show_info(reason)

        # Block critical commands.
        if not safety_result.allowed:
            self.ui.show_error(
                "This command has been blocked by Shellix."
            )
            return

        # SAFE command → execute automatically.
        if not safety_result.requires_confirmation:
            self.ui.show_info(
                "Command is considered safe."
            )
            self.ui.show_info(
                "Executing command..."
            )

            result = self.executor.execute(
                response.command
            )
            self.ui.show_execution_result(result)
            return

        # MEDIUM/HIGH → ask user.
        confirmed = self.ui.confirm_command(
            command=response.command,
            safety_level=safety_result.level.value,
        )

        if confirmed:
            self.ui.show_info(
                "Executing command..."
            )

            result = self.executor.execute(
                response.command
            )
            self.ui.show_execution_result(result)
        else:
            self.ui.show_info(
                "Command cancelled."
            )

    @staticmethod
    def is_exit_command(request: str) -> bool:
        return request.lower() in {
            "exit",
            "quit",
            ":q",
        }


class PromptGroup(TyperGroup):
    """Route the original positional request syntax to the hidden run command."""

    def resolve_command(self, ctx: typer.Context, args: list[str]):
        if args and not args[0].startswith("-") and args[0] != "configure":
            return "run", self.get_command(ctx, "run"), args
        return super().resolve_command(ctx, args)


app = typer.Typer(
    name="shellix", cls=PromptGroup,
    help="AI-powered terminal assistant using OpenRouter.",
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


def is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def configure_settings(manager: ConfigManager) -> Settings:
    try:
        existing = manager.load()
    except ConfigurationError:
        typer.echo("Existing settings are invalid or unreadable; enter replacement settings.")
        existing = None
    typer.echo("Shellix uses OpenRouter. Enter a key issued by OpenRouter, not NVIDIA.")
    try:
        key = typer.prompt(
            "OpenRouter API key" + (" (leave blank to keep existing key)" if existing else ""),
            hide_input=True, default="", show_default=False,
        ).strip()
        if not key and existing:
            key = existing.api_key.get_secret_value()
        if not key:
            raise ConfigurationError("OpenRouter API key cannot be empty.")
        model = typer.prompt("OpenRouter model ID", default=existing.model if existing else "",
                             show_default=bool(existing)).strip()
        if not model:
            raise ConfigurationError("OpenRouter model ID cannot be empty.")
        settings = Settings(api_key=key, model=model)
        manager.save(settings)
    except (typer.Abort, KeyboardInterrupt, EOFError):
        typer.echo("Configuration cancelled; previous settings were preserved.")
        raise typer.Exit(130) from None
    except ValidationError:
        raise ConfigurationError("Invalid settings. API key and model ID are required.") from None
    typer.echo("OpenRouter settings saved.")
    return settings


@app.command()
def configure() -> None:
    """Set the OpenRouter API key and model without starting the assistant."""
    if not is_interactive():
        typer.echo("Run shellix configure in an interactive terminal.", err=True)
        raise typer.Exit(1)
    try:
        configure_settings(ConfigManager())
    except ConfigurationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None


def start(prompt: Optional[str] = None) -> None:
    try:
        manager = ConfigManager()
        settings = manager.load()
        if settings is None:
            if not is_interactive():
                raise ConfigurationError("Missing configuration. Run shellix configure in an interactive terminal.")
            settings = configure_settings(manager)
        elif prompt is None and not is_interactive():
            raise ConfigurationError('Provide a request, for example: shellix "list files".')

        provider = OpenRouterProvider(api_key=settings.api_key.get_secret_value(), model=settings.model)
        cli = ShellixCLI(
            ui=TerminalUI(), session=SessionManager(), ai_service=AIService(provider),
            safety_validator=SafetyValidator(), executor=CommandExecutor(),
        )
        cli.run(prompt)
    except (ConfigurationError, AIRequestError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run shellix interactively, or shellix \"list files\" for one request."""
    if ctx.invoked_subcommand is None:
        start()


@app.command(hidden=True)
def run(prompt: str = typer.Argument(..., help="Natural-language request.")) -> None:
    start(prompt)
