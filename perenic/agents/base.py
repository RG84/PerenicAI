"""The base class that every Perenic agent builds on."""

from perenic.models import AgentReport, Message


class BaseAgent:
    """A Perenic agent.

    To make a new agent, create a class that inherits from BaseAgent,
    give it a `name`, and write a `run` method.
    """

    name = "base"

    def __init__(self):
        # The orchestrator fills this in so the agent can send messages.
        self.orchestrator = None

    def run(self, code: str, filename: str, inbox: list[Message]) -> AgentReport:
        """Check `code` and return a report.

        `inbox` holds messages that earlier agents posted, so agents can
        build on each other's work.
        """
        raise NotImplementedError("Each agent must write its own run() method")

    def post(self, topic: str, content: object) -> None:
        """Share something with the other agents."""
        if self.orchestrator is not None:
            self.orchestrator.publish(Message(sender=self.name, topic=topic, content=content))
