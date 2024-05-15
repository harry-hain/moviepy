import re


class ParsingState:
    def __init__(self):
        self._inside_output = False
        self._inside_file_metadata = False
        self._current_stream = None
        self._default_stream_found = False
        self._current_input_file = {"streams": []}
        self._last_metadata_field_added = None
        self._current_chapter = None

    def reset(self):
        self.__init__()

    def update_stream(self, stream_type, line):
        main_info_match = re.search(
            r"^Stream\s#(\d+):(\d+)(?:\[\w+\])?\(?(\w+)?\)?:\s(\w+):",
            line.lstrip(),
        )
        input_number, stream_number, language, stream_type = main_info_match.groups()
        input_number = int(input_number)
        stream_number = int(stream_number)
        stream_type_lower = stream_type.lower()
        if language == "und":
            language = None

        self._current_stream = {
            "input_number": input_number,
            "stream_number": stream_number,
            "stream_type": stream_type_lower,
            "language": language,
            "default": not self._default_stream_found or line.endswith("(default)"),
        }
        self._default_stream_found = True

        return self._current_stream

    def update_current_input_file(self, input_number, input_chapters):
        if "input_number" not in self._current_input_file:
            self._current_input_file = {"input_number": input_number, "streams": []}
        elif self._current_input_file["input_number"] != input_number:
            if len(input_chapters) >= input_number + 1:
                self._current_input_file["chapters"] = input_chapters[input_number]
            self._current_input_file = {"input_number": input_number, "streams": []}

        return self._current_input_file
