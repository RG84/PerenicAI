"""The base class that every PAT (Perennial Artificial Testing) agent builds on."""

from perenic.models import AgentReport, Message


class PATAgent:
    """A PAT agent.

    To make a new agent, create a class that inherits from PATAgent,
    give it a `name`, and write a `run` method. Industry agents also set
    `industry` and `claude_guidance`.
    """

    name = "pat-base"
    industry = None  # e.g. "healthcare"; None means the agent suits any industry
    claude_guidance = ""  # extra instructions for the Claude review

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
