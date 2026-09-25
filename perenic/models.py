"""Shared data types used by every Perenic agent.

A *dataclass* is a simple way to make a class that just holds data.
Python writes the __init__ method for us based on the fields below.
"""

from dataclasses import dataclass, field

# Severity levels, from least to most serious.
INFO = "info"
WARNING = "warning"
ERROR = "error"


@dataclass
class Finding:
    """One problem (or suggestion) that an agent found in the code."""

    rule: str  # short id, e.g. "bare-except"
    message: str  # human-readable explanation
    severity: str = WARNING  # INFO, WARNING or ERROR
    line: int | None = None  # line number in the file, if known
    source: str = "rules"  # "rules" (Python checks) or "claude" (AI review)
    regulation: str | None = None  # the document rule it risks breaching, if any


@dataclass
class AgentReport:
    """Everything one agent has to say about one piece of code."""

    agent_name: str
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    rules_checked: list[str] = field(default_factory=list)  # document sections consulted

    def count(self, severity: str) -> int:
        """How many findings have the given severity."""
        return sum(1 for f in self.findings if f.severity == severity)


@dataclass
class Message:
    """A note one agent posts for other agents to read (via the orchestrator)."""

    sender: str
    topic: str  # e.g. "review.findings"
    content: object
