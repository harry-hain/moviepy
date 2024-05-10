"""Implements VideoClip (base class for video clips) and its main subclasses:

- Animated clips:     VideoFileClip, ImageSequenceClip, BitmapClip
- Static image clips: ImageClip, ColorClip, TextClip,
"""

import copy as _copy

from moviepy.Clip import Clip
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
