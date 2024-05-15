import moviepy
from moviepy.editor import VideoFileClip, clips_array, vfx

# Reads in test_video.mp4
clip1 = moviepy.VideoFileClip("../../UG13_Work/Run Examples/test_video.mp4")
clip2 = moviepy.VideoFileClip("../../UG13_Work/Run Examples/test_video_2.mp4")

clip1 = clip1.margin(10)
clip2 = clip2.margin(10)


clip1_mx = clip1.fx( vfx.mirror_x)
clip1_my = clip1.fx( vfx.mirror_y)


clip2_res = clip2.resize(0.60) # downsize 60%
final_clip = clips_array([[clip1_mx, clip1_my],
                          [clip2, clip2_res]])
final_clip.resize(width=480).write_videofile("my_stack.mp4")




# Outputs mp4
final_clip.write_videofile("Outputs/Mixing_Clips.mp4") # Many options...