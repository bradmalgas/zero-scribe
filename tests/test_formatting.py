import pytest
from formatting import chunkWords, endsSentence, float_to_timestamp, isLocalBaseUrl, wrapCaptionText


# --- isLocalBaseUrl ---

def test_isLocalBaseUrl_localhost():
    assert isLocalBaseUrl("http://localhost:1234/v1") is True

def test_isLocalBaseUrl_127():
    assert isLocalBaseUrl("http://127.0.0.1:1234/v1") is True

def test_isLocalBaseUrl_ipv6_loopback():
    assert isLocalBaseUrl("http://[::1]:1234/v1") is True

def test_isLocalBaseUrl_all_interfaces():
    assert isLocalBaseUrl("http://0.0.0.0:1234/v1") is True

def test_isLocalBaseUrl_remote_openai():
    assert isLocalBaseUrl("https://api.openai.com/v1") is False

def test_isLocalBaseUrl_remote_arbitrary():
    assert isLocalBaseUrl("https://example.com/v1") is False


# --- float_to_timestamp ---

def test_float_to_timestamp_zero():
    assert float_to_timestamp(0.0) == "00:00:00,000"

def test_float_to_timestamp_seconds():
    assert float_to_timestamp(90.0) == "00:01:30,000"

def test_float_to_timestamp_hours():
    assert float_to_timestamp(3661.5) == "01:01:01,500"

def test_float_to_timestamp_milliseconds():
    assert float_to_timestamp(0.123) == "00:00:00,123"

def test_float_to_timestamp_negative_clamps_to_zero():
    assert float_to_timestamp(-5.0) == "00:00:00,000"

def test_float_to_timestamp_vtt_separator():
    assert float_to_timestamp(1.0, ".") == "00:00:01.000"


# --- wrapCaptionText ---

def test_wrapCaptionText_empty():
    assert wrapCaptionText("") == []

def test_wrapCaptionText_short_fits_one_line():
    assert wrapCaptionText("Hello world") == ["Hello world"]

def test_wrapCaptionText_wraps_at_42_chars():
    # 39-char word + "word" pushed to next line
    text = "A" * 39 + " word"
    lines = wrapCaptionText(text)
    assert len(lines) == 2
    assert lines[1] == "word"

def test_wrapCaptionText_exactly_42_chars_stays_on_one_line():
    assert wrapCaptionText("A" * 42) == ["A" * 42]

def test_wrapCaptionText_multiple_wraps():
    long_word = "A" * 43
    lines = wrapCaptionText(f"{long_word} {long_word}")
    assert lines == [long_word, long_word]


# --- endsSentence ---

def test_endsSentence_period():
    assert endsSentence("Hello.") is True

def test_endsSentence_question():
    assert endsSentence("Really?") is True

def test_endsSentence_exclamation():
    assert endsSentence("Wow!") is True

def test_endsSentence_ellipsis():
    assert endsSentence("And then...") is True

def test_endsSentence_no_punctuation():
    assert endsSentence("Hello") is False

def test_endsSentence_comma():
    assert endsSentence("Hello, world") is False

def test_endsSentence_strips_whitespace():
    assert endsSentence("Hello.  ") is True


# --- chunkWords ---

def _word(text, start, end):
    return {"word": text, "start": start, "end": end}

def test_chunkWords_empty():
    assert chunkWords([]) == []

def test_chunkWords_single_word():
    result = chunkWords([_word("hi", 0.0, 0.5)])
    assert result == [{"start": 0.0, "end": 0.5, "text": "hi"}]

def test_chunkWords_sentence_boundary_flushes_chunk():
    words = [_word("Done.", 0.0, 1.5), _word("Next", 2.0, 2.5)]
    result = chunkWords(words)
    assert result[0]["text"] == "Done."
    assert result[1]["text"] == "Next"

def test_chunkWords_no_flush_before_one_second():
    # Sentence ends but duration < 1s — stays in the same chunk
    words = [_word("Done.", 0.0, 0.4), _word("Next", 0.5, 0.9)]
    result = chunkWords(words)
    assert len(result) == 1
    assert "Done." in result[0]["text"]

def test_chunkWords_long_text_triggers_new_chunk():
    # First word is 88 chars; adding "overflow" makes candidate_text 97 chars > 84
    words = [_word("word" * 22, 0.0, 1.0), _word("overflow", 1.1, 2.0)]
    result = chunkWords(words)
    assert len(result) == 2

def test_chunkWords_long_duration_triggers_new_chunk():
    # candidate_duration = 9.0 - 0.0 = 9s > 6s threshold
    words = [_word("start", 0.0, 1.0), _word("end", 8.0, 9.0)]
    result = chunkWords(words)
    assert len(result) == 2
    assert result[0]["text"] == "start"
    assert result[1]["text"] == "end"

def test_chunkWords_skips_words_missing_timestamps():
    words = [
        {"word": "valid", "start": 0.0, "end": 1.0},
        {"word": "bad", "start": None, "end": 1.5},
        {"word": "also", "start": 2.0, "end": 3.0},
    ]
    result = chunkWords(words)
    combined = " ".join(c["text"] for c in result)
    assert "bad" not in combined
