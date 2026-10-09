"""Validate a self-contained bundle. Source IDs are labels, never file paths."""
from .core import verify


def check_bundle(bundle: dict, *, mode: str = 'exact') -> dict:
    if mode not in ('exact', 'whitespace'):
        raise ValueError('mode must be exact or whitespace')
    if not isinstance(bundle, dict) or set(bundle) != {'sources', 'claims'}:
        raise ValueError('bundle must contain exactly sources and claims')
    sources, claims = bundle['sources'], bundle['claims']
    if not isinstance(sources, dict) or not sources or len(sources) > 100:
        raise ValueError('sources must contain 1 to 100 entries')
    if any(not isinstance(k, str) or not k or not isinstance(v, str) for k, v in sources.items()):
        raise ValueError('sources must map non-empty IDs to literal text strings')
    if not isinstance(claims, list) or not 1 <= len(claims) <= 1000:
        raise ValueError('claims must contain 1 to 1000 entries')
    results, ids = [], set()
    for claim in claims:
        if not isinstance(claim, dict) or not {'id', 'source', 'quote'} <= set(claim):
            raise ValueError('each claim requires id, source, and quote')
        if set(claim) - {'id', 'source', 'quote', 'lines', 'source_sha256'}:
            raise ValueError('unknown claim field; check spelling')
        if any(not isinstance(claim[k], str) for k in ('id', 'source', 'quote')):
            raise ValueError('id, source, and quote must be strings')
        if not claim['id'] or not claim['source'] or claim['id'] in ids:
            raise ValueError('claim IDs must be non-empty and unique; source IDs must be non-empty')
        ids.add(claim['id'])
        # Validate optional fields even when the source ID is absent.
        options = {k: claim[k] for k in ('lines', 'source_sha256') if k in claim}
        result = verify(claim['quote'], sources.get(claim['source'], ''), mode=mode, **options).to_dict()
        if claim['source'] not in sources:
            result.update(status='MISSING_SOURCE', ok=False, source_sha256=None,
                          matches=(), detail='The source ID is not in this bundle.')
        results.append({'id': claim['id'], 'source': claim['source'], **result})
    passed = sum(row['ok'] for row in results)
    return {'schema_version': 1, 'mode': mode, 'ok': passed == len(results),
            'summary': {'total': len(results), 'passed': passed, 'failed': len(results) - passed},
            'results': results}
