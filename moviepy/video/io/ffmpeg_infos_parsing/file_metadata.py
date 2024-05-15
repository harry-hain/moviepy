class FileMetadata:
    def __init__(self):
        self.result = {
            "duration": None,
            "bitrate": None,
            "start": None,
            "metadata": {},
            "inputs": [],
            "video_found": False,
            "video_n_frames": None,
            "video_duration": None,
            "audio_found": False,
            "audio_bitrate": None,
        }