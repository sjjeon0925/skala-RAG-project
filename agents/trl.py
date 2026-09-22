from agents.assessment import assess
from state import ResearchState


def trl_agent(state: ResearchState) -> dict:
    return assess(state, "trl")
