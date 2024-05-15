from moviepy.config import FFMPEG_BINARY


class FFMPEGCommandBuilder:
    def __init__(self, filename, pixel_format, size, resize_algo, start_time=0):
        self.filename = filename
        self.pixel_format = pixel_format
        self.size = size
        self.resize_algo = resize_algo
        self.start_time = start_time

    def build(self):
        i_arg = ["-i", self.filename]
        if self.start_time != 0:
            offset = min(1, self.start_time)
            i_arg = [
                "-ss", "%.06f" % (self.start_time - offset),
                "-i", self.filename,
                "-ss", "%.06f" % offset,
            ]

        cmd = [
            FFMPEG_BINARY,
            *i_arg,
            "-loglevel", "error",
            "-f", "image2pipe",
            "-vf", f"scale={self.size[0]}:{self.size[1]}",
            "-sws_flags", self.resize_algo,
            "-pix_fmt", self.pixel_format,
            "-vcodec", "rawvideo",
            "-"
        ]
        return cmd
