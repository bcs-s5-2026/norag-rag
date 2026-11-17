"""V4 Part B: concept map explorer over the frozen V3 Kestrel concept graph.

Read-only: it loads the validated graph snapshot and never calls an LLM.
Every link and every mention comes with the quote and the chunk it was
extracted from, so the user can check it.
"""


def list_concepts(graph):
    """All concepts with their number of links, sorted by type then label."""
    links = {}
    for edge in graph.edges.values():
        for key in (edge['subject_id'], edge['object_id']):
            links[key] = links.get(key, 0) + 1
    rows = [dict(id=key, label=entity['label'], type=entity['type'], links=links.get(key, 0))
            for key, entity in graph.entities.items()]
    return sorted(rows, key=lambda row: (row['type'], row['label'].lower()))


def evidence(graph, provenance_ids):
    """The quotes behind a concept or a link, each with its source chunk."""
    rows = []
    for proof_id in provenance_ids:
        proof = graph.proofs[proof_id]
        chunk = graph.chunks[proof['chunk_id']]
        rows.append(dict(chunk_id=chunk['id'], document=chunk['name'], line=chunk['line'],
                         quote=proof['quote'], quote_start=proof['quote_start'],
                         quote_end=proof['quote_end'], chunk_text=chunk['text']))
    return rows


def neighborhood(graph, concept_id):
    """One concept, the concepts it is linked to, and the chunks that mention it."""
    entity = graph.entities.get(concept_id)
    if entity is None:
        return None
    links = []
    for edge in graph.edges.values():
        if concept_id not in (edge['subject_id'], edge['object_id']):
            continue
        outgoing = edge['subject_id'] == concept_id
        other = graph.entities[edge['object_id'] if outgoing else edge['subject_id']]
        links.append(dict(relation=edge['relation'], direction='out' if outgoing else 'in',
                          other=dict(id=other['id'], label=other['label'], type=other['type']),
                          condition=edge['condition_quote'],
                          evidence=evidence(graph, edge['provenance_ids'])))
    links.sort(key=lambda link: (link['relation'], link['other']['label'].lower()))
    return dict(concept=dict(id=entity['id'], label=entity['label'], type=entity['type'],
                             names=entity['names']),
                links=links, mentions=evidence(graph, entity['provenance_ids']))
