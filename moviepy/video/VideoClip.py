"""Implements VideoClip (base class for video clips) and its main subclasses:

- Animated clips:     VideoFileClip, ImageSequenceClip, BitmapClip
- Static image clips: ImageClip, ColorClip, TextClip,
"""

import copy as _copy
import os
import subprocess as sp
import tempfile

import numpy as np
from imageio import imread

from moviepy.Clip import Clip
from moviepy.config import IMAGEMAGICK_BINARY
from moviepy.decorators import (
    add_mask_if_none,
    apply_to_mask,
    convert_masks_to_RGB,
    convert_parameter_to_seconds,
    convert_path_to_string,
    outplace,
    requires_duration,
    requires_fps,
    use_clip_fps_by_default,
)
from moviepy.tools import (
    cross_platform_popen_params,
    subprocess_call,
)

from moviepy.video.operations.export_operations import ExportOperations
from moviepy.video.operations.clip_operations import ClipOperations
from moviepy.video.operations.compositing_operations import CompositingOperations
from moviepy.video.operations.conversion_operations import ConversionOperations
from moviepy.video.operations.audio_operations import AudioOperations
from moviepy.video.operations.filter_operations import FilterOperations

class VideoClip(Clip):
    """Base class for video clips.

    See ``VideoFileClip``, ``ImageClip`` etc. for more user-friendly classes.


    Parameters
    ----------

    is_mask
      `True` if the clip is going to be used as a mask.


    Attributes
    ----------

    size
      The size of the clip, (width,height), in pixels.

    w, h
      The width and height of the clip, in pixels.

    is_mask
      Boolean set to `True` if the clip is a mask.

    make_frame
      A function ``t-> frame at time t`` where ``frame`` is a
      w*h*3 RGB array.

    mask (default None)
      VideoClip mask attached to this clip. If mask is ``None``,
                The video clip is fully opaque.

    audio (default None)
      An AudioClip instance containing the audio of the video clip.

    pos
      A function ``t->(x,y)`` where ``x,y`` is the position
      of the clip when it is composed with other clips.
      See ``VideoClip.set_pos`` for more details

    relative_pos
      See variable ``pos``.

    layer
      Indicates which clip is rendered on top when two clips overlap in
      a CompositeVideoClip. The highest number is rendered on top.
      Default is 0.

    """

    def __init__(
        self, make_frame=None, is_mask=False, duration=None, has_constant_size=True
    ):
        super().__init__()
        self.mask = None
        self.audio = None
        self.pos = lambda t: (0, 0)
        self.relative_pos = False
        self.layer = 0
        if make_frame:
            self.make_frame = make_frame
            self.size = self.get_frame(0).shape[:2][::-1]
        self.is_mask = is_mask
        self.has_constant_size = has_constant_size
        if duration is not None:
            self.duration = duration
            self.end = duration
        self.export_ops = ExportOperations(self)
        self.clip_ops = ClipOperations(self)
        self.compositing_ops = CompositingOperations(self)
        self.conversion_ops = ConversionOperations(self)
        self.audio_ops = AudioOperations(self)
        self.filter_ops = FilterOperations(self)

    @property
    def w(self):
        """Returns the width of the video."""
        return self.size[0]

    @property
    def h(self):
        """Returns the height of the video."""
        return self.size[1]

    @property
    def aspect_ratio(self):
        """Returns the aspect ratio of the video."""
        return self.w / float(self.h)

    @property
    @requires_duration
    @requires_fps
    def n_frames(self):
        """Returns the number of frames of the video."""
        return int(self.duration * self.fps)

    def __copy__(self):
        """Mixed copy of the clip.

        Returns a shallow copy of the clip whose mask and audio will
        be shallow copies of the clip's mask and audio if they exist.

        This method is intensively used to produce new clips every time
        there is an outplace transformation of the clip (clip.resize,
        clip.subclip, etc.)

        Acts like a deepcopy except for the fact that readers and other
        possible unpickleables objects are not copied.
        """
        cls = self.__class__
        new_clip = cls.__new__(cls)
        for attr in self.__dict__:
            value = getattr(self, attr)
            if attr in ("mask", "audio"):
                value = _copy.copy(value)
            setattr(new_clip, attr, value)
        return new_clip

    copy = __copy__

    # ===============================================================
    # EXPORT OPERATIONS

    @convert_parameter_to_seconds(["t"])
    @convert_masks_to_RGB
    def save_frame(self, filename, t=0, with_mask=True):
        return self.export_ops.save_frame(filename, t, with_mask)

    @requires_duration
    @use_clip_fps_by_default
    @convert_masks_to_RGB
    @convert_path_to_string(["filename", "temp_audiofile", "temp_audiofile_path"])
    def write_videofile(self, filename, fps=None, codec=None, bitrate=None, audio=True,
                        audio_fps=44100, preset="medium", audio_nbytes=4, audio_codec=None,
                        audio_bitrate=None, audio_bufsize=2000, temp_audiofile=None,
                        temp_audiofile_path="", remove_temp=True, write_logfile=False,
                        threads=None, ffmpeg_params=None, logger="bar", pixel_format=None):
        return self.export_ops.write_videofile(filename, fps, codec, bitrate, audio,
                                               audio_fps, preset, audio_nbytes, audio_codec,
                                               audio_bitrate, audio_bufsize, temp_audiofile,
                                               temp_audiofile_path, remove_temp, write_logfile,
                                               threads, ffmpeg_params, logger, pixel_format)


    @requires_duration
    @use_clip_fps_by_default
    @convert_masks_to_RGB
    def write_images_sequence(self, name_format, fps=None, with_mask=True, logger="bar"):
        return self.export_ops.write_images_sequence(name_format, fps, with_mask, logger)


    @requires_duration
    @convert_masks_to_RGB
    @convert_path_to_string("filename")
    def write_gif(self, filename, fps=None, program="imageio", opt="nq", fuzz=1,
                  loop=0, dispose=False, colors=None, tempfiles=False, logger="bar",
                  pixel_format=None):
        return self.export_ops.write_gif(filename, fps, program, opt, fuzz, loop,
                                         dispose, colors, tempfiles, logger, pixel_format)


    # -----------------------------------------------------------------
    # F I L T E R I N G

    def subfx(self, fx, start_time=0, end_time=None, **kwargs):
        return self.filter_ops.subfx(fx, start_time, end_time, **kwargs)

    # IMAGE FILTERS

    def image_transform(self, image_func, apply_to=None):
        return self.filter_ops.image_transform(image_func, apply_to)

    # --------------------------------------------------------------
    # C O M P O S I T I N G

    def fill_array(self, pre_array, shape=(0, 0)):
        return CompositingOperations.fill_array(pre_array, shape)

    def blit_on(self, picture, t):
        return self.compositing_ops.blit_on(picture, t)

    def add_mask(self):
        return self.compositing_ops.add_mask()

    def on_color(self, size=None, color=(0, 0, 0), pos=None, col_opacity=None):
        return self.compositing_ops.on_color(size, color, pos, col_opacity)

    @outplace
    def with_make_frame(self, make_frame_function):
        return self.clip_ops.with_make_frame(make_frame_function)

    @outplace
    def with_audio(self, audio_clip):
        return self.clip_ops.with_audio(audio_clip)

    @outplace
    def with_mask(self, mask):
        return self.clip_ops.with_mask(mask)

    @add_mask_if_none
    @outplace
    def with_opacity(self, opacity):
        return self.clip_ops.with_opacity(opacity)

    @apply_to_mask
    @outplace
    def with_position(self, position, relative=False):
        return self.clip_ops.with_position(position, relative)

    @apply_to_mask
    @outplace
    def with_layer(self, layer):
        return self.clip_ops.with_layer(layer)

    # --------------------------------------------------------------
    # CONVERSIONS TO OTHER TYPES

    @convert_parameter_to_seconds(["t"])
    def to_ImageClip(self, t=0, with_mask=True, duration=None):
        return self.conversion_ops.to_ImageClip(t, with_mask, duration)

    def to_mask(self, canal=0):
        return self.conversion_ops.to_mask(canal)

    def to_RGB(self):
        return self.conversion_ops.to_RGB()

    # ----------------------------------------------------------------
    # Audio

    @outplace
    def without_audio(self, *args, **kwargs):
        return self.audio_ops.without_audio(*args, **kwargs)

    @outplace
    def afx(self, *args, **kwargs):
        return self.audio_ops.afx(*args, **kwargs)

    def __add__(self, other):
        return self.audio_ops.__add__(other)

    def __or__(self, other):
        return self.audio_ops.__or__(other)

    def __truediv__(self, other):
        return self.audio_ops.__truediv__(other)

    def __matmul__(self, n):
        return self.audio_ops.__matmul__(n)

    def __and__(self, mask):
        return self.with_mask(mask)


class DataVideoClip(VideoClip):
    """
    Class of video clips whose successive frames are functions
    of successive datasets

    Parameters
    ----------
    data
      A list of datasets, each dataset being used for one frame of the clip

    data_to_frame
      A function d -> video frame, where d is one element of the list `data`

    fps
      Number of frames per second in the animation
    """

    def __init__(self, data, data_to_frame, fps, is_mask=False, has_constant_size=True):
        self.data = data
        self.data_to_frame = data_to_frame
        self.fps = fps

        def make_frame(t):
            return self.data_to_frame(self.data[int(self.fps * t)])

        VideoClip.__init__(
            self,
            make_frame,
            is_mask=is_mask,
            duration=1.0 * len(data) / fps,
            has_constant_size=has_constant_size,
        )


class UpdatedVideoClip(VideoClip):
    """
    Class of clips whose make_frame requires some objects to
    be updated. Particularly practical in science where some
    algorithm needs to make some steps before a new frame can
    be generated.

    UpdatedVideoClips have the following make_frame:

    >>> def make_frame(t):
    >>>     while self.world.clip_t < t:
    >>>         world.update() # updates, and increases world.clip_t
    >>>     return world.to_frame()

    Parameters
    ----------

    world
      An object with the following attributes:
      - world.clip_t: the clip's time corresponding to the world's state.
      - world.update() : update the world's state, (including increasing
      world.clip_t of one time step).
      - world.to_frame() : renders a frame depending on the world's state.

    is_mask
      True if the clip is a WxH mask with values in 0-1

    duration
      Duration of the clip, in seconds

    """

    def __init__(self, world, is_mask=False, duration=None):
        self.world = world

        def make_frame(t):
            while self.world.clip_t < t:
                world.update()
            return world.to_frame()

        VideoClip.__init__(
            self, make_frame=make_frame, is_mask=is_mask, duration=duration
        )


"""---------------------------------------------------------------------

    ImageClip (base class for all 'static clips') and its subclasses
    ColorClip and TextClip.
    I would have liked to put these in a separate file but Python is bad
    at cyclic imports.

---------------------------------------------------------------------"""


class ImageClip(VideoClip):
    """Class for non-moving VideoClips.

    A video clip originating from a picture. This clip will simply
    display the given picture at all times.

    Examples
    --------

    >>> clip = ImageClip("myHouse.jpeg")
    >>> clip = ImageClip( someArray ) # a Numpy array represent

    Parameters
    ----------

    img
      Any picture file (png, tiff, jpeg, etc.) as a string or a path-like object,
      or any array representing an RGB image (for instance a frame from a VideoClip).

    is_mask
      Set this parameter to `True` if the clip is a mask.

    transparent
      Set this parameter to `True` (default) if you want the alpha layer
      of the picture (if it exists) to be used as a mask.

    Attributes
    ----------

    img
      Array representing the image of the clip.

    """

    def __init__(
        self, img, is_mask=False, transparent=True, fromalpha=False, duration=None
    ):
        VideoClip.__init__(self, is_mask=is_mask, duration=duration)

        if not isinstance(img, np.ndarray):
            # img is a string or path-like object, so read it in from disk
            img = imread(img)

        if len(img.shape) == 3:  # img is (now) a RGB(a) numpy array
            if img.shape[2] == 4:
                if fromalpha:
                    img = 1.0 * img[:, :, 3] / 255
                elif is_mask:
                    img = 1.0 * img[:, :, 0] / 255
                elif transparent:
                    self.mask = ImageClip(1.0 * img[:, :, 3] / 255, is_mask=True)
                    img = img[:, :, :3]
            elif is_mask:
                img = 1.0 * img[:, :, 0] / 255

        # if the image was just a 2D mask, it should arrive here
        # unchanged
        self.make_frame = lambda t: img
        self.size = img.shape[:2][::-1]
        self.img = img

    def transform(self, func, apply_to=None, keep_duration=True):
        """General transformation filter.

        Equivalent to VideoClip.transform. The result is no more an
        ImageClip, it has the class VideoClip (since it may be animated)
        """
        if apply_to is None:
            apply_to = []
        # When we use transform on an image clip it may become animated.
        # Therefore the result is not an ImageClip, just a VideoClip.
        new_clip = VideoClip.transform(
            self, func, apply_to=apply_to, keep_duration=keep_duration
        )
        new_clip.__class__ = VideoClip
        return new_clip

    @outplace
    def image_transform(self, image_func, apply_to=None):
        """Image-transformation filter.

        Does the same as VideoClip.image_transform, but for ImageClip the
        transformed clip is computed once and for all at the beginning,
        and not for each 'frame'.
        """
        if apply_to is None:
            apply_to = []
        arr = image_func(self.get_frame(0))
        self.size = arr.shape[:2][::-1]
        self.make_frame = lambda t: arr
        self.img = arr

        for attr in apply_to:
            a = getattr(self, attr, None)
            if a is not None:
                new_a = a.image_transform(image_func)
                setattr(self, attr, new_a)

    @outplace
    def time_transform(self, time_func, apply_to=None, keep_duration=False):
        """Time-transformation filter.

        Applies a transformation to the clip's timeline
        (see Clip.time_transform).

        This method does nothing for ImageClips (but it may affect their
        masks or their audios). The result is still an ImageClip.
        """
        if apply_to is None:
            apply_to = ["mask", "audio"]
        for attr in apply_to:
            a = getattr(self, attr, None)
            if a is not None:
                new_a = a.time_transform(time_func)
                setattr(self, attr, new_a)


class ColorClip(ImageClip):
    """An ImageClip showing just one color.

    Parameters
    ----------

    size
      Size (width, height) in pixels of the clip.

    color
      If argument ``is_mask`` is False, ``color`` indicates
      the color in RGB of the clip (default is black). If `is_mask``
      is True, ``color`` must be  a float between 0 and 1 (default is 1)

    is_mask
      Set to true if the clip will be used as a mask.

    """

    def __init__(self, size, color=None, is_mask=False, duration=None):
        w, h = size

        if is_mask:
            shape = (h, w)
            if color is None:
                color = 0
            elif not np.isscalar(color):
                raise Exception("Color has to be a scalar when mask is true")
        else:
            if color is None:
                color = (0, 0, 0)
            elif not hasattr(color, "__getitem__"):
                raise Exception("Color has to contain RGB of the clip")
            elif isinstance(color, str):
                raise Exception(
                    "Color cannot be string. Color has to contain RGB of the clip"
                )
            shape = (h, w, len(color))

        super().__init__(
            np.tile(color, w * h).reshape(shape), is_mask=is_mask, duration=duration
        )


class TextClip(ImageClip):
    """Class for autogenerated text clips.

    Creates an ImageClip originating from a script-generated text image.
    Requires ImageMagick.

    Parameters
    ----------

    text
      A string of the text to write. Can be replaced by argument
      ``filename``.

    filename
      The name of a file in which there is the text to write,
      as a string or a path-like object.
      Can be provided instead of argument ``txt``

    size
      Size of the picture in pixels. Can be auto-set if
      method='label', but mandatory if method='caption'.
      the height can be None, it will then be auto-determined.

    bg_color
      Color of the background. See ``TextClip.list('color')``
      for a list of acceptable names.

    color
      Color of the text. See ``TextClip.list('color')`` for a
      list of acceptable names.

    font
      Name of the font to use. See ``TextClip.list('font')`` for
      the list of fonts you can use on your computer.

    stroke_color
      Color of the stroke (=contour line) of the text. If ``None``,
      there will be no stroke.

    stroke_width
      Width of the stroke, in pixels. Can be a float, like 1.5.

    method
      Either 'label' (default, the picture will be autosized so as to fit
      exactly the size) or 'caption' (the text will be drawn in a picture
      with fixed size provided with the ``size`` argument). If `caption`,
      the text will be wrapped automagically (sometimes it is buggy, not
      my fault, complain to the ImageMagick crew) and can be aligned or
      centered (see parameter ``align``).

    kerning
      Changes the default spacing between letters. For
      instance ``kerning=-1`` will make the letters 1 pixel nearer from
      ach other compared to the default spacing.

    align
      center | East | West | South | North . Will only work if ``method``
      is set to ``caption``

    transparent
      ``True`` (default) if you want to take into account the
      transparency in the image.
    """

    @convert_path_to_string("filename")
    def __init__(
        self,
        text=None,
        filename=None,
        size=None,
        color="black",
        bg_color="transparent",
        font_size=None,
        font="Courier",
        stroke_color=None,
        stroke_width=1,
        method="label",
        kerning=None,
        align="center",
        interline=None,
        tempfilename=None,
        temptxt=None,
        transparent=True,
        remove_temp=True,
        print_cmd=False,
    ):
        if text is not None:
            if temptxt is None:
                temptxt_fd, temptxt = tempfile.mkstemp(suffix=".txt")
                try:  # only in Python3 will this work
                    os.write(temptxt_fd, bytes(text, "UTF8"))
                except TypeError:  # oops, fall back to Python2
                    os.write(temptxt_fd, text)
                os.close(temptxt_fd)
            text = "@" + temptxt
        elif filename is not None:
            # use a file instead of a text.
            text = "@" + filename
        else:
            raise ValueError(
                "You must provide either 'text' or 'filename' arguments to TextClip"
            )

        if size is not None:
            size = (
                "" if size[0] is None else str(size[0]),
                "" if size[1] is None else str(size[1]),
            )

        cmd = [
            IMAGEMAGICK_BINARY,
            "-background",
            bg_color,
            "-fill",
            color,
            "-font",
            font,
        ]

        if font_size is not None:
            cmd += ["-pointsize", "%d" % font_size]
        if kerning is not None:
            cmd += ["-kerning", "%0.1f" % kerning]
        if stroke_color is not None:
            cmd += ["-stroke", stroke_color, "-strokewidth", "%.01f" % stroke_width]
        if size is not None:
            cmd += ["-size", "%sx%s" % (size[0], size[1])]
        if align is not None:
            cmd += ["-gravity", align]
        if interline is not None:
            cmd += ["-interline-spacing", "%d" % interline]

        if tempfilename is None:
            tempfile_fd, tempfilename = tempfile.mkstemp(suffix=".png")
            os.close(tempfile_fd)

        cmd += [
            "%s:%s" % (method, text),
            "-type",
            "truecolormatte",
            "PNG32:%s" % tempfilename,
        ]

        if print_cmd:
            print(" ".join(cmd))

        try:
            subprocess_call(cmd, logger=None)
        except (IOError, OSError) as err:
            error = (
                f"MoviePy Error: creation of {filename} failed because of the "
                f"following error:\n\n{err}.\n\n."
                "This error can be due to the fact that ImageMagick "
                "is not installed on your computer, or (for Windows "
                "users) that you didn't specify the path to the "
                "ImageMagick binary. Check the documentation."
            )
            raise IOError(error)

        ImageClip.__init__(self, tempfilename, transparent=transparent)
        self.text = text
        self.color = color
        self.stroke_color = stroke_color

        if remove_temp:
            if tempfilename is not None and os.path.exists(tempfilename):
                os.remove(tempfilename)
            if temptxt is not None and os.path.exists(temptxt):
                os.remove(temptxt)

    @staticmethod
    def list(arg):
        """Returns a list of all valid entries for the ``font`` or ``color`` argument of
        ``TextClip``.
        """
        popen_params = cross_platform_popen_params(
            {"stdout": sp.PIPE, "stderr": sp.DEVNULL, "stdin": sp.DEVNULL}
        )

        process = sp.Popen(
            [IMAGEMAGICK_BINARY, "-list", arg], encoding="utf-8", **popen_params
        )
        result = process.communicate()[0]
        lines = result.splitlines()

        if arg == "font":
            # Slice removes first 8 characters: "  Font: "
            return [line[8:] for line in lines if line.startswith("  Font:")]
        elif arg == "color":
            # Each line is of the format "aqua  srgb(0,255,255)  SVG" so split
            # on space and take the first item to get the color name.
            # The first 5 lines are header information, not colors, so ignore
            return [line.split(" ")[0] for line in lines[5:]]
        else:
            raise Exception("MoviePy Error: Argument must equal 'font' or 'color'")

    @staticmethod
    def search(string, arg):
        """Returns the of all valid entries which contain ``string`` for the
        argument ``arg`` of ``TextClip``, for instance

        >>> # Find all the available fonts which contain "Courier"
        >>> print(TextClip.search('Courier', 'font'))
        """
        string = string.lower()
        names_list = TextClip.list(arg)
        return [name for name in names_list if string in name.lower()]


class BitmapClip(VideoClip):
    """Clip made of color bitmaps. Mainly designed for testing purposes."""

    DEFAULT_COLOR_DICT = {
        "R": (255, 0, 0),
        "G": (0, 255, 0),
        "B": (0, 0, 255),
        "O": (0, 0, 0),
        "W": (255, 255, 255),
        "A": (89, 225, 62),
        "C": (113, 157, 108),
        "D": (215, 182, 143),
        "E": (57, 26, 252),
        "F": (225, 135, 33),
    }

    @convert_parameter_to_seconds(["duration"])
    def __init__(
        self, bitmap_frames, *, fps=None, duration=None, color_dict=None, is_mask=False
    ):
        """Creates a VideoClip object from a bitmap representation. Primarily used
        in the test suite.

        Parameters
        ----------

        bitmap_frames
          A list of frames. Each frame is a list of strings. Each string
          represents a row of colors. Each color represents an (r, g, b) tuple.
          Example input (2 frames, 5x3 pixel size)::

              [["RRRRR",
                "RRBRR",
                "RRBRR"],
               ["RGGGR",
                "RGGGR",
                "RGGGR"]]

        fps
          The number of frames per second to display the clip at. `duration` will
          calculated from the total number of frames. If both `fps` and `duration`
          are set, `duration` will be ignored.

        duration
          The total duration of the clip. `fps` will be calculated from the total
          number of frames. If both `fps` and `duration` are set, `duration` will
          be ignored.

        color_dict
          A dictionary that can be used to set specific (r, g, b) values that
          correspond to the letters used in ``bitmap_frames``.
          eg ``{"A": (50, 150, 150)}``.

          Defaults to::

              {
                "R": (255, 0, 0),
                "G": (0, 255, 0),
                "B": (0, 0, 255),
                "O": (0, 0, 0),  # "O" represents black
                "W": (255, 255, 255),
                # "A", "C", "D", "E", "F" represent arbitrary colors
                "A": (89, 225, 62),
                "C": (113, 157, 108),
                "D": (215, 182, 143),
                "E": (57, 26, 252),
              }

        is_mask
          Set to ``True`` if the clip is going to be used as a mask.
        """
        assert fps is not None or duration is not None

        self.color_dict = color_dict if color_dict else self.DEFAULT_COLOR_DICT

        frame_list = []
        for input_frame in bitmap_frames:
            output_frame = []
            for row in input_frame:
                output_frame.append([self.color_dict[color] for color in row])
            frame_list.append(np.array(output_frame))

        frame_array = np.array(frame_list)
        self.total_frames = len(frame_array)

        if fps is None:
            fps = self.total_frames / duration
        else:
            duration = self.total_frames / fps

        VideoClip.__init__(
            self,
            make_frame=lambda t: frame_array[int(t * fps)],
            is_mask=is_mask,
            duration=duration,
        )
        self.fps = fps

    def to_bitmap(self, color_dict=None):
        """Returns a valid bitmap list that represents each frame of the clip.
        If `color_dict` is not specified, then it will use the same `color_dict`
        that was used to create the clip.
        """
        color_dict = color_dict or self.color_dict

        bitmap = []
        for frame in self.iter_frames():
            bitmap.append([])
            for line in frame:
                bitmap[-1].append("")
                for pixel in line:
                    letter = list(color_dict.keys())[
                        list(color_dict.values()).index(tuple(pixel))
                    ]
                    bitmap[-1][-1] += letter

        return bitmap
