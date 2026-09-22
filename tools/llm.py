"""OpenAI Responses JSON 연결. 비밀 값과 API 응답 원문은 예외에 넣지 않는다."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import config  # loads .env before configuration lookup


class ProviderError(RuntimeError):
    pass


def encode_evidence_refs(payload):
    text = json.dumps(payload, ensure_ascii=False)
    ids = list(dict.fromkeys(re.findall(r'\b(?:technical|trl|market|stakeholder|domain|counter)-(?:ITME|CXL-PIM)-[a-f0-9]{16}\b', text)))
    aliases = {}
    number = 0
    for eid in ids:
        while f'R{number:05d}' in text:
            number += 1
        alias = f'R{number:05d}'
        number += 1
        text = text.replace(eid, alias)
        aliases[alias] = eid
    return text, aliases


def decode_evidence_refs(value, aliases):
    if isinstance(value, str):
        return re.sub(r'\bR\d{5}\b', lambda m: aliases.get(m.group(), m.group()), value)
    if isinstance(value, list):
        return [decode_evidence_refs(v, aliases) for v in value]
    if isinstance(value, dict):
        return {decode_evidence_refs(k, aliases): decode_evidence_refs(v, aliases) for k,v in value.items()}
    return value


def post_json(url, payload, key):
    request = Request(url, data=json.dumps(payload).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}, method='POST')
    try:
        with urlopen(request, timeout=90) as response:
            return json.load(response)
    except HTTPError as exc:
        raise ProviderError(f'Provider HTTP {exc.code}') from None
    except (URLError, TimeoutError):
        raise ProviderError('Provider connection failed') from None


def complete_json(instructions, payload, schema):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise ProviderError('OPENAI_API_KEY is required in .env')
    encoded, aliases = encode_evidence_refs(payload)
    result = post_json('https://api.openai.com/v1/responses', {
        'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), 'store': False,
        'instructions': instructions,
        'input': encoded,
        'max_output_tokens': 5000,
        'text': {'format': {'type': 'json_schema', 'name': 'research_result', 'strict': True, 'schema': schema}},
    }, key)
    if result.get('status') != 'completed':
        raise ProviderError('Model response did not complete')
    text = ''.join(part.get('text', '') for item in result.get('output', [])
                   for part in item.get('content', []) if part.get('type') == 'output_text')
    try:
        return decode_evidence_refs(json.loads(text), aliases)
    except (ValueError, TypeError):
        raise ProviderError('Model did not return valid JSON') from None


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
