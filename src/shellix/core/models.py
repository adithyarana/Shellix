from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TerminalContext(BaseModel):
    os: str = Field(..., description="Operating system name.")
    shell: str = Field(..., description="Current shell.")
    current_directory: str = Field(
        ...,
        description="Current working directory.",
    )


class AIResponse(BaseModel):
    command: str = Field(
        ...,
        description="The shell command suggested by the AI.",
    )

    explanation: str = Field(
        ...,
        description="Explanation of what the command does.",
    )

    risk_level: RiskLevel = Field(
        ...,
        description="AI-estimated risk level.",
    )

    requires_confirmation: bool = Field(
        ...,
        description="Whether the command should require user confirmation.",
    )



class SafetyLevel(str, Enum):

    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyResult(BaseModel):
    """Result produced by the deterministic safety validator."""

    level: SafetyLevel = Field(
        ...,
        description="Safety level determined by Shellix.",
    )

    allowed: bool = Field(
        ...,
        description="Whether the command is allowed to proceed.",
    )

    requires_confirmation: bool = Field(
        ...,
        description="Whether user confirmation is required.",
    )

    reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for the safety classification.",
    )


class ExecutionResult(BaseModel):
    command: str = Field(
        ...,
        description="The command that was executed.",
    )

    stdout: str = Field(
        default="",
        description="Standard output from the command.",
    )

    stderr: str = Field(
        default="",
        description="Standard error from the command.",
    )

    exit_code: int = Field(
        ...,
        description="Process exit code.",
    )

    success: bool = Field(
        ...,
        description="Whether the command completed successfully.",
    )

    timed_out: bool = Field(
        default=False,
        description="Whether execution exceeded the timeout.",
    )