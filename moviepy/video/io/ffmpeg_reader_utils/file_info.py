import os
import subprocess as sp

from moviepy.config import FFMPEG_BINARY
from moviepy.tools import cross_platform_popen_params
from moviepy.video.io.ffmpeg_reader_utils.ffmpeg_infos_parser import FFmpegInfosParser


class FileInfo:
    def __init__(self, filename, infos, duration, ffmpeg_duration, n_frames, bitrate):
        self.filename = filename
        self.infos = infos
        self.duration = duration
        self.ffmpeg_duration = ffmpeg_duration
        self.n_frames = n_frames
        self.bitrate = bitrate

    @classmethod
    def ffmpeg_parse_infos(cls, filename, check_duration=True, fps_source="fps", decode_file=False, print_infos=False):
        """Get the information of a file using ffmpeg.

        Returns a dictionary with next fields:

        - ``"duration"``
        - ``"metadata"``
        - ``"inputs"``
        - ``"video_found"``
        - ``"video_fps"``
        - ``"video_n_frames"``
        - ``"video_duration"``
        - ``"video_bitrate"``
        - ``"video_metadata"``
        - ``"audio_found"``
        - ``"audio_fps"``
        - ``"audio_bitrate"``
        - ``"audio_metadata"``

        Note that "video_duration" is slightly smaller than "duration" to avoid
        fetching the incomplete frames at the end, which raises an error.

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
          Indicates if the whole file must be read to retrieve their duration.
          This is needed for some files in order to get the correct duration (see
          https://github.com/Zulko/moviepy/pull/1222).
        """
        # Open the file in a pipe, read output
        cmd = [FFMPEG_BINARY, "-hide_banner", "-i", filename]
        if decode_file:
            cmd.extend(["-f", "null", "-"])

        popen_params = cross_platform_popen_params(
            {
                "bufsize": 10 ** 5,
                "stdout": sp.PIPE,
                "stderr": sp.PIPE,
                "stdin": sp.DEVNULL,
            }
        )

        proc = sp.Popen(cmd, **popen_params)
        (output, error) = proc.communicate()
        infos = error.decode("utf8", errors="ignore")

        proc.terminate()
        del proc

        if print_infos:
            # print the whole info text returned by FFMPEG
            print(infos)

        try:
            return FFmpegInfosParser(
                infos,
                filename,
                fps_source=fps_source,
                check_duration=check_duration,
                decode_file=decode_file,
            ).parse()
        except Exception as exc:
            if os.path.isdir(filename):
                raise IsADirectoryError(f"'{filename}' is a directory")
            elif not os.path.exists(filename):
                raise FileNotFoundError(f"'{filename}' not found")
            raise IOError(f"Error passing `ffmpeg -i` command output:\n\n{infos}") from exc
