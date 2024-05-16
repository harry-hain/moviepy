import re
import warnings
from moviepy.video.io.ffmpeg_infos_parsing.file_metadata import FileMetadata
from moviepy.video.io.ffmpeg_infos_parsing.parsing_state import ParsingState


class FFmpegInfosParser:
    def __init__(self, infos, filename, fps_source="fps", check_duration=True, decode_file=False):
        self.infos = infos
        self.filename = filename
        self.fps_source = fps_source
        self.check_duration = check_duration
        self.duration_tag_separator = "time=" if decode_file else "Duration: "
        self.parsing_state = ParsingState()
        self.file_metadata = FileMetadata()

    def parse(self):
        input_chapters = []

        for line in self.infos.splitlines()[1:]:
            if self.is_duration_line(line):
                self.file_metadata.result["duration"] = self.file_metadata.parse_duration(line, self.duration_tag_separator)
            elif self.parsing_state._inside_output or line[0] != " ":
                if self.is_output_line(line):
                    self.parsing_state._inside_output = True
            elif self.is_metadata_start_line(line):
                self.parsing_state._inside_file_metadata = True
            elif self.is_duration_start_line(line):
                self.process_duration_start_line(line)
            elif self.parsing_state._inside_file_metadata:
                self.process_metadata_line(line)
            elif self.is_stream_line(line):
                self.process_stream_line(line, input_chapters)
            elif line.startswith("    Metadata:"):
                continue
            elif self.parsing_state._current_stream:
                self.process_current_stream_metadata_line(line)
            elif self.is_chapter_line(line):
                self.process_chapter_line(line, input_chapters)
            elif self.parsing_state._current_chapter:
                self.process_current_chapter_metadata_line(line)

        # Finalize last chapter if present
        if self.parsing_state._current_chapter:
            if len(input_chapters) < self.parsing_state._current_chapter["input_number"] + 1:
                input_chapters.append([])
            input_chapters[self.parsing_state._current_chapter["input_number"]].append(self.parsing_state._current_chapter)

        self.finalize_parsing(input_chapters)
        return self.file_metadata.result

    def is_duration_line(self, line):
        return self.duration_tag_separator == "time=" and self.check_duration and "time=" in line

    def is_output_line(self, line):
        return self.duration_tag_separator == "time=" and not self.parsing_state._inside_output and line[0] != " "

    def is_metadata_start_line(self, line):
        return not self.parsing_state._inside_file_metadata and line.startswith("  Metadata:")

    def is_duration_start_line(self, line):
        return line.startswith("  Duration:")

    def is_stream_line(self, line):
        return line.lstrip().startswith("Stream ")

    def is_chapter_line(self, line):
        return line.startswith("    Chapter")

    def process_duration_start_line(self, line):
        self.parsing_state._inside_file_metadata = False
        if self.check_duration and self.duration_tag_separator == "Duration: ":
            self.file_metadata.result["duration"] = self.file_metadata.parse_duration(line, self.duration_tag_separator)

        bitrate_match = re.search(r"bitrate: (\d+) kb/s", line)
        self.file_metadata.result["bitrate"] = int(bitrate_match.group(1)) if bitrate_match else None

        start_match = re.search(r"start: (\d+\.?\d+)", line)
        self.file_metadata.result["start"] = float(start_match.group(1)) if start_match else None

    def process_metadata_line(self, line):
        field, value = self.file_metadata.parse_metadata_field_value(line)

        if field == "":
            field = self.parsing_state._last_metadata_field_added
            value = self.file_metadata.result["metadata"][field] + "\n" + value
        else:
            self.parsing_state._last_metadata_field_added = field
        self.file_metadata.result["metadata"][field] = value

    def process_stream_line(self, line, input_chapters):
        stream_info = self.parsing_state.update_stream(line, input_chapters)
        if stream_info:
            stream_type_lower, input_number, stream_number = stream_info
            self.file_metadata.result[f"default_{stream_type_lower}_input_number"] = input_number
            self.file_metadata.result[f"default_{stream_type_lower}_stream_number"] = stream_number

            try:
                global_data, stream_data = self.parse_data_by_stream_type(stream_type_lower, line)
            except NotImplementedError as exc:
                warnings.warn(f"{str(exc)}\nffmpeg output:\n\n{self.infos}", UserWarning)
            else:
                self.file_metadata.update_global_data(global_data)
                self.parsing_state._current_stream.update(stream_data)

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

    def process_chapter_line(self, line, input_chapters):
        if self.parsing_state._current_chapter:
            if len(input_chapters) < self.parsing_state._current_chapter["input_number"] + 1:
                input_chapters.append([])
            input_chapters[self.parsing_state._current_chapter["input_number"]].append(self.parsing_state._current_chapter)

        chapter_data_match = re.search(
            r"^    Chapter #(\d+):(\d+): start (\d+\.?\d+?), end (\d+\.?\d+?)",
            line,
        )
        input_number, chapter_number, start, end = chapter_data_match.groups()

        self.parsing_state._current_chapter = {
            "input_number": int(input_number),
            "chapter_number": int(chapter_number),
            "start": float(start),
            "end": float(end),
        }

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

    def finalize_parsing(self, input_chapters):
        input_file = self.parsing_state.finalize_input_file(input_chapters)
        if input_file:
            self.file_metadata.result["inputs"].append(input_file)

        if self.file_metadata.result["video_found"] and self.check_duration:
            self.file_metadata.result["video_n_frames"] = int(
                self.file_metadata.result["duration"] * self.file_metadata.result["video_fps"]
            )
            self.file_metadata.result["video_duration"] = self.file_metadata.result["duration"]
        else:
            self.file_metadata.result["video_n_frames"] = 1
            self.file_metadata.result["video_duration"] = None

        if self.file_metadata.result["audio_found"] and not self.file_metadata.result.get("audio_bitrate"):
            self.file_metadata.result["audio_bitrate"] = None
            for streams_input in self.file_metadata.result["inputs"]:
                for stream in streams_input["streams"]:
                    if stream["stream_type"] == "audio" and stream.get("bitrate"):
                        self.file_metadata.result["audio_bitrate"] = stream["bitrate"]
                        break

                if self.file_metadata.result["audio_bitrate"] is not None:
                    break

    def parse_data_by_stream_type(self, stream_type, line):
        try:
            return {
                "audio": self.parse_audio_stream_data,
                "video": self.parse_video_stream_data,
                "data": lambda _line: ({}, {}),
            }[stream_type](line)
        except KeyError:
            raise NotImplementedError(f"{stream_type} stream parsing is not supported by moviepy and will be ignored")

    def parse_audio_stream_data(self, line):
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
                % (self.filename, self.infos)
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
            raise ValueError(f"fps source '{self.fps_source}' not supported parsing the video '{self.filename}'")

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
        return float(re.search(r" (\d+.?\d*) fps", line).group(1))

    def parse_tbr(self, line):
        s_tbr = re.search(r" (\d+.?\d*k?) tbr", line).group(1)
        if s_tbr[-1] == "k":
            tbr = float(s_tbr[:-1]) * 1000
        else:
            tbr = float(s_tbr)
        return tbr
