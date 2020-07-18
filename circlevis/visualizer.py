import numpy as np
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut, QMainWindow, QApplication
from PyQt5.QtCore import Qt

from circlevis.interface import Interface

PREVIOUS_ERRSTATE = np.seterr('raise')

class Visualizer(QMainWindow):
    # TODO refactor so users aren't faced with only one entry point with more
    # than a few optional arguments, but multiple different objects with fewer
    # (and more relevant) arguments each. Eg maybe expose Renderer, which would
    # take speeds and start_speed.
    def __init__(self, beatmap_info, replays=[], events=[], library=None, speeds=[1], start_speed=1, paint_info=True):
        super().__init__()

        self.setAutoFillBackground(True)
        self.setWindowTitle("Visualizer")
        self.interface = Interface(beatmap_info, replays, events, library, speeds, start_speed, paint_info)
        self.setCentralWidget(self.interface)

        QShortcut(QKeySequence(Qt.Key_Space), self, self.interface.pause)
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.interface.change_frame(reverse=False))
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.interface.change_frame(reverse=True))
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Right), self, self.interface.play_normal)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Left), self, self.interface.play_reverse)
        QShortcut(QKeySequence(Qt.Key_Up), self, self.interface.increase_speed)
        QShortcut(QKeySequence(Qt.Key_Down), self, self.interface.lower_speed)
        QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F11), self, lambda: self.interface.renderer.toggle_frametime)
        QShortcut(QKeySequence.FullScreen, self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_F), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.ALT + Qt.Key_Return), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.exit_fullscreen)
        QShortcut(QKeySequence.Paste, self, self.seek_to_paste_contents)

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
        self.interface.renderer.seek_to(time)
