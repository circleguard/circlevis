class BeatmapInfo:
    """
    Represents the information necessary to load a beatmap.

    Notes
    -----
    If multiple ways to load a beatmap are known, all ways should be provided
    so consumers can choose the order of ways to load the beatmap.

    If a way to load a beatmap is *not* available, it should be left as
    ``None``.
    """

    def __init__(self, *, map_id=None, path=None, beatmap=None):
        self.map_id = map_id
        self.path = path
        self.beatmap = beatmap

    def available(self):
        """
        Whether this beatmap can be loaded with the information we have or not.
        """
        return bool(self.map_id) or bool(self.path)
