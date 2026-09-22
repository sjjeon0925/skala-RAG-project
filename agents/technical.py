from config import TECHNICAL_EVIDENCE_ITEMS, QUERY_TERMS, RESULTS_PER_CRITERION
from agents.extraction import extract_evidence
from rag.pipeline import get_retriever
from state import ResearchState


def technical_agent(state: ResearchState) -> dict:
    retriever = get_retriever()
    evidence = dict(state['technical_evidence'])
    for tech in state['technologies']:
        for criterion in TECHNICAL_EVIDENCE_ITEMS:
            if state['retry_count'] and not any(g['technology'] == tech and g['item'] == criterion for g in state['missing_evidence']):
                continue
            queries = [q for q in state['search_queries'] if q.startswith(tech + ' ') and QUERY_TERMS[criterion] in q]
            if not queries:
                queries = [q for q in state['search_queries'] if q.startswith(tech + ' ')]
            candidates = {}
            for query in queries:
                for row in retriever.search(query, perspective='technical', technology=tech, role='core', k=RESULTS_PER_CRITERION):
                    candidates[row['evidence_id']] = row
            extracted, _ = extract_evidence(list(candidates.values())[:RESULTS_PER_CRITERION], technology=tech,
                                           perspective='technical', criterion=criterion)
            evidence.update(extracted)
    return {'technical_evidence': evidence}
