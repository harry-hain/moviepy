class FileInfo:
    def __init__(self, filename, infos, duration, ffmpeg_duration, n_frames, bitrate):
        self.filename = filename
        self.infos = infos
        self.duration = duration
        self.ffmpeg_duration = ffmpeg_duration
        self.n_frames = n_frames
        self.bitrate = bitrate
