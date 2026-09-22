from agents.assessment import assess
from state import ResearchState


def stakeholder_agent(state: ResearchState) -> dict:
    return assess(state, "stakeholder")
