"""Implements all the functions to read a video or a picture using ffmpeg."""
import os
import subprocess as sp

from moviepy.config import FFMPEG_BINARY  # ffmpeg, ffmpeg.exe, etc...
from moviepy.tools import cross_platform_popen_params
from moviepy.video.io.ffmpeg_utils.ffmpeg_command_builder import FFMPEGCommandBuilder
from moviepy.video.io.ffmpeg_utils.ffmpeg_infos_parser import FFmpegInfosParser
from moviepy.video.io.ffmpeg_utils.frame_processor import FrameProcessor


class FFMPEG_VideoReader:
    """Class for video byte-level reading with ffmpeg."""

    def __init__(self, filename, decode_file=True, print_infos=False, bufsize=None, pixel_format="rgb24", check_duration=True, target_resolution=None, resize_algo="bicubic", fps_source="fps"):
        self.filename = filename
        infos = ffmpeg_parse_infos(filename, check_duration, fps_source, decode_file, print_infos)
        self.fps = infos["video_fps"]
        self.duration = infos["video_duration"]
        self.n_frames = infos["video_n_frames"]
        self.size = target_resolution or infos["video_size"]
        self.frame_processor = FrameProcessor(self.size, 4 if pixel_format[-1] == "a" else 3)
        self.command_builder = FFMPEGCommandBuilder(filename, pixel_format, self.size, resize_algo)
        self.proc = None
        self.current_frame = 0  # Initialise current frame counter
        self.lastread = None  # Last read frame storage
        self.initialize()

    def initialize(self, start_time=0):
        if self.proc:
            self.close()  # Ensure any existing process is closed before re-initialising
        cmd = self.command_builder.build(start_time=start_time)
        popen_params = cross_platform_popen_params({
            "bufsize": self.frame_processor.calculate_nbytes() + 100,
            "stdout": sp.PIPE,
            "stderr": sp.PIPE,
            "stdin": sp.DEVNULL
        })
        self.proc = sp.Popen(cmd, **popen_params)
        self.current_frame = self.get_frame_number(start_time)
        self.lastread = self.frame_processor.read_frame(self.proc)

    def get_frame(self, t):
        """
        Retrieves the video frame at time t.
        """
        target_frame_number = self.get_frame_number(t)

        if not self.proc or abs(target_frame_number - self.current_frame) > 100:
            self.initialize(t)  # Reinitialise if the jump is too large or process is dead

        while self.current_frame < target_frame_number:
            self.lastread = self.frame_processor.read_frame(self.proc)
            self.current_frame += 1

        return self.lastread

    def get_frame_number(self, t):
        """
        Helper method to calculate the frame number based on the time t.
        """
        return int(self.fps * t + 0.00001)  # Adjust for floating-point arithmetic issues

    def close(self):
        """Terminates the ffmpeg process cleanly."""
        if self.proc:
            self.proc.terminate()
            self.proc.wait()
            self.proc = None
        self.lastread = None

    def __del__(self):
        self.close()

def ffmpeg_read_image(filename, with_mask=True, pixel_format=None):
    """Read an image file (PNG, BMP, JPEG...).

    Wraps FFMPEG_Videoreader to read just one image.
    Returns an ImageClip.

    This function is not meant to be used directly in MoviePy.
    Use ImageClip instead to make clips out of image files.

    Parameters
    ----------

    filename
      Name of the image file. Can be of any format supported by ffmpeg.

    with_mask
      If the image has a transparency layer, ``with_mask=true`` will save
      this layer as the mask of the returned ImageClip

    pixel_format
      Optional: Pixel format for the image to read. If is not specified
      'rgb24' will be used as the default format unless ``with_mask`` is set
      as ``True``, then 'rgba' will be used.

    """
    if not pixel_format:
        pixel_format = "rgba" if with_mask else "rgb24"
    reader = FFMPEG_VideoReader(
        filename, pixel_format=pixel_format, check_duration=False
    )
    im = reader.last_read
    del reader
    return im


def ffmpeg_parse_infos(
    filename,
    check_duration=True,
    fps_source="fps",
    decode_file=False,
    print_infos=False,
):
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
            "bufsize": 10**5,
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
