from __future__ import annotations
from typing import Optional
import typer
from shellix.ai.openrouter import OpenRouterProvider
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


app = typer.Typer(
    name="shellix",
    help="AI-powered terminal assistant.",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    prompt: Optional[str] = typer.Argument(
        None,
        help="Optional natural-language request.",
    ),
) -> None:
    """Start Shellix."""

    ui = TerminalUI()
    session = SessionManager()

    provider = OpenRouterProvider()
    ai_service = AIService(provider)
    safety_validator = SafetyValidator()
    executor = CommandExecutor()

    cli = ShellixCLI(
        ui=ui,
        session=session,
        ai_service=ai_service,
        safety_validator=safety_validator,
        executor=executor,
    )

    cli.run(prompt)