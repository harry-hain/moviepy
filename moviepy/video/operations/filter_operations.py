# filter_operations.py
from moviepy.video.compositing.concatenate import concatenate_videoclips

class FilterOperations:
    def __init__(self, video_clip):
        self.video_clip = video_clip

    def subfx(self, fx, start_time=0, end_time=None, **kwargs):
        """Apply a transformation to a part of the clip.

        Returns a new clip in which the function ``fun`` (clip->clip)
        has been applied to the subclip between times `start_time` and `end_time`
        (in seconds).

        Examples
        --------

        >>> # The scene between times t=3s and t=6s in ``clip`` will be
        >>> # be played twice slower in ``new_clip``
        >>> new_clip = clip.subapply(lambda c:c.multiply_speed(0.5) , 3,6)

        """
        left = None if (start_time == 0) else self.video_clip.subclip(0, start_time)
        center = self.video_clip.subclip(start_time, end_time).fx(fx, **kwargs)
        right = None if (end_time is None) else self.video_clip.subclip(start_time=end_time)

        clips = [clip for clip in [left, center, right] if clip is not None]
        return concatenate_videoclips(clips).with_start(self.video_clip.start)

    def image_transform(self, image_func, apply_to=None):
        """Modifies the images of a clip by replacing the frame `get_frame(t)` by
                another frame,  `image_func(get_frame(t))`.
                """
        apply_to = apply_to or []
        return self.video_clip.transform(lambda get_frame, t: image_func(get_frame(t)), apply_to)
