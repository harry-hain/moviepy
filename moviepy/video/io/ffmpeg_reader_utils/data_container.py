class FileInfo:
    def __init__(self, filename, infos, duration, ffmpeg_duration, n_frames, bitrate):
        self.filename = filename
        self.infos = infos
        self.duration = duration
        self.ffmpeg_duration = ffmpeg_duration
        self.n_frames = n_frames
        self.bitrate = bitrate

class VideoProperties:
    def __init__(self, fps, size, rotation, target_resolution, resize_algo, pixel_format, depth, bufsize):
        self.fps = fps
        self.size = size
        self.rotation = rotation
        self.target_resolution = target_resolution
        self.resize_algo = resize_algo
        self.pixel_format = pixel_format
        self.depth = depth
        self.bufsize = bufsize

class ProcessingState:
    def __init__(self, proc=None, pos=0, lastread=None):
        self.proc = proc
        self.pos = pos
        self.lastread = lastread
