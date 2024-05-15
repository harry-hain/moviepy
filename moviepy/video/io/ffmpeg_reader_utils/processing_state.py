import warnings

import numpy as np


class ProcessingState:
    def __init__(self, proc=None, pos=0, last_read=None):
        self.proc = proc
        self.pos = pos
        self.last_read = last_read

    def close(self, delete_last_read=True):
        """Closes the reader terminating the process, if it is still open."""
        if self.proc:
            if self.proc.poll() is None:
                self.proc.terminate()
                self.proc.stdout.close()
                self.proc.stderr.close()
                self.proc.wait()
            self.proc = None
        if delete_last_read:
            self.last_read = None

    def skip_frames(self, size, depth, n=1):
        """Reads and throws away n frames"""
        w, h = size
        for i in range(n):
            self.proc.stdout.read(depth * w * h)
        self.pos += n

    def read_frame(self, size, depth, file_info, video_properties):
        """Reads the next frame from the file."""
        w, h = size
        nbytes = depth * w * h
        s = self.proc.stdout.read(nbytes)
        if len(s) != nbytes:
            warnings.warn(
                (
                    "In file %s, %d bytes wanted but %d bytes read at frame index"
                    " %d (out of a total %d frames), at time %.02f/%.02f sec."
                    " Using the last valid frame instead."
                )
                % (
                    file_info.filename,
                    nbytes,
                    len(s),
                    self.pos,
                    file_info.n_frames,
                    1.0 * self.pos / video_properties.fps,
                    file_info.duration,
                ),
                UserWarning,
            )
            if self.last_read is None:
                raise IOError(
                    (
                        "MoviePy error: failed to read the first frame of "
                        f"video file {file_info.filename}. That might mean that the file is "
                        "corrupted. That may also mean that you are using "
                        "a deprecated version of FFMPEG. On Ubuntu/Debian "
                        "for instance the version in the repos is deprecated. "
                        "Please update to a recent version from the website."
                    )
                )

            result = self.last_read

        else:
            if hasattr(np, "frombuffer"):
                result = np.frombuffer(s, dtype="uint8")
            else:
                result = np.fromstring(s, dtype="uint8")
            result.shape = (h, w, len(s) // (w * h))  # reshape((h, w, len(s)//(w*h)))
            self.last_read = result

        self.pos += 1
        return result

