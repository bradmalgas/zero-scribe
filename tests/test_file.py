from config import AUDIO_DIR, CAPTIONS_DIR, NOTES_DIR, TRANSCRIPTS_DIR
from file import buildOutputPaths


def test_buildOutputPaths_returns_all_keys():
    paths = buildOutputPaths()
    assert set(paths.keys()) == {"audio", "mic", "system", "notes", "transcript", "captions"}

def test_buildOutputPaths_audio_in_audio_dir():
    paths = buildOutputPaths()
    assert paths["audio"].parent == AUDIO_DIR
    assert paths["mic"].parent == AUDIO_DIR
    assert paths["system"].parent == AUDIO_DIR

def test_buildOutputPaths_notes_in_notes_dir():
    assert buildOutputPaths()["notes"].parent == NOTES_DIR

def test_buildOutputPaths_transcript_in_transcripts_dir():
    assert buildOutputPaths()["transcript"].parent == TRANSCRIPTS_DIR

def test_buildOutputPaths_captions_in_captions_dir():
    assert buildOutputPaths()["captions"].parent == CAPTIONS_DIR

def test_buildOutputPaths_wav_extensions():
    paths = buildOutputPaths()
    assert paths["audio"].suffix == ".wav"
    assert paths["mic"].suffix == ".wav"
    assert paths["system"].suffix == ".wav"

def test_buildOutputPaths_markdown_extensions():
    paths = buildOutputPaths()
    assert paths["notes"].suffix == ".md"
    assert paths["transcript"].suffix == ".md"

def test_buildOutputPaths_unique_across_calls():
    # Two calls a moment apart should not collide in practice, but the
    # structure should be consistent regardless.
    a = buildOutputPaths()
    b = buildOutputPaths()
    assert set(a.keys()) == set(b.keys())
