import re
import warnings


class StreamHandler:
    """Handles the parsing of stream information from FFmpeg output."""

    def __init__(self, parsing_state, file_metadata, fps_source):
        self.parsing_state = parsing_state
        self.file_metadata = file_metadata
        self.fps_source = fps_source

    def process_stream_line(self, line, input_chapters):
        """Process a line containing stream information."""
        stream_info = self.parsing_state.update_stream(line, input_chapters)
        if stream_info:
            stream_type_lower, input_number, stream_number = stream_info
            self.file_metadata.result[f"default_{stream_type_lower}_input_number"] = input_number
            self.file_metadata.result[f"default_{stream_type_lower}_stream_number"] = stream_number

            try:
                global_data, stream_data = self.parse_data_by_stream_type(stream_type_lower, line)
            except NotImplementedError as exc:
                warnings.warn(f"{str(exc)}\nffmpeg output:\n\n{self.file_metadata.infos}", UserWarning)
            else:
                self.file_metadata.update_global_data(global_data)
                self.parsing_state._current_stream.update(stream_data)

    def parse_data_by_stream_type(self, stream_type, line):
        """Parse data based on stream type (audio, video, data)."""
        try:
            return {
                "audio": self.parse_audio_stream_data,
                "video": self.parse_video_stream_data,
                "data": lambda _line: ({}, {}),
            }[stream_type](line)
        except KeyError:
            raise NotImplementedError(f"{stream_type} stream parsing is not supported by moviepy and will be ignored")

    def parse_audio_stream_data(self, line):
        """Parse audio stream data."""
        global_data, stream_data = ({"audio_found": True}, {})
        try:
            stream_data["fps"] = int(re.search(r" (\d+) Hz", line).group(1))
        except (AttributeError, ValueError):
            stream_data["fps"] = "unknown"
        match_audio_bitrate = re.search(r"(\d+) kb/s", line)
        stream_data["bitrate"] = int(match_audio_bitrate.group(1)) if match_audio_bitrate else None
        if self.parsing_state._current_stream["default"]:
            global_data["audio_fps"] = stream_data["fps"]
            global_data["audio_bitrate"] = stream_data["bitrate"]
        return global_data, stream_data

    def parse_video_stream_data(self, line):
        """Parse video stream data."""
        global_data, stream_data = ({"video_found": True}, {})

        try:
            match_video_size = re.search(r" (\d+)x(\d+)[,\s]", line)
            if match_video_size:
                stream_data["size"] = [int(num) for num in match_video_size.groups()]
        except Exception:
            raise IOError(
                (
                    "MoviePy error: failed to read video dimensions in"
                    " file '%s'.\nHere are the file infos returned by"
                    "ffmpeg:\n\n%s"
                )
                % (self.file_metadata.filename, self.file_metadata.infos)
            )

        match_bitrate = re.search(r"(\d+) kb/s", line)
        stream_data["bitrate"] = int(match_bitrate.group(1)) if match_bitrate else None

        if self.fps_source == "fps":
            try:
                fps = self.parse_fps(line)
            except (AttributeError, ValueError):
                fps = self.parse_tbr(line)
        elif self.fps_source == "tbr":
            try:
                fps = self.parse_tbr(line)
            except (AttributeError, ValueError):
                fps = self.parse_fps(line)
        else:
            raise ValueError(
                f"fps source '{self.fps_source}' not supported parsing the video '{self.file_metadata.filename}'")

        coef = 1000.0 / 1001.0
        for x in [23, 24, 25, 30, 50]:
            if fps != x and abs(fps - x * coef) < 0.01:
                fps = x * coef
        stream_data["fps"] = fps

        if self.parsing_state._current_stream["default"] or "video_size" not in self.file_metadata.result:
            global_data["video_size"] = stream_data.get("size", None)
        if self.parsing_state._current_stream["default"] or "video_bitrate" not in self.file_metadata.result:
            global_data["video_bitrate"] = stream_data.get("bitrate", None)
        if self.parsing_state._current_stream["default"] or "video_fps" not in self.file_metadata.result:
            global_data["video_fps"] = stream_data["fps"]

        return global_data, stream_data

    def parse_fps(self, line):
        """Extract frames per second (fps) from the line."""
        return float(re.search(r" (\d+.?\d*) fps", line).group(1))

    def parse_tbr(self, line):
        """Extract time base rate (tbr) from the line."""
        s_tbr = re.search(r" (\d+.?\d*k?) tbr", line).group(1)
        if s_tbr[-1] == "k":
            tbr = float(s_tbr[:-1]) * 1000
        else:
            tbr = float(s_tbr)
        return tbr
