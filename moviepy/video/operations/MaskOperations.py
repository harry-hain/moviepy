class MaskOperations:
    def __init__(self, is_mask=False):
        self.mask = None
        self.is_mask = is_mask

    def getMask(self):
        return self.mask

    def setMask(self, mask):
        self.mask = mask

    def getIs_mask(self):
        return self.is_mask

    def setIs_mask(self, is_mask):
        self.is_mask = is_mask

    def with_mask(self, mask):
        """Set the clip's mask.

        Returns a copy of the VideoClip with the mask attribute set to
        ``mask``, which must be a greyscale (values in 0-1) VideoClip.
        """
        assert mask is None or mask.is_mask
        self.mask = mask

    def with_opacity(self, opacity):
        """Set the opacity/transparency level of the clip.

        Returns a semi-transparent copy of the clip where the mask is
        multiplied by ``op`` (any float, normally between 0 and 1).
        """
        self.mask = self.mask.image_transform(lambda pic: opacity * pic)

    def apply_mask(self, new_clip, t):
        if self.mask is not None:
            new_clip.mask = self.mask.to_ImageClip(t)
        return new_clip