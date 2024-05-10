import numpy as np
import os
import proglog
from imageio import imsave
from moviepy.video.io.ffmpeg_writer import ffmpeg_write_video
from moviepy.video.io.gif_writers import (
    write_gif_with_image_io,
    write_gif_with_tempfiles,
    write_gif
)
from moviepy.tools import (
    extensions_dict,
    find_extension
)


class ExportOperations:
    def __init__(self, clip):
        self.clip = clip

    def save_frame(self, filename, t=0, with_mask=True):
        """Save a clip's frame to an image file.

        Saves the frame of clip corresponding to time ``t`` in ``filename``.
        ``t`` can be expressed in seconds (15.35), in (min, sec),
        in (hour, min, sec), or as a string: '01:03:05.35'.

        Parameters
        ----------

        filename : str
          Name of the file in which the frame will be stored.

        t : float or tuple or str, optional
          Moment of the frame to be saved. As default, the first frame will be
          saved.

        with_mask : bool, optional
          If is ``True`` the mask is saved in the alpha layer of the picture
          (only works with PNGs).
        """
        im = self.clip.get_frame(t)
        if with_mask and self.clip.mask is not None:
            mask = 255 * self.clip.mask.get_frame(t)
            im = np.dstack([im, mask]).astype("uint8")
        else:
            im = im.astype("uint8")
        imsave(filename, im)

    def write_videofile(self, filename, fps=None, codec=None, bitrate=None, audio=True,
                        audio_fps=44100, preset="medium", audio_nbytes=4, audio_codec=None,
                        audio_bitrate=None, audio_bufsize=2000, temp_audiofile=None,
                        temp_audiofile_path="", remove_temp=True, write_logfile=False,
                        threads=None, ffmpeg_params=None, logger="bar", pixel_format=None):
        """Write the clip to a videofile.

        Parameters
        ----------

        filename
          Name of the video file to write in, as a string or a path-like object.
          The extension must correspond to the "codec" used (see below),
          or simply be '.avi' (which will work with any codec).

        fps
          Number of frames per second in the resulting video file. If None is
          provided, and the clip has an fps attribute, this fps will be used.

        codec
          Codec to use for image encoding. Can be any codec supported
          by ffmpeg. If the filename is has extension '.mp4', '.ogv', '.webm',
          the codec will be set accordingly, but you can still set it if you
          don't like the default. For other extensions, the output filename
          must be set accordingly.

          Some examples of codecs are:

          - ``'libx264'`` (default codec for file extension ``.mp4``)
            makes well-compressed videos (quality tunable using 'bitrate').
          - ``'mpeg4'`` (other codec for extension ``.mp4``) can be an alternative
            to ``'libx264'``, and produces higher quality videos by default.
          - ``'rawvideo'`` (use file extension ``.avi``) will produce
            a video of perfect quality, of possibly very huge size.
          - ``png`` (use file extension ``.avi``) will produce a video
            of perfect quality, of smaller size than with ``rawvideo``.
          - ``'libvorbis'`` (use file extension ``.ogv``) is a nice video
            format, which is completely free/ open source. However not
            everyone has the codecs installed by default on their machine.
          - ``'libvpx'`` (use file extension ``.webm``) is tiny a video
            format well indicated for web videos (with HTML5). Open source.

        audio
          Either ``True``, ``False``, or a file name.
          If ``True`` and the clip has an audio clip attached, this
          audio clip will be incorporated as a soundtrack in the movie.
          If ``audio`` is the name of an audio file, this audio file
          will be incorporated as a soundtrack in the movie.

        audio_fps
          frame rate to use when generating the sound.

        temp_audiofile
          the name of the temporary audiofile, as a string or path-like object,
          to be created and then used to write the complete video, if any.

        temp_audiofile_path
          the location that the temporary audiofile is placed, as a
          string or path-like object. Defaults to the current working directory.

        audio_codec
          Which audio codec should be used. Examples are 'libmp3lame'
          for '.mp3', 'libvorbis' for 'ogg', 'libfdk_aac':'m4a',
          'pcm_s16le' for 16-bit wav and 'pcm_s32le' for 32-bit wav.
          Default is 'libmp3lame', unless the video extension is 'ogv'
          or 'webm', at which case the default is 'libvorbis'.

        audio_bitrate
          Audio bitrate, given as a string like '50k', '500k', '3000k'.
          Will determine the size/quality of audio in the output file.
          Note that it mainly an indicative goal, the bitrate won't
          necessarily be the this in the final file.

        preset
          Sets the time that FFMPEG will spend optimizing the compression.
          Choices are: ultrafast, superfast, veryfast, faster, fast, medium,
          slow, slower, veryslow, placebo. Note that this does not impact
          the quality of the video, only the size of the video file. So
          choose ultrafast when you are in a hurry and file size does not
          matter.

        threads
          Number of threads to use for ffmpeg. Can speed up the writing of
          the video on multicore computers.

        ffmpeg_params
          Any additional ffmpeg parameters you would like to pass, as a list
          of terms, like ['-option1', 'value1', '-option2', 'value2'].

        write_logfile
          If true, will write log files for the audio and the video.
          These will be files ending with '.log' with the name of the
          output file in them.

        logger
          Either ``"bar"`` for progress bar or ``None`` or any Proglog logger.

        pixel_format
          Pixel format for the output video file.

        Examples
        --------

        >>> from moviepy import VideoFileClip
        >>> clip = VideoFileClip("myvideo.mp4").subclip(100,120)
        >>> clip.write_videofile("my_new_video.mp4")
        >>> clip.close()

        """
        logger = proglog.default_bar_logger(logger)
        name, ext = os.path.splitext(filename)
        ext = ext.lower()

        if codec is None:
            codec = extensions_dict[ext[1:]]['codec'][0]

        if audio_codec is None:
            audio_codec = 'libmp3lame' if ext not in ['.ogv', '.webm'] else 'libvorbis'

        audiofile = audio if isinstance(audio, str) else None
        make_audio = (audiofile is None) and audio and (self.clip.audio is not None)

        if make_audio:
            audio_ext = find_extension(audio_codec)
            audiofile = f"{name}_TEMP_AUDIO.{audio_ext}"
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
            if os.path.exists(audiofile):
                os.remove(audiofile)

    def write_images_sequence(self, name_format, fps=None, with_mask=True, logger="bar"):
        """Writes the videoclip to a sequence of image files.

        Parameters
        ----------

        name_format
          A filename specifying the numerotation format and extension
          of the pictures. For instance "frame%03d.png" for filenames
          indexed with 3 digits and PNG format. Also possible:
          "some_folder/frame%04d.jpeg", etc.

        fps
          Number of frames per second to consider when writing the
          clip. If not specified, the clip's ``fps`` attribute will
          be used if it has one.

        with_mask
          will save the clip's mask (if any) as an alpha canal (PNGs only).

        logger
          Either ``"bar"`` for progress bar or ``None`` or any Proglog logger.


        Returns
        -------

        names_list
          A list of all the files generated.

        Notes
        -----

        The resulting image sequence can be read using e.g. the class
        ``ImageSequenceClip``.

        """
        logger = proglog.default_bar_logger(logger)
        fps = fps or self.clip.fps
        frame_times = np.arange(0, self.clip.duration, 1.0 / fps)
        filenames = [name_format % i for i in range(len(frame_times))]

        for t, filename in zip(frame_times, filenames):
            self.save_frame(filename, t, with_mask)

        return filenames

    def write_gif(self, filename, fps=None, program="imageio", opt="nq", fuzz=1, loop=0,
                  dispose=False, colors=None, tempfiles=False, logger="bar", pixel_format=None):
        """Write the VideoClip to a GIF file.

        Converts a VideoClip into an animated GIF using ImageMagick
        or ffmpeg.

        Parameters
        ----------

        filename
          Name of the resulting gif file, as a string or a path-like object.

        fps
          Number of frames per second (see note below). If it
          isn't provided, then the function will look for the clip's
          ``fps`` attribute (VideoFileClip, for instance, have one).

        program
          Software to use for the conversion, either 'imageio' (this will use
          the library FreeImage through ImageIO), or 'ImageMagick', or 'ffmpeg'.

        opt
          Optimalization to apply. If program='imageio', opt must be either 'wu'
          (Wu) or 'nq' (Neuquant). If program='ImageMagick',
          either 'optimizeplus' or 'OptimizeTransparency'.

        fuzz
          (ImageMagick only) Compresses the GIF by considering that
          the colors that are less than fuzz% different are in fact
          the same.

        tempfiles
          Writes every frame to a file instead of passing them in the RAM.
          Useful on computers with little RAM. Can only be used with
          ImageMagick' or 'ffmpeg'.

        progress_bar
          If True, displays a progress bar

        pixel_format
          Pixel format for the output gif file. If is not specified
          'rgb24' will be used as the default format unless ``clip.mask``
          exist, then 'rgba' will be used. This option is only going to
          be accepted if ``program=ffmpeg`` or when ``tempfiles=True``


        Notes
        -----

        The gif will be playing the clip in real time (you can
        only change the frame rate). If you want the gif to be played
        slower than the clip you will use ::

            >>> # slow down clip 50% and make it a gif
            >>> myClip.multiply_speed(0.5).to_gif('myClip.gif')

        """
        logger = proglog.default_bar_logger(logger)
        if program == "imageio":
            write_gif_with_image_io(self.clip, filename, fps, opt, loop, colors, logger)
        elif tempfiles:
            write_gif_with_tempfiles(self.clip, filename, fps, program, opt, fuzz, loop, dispose, colors, logger,
                                     pixel_format)
        else:
            write_gif(self.clip, filename, fps, program, opt, fuzz, loop, dispose, colors, logger, pixel_format)
