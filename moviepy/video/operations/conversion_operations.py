import numpy as np
from moviepy.video.sub_clips.image_clip import ImageClip
from moviepy.decorators import convert_parameter_to_seconds

class ConversionOperations:
    def __init__(self, video_clip):
        self.video_clip = video_clip

    @convert_parameter_to_seconds(["t"])
    def to_ImageClip(self, t=0, with_mask=True, duration=None):
        """
        Returns an ImageClip made out of the clip's frame at time ``t``,
        which can be expressed in seconds (15.35), in (min, sec),
        in (hour, min, sec), or as a string: '01:03:05.35'.
        """
        new_clip = ImageClip(self.video_clip.get_frame(t), is_mask=self.video_clip.is_mask, duration=duration)
        if with_mask and self.video_clip.mask is not None:
            new_clip.mask = self.video_clip.mask.to_ImageClip(t)
        return new_clip

    def to_mask(self, canal=0):
        """Return a mask video clip made from the clip."""
        if self.video_clip.is_mask:
            return self.video_clip
        else:
            new_clip = self.video_clip.image_transform(lambda pic: 1.0 * pic[:, :, canal] / 255)
            new_clip.is_mask = True
            return new_clip

    def to_RGB(self):
        """Return a non-mask video clip made from the mask video clip."""
        if self.video_clip.is_mask:
            new_clip = self.video_clip.image_transform(
                lambda pic: np.dstack(3 * [255 * pic]).astype("uint8")
            )
            new_clip.is_mask = False
            return new_clip
        else:
            return self.video_clip
