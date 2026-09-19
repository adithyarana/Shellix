from __future__ import annotations
import subprocess
from shellix.core.models import ExecutionResult


class CommandExecutor:
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def execute(self, command: str) -> ExecutionResult:
        try:
            completed_process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return ExecutionResult(
                command=command,
                stdout=completed_process.stdout,
                stderr=completed_process.stderr,
                exit_code=completed_process.returncode,
                success=completed_process.returncode == 0,
                timed_out=False,
            )

        except subprocess.TimeoutExpired as exc:
            stdout = self._decode_output(exc.stdout)
            stderr = self._decode_output(exc.stderr)

            return ExecutionResult(
                command=command,
                stdout=stdout,
                stderr=stderr,
                exit_code=-1,
                success=False,
                timed_out=True,
            )

        except OSError as exc:
            return ExecutionResult(
                command=command,
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                success=False,
                timed_out=False,
            )

    @staticmethod
    def _decode_output(output: object) -> str:
        """Convert subprocess output into a string."""

        if output is None:
            return ""

        if isinstance(output, bytes):
            return output.decode(
                "utf-8",
                errors="replace",
            )

        return str(output)