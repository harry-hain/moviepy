import re


class ChapterHandler:
    """Handles the parsing of chapter information from FFmpeg output."""

    def __init__(self, parsing_state, file_metadata):
        self.parsing_state = parsing_state
        self.file_metadata = file_metadata

    def process_chapter_line(self, line, input_chapters):
        """Process a line containing chapter information."""
        if self.parsing_state._current_chapter:
            if len(input_chapters) < self.parsing_state._current_chapter["input_number"] + 1:
                input_chapters.append([])
            input_chapters[self.parsing_state._current_chapter["input_number"]].append(
                self.parsing_state._current_chapter)

        chapter_data_match = re.search(
            r"^ {4}Chapter #(\d+):(\d+): start (\d+\.?\d+?), end (\d+\.?\d+?)",
            line,
        )
        input_number, chapter_number, start, end = chapter_data_match.groups()

        self.parsing_state._current_chapter = {
            "input_number": int(input_number),
            "chapter_number": int(chapter_number),
            "start": float(start),
            "end": float(end),
        }
