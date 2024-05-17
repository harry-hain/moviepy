def get_size_with_rotation(size, rotation):
    if rotation in [90, 270]:
        return [size[1], size[0]]
    return size


def get_resized_target_resolution(size, target_resolution):
    if None in target_resolution:
        ratio = 1
        for idx, target in enumerate(target_resolution):
            if target:
                ratio = target / size[idx]
        return int(size[0] * ratio), int(size[1] * ratio)
    return target_resolution


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

    def initialize(self):
        self.size = get_size_with_rotation(self.size, self.rotation)
        if self.target_resolution:
            self.size = get_resized_target_resolution(self.size, self.target_resolution)
        self.depth = 4 if self.pixel_format[-1] == "a" else 3
        if self.bufsize is None:
            w, h = self.size
            self.bufsize = self.depth * w * h + 100

    def get_frame_number(self, t):
        """Helper method to return the frame number at time ``t``"""
        return int(self.fps * t + 0.00001)
