from moviepy.video.io.ffmpeg_reader_utils.file_info import FileInfo
from moviepy.video.io.ffmpeg_reader_utils.processing_state import ProcessingState
from moviepy.video.io.ffmpeg_reader_utils.video_properties import VideoProperties


class FFMPEG_VideoReaderInitialiser:
    def __init__(self, filename, decode_file, print_infos, bufsize, pixel_format, check_duration, target_resolution, resize_algo, fps_source):
        self.filename = filename
        self.decode_file = decode_file
        self.print_infos = print_infos
        self.bufsize = bufsize
        self.pixel_format = pixel_format
        self.check_duration = check_duration
        self.target_resolution = target_resolution
        self.resize_algo = resize_algo
        self.fps_source = fps_source

    def initialize(self):
        infos = FileInfo.ffmpeg_parse_infos(
            self.filename,
            check_duration=self.check_duration,
            fps_source=self.fps_source,
            decode_file=self.decode_file,
            print_infos=self.print_infos,
        )

        # Initialise FileInfo container
        file_info = FileInfo(
            filename=self.filename,
            infos=infos,
            duration=infos["video_duration"],
            ffmpeg_duration=infos["duration"],
            n_frames=infos["video_n_frames"],
            bitrate=infos["video_bitrate"]
        )

        # Initialise VideoProperties container
        size = infos["video_size"]
        rotation = abs(infos.get("video_rotation", 0))

        video_properties = VideoProperties(
            fps=infos["video_fps"],
            size=size,
            rotation=rotation,
            target_resolution=self.target_resolution,
            resize_algo=self.resize_algo,
            pixel_format=self.pixel_format,
            depth=None,
            bufsize=self.bufsize
        )
        video_properties.initialize()

        # Initialise ProcessingState container
        processing_state = ProcessingState()

        return file_info, video_properties, processing_state
