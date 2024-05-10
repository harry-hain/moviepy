class ClipOperations:
    def __init__(self, video_clip):
        self.video_clip = video_clip

    def with_make_frame(self, make_frame_function):
        """Change the clip's ``get_frame``.

                Returns a copy of the VideoClip instance, with the make_frame
                attribute set to `mf`.
                """
        new_clip = self.video_clip.copy()
        new_clip.make_frame = make_frame_function
        new_clip.size = new_clip.get_frame(0).shape[:2][::-1]
        return new_clip

    def with_audio(self, audio_clip):
        """Attach an AudioClip to the VideoClip.

                Returns a copy of the VideoClip instance, with the `audio`
                attribute set to ``audio``, which must be an AudioClip instance.
                """
        new_clip = self.video_clip.copy()
        new_clip.audio = audio_clip
        return new_clip

    def with_mask(self, mask):
        """Set the clip's mask.

                Returns a copy of the VideoClip with the mask attribute set to
                ``mask``, which must be a greyscale (values in 0-1) VideoClip.
                """
        assert mask is None or mask.is_mask
        new_clip = self.video_clip.copy()
        new_clip.mask = mask
        return new_clip

    def with_opacity(self, opacity):
        """Set the opacity/transparency level of the clip.

                Returns a semi-transparent copy of the clip where the mask is
                multiplied by ``op`` (any float, normally between 0 and 1).
                """
        new_clip = self.video_clip.copy()
        if new_clip.mask:
            new_clip.mask = new_clip.mask.image_transform(lambda pic: opacity * pic)
        return new_clip

    def with_position(self, position, relative=False):
        """Set the clip's position in compositions.

                Sets the position that the clip will have when included
                in compositions. The argument ``pos`` can be either a couple
                ``(x,y)`` or a function ``t-> (x,y)``. `x` and `y` mark the
                location of the top left corner of the clip, and can be
                of several types.

                Examples
                --------

                >>> clip.with_position((45,150)) # x=45, y=150
                >>>
                >>> # clip horizontally centered, at the top of the picture
                >>> clip.with_position(("center","top"))
                >>>
                >>> # clip is at 40% of the width, 70% of the height:
                >>> clip.with_position((0.4,0.7), relative=True)
                >>>
                >>> # clip's position is horizontally centered, and moving up !
                >>> clip.with_position(lambda t: ('center', 50+t) )

                """
        new_clip = self.video_clip.copy()
        new_clip.relative_pos = relative
        new_clip.pos = position if hasattr(position, "__call__") else lambda t: position
        return new_clip

    def with_layer(self, layer):
        """Set the clip's layer in compositions. Clips with a greater ``layer``
                attribute will be displayed on top of others.

                Note: Only has effect when the clip is used in a CompositeVideoClip.
                """
        new_clip = self.video_clip.copy()
        new_clip.layer = layer
        return new_clip
