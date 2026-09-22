from agents.assessment import assess
from state import ResearchState


def domain_agent(state: ResearchState) -> dict:
    return assess(state, "domain")
