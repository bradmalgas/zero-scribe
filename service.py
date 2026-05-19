from audio import recordAudio
from file import ensureOutputDirs
from models import FormattingRequest, RecordingRequest, RecordingResult

# record_audio -> RecordingResult
def record_audio(request: RecordingRequest) -> RecordingResult:
    ensureOutputDirs()
    resp = recordAudio(req=request)
    return resp

# format_notes -> FormmatingResult
# run_pipeline -> PipelineResult