"""Fixed, evidence-anchored Kestrel graph extraction schema (construction only)."""
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 'kestrel-graph-v1'
EntityType = Literal['ErrorCode', 'Service', 'Team', 'Channel', 'Feature', 'Plan', 'Role', 'Policy', 'Rule', 'Value']
RelationType = Literal['RAISED_BY', 'OWNED_BY', 'CONTACT_CHANNEL', 'ESCALATE_TO', 'PROVIDES',
                       'AVAILABLE_ON', 'HAS_RULE', 'HAS_VALUE', 'REQUIRES', 'REPLACED_BY']
ENDPOINTS = {
    'RAISED_BY': ({'ErrorCode'}, {'Service'}),
    'OWNED_BY': ({'Service', 'Policy'}, {'Team'}),
    'CONTACT_CHANNEL': ({'Team'}, {'Channel'}),
    'ESCALATE_TO': ({'ErrorCode'}, {'Team'}),
    'PROVIDES': ({'Service'}, {'Feature'}),
    'AVAILABLE_ON': ({'Feature'}, {'Plan'}),
    'HAS_RULE': ({'Policy', 'Feature', 'Plan', 'Role'}, {'Rule'}),
    'HAS_VALUE': ({'Rule'}, {'Value'}),
    'REQUIRES': ({'Feature'}, {'Feature', 'Role'}),
    'REPLACED_BY': ({'Service'}, {'Service'}),
}


def normalize(label):
    # Preserve digits, word order, accents and substantive punctuation. No fuzzy match.
    value = unicodedata.normalize('NFKC', label).casefold()
    value = value.translate(str.maketrans({'–': '-', '—': '-', '‑': '-', '’': "'"}))
    return ' '.join(value.split())


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Mention(StrictModel):
    type: EntityType
    label: str = Field(min_length=1, max_length=300)

    @model_validator(mode='after')
    def valid_label(self):
        if not normalize(self.label):
            raise ValueError('Entity label must not be blank.')
        if self.type == 'ErrorCode' and not re.fullmatch(r'kst-\d{4}', normalize(self.label)):
            raise ValueError('ErrorCode must be a complete KST-0000 identifier.')
        return self


class Triple(StrictModel):
    subject: Mention
    relation: RelationType
    object: Mention
    evidence_quote: str = Field(min_length=1, max_length=4000)
    condition_quote: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def endpoints(self):
        subjects, objects = ENDPOINTS[self.relation]
        if self.subject.type not in subjects or self.object.type not in objects:
            raise ValueError('Relation has invalid endpoint types or direction.')
        return self


class Alias(StrictModel):
    canonical: Mention
    alias: str = Field(min_length=1, max_length=300)
    evidence_quote: str = Field(min_length=1, max_length=4000)


class Extraction(StrictModel):
    triples: list[Triple] = Field(max_length=60)
    aliases: list[Alias] = Field(max_length=20)


class SourcedAlias(Alias):
    chunk_id: str = Field(min_length=1)


class ProviderResponse(StrictModel):
    text: str
    model: str = Field(min_length=1)
    response_id: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    finish_reason: str = 'stop'


def check_quote(quote, chunk, *labels):
    if not quote.strip() or quote not in chunk['text']:
        raise ValueError('Supporting quotation is not a literal substring of the supplied chunk.')
    if any(not re.search(r'(?<!\w)'+re.escape(normalize(label))+r'(?!\w)', normalize(quote))
           for label in labels):
        raise ValueError('Evidence must contain both endpoint names (or both alias names).')


def check_alias(alias, chunk):
    Mention(type=alias.canonical.type, label=alias.alias)
    check_quote(alias.evidence_quote, chunk, alias.canonical.label, alias.alias)
    if re.search(r'\breplac\w*|\bsupersed\w*|\bolder\b|\bprevious\b', normalize(alias.evidence_quote)):
        raise ValueError('Historical replacement is not evidence of entity identity; use REPLACED_BY.')
    quote = normalize(alias.evidence_quote)
    if (re.search(r'\b(not|different|distinct|unrelated|separate)\b', quote) or
            not re.search(r'also called|also known as|alias|abbreviat\w*|stands for|same (entity|service|feature)', quote)):
        raise ValueError('Aliases need an explicit positive equivalence statement, not name co-occurrence.')


def validate_extraction(raw, chunk):
    extraction = Extraction.model_validate_json(raw)
    for triple in extraction.triples:
        check_quote(triple.evidence_quote, chunk, triple.subject.label, triple.object.label)
        if triple.condition_quote is not None:
            if not triple.condition_quote.strip() or triple.condition_quote not in triple.evidence_quote:
                raise ValueError('Condition must be an exact substring of the supporting quotation.')
    for alias in extraction.aliases:
        check_alias(alias, chunk)
    return extraction


# ---------------------------------------------------------------------------
# Recipe v2 additions (V3 rebuild). v1 behaviour above is unchanged.
# ---------------------------------------------------------------------------
_HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*$')


def section_context(document_text, start):
    """Markdown heading path in force at character `start`, plus the header row
    of a table when the chunk begins inside one.

    Chunks are cut every 800 characters, so the second half of a `### KST-2040`
    section no longer says which error it belongs to. The heading path restores
    that context deterministically (no LLM), similar to "contextual chunk
    headers". It is sent with the chunk and may supply an endpoint label, but the
    evidence quote itself must still be a literal substring of the chunk.
    """
    before = document_text[:start]
    stack = []
    for line in before.splitlines():
        match = _HEADING.match(line)
        if match:
            level = len(match.group(1))
            stack = [h for h in stack if h[0] < level]+[(level, line.strip())]
    parts = [text for _, text in stack]
    # Table header: the chunk starts on (or inside) a run of table rows.
    line_start = before.rfind('\n')+1
    lines = before[:line_start].splitlines()
    current = document_text[line_start:document_text.find('\n', start) if '\n' in document_text[start:] else None]
    if current.lstrip().startswith('|'):
        rows = []
        for line in reversed(lines):
            if not line.lstrip().startswith('|'):
                break
            rows.append(line)
        rows.reverse()
        if len(rows) >= 2 and set(rows[1].replace('|', '').strip()) <= set('-: '):
            parts.append('Table header: '+rows[0].strip())
    return ' > '.join(parts)


def quote_context(context, chunk, quote):
    """Heading path in force at the QUOTE (not the chunk start): the chunk-start
    path plus any headings inside the chunk before the quote. A chunk can hold the
    end of ### KST-1001 and the start of ### KST-1007; a quote in the second part
    must only be anchored to KST-1007."""
    parts = context.split(' > ') if context else []
    headings = [x for x in parts if x.startswith('#')]
    table = [x for x in parts if x.startswith('Table header: ')]
    prefix = '\n'.join(headings)+'\n'
    local = section_context(prefix+chunk['text'], len(prefix)+chunk['text'].index(quote))
    if table and 'Table header: ' not in local:
        local = ' > '.join(x for x in (local, table[0]) if x)
    return local


def _label_in(label, text):
    return bool(re.search(r'(?<!\w)'+re.escape(normalize(label))+r'(?!\w)', normalize(text)))


def check_quote_v2(quote, chunk, context, *labels):
    """Quote must be literal chunk text and name at least one endpoint; the other
    endpoint may come from the chunk's heading context. Returns the labels that
    were resolved from the heading (recorded in provenance)."""
    if not quote.strip() or quote not in chunk['text']:
        raise ValueError('Supporting quotation is not a literal substring of the supplied chunk.')
    in_quote = [label for label in labels if _label_in(label, quote)]
    if not in_quote:
        raise ValueError('Evidence must name at least one endpoint.')
    from_heading = [label for label in labels if label not in in_quote]
    local = quote_context(context, chunk, quote) if from_heading else ''
    for label in from_heading:
        if not (local and _label_in(label, local)):
            raise ValueError('Endpoint is neither in the evidence quotation nor in the section heading.')
    return from_heading


def filter_extraction(raw, chunk, context=''):
    """Per-item validation: an invalid triple/alias is dropped and recorded, the
    valid rest of the chunk is kept. v1 rejected the whole response instead,
    which threw away 10 of 43 chunks. Malformed JSON still rejects the response."""
    import json
    from pydantic import ValidationError
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) - {'triples', 'aliases'}:
        raise ValueError('Extraction must be a JSON object with only triples/aliases.')
    triples, aliases, dropped = [], [], []
    raw_triples = data.get('triples') or []
    raw_aliases = data.get('aliases') or []
    if not isinstance(raw_triples, list) or not isinstance(raw_aliases, list):
        raise ValueError('triples and aliases must be lists.')
    for index, item in enumerate(raw_triples):
        try:
            if len(triples) >= 60:
                raise ValueError('More than 60 triples in one chunk.')
            triple = Triple.model_validate(item)
            check_quote_v2(triple.evidence_quote, chunk, context, triple.subject.label, triple.object.label)
            if triple.condition_quote is not None and triple.condition_quote not in triple.evidence_quote:
                raise ValueError('Condition must be an exact substring of the supporting quotation.')
            triples.append(triple)
        except (ValidationError, ValueError, TypeError) as exc:
            dropped.append(dict(kind='triple', index=index, item=item, error=str(exc)[:400]))
    for index, item in enumerate(raw_aliases):
        try:
            if len(aliases) >= 20:
                raise ValueError('More than 20 aliases in one chunk.')
            alias = Alias.model_validate(item)
            check_alias(alias, chunk)
            aliases.append(alias)
        except (ValidationError, ValueError, TypeError) as exc:
            dropped.append(dict(kind='alias', index=index, item=item, error=str(exc)[:400]))
    return Extraction(triples=triples, aliases=aliases), dropped
