"""Unit tests for deterministic text statistics and segmentation functions."""

from app.schemas.analysis import TextStatistics
from app.services.statistics import (
    calculate_length_distribution,
    calculate_mean_and_std_dev,
    calculate_punctuation_frequencies,
    calculate_sentence_lengths,
    compute_text_statistics,
    extract_words,
    find_repeated_phrases,
    find_repeated_words,
    split_paragraphs,
    split_sentences,
)


def test_split_paragraphs_basic() -> None:
    """Test paragraph splitting with varying newline spacing."""
    text = "Paragraph one.\n\nParagraph two.\n\n\nParagraph three."
    paragraphs = split_paragraphs(text)
    assert len(paragraphs) == 3
    assert paragraphs[0] == "Paragraph one."
    assert paragraphs[1] == "Paragraph two."
    assert paragraphs[2] == "Paragraph three."


def test_split_paragraphs_single_or_empty() -> None:
    """Test paragraph splitting on single paragraph and whitespace."""
    assert split_paragraphs("Single paragraph text.") == ["Single paragraph text."]
    assert split_paragraphs("") == []
    assert split_paragraphs("   \n\n  \t  ") == []


def test_split_sentences_basic_terminals() -> None:
    """Test sentence segmentation with period, question mark, and exclamation."""
    text = "First sentence. Second sentence? Third sentence! Fourth sentence."
    sentences = split_sentences(text)
    assert len(sentences) == 4
    assert sentences[0].text == "First sentence."
    assert sentences[1].text == "Second sentence?"
    assert sentences[2].text == "Third sentence!"
    assert sentences[3].text == "Fourth sentence."


def test_split_sentences_abbreviations_and_decimals() -> None:
    """Test abbreviations and decimals do not create false sentence breaks."""
    text = (
        "Dr. Smith visited the U.S. Capitol with Mr. Hyde. "
        "The estimated cost was $3.14 per unit. "
        "They arrived at 5 p.m. without delay."
    )
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0].text.startswith("Dr. Smith")
    assert sentences[0].text.endswith("Mr. Hyde.")
    assert "3.14" in sentences[1].text
    assert sentences[2].text.startswith("They arrived")


def test_split_sentences_quotations_and_ellipses() -> None:
    """Test sentence boundary handling after quotation marks and ellipses."""
    text = 'She said, "Let us begin!" Then she smiled. He waited... Nothing happened.'
    sentences = split_sentences(text)
    assert len(sentences) == 4
    assert sentences[0].text == 'She said, "Let us begin!"'
    assert sentences[1].text == "Then she smiled."
    assert sentences[2].text == "He waited..."
    assert sentences[3].text == "Nothing happened."


def test_split_sentences_unicode_punctuation() -> None:
    """Test sentence segmentation with full-width Unicode punctuation."""
    text = "日本語の文です。次の文です！最後の文ですか？"
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0].text == "日本語の文です。"
    assert sentences[1].text == "次の文です！"
    assert sentences[2].text == "最後の文ですか？"


def test_split_sentences_unpunctuated() -> None:
    """Test segmentation on text lacking terminal punctuation."""
    text = "This is a headline without a trailing period"
    sentences = split_sentences(text)
    assert len(sentences) == 1
    assert sentences[0].text == text
    assert sentences[0].start == 0
    assert sentences[0].end == len(text)


def test_split_sentences_spans() -> None:
    """Test that sentence span offsets match the original text indices."""
    text = "Sentence one. Sentence two is longer. Final."
    sentences = split_sentences(text)
    for span in sentences:
        assert text[span.start : span.end] == span.text


def test_extract_words_unicode_and_contractions() -> None:
    """Test word extraction with contractions, hyphens, and Unicode accents."""
    text = "The state-of-the-art café didn't close until naïve customers left."
    words = extract_words(text)
    assert "state-of-the-art" in words
    assert "café" in words
    assert "didn't" in words
    assert "naïve" in words


def test_calculate_sentence_lengths() -> None:
    """Test calculation of word count sequence across sentences."""
    text = "Three little words. One two three four five."
    sentences = split_sentences(text)
    lengths = calculate_sentence_lengths(sentences)
    assert lengths == [3, 5]


def test_calculate_mean_and_std_dev() -> None:
    """Test mean and standard deviation computation."""
    # Lengths: [10, 10, 10] -> std_dev = 0.0
    mean, std = calculate_mean_and_std_dev([10, 10, 10])
    assert mean == 10.0
    assert std == 0.0

    # Lengths: [10, 20] -> mean = 15.0, sample std = 7.07
    mean2, std2 = calculate_mean_and_std_dev([10, 20])
    assert mean2 == 15.0
    assert std2 == 7.07

    # Empty
    assert calculate_mean_and_std_dev([]) == (0.0, 0.0)
    # Single sentence
    assert calculate_mean_and_std_dev([15]) == (15.0, 0.0)


def test_calculate_length_distribution() -> None:
    """Test distribution bin counts."""
    lengths = [3, 4, 10, 15, 20, 30, 45]
    dist = calculate_length_distribution(lengths)
    assert dist["1-5"] == 2
    assert dist["6-14"] == 1
    assert dist["15-25"] == 2
    assert dist["26-40"] == 1
    assert dist["41+"] == 1


def test_calculate_punctuation_frequencies() -> None:
    """Test counting of ASCII and Unicode punctuation characters."""
    text = "Hello, world! How are you? Fine; thanks--yes—indeed."
    freqs = calculate_punctuation_frequencies(text)
    assert freqs[","] == 1
    assert freqs["!"] == 1
    assert freqs["?"] == 1
    assert freqs[";"] == 1
    assert freqs["—"] == 1
    assert freqs["--"] == 1


def test_find_repeated_words_filters_stopwords() -> None:
    """Test that repeated words exclude common stopwords."""
    text = "the the the rapid rapid rapid development development analysis"
    words = extract_words(text)
    repeated = find_repeated_words(words, min_count=3, min_length=4)
    items = {r.item: r.count for r in repeated}

    # 'the' is a stopword and must be excluded
    assert "the" not in items
    # 'rapid' appears 3 times and length >= 4
    assert items.get("rapid") == 3
    # 'development' appears 2 times, so below min_count=3
    assert "development" not in items


def test_find_repeated_phrases_subsumption_and_spans() -> None:
    """Test repeated multiword phrase detection and sub-phrase subsumption."""
    text = (
        "The rapid technological development occurred quickly. "
        "Later, the rapid technological development continued. "
        "Finally, the rapid technological development was celebrated."
    )
    words = extract_words(text)
    phrases = find_repeated_phrases(
        text=text,
        words=words,
        min_phrase_words=3,
        max_phrase_words=4,
        min_repetitions=2,
    )

    phrase_map = {p.phrase: p.count for p in phrases}
    # Longest phrase 'the rapid technological development' (4 words) appears 3 times
    assert "the rapid technological development" in phrase_map
    assert phrase_map["the rapid technological development"] == 3

    # Shorter sub-phrase 'the rapid technological' also appears 3 times,
    # so it should be subsumed by the longer 4-word phrase
    assert "the rapid technological" not in phrase_map

    # Check spans match text
    found_item = next(
        p for p in phrases if p.phrase == "the rapid technological development"
    )
    assert len(found_item.spans) == 3
    for span in found_item.spans:
        assert text[span.start : span.end].lower() == found_item.phrase


def test_compute_text_statistics_full() -> None:
    """Test aggregated TextStatistics computation."""
    text = (
        "This is paragraph one with several words.\n\n"
        "This is paragraph two. It contains two distinct sentences."
    )
    stats = compute_text_statistics(text)
    assert isinstance(stats, TextStatistics)
    assert stats.paragraph_count == 2
    assert stats.sentence_count == 3
    assert stats.word_count > 0
    assert stats.character_count == len(text)
    assert stats.character_count_no_spaces < stats.character_count
    assert stats.avg_sentence_length > 0
    assert len(stats.sentence_lengths) == 3
    assert sum(stats.sentence_length_distribution.values()) == 3


def test_split_sentences_standalone_ellipses_not_ghost_sentences() -> None:
    """Test that standalone ellipses or symbol lines do not create 0-word sentences."""
    text = "First clear thought. ... Second clear thought."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[0].text == "First clear thought."
    assert sentences[1].text == "Second clear thought."
    lengths = calculate_sentence_lengths(sentences)
    assert lengths == [3, 3]


def test_calculate_mean_and_std_dev_sample_definition() -> None:
    """Test statistical properties of sample standard deviation."""
    # N = 3 with values [10, 12, 14]: mean = 12.0, sample stdev = 2.0
    mean, std = calculate_mean_and_std_dev([10, 12, 14])
    assert mean == 12.0
    assert std == 2.0

    # N = 1 returns 0.0
    assert calculate_mean_and_std_dev([15])[1] == 0.0

    # N = 0 returns 0.0
    assert calculate_mean_and_std_dev([]) == (0.0, 0.0)
