"""The orchestrator runs the PAT agents and lets them talk to each other.

Agents don't call each other directly. Instead each agent posts messages
to the orchestrator, and every agent that runs afterwards receives them
in its `inbox`. This keeps agents independent: you can add or remove one
without changing the others.
"""

from dataclasses import dataclass, field

from perenic.agents.base import PATAgent
from perenic.models import ERROR, AgentReport, Message


@dataclass
class GateResult:
    """The final answer for one file: did it pass the quality gate?"""

    filename: str
    passed: bool
    reports: list[AgentReport] = field(default_factory=list)


class Orchestrator:
    def __init__(self, agents: list[PATAgent]):
        self.agents = agents
        self.messages: list[Message] = []
        for agent in agents:
            agent.orchestrator = self

    def publish(self, message: Message) -> None:
        """Called by agents (through PATAgent.post) to share a message."""
        self.messages.append(message)

    def review(self, code: str, filename: str) -> GateResult:
        """Run every agent on the code, in order, and decide pass/fail."""
        self.messages = []  # fresh conversation for each file
        reports = []
        for agent in self.agents:
            inbox = list(self.messages)  # a copy of everything posted so far
            reports.append(agent.run(code, filename, inbox))

        # The gate fails if any agent found an ERROR-level problem.
        passed = all(report.count(ERROR) == 0 for report in reports)
        return GateResult(filename=filename, passed=passed, reports=reports)
