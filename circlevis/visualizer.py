import numpy as np
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt

from circlevis.interface import Interface
from circlevis.palette import dark_palette

PREVIOUS_ERRSTATE = np.seterr('raise')

class Visualizer(QMainWindow):
    # TODO refactor so users aren't faced with only one entry point with more
    # than a few optional arguments, but multiple different objects with fewer
    # (and more relevant) arguments each. Eg maybe expose Renderer, which would
    # take speeds and start_speed.
    def __init__(self, beatmap_info, replays=[], events=[], library=None,
        speeds=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 3.0, 5.0, 10.0],
        start_speed=1, paint_info=True, statistic_functions=[], snaps_args={}):
        super().__init__()

        self.beatmap_info = beatmap_info
        self.replays = replays
        self.events = events
        self.library = library
        self.speeds = speeds
        self.start_speed = start_speed
        self.paint_info = paint_info
        self.statistic_functions = statistic_functions
        self.snaps_args = snaps_args

        self.setAutoFillBackground(True)
        self.setWindowTitle("Visualizer")
        self.interface = Interface(beatmap_info, replays, events, library,
            speeds, start_speed, paint_info, statistic_functions, snaps_args)
        self.interface.renderer.loaded_signal.connect(self.on_load)
        self.setCentralWidget(self.interface)

        QShortcut(Qt.Key.Key_Space, self, self.interface.toggle_pause)
        QShortcut(Qt.Key.Key_Right, self,
            lambda: self.interface.change_frame(reverse=False))
        QShortcut(Qt.Key.Key_Left, self,
            lambda: self.interface.change_frame(reverse=True))
        QShortcut(Qt.Key.Key_Control + Qt.Key.Key_Right, self,
            self.interface.play_normal)
        QShortcut(Qt.Key.Key_Control + Qt.Key.Key_Left, self,
            self.interface.play_reverse)
        QShortcut(Qt.Key.Key_Up, self, self.interface.increase_speed)
        QShortcut(Qt.Key.Key_Down, self, self.interface.lower_speed)
        QShortcut(Qt.Key.Key_Control + Qt.Key.Key_F11, self,
             self.interface.renderer.toggle_frametime)
        QShortcut(QKeySequence.StandardKey.FullScreen, self,
            self.toggle_fullscreen)
        QShortcut(Qt.Key.Key_F, self, self.toggle_fullscreen)
        QShortcut(Qt.Key.Key_Alt + Qt.Key.Key_Return, self,
            self.toggle_fullscreen)
        QShortcut(Qt.Key.Key_Escape, self, self.exit_fullscreen)
        QShortcut(QKeySequence.StandardKey.Paste, self,
            self.seek_to_paste_contents)
        QShortcut(Qt.Key.Key_Period, self, lambda: self.interface.change_by(1))
        QShortcut(Qt.Key.Key_Comma, self, lambda: self.interface.change_by(-1))

        # ugly hack to make the window 20% larger, we can't change gameplay
        # height because that's baked in as the osu! gameplay height and is
        # not meant to be changed to increase the window size (same with width).
        from .renderer import (GAMEPLAY_WIDTH, GAMEPLAY_HEIGHT,
            GAMEPLAY_PADDING_WIDTH, GAMEPLAY_PADDING_HEIGHT)
        self.resize(int((GAMEPLAY_WIDTH + GAMEPLAY_PADDING_WIDTH * 2) * 1.2),
                    int((GAMEPLAY_HEIGHT + GAMEPLAY_PADDING_HEIGHT * 2) * 1.2))

    def closeEvent(self, event):
        super().closeEvent(event)
        self.interface.renderer.timer.stop()
        np.seterr(**PREVIOUS_ERRSTATE)

    def toggle_fullscreen(self):
        if self.windowState() == Qt.WindowFullScreen:
            self.exit_fullscreen()
            return
        else:
            self.setWindowState(Qt.WindowFullScreen)

    def exit_fullscreen(self):
        self.setWindowState(Qt.WindowNoState)

    def seek_to_paste_contents(self):
        clipboard = QApplication.clipboard()
        time = clipboard.text()
        try:
            # need float to convert x.0 values, then int to make it an int after
            # (seek_to needs a ms value as an int)
            time = int(float(time))
        except ValueError:
            # invalid time, don't seek
            return
        self.seek_to(time)

    def seek_to(self, timestamp):
        self.interface.renderer.seek_to(timestamp)

    def toggle_pause(self):
        self.interface.toggle_pause()

    def pause(self):
        self.interface.pause()

    def unpause(self):
        self.interface.unpause()

    def save_as_image(self):
        return self.grab().toImage()

    def on_load(self):
        """
        Will be called when the visualizer has completely loaded (including
        processing the beatmap, replays, sliders, and anything else) and is
        ready to display gameplay.
        """
        pass

    # TODO remove in circlevis 2.0.0
    force_pause = pause
    force_unpause = unpause

class VisualizerApp(QApplication):
    """
    ``speeds`` must contain ``start_speed``, ``1``, ``0.75``, and ``1.5``.
    """
    def __init__(self, beatmap_info, replays=[], events=[], library=None,
        speeds=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 3.0, 5.0, 10.0],
        start_speed=1, paint_info=True, statistic_functions=[], snaps_args={}):
        super().__init__([])
        self.setStyle("Fusion")
        self.setApplicationName("Circlevis")

        self.beatmap_info = beatmap_info
        self.replays = replays
        self.events = events
        self.library = library
        self.speeds = speeds
        self.start_speed = start_speed
        self.paint_info = paint_info
        self.statistic_functions = statistic_functions
        self.snaps_args = snaps_args

    def exec(self):
        """
        Displays the visualizer and enters into the event loop, which will block
        the calling thread.
        """
        self.setPalette(dark_palette)
        # we can't create this in ``__init__`` because we can't instantiate a
        # ``QWidget`` before a ``QApplication``, so delay until here, which is
        # all it's necessary for.
        self.visualizer = Visualizer(self.beatmap_info, self.replays,
            self.events, self.library, self.speeds, self.start_speed,
            self.paint_info, self.statistic_functions, self.snaps_args)
        self.visualizer.interface.renderer.loaded_signal.connect(self.on_load)
        self.visualizer.show()
        super().exec()

    def toggle_pause(self):
        self.visualizer.toggle_pause()

    def seek_to(self, timestamp):
        self.visualizer.seek_to(timestamp)

    def pause(self):
        self.visualizer.pause()

    def unpause(self):
        self.visualizer.unpause()

    def save_as_image(self):
        return self.visualizer.grab().toImage()

    def on_load(self):
        """
        Will be called when the visualizer has completely loaded (including
        processing the beatmap, replays, sliders, and anything else) and is
        ready to display gameplay.
        """
        pass

    # TODO remove in circlevis 2.0.0
    force_pause = pause
    force_unpause = unpause
