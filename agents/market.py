from agents.assessment import assess
from state import ResearchState


def market_agent(state: ResearchState) -> dict:
    return assess(state, "market")
