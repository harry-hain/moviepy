# Assume necessary imports are made, such as numpy, proglog, etc.
from moviepy.decorators import convert_parameter_to_seconds, convert_masks_to_RGB, requires_duration, \
    use_clip_fps_by_default, convert_path_to_string
from moviepy.video.io.ffmpeg_writer import ffmpeg_write_video
from moviepy.video.io.gif_writers import (
    write_gif_with_image_io,
    write_gif_with_tempfiles,
    write_gif
)
import numpy as np
from imageio import imsave
from moviepy.tools import (
    extensions_dict,
    find_extension,
)
import proglog
import os
import copy as _copy

class ExportOperations:
    def __init__(self, clip):
        self.clip = clip


    def save_frame(self, filename, t=0, with_mask=True):
        im = self.clip.get_frame(t)
        if with_mask and self.clip.mask is not None:
            mask = 255 * self.clip.mask.get_frame(t)
            im = np.dstack([im, mask]).astype("uint8")
        else:
            im = im.astype("uint8")
        imsave(filename, im)

    @requires_duration
    @use_clip_fps_by_default
    @convert_masks_to_RGB
    @convert_path_to_string(["filename", "temp_audiofile", "temp_audiofile_path"])
    def write_videofile(self, filename, fps=None, codec=None, bitrate=None, audio=True,
                        audio_fps=44100, preset="medium", audio_nbytes=4, audio_codec=None,
                        audio_bitrate=None, audio_bufsize=2000, temp_audiofile=None,
                        temp_audiofile_path="", remove_temp=True, write_logfile=False,
                        threads=None, ffmpeg_params=None, logger="bar", pixel_format=None):
        logger = proglog.default_bar_logger(logger)
        ext = os.path.splitext(filename)[-1].lower()

        if codec is None:
            codec = extensions_dict[ext[1:]]['codec'][0]

        if audio_codec is None:
            audio_codec = 'libmp3lame' if ext not in ['.ogv', '.webm'] else 'libvorbis'

        audiofile = audio if isinstance(audio, str) else None
        make_audio = (audiofile is None) and audio and (self.clip.audio is not None)

        if make_audio:
            audio_ext = find_extension(audio_codec)
            audiofile = os.path.join(temp_audiofile_path, f"{os.path.basename(filename)}_TEMP_AUDIO.{audio_ext}")
            self.clip.audio.write_audiofile(
                audiofile,
                codec=audio_codec,
                bitrate=audio_bitrate,
                fps=audio_fps,
                nbytes=audio_nbytes,
                bufsize=audio_bufsize
            )

        ffmpeg_write_video(
            self.clip,
            filename,
            fps,
            codec,
            bitrate,
            preset=preset,
            write_logfile=write_logfile,
            audiofile=audiofile if make_audio else None,
            threads=threads,
            ffmpeg_params=ffmpeg_params,
            logger=logger,
            pixel_format=pixel_format
        )

        if remove_temp and make_audio:
            os.remove(audiofile)

    @requires_duration
    @use_clip_fps_by_default
    @convert_masks_to_RGB
    def write_images_sequence(self, name_format, fps=None, with_mask=True, logger="bar"):
        logger = proglog.default_bar_logger(logger)
        fps = fps or self.clip.fps
        duration = int(self.clip.duration)
        filenames = [name_format % i for i in range(0, duration, int(1/fps))]

        for i, filename in enumerate(filenames):
            self.save_frame(filename, t=i/fps, with_mask=with_mask)

        return filenames

    @requires_duration
    @convert_masks_to_RGB
    @convert_path_to_string("filename")
    def write_gif(self, filename, fps=None, program="imageio", opt="nq", fuzz=1, loop=0,
                  dispose=False, colors=None, tempfiles=False, logger="bar", pixel_format=None):
        logger = proglog.default_bar_logger(logger)
        if program == "imageio":
            write_gif_with_image_io(self.clip, filename, fps, opt, loop, colors, logger)
        elif tempfiles:
            write_gif_with_tempfiles(self.clip, filename, fps, program, opt, fuzz, loop, dispose, colors, logger, pixel_format)
        else:
            write_gif(self.clip, filename, fps, program, opt, fuzz, loop, dispose, colors, logger, pixel_format)

    def __deepcopy__(self, memo):
        # Return self to ensure all copies of the clip share the same ExportOperations instance
        return self