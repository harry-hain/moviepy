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
