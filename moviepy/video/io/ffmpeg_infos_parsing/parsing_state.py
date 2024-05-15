class ParsingState:
    def __init__(self):
        self._inside_file_metadata = False
        self._inside_output = False
        self._default_stream_found = False
        self._current_input_file = {"streams": []}
        self._current_stream = None
        self._current_chapter = None
        self._last_metadata_field_added = None

    def reset(self):
        self._inside_file_metadata = False
        self._inside_output = False
        self._default_stream_found = False
        self._current_input_file = {"streams": []}
        self._current_stream = None
        self._current_chapter = None
        self._last_metadata_field_added = None
