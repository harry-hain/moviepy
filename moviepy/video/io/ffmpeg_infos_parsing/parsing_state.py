import re

class ParsingState:
    def __init__(self):
        self.reset()

    def reset(self):
        self._inside_output = False
        self._inside_file_metadata = False
        self._current_stream = None
        self._default_stream_found = False
        self._current_input_file = None
        self._last_metadata_field_added = None
        self._current_chapter = None

    def create_new_input_file(self, input_number):
        return {"input_number": input_number, "streams": []}

    def update_stream(self, line, input_chapters):
        if self._current_stream:
            self._current_input_file["streams"].append(self._current_stream)

        main_info_match = re.search(
            r"^Stream\s#(\d+):(\d+)(?:\[\w+\])?\(?(\w+)?\)?:\s(\w+):",
            line.lstrip(),
        )

        if not main_info_match:
            # Handle the case where the line does not match the expected pattern
            return None

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

        if self._current_input_file is None:
            self._current_input_file = self.create_new_input_file(input_number)
        elif self._current_input_file["input_number"] != input_number:
            if len(input_chapters) >= input_number + 1:
                self._current_input_file["chapters"] = input_chapters[input_number]
            self._current_input_file = self.create_new_input_file(input_number)

        return stream_type_lower, input_number, stream_number

    def finalize_input_file(self, input_chapters):
        if self._current_input_file:
            self._current_input_file["streams"].append(self._current_stream)
            if len(input_chapters) == self._current_input_file["input_number"] + 1:
                self._current_input_file["chapters"] = input_chapters[
                    self._current_input_file["input_number"]
                ]
            return self._current_input_file
        return None
