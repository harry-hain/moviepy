from moviepy import convert_to_seconds
import re
from moviepy.video.io.ffmpeg_utils.ffmpeg_parsing_utils.ffmpeg_stream_parsing import extract_stream_info, \
    extract_chapter_info
from moviepy.video.io.ffmpeg_utils.ffmpeg_parsing_utils.ffmpeg_metadata_parsing import parse_metadata_field_value, \
    video_metadata_type_casting
from moviepy.video.io.ffmpeg_utils.ffmpeg_parsing_utils.ffmpeg_parsing_utilities import extract_start_time, \
    extract_bitrate, parse_fps, parse_tbr


class FFmpegInfosParser:
    """Finite state ffmpeg `-i` command option file information parser.
    Is designed to parse the output fast, in one loop. Iterates line by
    line of the `ffmpeg -i <filename> [-f null -]` command output changing
    the internal state of the parser.

    Parameters
    ----------

    filename
      Name of the file parsed, only used to raise accurate error messages.

    infos
      Information returned by FFmpeg.

    fps_source
      Indicates what source data will be preferably used to retrieve fps data.

    check_duration
      Enable or disable the parsing of the duration of the file. Useful to
      skip the duration check, for example, for images.

    decode_file
      Indicates if the whole file has been decoded. The duration parsing strategy
      will differ depending on this argument.
    """

    def __init__(self, infos, filename, fps_source="fps", check_duration=True, decode_file=False):
        self._inside_file_metadata = None
        self._current_chapter = None
        self._inside_output = None
        self._current_stream = None
        self._current_input_file = None
        self.infos = infos
        self.filename = filename
        self.check_duration = check_duration
        self.fps_source = fps_source
        self.duration_tag_separator = "time=" if decode_file else "Duration: "
        self._reset_state()

    def _reset_state(self):
        self._inside_file_metadata = False
        self._inside_output = False
        self._default_stream_found = False
        self._current_input_file = {"streams": []}
        self._current_stream = None
        self._current_chapter = None
        self.result = {
            "video_found": False,
            "audio_found": False,
            "metadata": {},
            "inputs": []
        }
        self._last_metadata_field_added = None

    def parse(self):
        input_chapters = []
        lines = self.infos.splitlines()[1:]

        for line in lines:
            if self.duration_tag_separator in line and self.check_duration:
                self.handle_duration_line(line)
            elif line[0] != " " or self._inside_output:
                self.handle_output_block(line)
            elif "Metadata:" in line:
                self.handle_metadata_start(line)
            elif "Duration:" in line:
                self.handle_duration_line(line)
            elif line.strip().startswith("Stream "):
                self.handle_stream_line(line, input_chapters)
            elif line.strip().startswith("Chapter"):
                self.handle_chapter_line(line, input_chapters)

        self.finalize_input_file(input_chapters)
        return self.result

    def handle_duration_line(self, line):
        if "Duration:" in line:
            self.result["duration"] = self.parse_duration(line)
            self.result["bitrate"] = extract_bitrate(line)
            self.result["start"] = extract_start_time(line)

    def handle_output_block(self, line):
        if self.duration_tag_separator == "time=" and not self._inside_output:
            self._inside_output = True

    def handle_metadata_start(self, line):
        if line.startswith("  Metadata:"):
            self._inside_file_metadata = True
        elif line.startswith("  Duration:"):
            self._inside_file_metadata = False

    def handle_stream_line(self, line, input_chapters):
        if self._current_stream:
            self._current_input_file["streams"].append(self._current_stream)
        self._current_stream = extract_stream_info(line)
        if self._current_stream["default"]:
            self.set_default_stream_numbers()
        self.handle_new_input_file(line, input_chapters)

    def handle_chapter_line(self, line, input_chapters):
        if self._current_chapter:
            input_chapters[self._current_chapter["input_number"]].append(self._current_chapter)
        self._current_chapter = extract_chapter_info(line)

    def finalize_input_file(self, input_chapters):
        if self._current_input_file:
            self._current_input_file["streams"].append(self._current_stream)
            if len(input_chapters) == self._current_input_file["input_number"] + 1:
                self._current_input_file["chapters"] = input_chapters[self._current_input_file["input_number"]]
            self.result["inputs"].append(self._current_input_file)

    def set_default_stream_numbers(self):
        """Sets the default stream numbers for easier access."""
        stream_type = self._current_stream["stream_type"]
        input_number = self._current_stream["input_number"]
        stream_number = self._current_stream["stream_number"]
        self.result[f"default_{stream_type}_input_number"] = input_number
        self.result[f"default_{stream_type}_stream_number"] = stream_number

    def handle_new_input_file(self, line, input_chapters):
        """Handles logic for when a new input file block starts in the FFmpeg output."""
        input_number = self._current_stream["input_number"]
        if "input_number" not in self._current_input_file or self._current_input_file["input_number"] != input_number:
            if self._current_input_file.get("input_number") is not None:
                if len(input_chapters) >= input_number + 1:
                    self._current_input_file["chapters"] = input_chapters[input_number]
                self.result["inputs"].append(self._current_input_file)
            self._current_input_file = {"input_number": input_number, "streams": []}

    def parse_data_by_stream_type(self, stream_type, line):
        """Parses data from "Stream ... {stream_type}" line."""
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
        """Parses data from "Stream ... Audio" line."""
        global_data, stream_data = ({"audio_found": True}, {})
        try:
            stream_data["fps"] = int(re.search(r" (\d+) Hz", line).group(1))
        except (AttributeError, ValueError):
            # AttributeError: 'NoneType' object has no attribute 'group'
            # ValueError: invalid literal for int() with base 10: '<string>'
            stream_data["fps"] = "unknown"
        match_audio_bitrate = re.search(r"(\d+) kb/s", line)
        stream_data["bitrate"] = (
            int(match_audio_bitrate.group(1)) if match_audio_bitrate else None
        )
        if self._current_stream["default"]:
            global_data["audio_fps"] = stream_data["fps"]
            global_data["audio_bitrate"] = stream_data["bitrate"]
        return (global_data, stream_data)

    def parse_video_stream_data(self, line):
        """Parses data from "Stream ... Video" line."""
        global_data, stream_data = ({"video_found": True}, {})

        try:
            match_video_size = re.search(r" (\d+)x(\d+)[,\s]", line)
            if match_video_size:
                # size, of the form 460x320 (w x h)
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

        # Get the frame rate. Sometimes it's 'tbr', sometimes 'fps', sometimes
        # tbc, and sometimes tbc/2...
        # Current policy: Trust fps first, then tbr unless fps_source is
        # specified as 'tbr' in which case try tbr then fps

        # If result is near from x*1000/1001 where x is 23,24,25,50,
        # replace by x*1000/1001 (very common case for the fps).

        if self.fps_source == "fps":
            try:
                fps = parse_fps(line)
            except (AttributeError, ValueError):
                fps = parse_tbr(line)
        elif self.fps_source == "tbr":
            try:
                fps = parse_tbr(line)
            except (AttributeError, ValueError):
                fps = parse_fps(line)
        else:
            raise ValueError(
                "fps source '%s' not supported parsing the video '%s'"
                % (self.fps_source, self.filename)
            )

        # It is known that a fps of 24 is often written as 24000/1001
        # but then ffmpeg nicely rounds it to 23.98, which we hate.
        coef = 1000.0 / 1001.0
        for x in [23, 24, 25, 30, 50]:
            if (fps != x) and abs(fps - x * coef) < 0.01:
                fps = x * coef
        stream_data["fps"] = fps

        if self._current_stream["default"] or "video_size" not in self.result:
            global_data["video_size"] = stream_data.get("size", None)
        if self._current_stream["default"] or "video_bitrate" not in self.result:
            global_data["video_bitrate"] = stream_data.get("bitrate", None)
        if self._current_stream["default"] or "video_fps" not in self.result:
            global_data["video_fps"] = stream_data["fps"]

        return global_data, stream_data

    def parse_duration(self, line):
        """Parse the duration from the line that outputs the duration of
        the container.
        """
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
