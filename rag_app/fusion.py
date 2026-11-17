"""Plain Reciprocal Rank Fusion over independently ranked canonical chunks."""
import math

SOURCE_FIELDS = ('id', 'document_id', 'name', 'start', 'end', 'line', 'text')


def reciprocal_rank_fusion(rankings, rank_constant=60, top_k=5):
    """Deduplicate each list before assigning 1-based ranks; never mix raw scores.

    The first occurrence of a chunk within a list wins. Conflicting source data
    for the same ID is an integrity error. Input dictionaries are never modified.
    """
    if type(rank_constant) is not int or rank_constant < 0:
        raise ValueError('RRF rank constant must be a nonnegative integer.')
    if type(top_k) is not int or top_k < 1:
        raise ValueError('Final top-k must be a positive integer.')
    chunks, origins = {}, {}
    for retriever in sorted(rankings):
        seen = set()
        for row in rankings[retriever]:
            identifier = row.get('id')
            if not isinstance(identifier, str) or not identifier:
                raise ValueError('Every retrieved chunk must have a stable ID.')
            source = {key: row[key] for key in SOURCE_FIELDS if key in row}
            if identifier in chunks and chunks[identifier] != source:
                raise ValueError('Conflicting source data for the same chunk ID.')
            chunks[identifier] = source
            if identifier in seen:
                continue
            seen.add(identifier)
            raw_score = row.get('similarity') if retriever == 'dense' else row.get('score')
            origin = dict(rank=len(seen), raw_score=raw_score)
            if retriever == 'graph':
                origin['path_ids'] = list(row.get('graph_path_ids', []))
            origins.setdefault(identifier, {})[retriever] = origin
    scored = [(math.fsum(1/(rank_constant+origin['rank']) for origin in found.values()), identifier)
              for identifier, found in origins.items()]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [dict(chunks[identifier], origins=origins[identifier],
                 fused_rank=rank, rrf_score=score)
            for rank, (score, identifier) in enumerate(scored[:top_k], 1)]
