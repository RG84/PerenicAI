from perenic.__main__ import main
from perenic.agents import PATAgent, PATCodeReviewerAgent
from perenic.models import AgentReport
from perenic.orchestrator import Orchestrator


class ListenerAgent(PATAgent):
    """A test agent that records what earlier agents told it."""

    name = "listener"

    def run(self, code, filename, inbox):
        self.received = inbox
        return AgentReport(agent_name=self.name)


def test_gate_fails_on_error_findings():
    orchestrator = Orchestrator([PATCodeReviewerAgent(use_claude=False)])
    result = orchestrator.review("def f(x=[]):\n    return x\n", "bad.py")
    assert result.passed is False


def test_gate_passes_on_clean_code():
    orchestrator = Orchestrator([PATCodeReviewerAgent(use_claude=False)])
    result = orchestrator.review('def f():\n    """Doc."""\n    return 1\n', "good.py")
    assert result.passed is True


def test_later_agents_receive_earlier_agents_messages():
    listener = ListenerAgent()
    orchestrator = Orchestrator([PATCodeReviewerAgent(use_claude=False), listener])
    orchestrator.review("def f(x=[]):\n    return x\n", "bad.py")

    topics = [message.topic for message in listener.received]
    assert topics == ["review.findings"]
    assert listener.received[0].sender == "pat-code-reviewer"


def test_cli_exit_code(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x=[]):\n    return x\n")
    good = tmp_path / "good.py"
    good.write_text('def f():\n    """Doc."""\n    return 1\n')

    assert main(["review", str(good), "--no-claude"]) == 0
    assert main(["review", str(bad), "--no-claude"]) == 1
