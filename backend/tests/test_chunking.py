import pytest
from pydantic import ValidationError

from app.chunking import ChunkSettings, split_text


def test_short_document_produces_one_exact_chunk():
    text = "A raven arrived."
    chunks = split_text(text, ChunkSettings())

    assert len(chunks) == 1
    assert chunks[0].start == 0
    assert chunks[0].end == len(text)
    assert chunks[0].text == text


def test_exact_size_does_not_create_a_redundant_tail():
    chunks = split_text(
        "a" * 100,
        ChunkSettings(chunk_size=100, overlap=20),
    )

    assert len(chunks) == 1


def test_overlap_and_offsets_preserve_the_source():
    text = "".join(chr(0x400 + index) for index in range(250))
    settings = ChunkSettings(chunk_size=100, overlap=20)

    chunks = split_text(text, settings)

    assert [(chunk.start, chunk.end) for chunk in chunks] == [
        (0, 100),
        (80, 180),
        (160, 250),
    ]

    for index, chunk in enumerate(chunks):
        assert chunk.index == index
        assert chunk.text == text[chunk.start:chunk.end]

    for previous, current in zip(chunks, chunks[1:]):
        assert previous.text[-20:] == current.text[:20]

    reconstructed = chunks[0].text + "".join(
        chunk.text[20:] for chunk in chunks[1:]
    )
    assert reconstructed == text


def test_zero_overlap_preserves_all_characters():
    text = "x" * 250
    chunks = split_text(
        text,
        ChunkSettings(chunk_size=100, overlap=0),
    )

    assert "".join(chunk.text for chunk in chunks) == text
    assert len(chunks) == 3


@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_empty_or_blank_text_produces_no_chunks(text):
    assert split_text(text, ChunkSettings()) == []


@pytest.mark.parametrize(
    "settings",
    [
        {"chunk_size": 99},
        {"chunk_size": 2001},
        {"overlap": -1},
        {"chunk_size": 100, "overlap": 100},
        {"chunk_size": 100, "overlap": 101},
    ],
)
def test_invalid_settings_are_rejected(settings):
    with pytest.raises(ValidationError):
        ChunkSettings(**settings)