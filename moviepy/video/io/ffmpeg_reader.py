"""Implements all the functions to read a video or a picture using ffmpeg."""
import os
import re
import subprocess as sp
import warnings

import numpy as np

from moviepy.config import FFMPEG_BINARY  # ffmpeg, ffmpeg.exe, etc...
from moviepy.tools import cross_platform_popen_params
from moviepy.video.io.ffmpeg_reader_utils.ffmpeg_infos_parser import FFmpegInfosParser
from moviepy.video.io.ffmpeg_reader_utils.data_container import FileInfo, VideoProperties, ProcessingState


class FFMPEG_VideoReader:
    """Class for video byte-level reading with ffmpeg."""

    def __init__(
        self,
        filename,
        decode_file=True,
        print_infos=False,
        bufsize=None,
        pixel_format="rgb24",
        check_duration=True,
        target_resolution=None,
        resize_algo="bicubic",
        fps_source="fps",
    ):
        infos = ffmpeg_parse_infos(
            filename,
            check_duration=check_duration,
            fps_source=fps_source,
            decode_file=decode_file,
            print_infos=print_infos,
        )

        # Initialize FileInfo container
        self.file_info = FileInfo(
            filename=filename,
            infos=infos,
            duration=infos["video_duration"],
            ffmpeg_duration=infos["duration"],
            n_frames=infos["video_n_frames"],
            bitrate=infos["video_bitrate"]
        )

        # Initialize VideoProperties container
        size = infos["video_size"]
        rotation = abs(infos.get("video_rotation", 0))
        if rotation in [90, 270]:
            size = [size[1], size[0]]

        if target_resolution:
            if None in target_resolution:
                ratio = 1
                for idx, target in enumerate(target_resolution):
                    if target:
                        ratio = target / size[idx]
                size = (int(size[0] * ratio), int(size[1] * ratio))
            else:
                size = target_resolution

        depth = 4 if pixel_format[-1] == "a" else 3

        if bufsize is None:
            w, h = size
            bufsize = depth * w * h + 100

        self.video_properties = VideoProperties(
            fps=infos["video_fps"],
            size=size,
            rotation=rotation,
            target_resolution=target_resolution,
            resize_algo=resize_algo,
            pixel_format=pixel_format,
            depth=depth,
            bufsize=bufsize
        )

        # Initialize ProcessingState container
        self.processing_state = ProcessingState()

        self.initialize()

    def initialize(self, start_time=0):
        """Opens the file, creates the pipe."""
        self.close(delete_lastread=False)  # if any

        if start_time != 0:
            offset = min(1, start_time)
            i_arg = [
                "-ss",
                "%.06f" % (start_time - offset),
                "-i",
                self.file_info.filename,
                "-ss",
                "%.06f" % offset,
            ]
        else:
            i_arg = ["-i", self.file_info.filename]

        cmd = (
            [FFMPEG_BINARY]
            + i_arg
            + [
                "-loglevel",
                "error",
                "-f",
                "image2pipe",
                "-vf",
                "scale=%d:%d" % tuple(self.video_properties.size),
                "-sws_flags",
                self.video_properties.resize_algo,
                "-pix_fmt",
                self.video_properties.pixel_format,
                "-vcodec",
                "rawvideo",
                "-",
            ]
        )
        popen_params = cross_platform_popen_params(
            {
                "bufsize": self.video_properties.bufsize,
                "stdout": sp.PIPE,
                "stderr": sp.PIPE,
                "stdin": sp.DEVNULL,
            }
        )
        self.processing_state.proc = sp.Popen(cmd, **popen_params)

        # self.pos represents the (0-indexed) index of the frame that is next in line
        # to be read by self.read_frame().
        # Eg when self.pos is 1, the 2nd frame will be read next.
        self.processing_state.pos = self.get_frame_number(start_time)
        self.processing_state.lastread = self.read_frame()

    def skip_frames(self, n=1):
        """Reads and throws away n frames"""
        w, h = self.video_properties.size
        for i in range(n):
            self.processing_state.proc.stdout.read(self.video_properties.depth * w * h)

        self.processing_state.pos += n

    def read_frame(self):
        """Reads the next frame from the file."""
        w, h = self.video_properties.size
        nbytes = self.video_properties.depth * w * h

        s = self.processing_state.proc.stdout.read(nbytes)

        if len(s) != nbytes:
            warnings.warn(
                (
                    "In file %s, %d bytes wanted but %d bytes read at frame index"
                    " %d (out of a total %d frames), at time %.02f/%.02f sec."
                    " Using the last valid frame instead."
                )
                % (
                    self.file_info.filename,
                    nbytes,
                    len(s),
                    self.processing_state.pos,
                    self.file_info.n_frames,
                    1.0 * self.processing_state.pos / self.video_properties.fps,
                    self.file_info.duration,
                ),
                UserWarning,
            )
            if not hasattr(self.processing_state, "last_read"):
                raise IOError(
                    (
                        "MoviePy error: failed to read the first frame of "
                        f"video file {self.file_info.filename}. That might mean that the file is "
                        "corrupted. That may also mean that you are using "
                        "a deprecated version of FFMPEG. On Ubuntu/Debian "
                        "for instance the version in the repos is deprecated. "
                        "Please update to a recent version from the website."
                    )
                )

            result = self.processing_state.last_read

        else:
            if hasattr(np, "frombuffer"):
                result = np.frombuffer(s, dtype="uint8")
            else:
                result = np.fromstring(s, dtype="uint8")
            result.shape = (h, w, len(s) // (w * h))  # reshape((h, w, len(s)//(w*h)))
            self.processing_state.last_read = result

        # We have to do this down here because `self.processing_state.pos` is used in the warning above
        self.processing_state.pos += 1

        return result

    def get_frame(self, t):
        """Read a file video frame at time t."""
        pos = self.get_frame_number(t) + 1

        # Initialize proc if it is not open
        if not self.processing_state.proc:
            print("Proc not detected")
            self.initialize(t)
            return self.processing_state.last_read

        if pos == self.processing_state.pos:
            return self.processing_state.last_read
        elif (pos < self.processing_state.pos) or (pos > self.processing_state.pos + 100):
            self.initialize(t)
            return self.processing_state.lastread
        else:
            self.skip_frames(pos - self.processing_state.pos - 1)
            result = self.read_frame()
            return result

    def get_frame_number(self, t):
        """Helper method to return the frame number at time ``t``"""
        return int(self.video_properties.fps * t + 0.00001)

    def close(self, delete_lastread=True):
        """Closes the reader terminating the process, if is still open."""
        if self.processing_state.proc:
            if self.processing_state.proc.poll() is None:
                self.processing_state.proc.terminate()
                self.processing_state.proc.stdout.close()
                self.processing_state.proc.stderr.close()
                self.processing_state.proc.wait()
            self.processing_state.proc = None
        if delete_lastread and hasattr(self.processing_state, "last_read"):
            del self.processing_state.last_read

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
