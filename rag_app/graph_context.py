"""Auditable offline context repair of a narrow class of model quotation errors.

Never calls a provider, changes endpoints/relations, or accepts a malformed triple.
Original extraction/cache/quarantine/attempt records are preserved unchanged.
"""
import copy
import json
import re
from pathlib import Path

from .graph_build import GraphBuilder, assemble, atomic_json, digest, read_json
from .graph_schema import Triple, normalize, validate_extraction

VERSION = 'bounded-heading-context-v1'


def reject_boundary_fragments(graph):
    """A name cut mid-word is mechanically incomplete, not an alias to guess."""
    documents = {}
    for chunk in sorted(graph['chunks'], key=lambda c: (c['document_id'], c['start'])):
        text = documents.get(chunk['document_id'], '')
        documents[chunk['document_id']] = text+chunk['text'][max(0, len(text)-chunk['start']):]
    chunks = {c['id']: c for c in graph['chunks']}
    entities = {e['id']: e for e in graph['entities']}
    proofs = {p['id']: p for p in graph['provenance']}
    retained, rejected = [], []
    for edge in graph['relations']:
        bad = []
        for pid in edge['provenance_ids']:
            proof = proofs[pid]; chunk = chunks[proof['chunk_id']]
            after = documents[chunk['document_id']][chunk['end']:chunk['end']+1]
            if not after.isalnum() or proof['quote_end'] != chunk['end']: continue
            for eid in (edge['subject_id'], edge['object_id']):
                if any(normalize(proof['quote']).endswith(normalize(name)) and name[-1:].isalnum()
                       for name in entities[eid]['names']):
                    bad.append(pid)
        if bad:
            rejected.append(dict(relation_id=edge['id'], subject=entities[edge['subject_id']]['label'],
                                 object=entities[edge['object_id']]['label'], provenance_ids=sorted(set(bad)),
                                 reason='Entity label ends at the chunk boundary inside a continuing source word; no fuzzy resolution applied.'))
        edge['provenance_ids'] = [p for p in edge['provenance_ids'] if p not in bad]
        if edge['provenance_ids']: retained.append(edge)
    graph['relations'] = retained
    used = {e[k] for e in retained for k in ('subject_id', 'object_id')}
    graph['entities'] = [e for e in graph['entities'] if e['id'] in used]
    used_proofs = {p for e in retained+graph['entities'] for p in e['provenance_ids']}
    graph['provenance'] = [p for p in graph['provenance'] if p['id'] in used_proofs]
    return rejected


def expand_quote(triple, chunk):
    """Only explicit owner/raised-by/escalation fields inside the named section."""
    quote, text = triple.evidence_quote, chunk['text']
    clean = normalize(quote.replace('**', ''))
    if triple.relation == 'OWNED_BY':
        if not re.search(r'(?:\bpolicy owner|\bowner)\s*:\s*'+re.escape(normalize(triple.object.label))+r'\b', clean):
            return None
    elif triple.relation == 'ESCALATE_TO':
        if 'escalate:' not in clean:
            return None
    elif triple.relation == 'RAISED_BY':
        if 'raised by '+normalize(triple.object.label) not in clean:
            return None
    else:
        return None
    headers = list(re.finditer(r'^#{1,3}\s+([^\n]+)', text, re.MULTILINE))
    for i, header in enumerate(headers):
        title = normalize(header.group(1))
        label = normalize(triple.subject.label)
        matches = (title == label if triple.subject.type in ('Service', 'Policy') else
                   bool(re.match(re.escape(label)+r'(?:\s|$)', title)) if triple.subject.type == 'ErrorCode' else False)
        if not matches: continue
        end = headers[i+1].start() if i+1 < len(headers) else len(text)
        at = text.find(quote, header.start(), end)
        if at >= 0:
            context = text[header.start():at+len(quote)]
            candidate = triple.model_dump(); candidate['evidence_quote'] = context
            # Keep exactly the same strict schema/anchor/condition validation.
            validate_extraction(json.dumps(dict(triples=[candidate], aliases=[])), chunk)
            return candidate
    return None


def derive(builder, raw_graph, quarantine_dir):
    entries, repairs, excluded = [], [], []
    for row in builder.rows:
        entry, _ = builder.cached(row)
        if entry: entries.append(entry)
    for path in sorted(Path(quarantine_dir).glob('*.json')):
        record = read_json(path)
        if record.get('attempt', {}).get('build_id') != builder.build_id: continue
        try:
            output = json.loads(record['response']['text'])
        except (ValueError, KeyError): continue
        accepted, changes = [], []
        for index, value in enumerate(output.get('triples', [])):
            try:
                original = Triple.model_validate(value)
                repaired = expand_quote(original, record['chunk'])
                if repaired is None:
                    excluded.append(dict(attempt_id=record['attempt']['id'], triple_index=index, reason='Outside bounded explicit-field repair policy.'))
                    continue
            except ValueError:
                excluded.append(dict(attempt_id=record['attempt']['id'], triple_index=index, reason='Schema or exact-source validation failed.'))
                continue
            accepted.append(repaired)
            changes.append(dict(triple_index=index, original_quote=original.evidence_quote,
                                expanded_quote=repaired['evidence_quote'], subject=original.subject.model_dump(),
                                relation=original.relation, object=original.object.model_dump()))
        if not accepted: continue
        original_response = record['response']
        response = dict(original_response, text=json.dumps(dict(triples=accepted, aliases=[]), ensure_ascii=False))
        key = digest([record['attempt']['cache_key'], VERSION, response])
        entry = dict(key=key, recipe=builder.recipe, chunk=record['chunk'], response=response,
                     sha256=digest(response), extraction=validate_extraction(response['text'], record['chunk']).model_dump(),
                     attempt_id=record['attempt']['id'], extracted_at=record['attempt']['finished_at'],
                     extraction_seconds=record['attempt']['seconds'],
                     derivation=dict(method=VERSION, original_response_sha256=digest(original_response),
                                     original_attempt_id=record['attempt']['id'], repairs=changes))
        entries.append(entry); repairs.append(entry)
    derived = assemble(builder, entries)
    derived['chunks'] = raw_graph['chunks']
    boundary_rejections = reject_boundary_fragments(derived)
    derived_keys = {e['key']: e for e in repairs}
    for proof in derived['provenance']:
        if proof['cache_key'] in derived_keys:
            proof['derivation'] = derived_keys[proof['cache_key']]['derivation']
            proof['human_reviewed'] = False
    manifest = copy.deepcopy(raw_graph['manifest'])
    manifest['offline_derivation'] = dict(parent_build_id=raw_graph['build_id'], method=VERSION,
             implementation_sha256=digest(Path(__file__).read_text()),
             repaired_extraction_keys=sorted(derived_keys))
    derived.update(build_id=digest(manifest), parent_build_id=raw_graph['build_id'], manifest=manifest,
                   complete=False, schema_version=raw_graph['schema_version'], chunks=raw_graph['chunks'],
                   pending=raw_graph['pending'], build_stats=raw_graph['build_stats'], last_run=raw_graph['last_run'],
                   extractions=raw_graph['extractions']+[dict(key=e['key'], derivation=e['derivation'], response=e['response']) for e in repairs],
                   coverage=dict(raw_graph['coverage'], context_repaired_chunks=len(repairs),
                                 context_repaired_triples=sum(len(e['extraction']['triples']) for e in repairs)),
                   offline_repair_report=dict(method=VERSION, external_calls=0, excluded=excluded,
                                              boundary_rejections=boundary_rejections,
                                              repairs=[e['derivation'] for e in repairs]))
    derived['graph_content_sha256'] = digest({k: derived[k] for k in ('entities', 'relations', 'provenance', 'merge_decisions')})
    return derived, repairs
