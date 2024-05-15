import moviepy

# Reads in test_video.mp4, creates a subclip of it
# Reads in test_video.mp4, creates a subclip of it
video = moviepy.VideoFileClip("test_video.mp4").subclip(0, 5)

# Changes the format to webm and adjusts the fps
video.write_videofile("Outputs/ReadMP4_Subclip_OutputWebm.webm", fps=25) # Many options...