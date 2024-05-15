import numpy as np
import warnings


def read_bytes(proc, nbytes):
    """
    Safely read nbytes from the ffmpeg process, handling short reads.
    """
    data = proc.stdout.read(nbytes)
    if len(data) != nbytes:
        return None
    return data


class FrameProcessor:
    def __init__(self, size, depth):
        self.size = size
        self.depth = depth

    def read_frame(self, proc):
        """
        Reads the next frame from the ffmpeg process stdout.
        """
        frame_data = read_bytes(proc, self.calculate_nbytes())
        if frame_data is None:
            warnings.warn(
                f"In file, {self.calculate_nbytes()} bytes wanted but fewer bytes read. Using the last valid frame instead.",
                UserWarning)
            return None  # This will need to be handled by the caller.
        return self.convert_to_image(frame_data)

    def skip_frames(self, proc, n=1):
        """
        Skips n frames in the ffmpeg process stdout.
        """
        nbytes = self.calculate_nbytes()
        for _ in range(n):
            skipped_data = read_bytes(proc, nbytes)
            if skipped_data is None:
                warnings.warn(f"Failed to skip {n} frames; fewer bytes read than expected.", UserWarning)
                break  # Stop skipping if we run out of data.

    def convert_to_image(self, raw_data):
        """
        Converts raw bytes into an image.
        """
        if hasattr(np, "frombuffer"):
            result = np.frombuffer(raw_data, dtype="uint8")
        else:
            result = np.fromstring(raw_data, dtype="uint8")
        result.shape = (self.size[1], self.size[0], self.depth)
        return result

    def calculate_nbytes(self):
        """
        Calculate the number of bytes to read per frame based on dimensions and depth.
        """
        w, h = self.size
        return self.depth * w * h
