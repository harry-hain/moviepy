import numpy as np
from moviepy.video.sub_clips.image_clip import ImageClip


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
            color = 0 if color is None else color
            super().__init__(np.tile(color, w * h).reshape((h, w)), is_mask=True, duration=duration)
        else:
            color = (0, 0, 0) if color is None else color
            super().__init__(np.tile(color, w * h).reshape((h, w, len(color))), is_mask=False, duration=duration)
