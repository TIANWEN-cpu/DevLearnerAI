"""Data classes for the practice module."""

from dataclasses import dataclass, field


@dataclass
class Exercise:
    """Represents a single coding exercise."""

    id: str
    title: str
    track_id: str
    difficulty: str
    prompt: str
    lesson_id: str
    hints: list[str] = field(default_factory=list)
    starter_code: str = ""
    expected_nodes: list[str] = field(default_factory=list)
    required_names: list[str] = field(default_factory=list)
    tests: list[dict] = field(default_factory=list)
    required_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result of evaluating a submitted exercise answer."""

    passed: bool
    score: int
    feedback_lines: list[str]
    stdout: str = ""
    duration_sec: int = 0

    @property
    def feedback_text(self) -> str:
        return "\n".join(self.feedback_lines)
