from dataclasses import dataclass
from typing import Type, Callable
from functools import partial

from circleguard import Replay
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QKeySequence, QShortcut

from circlevis.beatmap_info import BeatmapInfo
from circlevis.visualizer import Visualizer
from circlevis.palette import dark_palette


@dataclass
class ClassifierHotkey:
    """
    A hotkey for use in a ``Classifier``. Listens for ``keys`` and calls
    ``callback`` when the hotkey is pressed.
    """
    keys: Type[Qt.Key]
    callback: Callable[[Replay], None]


class Classifier:
    """
    A standalone application intended for batch reviewing replays and
    classifying them in some way.

    For instance, you may want to go through the top 50 scores on a map and
    assign a "cursordance score" to them, depending on how often the user
    cursordanced.

    To do so, you could assign the number keys 0-9 to a score from 1 to 10 via
    ``hotkeys`` and give ``Classifier`` the list of replays you want to
    classify. ``Classifier`` will visualize the scores, one at a time, in order.
    When you've decided on a score for the replay, hit the corresponding number
    button, and have your function call ``self.next_replay`` to show the next
    replay in order to you.
    """
    def __init__(self, replays, cg, hotkeys):
        self.app = QApplication([])
        self.app.setStyle("Fusion")
        self.app.setApplicationName("Circlevis")
        self.app.setPalette(dark_palette)

        self._replays = iter(replays)
        self.cg = cg
        self.hotkeys = hotkeys
        self.vis = None

    def start(self):
        self.next_replay()
        self.app.exec()

    def next_replay(self):
        """
        Close the current visualization and show the next replay.
        """
        if self.vis:
            self.vis.close()

        try:
            replay = next(self._replays)
        except StopIteration:
            self.done()
            return

        self.load(replay)
        bm = self.beatmap_info(replay)

        if self.should_skip(replay, bm):
            return self.next_replay()

        self.vis = self.visualizer(bm, replay)
        for hotkey in self.hotkeys:
            QShortcut(QKeySequence(hotkey.keys), self.vis,
                partial(hotkey.callback, replay))
        self.vis.show()

    def visualizer(self, bm, replay):
        """
        Return the desired ``Visualizer`` to show. Provided as a hook for
        subclasses, primarily in case subclasses want to return a subclass of
        ``Visualizer``.
        """
        return Visualizer(bm, [replay])

    def load(self, replay):
        """
        Load the replay so it can be visualized. Provided as a hook for
        subclasses.
        """
        self.cg.load(replay)

    def beatmap_info(self, replay):
        """
        Return the desired ``BeatmapInfo`` for the replay, for use in a
        ``Visualizer``. Provided as a hook for subclasses.
        """
        return BeatmapInfo(map_id=replay.map_id)

    def should_skip(self, _replay, _bm):
        """
        Whether this replay should be skipped and not visualized at all.
        Provided as a hook for subclasses, for when a replay cannot be loaded,
        for example.
        """
        return False

    def done(self):
        """
        Called when the classifier has finished classifying all of its replays.
        """
        pass
