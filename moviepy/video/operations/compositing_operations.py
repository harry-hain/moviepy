# compositing_operations.py
import numpy as np
from moviepy.video.VideoClip import ColorClip, ImageClip, VideoClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.tools.drawing import blit

class CompositingOperations:
    def __init__(self, video_clip):
        self.video_clip = video_clip

    def blit_on(self, picture, t):
        """Returns the result of the blit of the clip's frame at time `t`
        on the given `picture`, the position of the clip being given
        by the clip's ``pos`` attribute. Meant for compositing.
        """
        frame = self.video_clip.get_frame(t).astype("uint8")
        pos = self.video_clip.pos(t)
        return blit(frame, picture, pos, mask=self.video_clip.mask.get_frame(t) if self.video_clip.mask else None)

    def add_mask(self):
        """Add a mask VideoClip to the VideoClip.

        Returns a copy of the clip with a completely opaque mask
        (made of ones). This makes computations slower compared to
        having a None mask but can be useful in many cases. Choose

        Set ``constant_size`` to  `False` for clips with moving
        image size.
        """
        if self.video_clip.has_constant_size:
            mask = ColorClip(self.video_clip.size, 1.0, is_mask=True)
            self.video_clip.mask = mask.with_duration(self.video_clip.duration)
        else:
            def make_frame(t):
                return np.ones(self.video_clip.get_frame(t).shape[:2], dtype=float)
            self.video_clip.mask = VideoClip(is_mask=True, make_frame=make_frame).with_duration(self.video_clip.duration)

    def on_color(self, size=None, color=(0, 0, 0), pos=None, col_opacity=None):
        """Place the clip on a colored background.

        Returns a clip made of the current clip overlaid on a color
        clip of a possibly bigger size. Can serve to flatten transparent
        clips.

        Parameters
        ----------

        size
          Size (width, height) in pixels of the final clip.
          By default it will be the size of the current clip.

        color
          Background color of the final clip ([R,G,B]).

        pos
          Position of the clip in the final clip. 'center' is the default

        col_opacity
          Parameter in 0..1 indicating the opacity of the colored
          background.
        """
        if size is None:
            size = self.video_clip.size
        if pos is None:
            pos = "center"
        background_clip = ColorClip(size, color, duration=self.video_clip.duration)
        if col_opacity is not None:
            background_clip = background_clip.with_opacity(col_opacity)
        return CompositeVideoClip([background_clip, self.video_clip.set_pos(pos)])

    @staticmethod
    def fill_array(pre_array, shape=(0, 0)):
        """Resizes the array to the specified shape by padding with zeros or slicing.
        Parameters:
        pre_array (np.ndarray): The input array to resize.
        shape (tuple): The desired shape (height, width) as a tuple.
        Returns:
        np.ndarray: The resized array.
        """
        current_shape = pre_array.shape
        new_shape = (max(shape[0], current_shape[0]), max(shape[1], current_shape[1]))
        padded_array = np.zeros(new_shape, dtype=pre_array.dtype)

        # Compute slicing indices
        vertical_start = (new_shape[0] - current_shape[0]) // 2
        horizontal_start = (new_shape[1] - current_shape[1]) // 2

        padded_array[
            vertical_start:vertical_start + current_shape[0],
            horizontal_start:horizontal_start + current_shape[1]
        ] = pre_array

        # If the requested shape is smaller than the current shape, slice the padded array
        return padded_array[:shape[0], :shape[1]]