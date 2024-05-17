import re
from moviepy.video.io.ffmpeg_infos_parsing.file_metadata import FileMetadata
from moviepy.video.io.ffmpeg_infos_parsing.parsing_state import ParsingState
from moviepy.video.io.ffmpeg_infos_parsing.parsing_handlers.stream_handler import StreamHandler
from moviepy.video.io.ffmpeg_infos_parsing.parsing_handlers.chapter_handler import ChapterHandler
from moviepy.video.io.ffmpeg_infos_parsing.parsing_handlers.metadata_handler import MetadataHandler


class FFmpegInfosParser:
    """Parser for extracting information from FFmpeg output."""

    def __init__(self, infos, filename, fps_source="fps", check_duration=True, decode_file=False):
        self.infos = infos
        self.filename = filename
        self.fps_source = fps_source
        self.check_duration = check_duration
        self.duration_tag_separator = "time=" if decode_file else "Duration: "
        self.parsing_state = ParsingState()
        self.file_metadata = FileMetadata()
        self.stream_handler = StreamHandler(self.parsing_state, self.file_metadata, self.fps_source)
        self.chapter_handler = ChapterHandler(self.parsing_state, self.file_metadata)
        self.metadata_handler = MetadataHandler(self.parsing_state, self.file_metadata)

    def parse(self):
        """Main parsing method to extract and structure FFmpeg output."""
        input_chapters = []

        for line in self.infos.splitlines()[1:]:
            if self.is_duration_line(line):
                self.file_metadata.result["duration"] = self.file_metadata.parse_duration(line,
                                                                                          self.duration_tag_separator)
            elif self.parsing_state._inside_output or line[0] != " ":
                if self.is_output_line(line):
                    self.parsing_state._inside_output = True
            elif self.is_metadata_start_line(line):
                self.parsing_state._inside_file_metadata = True
            elif self.is_duration_start_line(line):
                self.process_duration_start_line(line)
            elif self.parsing_state._inside_file_metadata:
                self.metadata_handler.process_metadata_line(line)
            elif self.is_stream_line(line):
                self.stream_handler.process_stream_line(line, input_chapters)
            elif line.startswith("    Metadata:"):
                continue
            elif self.parsing_state._current_stream:
                self.metadata_handler.process_current_stream_metadata_line(line)
            elif self.is_chapter_line(line):
                self.chapter_handler.process_chapter_line(line, input_chapters)
            elif self.parsing_state._current_chapter:
                self.metadata_handler.process_current_chapter_metadata_line(line)

        # Finalise last chapter if present
        if self.parsing_state._current_chapter:
            if len(input_chapters) < self.parsing_state._current_chapter["input_number"] + 1:
                input_chapters.append([])
            input_chapters[self.parsing_state._current_chapter["input_number"]].append(
                self.parsing_state._current_chapter)

        self.finalise_parsing(input_chapters)
        return self.file_metadata.result

    def is_duration_line(self, line):
        """Check if the line contains duration information."""
        return self.duration_tag_separator == "time=" and self.check_duration and "time=" in line

    def is_output_line(self, line):
        """Check if the line indicates the start of output information."""
        return self.duration_tag_separator == "time=" and not self.parsing_state._inside_output and line[0] != " "

    def is_metadata_start_line(self, line):
        """Check if the line indicates the start of metadata."""
        return not self.parsing_state._inside_file_metadata and line.startswith("  Metadata:")

    def is_duration_start_line(self, line):
        """Check if the line contains start duration information."""
        return line.startswith("  Duration:")

    def is_stream_line(self, line):
        """Check if the line contains stream information."""
        return line.lstrip().startswith("Stream ")

    def is_chapter_line(self, line):
        """Check if the line contains chapter information."""
        return line.startswith("    Chapter")

    def process_duration_start_line(self, line):
        """Process duration start line to extract duration, bitrate, and start time."""
        self.parsing_state._inside_file_metadata = False
        if self.check_duration and self.duration_tag_separator == "Duration: ":
            self.file_metadata.result["duration"] = self.file_metadata.parse_duration(line, self.duration_tag_separator)

        bitrate_match = re.search(r"bitrate: (\d+) kb/s", line)
        self.file_metadata.result["bitrate"] = int(bitrate_match.group(1)) if bitrate_match else None

        start_match = re.search(r"start: (\d+\.?\d+)", line)
        self.file_metadata.result["start"] = float(start_match.group(1)) if start_match else None

    def finalise_parsing(self, input_chapters):
        """Finalise parsing by appending input files and updating metadata."""
        input_file = self.parsing_state.finalise_input_file(input_chapters)
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
