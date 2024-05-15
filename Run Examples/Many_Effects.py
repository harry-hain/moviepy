import moviepy

# Reads in test_video.mp4
clip = moviepy.VideoFileClip("test_video.mp4")

# !!! You can apply anything from withing fx to a video !!!
# !!! Ignore what the IDE says, it is wrong !!!




# 1
# Rotate clip 180
clip = clip.rotate(180)

# 2
# Make clip black and white
clip = clip.blackwhite()

# 3
# Only works on composite clip, NOT CURRENTLY WORKING
# Make clip blink, 2 seconds on, 1 second off
# clip = clip.blink(duration_on=1, duration_off=1)

# 4
# Crops the clip in a funky way (multiple ways of doing this
clip = clip.crop(x1=50, y1=60, x2=460, y2=275)

# 5
# Unsure, NOT CURRENTLY WORKING
# Makes the clips even size?
# clip = clip.even_size()

# 6
# Makes the clip fade in over 1 second
clip = clip.fadein(duration=1)

# 7
# Makes the clip fadeout over 1 second
clip = clip.fadeout(duration=1)

# 8
# Freeze the clip at time 1 second for 2 seconds
clip = clip.freeze(t=1, freeze_duration=2)

# 9
# Freezes region for entire duration of clip, NOT CURRENTLY WORKING
# Freezes a region at time t where region is (0, 0, 100, 100)
# clip = clip.freeze_region(t=5, region=(0, 0, 100, 100))

# 10
# Adjusts the gamma of the clip, takes 1 input, gamma
clip = clip.gamma_corr(10)

# 12
# Requires opencv, NOT CURRENTLY WORKING
# headBlurs the clip, requires fx, fy, r_zone
# clip = clip.headblur(300, 300, 10)

# 13
# Invert Colors
clip = clip.invert_colors()


# Outputs mp4
clip.write_videofile("Outputs/Many_Effects.mp4") # Many options...