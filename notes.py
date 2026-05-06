from pathlib import Path

def exportMarkdown(markdown: str, outputPath: Path):
    try:
        with open(outputPath, 'w', encoding="utf-8") as file:
            file.write(markdown)
    except OSError as exc:
        raise RuntimeError(
            f"Could not write notes to {outputPath}. Check folder permissions."
        ) from exc