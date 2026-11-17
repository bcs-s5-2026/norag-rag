"""Versioned lexical tokenization shared by BM25 and the V2 Words inspector."""
import re

TOKENIZER_VERSION = 'unicode-casefold-internal-hyphen-apostrophe-v1'


def tokens(text):
    # Preserve identifiers such as KST-2044; punctuation (including #) separates tokens.
    return re.findall(r"[^\W_]+(?:[-'’][^\W_]+)*", text.casefold())
