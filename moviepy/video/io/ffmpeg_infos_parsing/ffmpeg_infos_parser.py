import re
import warnings
from moviepy.video.io.ffmpeg_infos_parsing.parsing_state import ParsingState
from moviepy.video.io.ffmpeg_infos_parsing.file_metadata import FileMetadata

class FFmpegInfosParser:
    def __init__(
            self,
            infos,
            filename,
            fps_source="fps",
            check_duration=True,
            decode_file=False,
    ):
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
            if (
                    self.duration_tag_separator == "time="
                    and self.check_duration
                    and "time=" in line
            ):
                self.file_metadata.result["duration"] = self.parse_duration(line)
            elif self.parsing_state._inside_output or line[0] != " ":
                if self.duration_tag_separator == "time=" and not self.parsing_state._inside_output:
                    self.parsing_state._inside_output = True
            elif not self.parsing_state._inside_file_metadata and line.startswith("  Metadata:"):
                self.parsing_state._inside_file_metadata = True
            elif line.startswith("  Duration:"):
                self.parsing_state._inside_file_metadata = False
                if self.check_duration and self.duration_tag_separator == "Duration: ":
                    self.file_metadata.result["duration"] = self.parse_duration(line)

                bitrate_match = re.search(r"bitrate: (\d+) kb/s", line)
                self.file_metadata.result["bitrate"] = (
                    int(bitrate_match.group(1)) if bitrate_match else None
                )

                start_match = re.search(r"start: (\d+\.?\d+)", line)
                self.file_metadata.result["start"] = (
                    float(start_match.group(1)) if start_match else None
                )
            elif self.parsing_state._inside_file_metadata:
                field, value = self.parse_metadata_field_value(line)

                if field == "":
                    field = self.parsing_state._last_metadata_field_added
                    value = self.file_metadata.result["metadata"][field] + "\n" + value
                else:
                    self.parsing_state._last_metadata_field_added = field
                self.file_metadata.result["metadata"][field] = value
            elif line.lstrip().startswith("Stream "):
                if self.parsing_state._current_stream:
                    self.parsing_state._current_input_file["streams"].append(self.parsing_state._current_stream)

                main_info_match = re.search(
                    r"^Stream\s#(\d+):(\d+)(?:\[\w+\])?\(?(\w+)?\)?:\s(\w+):",
                    line.lstrip(),
                )
                (
                    input_number,
                    stream_number,
                    language,
                    stream_type,
                ) = main_info_match.groups()
                input_number = int(input_number)
                stream_number = int(stream_number)
                stream_type_lower = stream_type.lower()

                if language == "und":
                    language = None

                self.parsing_state._current_stream = {
                    "input_number": input_number,
                    "stream_number": stream_number,
                    "stream_type": stream_type_lower,
                    "language": language,
                    "default": not self.parsing_state._default_stream_found
                               or line.endswith("(default)"),
                }
                self.parsing_state._default_stream_found = True

                if self.parsing_state._current_stream["default"]:
                    self.file_metadata.result[
                        f"default_{stream_type_lower}_input_number"
                    ] = input_number
                    self.file_metadata.result[
                        f"default_{stream_type_lower}_stream_number"
                    ] = stream_number

                if self.parsing_state._current_chapter:
                    input_chapters[input_number].append(self.parsing_state._current_chapter)
                    self.parsing_state._current_chapter = None

                if "input_number" not in self.parsing_state._current_input_file:
                    self.parsing_state._current_input_file = {"input_number": input_number, "streams": []}
                elif self.parsing_state._current_input_file["input_number"] != input_number:
                    if len(input_chapters) >= input_number + 1:
                        self.parsing_state._current_input_file["chapters"] = input_chapters[input_number]

                    self.file_metadata.result["inputs"].append(self.parsing_state._current_input_file)
                    self.parsing_state._current_input_file = {"input_number": input_number, "streams": []}

                try:
                    global_data, stream_data = self.parse_data_by_stream_type(
                        stream_type, line
                    )
                except NotImplementedError as exc:
                    warnings.warn(
                        f"{str(exc)}\nffmpeg output:\n\n{self.infos}", UserWarning
                    )
                else:
                    self.file_metadata.result.update(global_data)
                    self.parsing_state._current_stream.update(stream_data)
            elif line.startswith("    Metadata:"):
                continue
            elif self.parsing_state._current_stream:
                if "metadata" not in self.parsing_state._current_stream:
                    self.parsing_state._current_stream["metadata"] = {}

                field, value = self.parse_metadata_field_value(line)

                if self.parsing_state._current_stream["stream_type"] == "video":
                    field, value = self.video_metadata_type_casting(field, value)
                    if field == "rotate":
                        self.file_metadata.result["video_rotation"] = value

                if field == "":
                    field = self.parsing_state._last_metadata_field_added
                    value = self.parsing_state._current_stream["metadata"][field] + "\n" + value
                else:
                    self.parsing_state._last_metadata_field_added = field
                self.parsing_state._current_stream["metadata"][field] = value
            elif line.startswith("    Chapter"):
                if self.parsing_state._current_chapter:
                    if len(input_chapters) < self.parsing_state._current_chapter["input_number"] + 1:
                        input_chapters.append([])
                    input_chapters[self.parsing_state._current_chapter["input_number"]].append(
                        self.parsing_state._current_chapter
                    )

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
            elif self.parsing_state._current_chapter:
                if "metadata" not in self.parsing_state._current_chapter:
                    self.parsing_state._current_chapter["metadata"] = {}
                field, value = self.parse_metadata_field_value(line)

                if field == "":
                    field = self.parsing_state._last_metadata_field_added
                    value = self.parsing_state._current_chapter["metadata"][field] + "\n" + value
                else:
                    self.parsing_state._last_metadata_field_added = field
                self.parsing_state._current_chapter["metadata"][field] = value

        if self.parsing_state._current_input_file:
            self.parsing_state._current_input_file["streams"].append(self.parsing_state._current_stream)
            if len(input_chapters) == self.parsing_state._current_input_file["input_number"] + 1:
                self.parsing_state._current_input_file["chapters"] = input_chapters[
                    self.parsing_state._current_input_file["input_number"]
                ]
            self.file_metadata.result["inputs"].append(self.parsing_state._current_input_file)

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

        result = self.file_metadata.result
        self.parsing_state.reset()
        return result

    def parse_data_by_stream_type(self, stream_type, line):
        try:
            return {
                "Audio": self.parse_audio_stream_data,
                "Video": self.parse_video_stream_data,
                "Data": lambda _line: ({}, {}),
            }[stream_type](line)
        except KeyError:
            raise NotImplementedError(
                f"{stream_type} stream parsing is not supported by moviepy and"
                " will be ignored"
            )

    def parse_audio_stream_data(self, line):
        global_data, stream_data = ({"audio_found": True}, {})
        try:
            stream_data["fps"] = int(re.search(r" (\d+) Hz", line).group(1))
        except (AttributeError, ValueError):
            stream_data["fps"] = "unknown"
        match_audio_bitrate = re.search(r"(\d+) kb/s", line)
        stream_data["bitrate"] = (
            int(match_audio_bitrate.group(1)) if match_audio_bitrate else None
        )
        if self.parsing_state._current_stream["default"]:
            global_data["audio_fps"] = stream_data["fps"]
            global_data["audio_bitrate"] = stream_data["bitrate"]
        return (global_data, stream_data)

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
            raise ValueError(
                ("fps source '%s' not supported parsing the video '%s'")
                % (self.fps_source, self.filename)
            )

        coef = 1000.0 / 1001.0
        for x in [23, 24, 25, 30, 50]:
            if (fps != x) and abs(fps - x * coef) < 0.01:
                fps = x * coef
        stream_data["fps"] = fps

        if self.parsing_state._current_stream["default"] or "video_size" not in self.file_metadata.result:
            global_data["video_size"] = stream_data.get("size", None)
        if self.parsing_state._current_stream["default"] or "video_bitrate" not in self.file_metadata.result:
            global_data["video_bitrate"] = stream_data.get("bitrate", None)
        if self.parsing_state._current_stream["default"] or "video_fps" not in self.file_metadata.result:
            global_data["video_fps"] = stream_data["fps"]

        return (global_data, stream_data)

    def parse_fps(self, line):
        return float(re.search(r" (\d+.?\d*) fps", line).group(1))

    def parse_tbr(self, line):
        s_tbr = re.search(r" (\d+.?\d*k?) tbr", line).group(1)
        if s_tbr[-1] == "k":
            tbr = float(s_tbr[:-1]) * 1000
        else:
            tbr = float(s_tbr)
        return tbr

    def parse_duration(self, line):
        try:
            time_raw_string = line.split(self.duration_tag_separator)[-1]
            match_duration = re.search(
                r"([0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9])",
                time_raw_string,
            )
            return convert_to_seconds(match_duration.group(1))
        except Exception:
            raise IOError(
                (
                    "MoviePy error: failed to read the duration of file '%s'.\n"
                    "Here are the file infos returned by ffmpeg:\n\n%s"
                )
                % (self.filename, self.infos)
            )

    def parse_metadata_field_value(self, line):
        raw_field, raw_value = line.split(":", 1)
        return (raw_field.strip(" "), raw_value.strip(" "))

    def video_metadata_type_casting(self, field, value):
        if field == "rotate":
            return (field, float(value))
        return (field, value)


def convert_to_seconds(time):
    factors = (1, 60, 3600)

    if isinstance(time, str):
        time = [float(part.replace(",", ".")) for part in time.split(":")]

    if not isinstance(time, (tuple, list)):
        return time

    return sum(mult * part for mult, part in zip(factors, reversed(time)))
