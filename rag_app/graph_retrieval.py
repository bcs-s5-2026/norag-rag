"""Deterministic, local entity-seeded graph traversal projected to ranked chunks.

Loads a frozen extraction snapshot. Never builds a graph or calls an LLM.
"""
import json
import math
import re
from collections import Counter, defaultdict, deque
from pathlib import Path

from .graph_build import digest
from .graph_schema import ENDPOINTS, normalize
from .lexical import tokens
from .service import ROOT

# V3 final: the complete recipe-v2 graph. The partial v1 graph stays in concepts/kestrel_graph/
# for comparison; RAG_GRAPH_PATH overrides both.
import os as _os
DEFAULT_GRAPH_PATH = Path(_os.getenv('RAG_GRAPH_PATH') or (
    ROOT/'concepts/kestrel_graph_v2/graph.json' if (ROOT/'concepts/kestrel_graph_v2/graph.json').exists()
    else ROOT/'concepts/kestrel_graph/graph.json'))
STOP = set('a an the and or to of in on for with from by as is are was were be been it its this that what which who how when where why do does did i my me can could should would tell please kestrel service services team teams support'.split())
PRIORITY = {name: i for i, name in enumerate(('RAISED_BY', 'OWNED_BY', 'CONTACT_CHANNEL', 'ESCALATE_TO', 'PROVIDES', 'AVAILABLE_ON', 'HAS_RULE', 'HAS_VALUE', 'REQUIRES', 'REPLACED_BY'))}


class GraphRetrievalError(ValueError):
    pass


class GraphIndex:
    def __init__(self, graph):
        self.graph = graph
        try:
            if digest(graph['manifest']) != graph['build_id']:
                raise GraphRetrievalError('Graph manifest/build ID mismatch.')
            content = {k: graph[k] for k in ('entities', 'relations', 'provenance', 'merge_decisions')}
            if digest(content) != graph['graph_content_sha256']:
                raise GraphRetrievalError('Graph checksum mismatch.')
            self.entities = self.unique(graph['entities'])
            self.edges = self.unique(graph['relations'])
            self.proofs = self.unique(graph['provenance'])
            self.chunks = self.unique(graph['chunks'])
            self.document_ids = {s['document_id'] for s in graph['manifest']['sources']}
            for chunk in self.chunks.values():
                if (chunk['document_id'] not in self.document_ids or chunk['start'] < 0
                        or chunk['end']-chunk['start'] != len(chunk['text'])
                        or chunk['id'] != f"{chunk['document_id']}:{chunk['start']}:{chunk['end']}"):
                    raise GraphRetrievalError('Invalid canonical graph chunk metadata.')
            for proof in self.proofs.values():
                chunk = self.chunks[proof['chunk_id']]
                start = proof['quote_start']-chunk['start']
                if (start < 0 or chunk['text'][start:start+len(proof['quote'])] != proof['quote']
                        or proof['source_document'] != chunk['name'] or proof['document_id'] != chunk['document_id']
                        or proof['quote_end'] != proof['quote_start']+len(proof['quote'])):
                    raise GraphRetrievalError('Graph proof does not match its canonical source chunk.')
            for entity in self.entities.values():
                if not entity['provenance_ids'] or not set(entity['provenance_ids']) <= self.proofs.keys():
                    raise GraphRetrievalError('Entity has missing provenance.')
            for edge in self.edges.values():
                subjects, objects = ENDPOINTS[edge['relation']]
                if (self.entities[edge['subject_id']]['type'] not in subjects or
                        self.entities[edge['object_id']]['type'] not in objects or
                        not edge['provenance_ids'] or not set(edge['provenance_ids']) <= self.proofs.keys()):
                    raise GraphRetrievalError('Invalid graph edge endpoints/provenance.')
        except (KeyError, TypeError) as exc:
            raise GraphRetrievalError('Malformed graph snapshot.') from exc

    @staticmethod
    def unique(rows):
        result = {r['id']: r for r in rows}
        if len(result) != len(rows):
            raise GraphRetrievalError('Duplicate graph record IDs.')
        return result

    @classmethod
    def load(cls, path=None):
        try:
            return cls(json.loads(Path(path or DEFAULT_GRAPH_PATH).read_text(encoding='utf-8')))
        except FileNotFoundError as exc:
            raise GraphRetrievalError('Graph snapshot unavailable; load the frozen Kestrel graph first.') from exc
        except (OSError, ValueError) as exc:
            if isinstance(exc, GraphRetrievalError): raise
            raise GraphRetrievalError('Graph snapshot unreadable or corrupt.') from exc

    def _check_request(self, selected, settings):
        if not selected or not selected <= self.document_ids:
            raise GraphRetrievalError('Graph retrieval supports only selected Kestrel source versions.')
        manifest = self.graph['manifest']
        if settings.chunk_size != manifest['chunk_size'] or settings.chunk_overlap != manifest['chunk_overlap']:
            raise GraphRetrievalError('Graph chunk settings differ from the frozen extraction snapshot.')

    def search(self, question, document_ids, settings, depth=20):
        selected = set(document_ids)
        self._check_request(selected, settings)
        if type(depth) is not int or depth < 1:
            raise GraphRetrievalError('Graph candidate depth must be positive.')
        def proofs(ids):
            return [self.proofs[p] for p in ids if self.proofs[p]['document_id'] in selected]
        active = {k: e for k, e in self.entities.items() if proofs(e['provenance_ids'])}
        adjacency = defaultdict(list)
        for edge in self.edges.values():
            if not proofs(edge['provenance_ids']): continue
            a, b = edge['subject_id'], edge['object_id']
            if a in active and b in active:
                adjacency[a].append((edge, b, 'forward'))
                adjacency[b].append((edge, a, 'reverse'))
        normalized_question = normalize(question)
        seeds = []
        def mentioned(name):
            # A one-word, capitalized name (plan "Team", "Business"; team "Identity") is also a
            # common English word. Match it case-sensitively so "which team's channel" does not
            # seed the "Team" plan (V3 failure on q12). Codes and multi-word names stay case-insensitive.
            if re.fullmatch(r'[A-Z][a-z]+', name.strip()):
                return re.search(r'(?<!\w)'+re.escape(name.strip())+r'(?!\w)', question) is not None
            return re.search(r'(?<!\w)'+re.escape(normalize(name))+r'(?!\w)', normalized_question) is not None
        for key, entity in sorted(active.items()):
            names = [n for n in entity['names'] if mentioned(n)]
            if names:
                seeds.append(dict(id=key, label=entity['label'], type=entity['type'],
                                  score=float(max(len(tokens(n)) for n in names)), matched_by='exact_name', matches=names))
        code_seeds = [s for s in seeds if s['type'] == 'ErrorCode']
        if code_seeds: seeds = code_seeds
        if not seeds:
            # Local lexical matching over graph entity descriptors, not a hidden
            # call to dense/BM25 chunk retrieval and never to a query-planning LLM.
            query = set(tokens(question))-STOP
            descriptors = {k: set(tokens(' '.join(e['names'])+' '+ ' '.join(p['quote'] for p in proofs(e['provenance_ids']))))-STOP for k, e in active.items()}
            df = Counter(t for terms in descriptors.values() for t in terms)
            for k, terms in descriptors.items():
                shared = terms & query
                if shared:
                    score = sum(math.log((len(active)+1)/(df[t]+1))+1 for t in sorted(shared))/math.sqrt(max(1, len(terms)))
                    seeds.append(dict(id=k, label=active[k]['label'], type=active[k]['type'],
                                      score=score, matched_by='lexical_graph_descriptor', matches=sorted(shared)))
        seeds = sorted(seeds, key=lambda s: (-s['score'], s['id']))[:3]
        paths, contributions, chunk_paths = [], defaultdict(dict), defaultdict(set)
        queue = deque((s, [s['id']], []) for s in seeds)
        expansions = 0
        while queue and expansions < 200:
            seed, nodes, steps = queue.popleft(); expansions += 1
            path_id = 'path_'+digest([seed['id'], [(e['id'], direction) for e, direction in steps]])
            evidence = {p['chunk_id'] for p in proofs(active[nodes[-1]]['provenance_ids'])}
            for edge, direction in steps:
                evidence.update(p['chunk_id'] for p in proofs(edge['provenance_ids']))
            trace = dict(id=path_id, seed_id=seed['id'], nodes=[dict(id=n, label=active[n]['label'], type=active[n]['type']) for n in nodes],
                         edges=[dict(id=e['id'], relation=e['relation'], subject_id=e['subject_id'], object_id=e['object_id'],
                                     direction=direction, condition_quote=e['condition_quote'],
                                     evidence=proofs(e['provenance_ids'])) for e, direction in steps], chunk_ids=sorted(evidence))
            paths.append(trace)
            for identifier in evidence:
                contributions[identifier][path_id] = seed['score']/(1+len(steps))
                chunk_paths[identifier].add(path_id)
            if len(steps) >= 3: continue
            ordered = sorted(adjacency[nodes[-1]], key=lambda x: (PRIORITY.get(x[0]['relation'], len(PRIORITY)), x[0]['id'], x[1]))[:12]
            for edge, target, direction in ordered:
                if target not in nodes:
                    queue.append((seed, nodes+[target], steps+[(edge, direction)]))
        scored = sorted(((math.fsum(values.values()), k) for k, values in contributions.items()), key=lambda x: (-x[0], x[1]))[:depth]
        results = [dict(self.chunks[k], score=score, rank=rank, retriever='graph', graph_path_ids=sorted(chunk_paths[k])) for rank, (score, k) in enumerate(scored, 1)]
        used_paths = {p for r in results for p in r['graph_path_ids']}
        trace = dict(build_id=self.graph['build_id'], complete=self.graph['complete'], coverage=self.graph['coverage'],
                     matched_entities=seeds, paths=[p for p in paths if p['id'] in used_paths],
                     chunks=[self.chunks[k] for k in sorted({c for p in paths if p['id'] in used_paths for c in p['chunk_ids']})],
                     traversal_limit_reached=bool(queue), max_edges=3,
                     reason=None if results else 'No supported graph entities/path evidence matched this question.')
        return results, trace
