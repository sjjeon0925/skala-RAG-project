"""모든 Agent가 공유하는 인용·수치 검증과 근거 인덱스."""
import hashlib
import logging
import re
import unicodedata

from config import PERSPECTIVE_CRITERIA

LOGGER = logging.getLogger('capstone.workflow')


def normalize(text):
    text = unicodedata.normalize('NFKC', str(text)).replace('−','-').replace('–','-').replace('\u00ad','')
    text = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', text)
    return re.sub(r'\s+', ' ', text).strip()


def quote_matches(quote, content):
    # PDF word spacing and line-break hyphens are formatting, not claim changes.
    def canonical(text):
        text = re.sub(r'(?<=[A-Za-z])-\s*(?=[A-Za-z])', '', normalize(text))
        return re.sub(r'\s+', '', text)
    return bool(quote) and canonical(quote) in canonical(content)


def numbers(text):
    return set(re.findall(r'(?<![A-Za-z])\d+(?:[.,]\d+)*', normalize(text)))


def evidence_errors(evidence):
    errors = []
    source = evidence.get('source', {})
    if not evidence.get('claim') or not evidence.get('content') or not isinstance(source, dict) or not source.get('url'):
        errors.append('citation_mismatch')
    if not isinstance(source, dict):
        return errors
    if source.get('document_id') and (not isinstance(evidence.get('page'), int) or evidence['page'] < 1):
        errors.append('citation_mismatch')
    claim = evidence.get('claim', '')
    quantitative = evidence.get('quantitative') or re.search(r'\d\s*(?:%|×|ms\b|[KMGT]i?B\b|배)', claim)
    if quantitative:
        conditions = evidence.get('experimental_condition', {})
        if not conditions or not conditions.get('unit') or not conditions.get('baseline'):
            errors.append('missing_numeric_conditions')
        quote = normalize(evidence.get('content', ''))
        if not numbers(evidence.get('claim', '')).issubset(numbers(quote)):
            errors.append('numeric_mismatch')
        if any(not quote_matches(str(value).lower(), quote.lower()) for value in conditions.values() if value):
            errors.append('condition_mismatch')
    if not numbers(claim).issubset(numbers(evidence.get('content', ''))):
        errors.append('numeric_mismatch')
    return list(dict.fromkeys(errors))


def collect_evidence(state):
    result = {}
    def merge(items):
        for key, value in items.items():
            if key in result and result[key] != value:
                raise ValueError(f'Duplicate evidence ID: {key}')
            result[key] = value
    merge(state.get('technical_evidence', {}))
    for perspective in PERSPECTIVE_CRITERIA:
        merge(state.get(f'{perspective}_analysis', {}).get('evidence', {}))
    for counter in state.get('counter_evidence', {}).values():
        merge(counter.get('evidence', {}))
    return result


def stable_id(perspective, technology, criterion, source_id, claim):
    digest = hashlib.sha256('|'.join((criterion, source_id, normalize(claim))).encode()).hexdigest()[:16]
    return f'{perspective}-{technology}-{digest}'


def deduplicate_gaps(gaps):
    result = {}
    for gap in gaps:
        key = (gap['technology'], gap['perspective'], gap['item'])
        result.setdefault(key, gap)
    return list(result.values())
