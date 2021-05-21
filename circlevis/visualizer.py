import numpy as np
from PyQt5.QtGui import QKeySequence, QPalette, QColor
from PyQt5.QtWidgets import QShortcut, QMainWindow, QApplication
from PyQt5.QtCore import Qt

from circlevis.interface import Interface

PREVIOUS_ERRSTATE = np.seterr('raise')

class Visualizer(QMainWindow):
    # TODO refactor so users aren't faced with only one entry point with more
    # than a few optional arguments, but multiple different objects with fewer
    # (and more relevant) arguments each. Eg maybe expose Renderer, which would
    # take speeds and start_speed.
    def __init__(self, beatmap_info, replays=[], events=[], library=None, \
        speeds=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 3.0, 5.0, 10.0], start_speed=1,\
        paint_info=True, statistic_functions=[], snaps_args={}):
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
        self.interface = Interface(beatmap_info, replays, events, library, \
            speeds, start_speed, paint_info, statistic_functions, snaps_args)
        self.setCentralWidget(self.interface)

        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Right), self, \
            lambda: self.interface.change_frame(reverse=False))
        QShortcut(QKeySequence(Qt.Key_Left), self, \
            lambda: self.interface.change_frame(reverse=True))
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Right), self, \
            self.interface.play_normal)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Left), self, \
            self.interface.play_reverse)
        QShortcut(QKeySequence(Qt.Key_Up), self, \
            self.interface.increase_speed)
        QShortcut(QKeySequence(Qt.Key_Down), self, \
            self.interface.lower_speed)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F11), self, \
            lambda: self.interface.renderer.toggle_frametime)
        QShortcut(QKeySequence.FullScreen, self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_F), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.ALT + Qt.Key_Return), self, \
            self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.exit_fullscreen)
        QShortcut(QKeySequence.Paste, self, self.seek_to_paste_contents)

        # ugly hack to make the window 20% larger, we can't change gameplay
        # height because that's baked in as the osu! gameplay height and is
        # not meant to be changed to increase the window size (same with width).
        from .renderer import (GAMEPLAY_WIDTH, GAMEPLAY_HEIGHT,
            GAMEPLAY_PADDING_WIDTH, GAMEPLAY_PADDING_HEIGHT)
        self.resize((GAMEPLAY_WIDTH + GAMEPLAY_PADDING_WIDTH * 2) * 1.2, \
                    (GAMEPLAY_HEIGHT + GAMEPLAY_PADDING_HEIGHT * 2) * 1.2)

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

    def pause(self):
        self.interface.pause()

    def force_pause(self):
        self.interface.force_pause()

    def force_unpause(self):
        self.interface.force_unpause()

    def save_as_image(self):
        return self.grab().toImage()

class VisualizerApp(QApplication):
    """
    ``speeds`` must contain ``start_speed``, ``1``, ``0.75``, and ``1.5``.
    """
    def __init__(self, beatmap_info, replays=[], events=[], library=None, \
        speeds=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 3.0, 5.0, 10.0], start_speed=1,\
        paint_info=True, statistic_functions=[], snaps_args={}):
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
        self.set_palette()
        # we can't create this in ``__init__`` because we can't instantiate a
        # ``QWidget`` before a ``QApplication``, so delay until here, which is
        # all it's necessary for.
        self.visualizer = Visualizer(self.beatmap_info, self.replays, \
            self.events, self.library, self.speeds, self.start_speed, \
            self.paint_info, self.statistic_functions, self.snaps_args)
        self.visualizer.show()
        super().exec()

    def set_palette(self):
        accent = QColor(71, 174, 247)
        dark_p = QPalette()

        dark_p.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_p.setColor(QPalette.WindowText, Qt.white)
        dark_p.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_p.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_p.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
        dark_p.setColor(QPalette.ToolTipText, Qt.white)
        dark_p.setColor(QPalette.Text, Qt.white)
        dark_p.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_p.setColor(QPalette.ButtonText, Qt.white)
        dark_p.setColor(QPalette.BrightText, Qt.red)
        dark_p.setColor(QPalette.Highlight, accent)
        dark_p.setColor(QPalette.Inactive, QPalette.Highlight, Qt.lightGray)
        dark_p.setColor(QPalette.HighlightedText, Qt.black)
        dark_p.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.Highlight, Qt.darkGray)
        dark_p.setColor(QPalette.Disabled, QPalette.Base, QColor(53, 53, 53))
        dark_p.setColor(QPalette.Link, accent)
        dark_p.setColor(QPalette.LinkVisited, accent)

        self.setPalette(dark_p)

    def pause(self):
        self.visualizer.pause()

    def seek_to(self, timestamp):
        self.visualizer.seek_to(timestamp)

    def force_pause(self):
        self.visualizer.force_pause()

    def force_unpause(self):
        self.visualizer.force_unpause()

    def save_as_image(self):
        return self.visualizer.grab().toImage()
