class MetadataHandler:
    def __init__(self, parsing_state, file_metadata):
        self.parsing_state = parsing_state
        self.file_metadata = file_metadata

    def process_metadata_line(self, line):
        field, value = self.file_metadata.parse_metadata_field_value(line)

        if field == "":
            field = self.parsing_state._last_metadata_field_added
            value = self.file_metadata.result["metadata"][field] + "\n" + value
        else:
            self.parsing_state._last_metadata_field_added = field
        self.file_metadata.result["metadata"][field] = value

    def process_current_stream_metadata_line(self, line):
        if "metadata" not in self.parsing_state._current_stream:
            self.parsing_state._current_stream["metadata"] = {}

        field, value = self.file_metadata.parse_metadata_field_value(line)

        if self.parsing_state._current_stream["stream_type"] == "video":
            field, value = self.file_metadata.video_metadata_type_casting(field, value)
            if field == "rotate":
                self.file_metadata.result["video_rotation"] = value

        if field == "":
            field = self.parsing_state._last_metadata_field_added
            value = self.parsing_state._current_stream["metadata"][field] + "\n" + value
        else:
            self.parsing_state._last_metadata_field_added = field
        self.parsing_state._current_stream["metadata"][field] = value

    def process_current_chapter_metadata_line(self, line):
        if "metadata" not in self.parsing_state._current_chapter:
            self.parsing_state._current_chapter["metadata"] = {}
        field, value = self.file_metadata.parse_metadata_field_value(line)

        if field == "":
            field = self.parsing_state._last_metadata_field_added
            value = self.parsing_state._current_chapter["metadata"][field] + "\n" + value
        else:
            self.parsing_state._last_metadata_field_added = field
        self.parsing_state._current_chapter["metadata"][field] = value
