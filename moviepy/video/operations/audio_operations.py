from moviepy.decorators import outplace
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.compositing.CompositeVideoClip import clips_array
from moviepy.video.fx.rotate import rotate
from moviepy.video.VideoClip import VideoClip
from numbers import Real

class AudioOperations:
    def __init__(self, video_clip):
        self.video_clip = video_clip

    @outplace
    def without_audio(self):
        """Remove the clip's audio.

        Return a copy of the clip with audio set to None.
        """
        self.video_clip.audio = None

    @outplace
    def afx(self, fun, *args, **kwargs):
        """Transform the clip's audio.

        Return a new clip whose audio has been transformed by ``fun``.
        """
        self.video_clip.audio = self.video_clip.audio.fx(fun, *args, **kwargs)

    def __add__(self, other):
        if isinstance(other, VideoClip):
            is_clips_same_size = self.video_clip.size == other.size
            method = "chain" if is_clips_same_size else "compose"
            clips_list = [self.video_clip, other]
            return concatenate_videoclips(clips_list, method=method)
        return NotImplemented

    def __or__(self, other):
        """
        Implement the or (self | other) to produce a video with self and other
        placed side by side horizontally.
        """
        if isinstance(other, VideoClip):
            return clips_array([[self.video_clip, other]])
        return NotImplemented

    def __truediv__(self, other):
        """
        Implement division (self / other) to produce a video with self
        placed on top of other.
        """
        if isinstance(other, VideoClip):
            return clips_array([[self.video_clip], [other]])
        return NotImplemented

    def __matmul__(self, n):
        """Rotate the video by n degrees."""
        if not isinstance(n, Real):
            return NotImplemented
        return rotate(self.video_clip, n)

    def __and__(self, mask):
        """Apply a mask to the video clip."""
        return self.video_clip.with_mask(mask)
