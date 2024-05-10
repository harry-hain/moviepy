from moviepy.video.VideoClip import VideoClip


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
