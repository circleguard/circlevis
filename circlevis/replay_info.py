from functools import partial
import math

from PyQt5.QtWidgets import (QLabel, QVBoxLayout, QFrame, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from circleguard import KeylessCircleguard, Snap, Hit, Mod
from circleguard.utils import convert_statistic
from slider.mod import circle_radius
import numpy as np

class ReplayInfo(QFrame):
    seek_to = pyqtSignal(int)
    close_button_clicked = pyqtSignal()

    UR_YELLOW_THRESH = 60
    UR_RED_THRESH = 40
    FRAMETIME_YELLOW_THRESH = 14
    FRAMETIME_RED_THRESH = 11

    # in pixels
    EDGE_HIT_THRESH = 3

    def __init__(self, replay, beatmap, slider_dir, ur_result=None, \
        frametime_result=None, snaps_result=None, hits=None):
        """
        If passed, the `ur_result`, `frametime_result`, `snaps_result`, and
        `hits` parameters will be used instead of recalculating them from
        scratch.
        """
        super().__init__()
        self.replay = replay
        # replay is already loaded so we don't need an api key. We pass a slider
        # dir because `Interface` has already loaded a beatmap for us, but
        # circleguard doesn't know that, so it will redownload the beatmap for
        # ur calc unless we give it the slider dir we've already saved the
        # beatmap too.
        # It would probably be better if we could pass the entire `Library`
        # object to slider instead, but I'm pretty sure `Library` instantiation
        # is really cheap. What matters is the .osu files are already there.
        circleguard = KeylessCircleguard(slider_dir=slider_dir)
        hitcircle_radius = circle_radius(beatmap.cs(hard_rock=Mod.HR in replay.mods))

        mods = replay.mods.short_name()

        info_label = QLabel(f"{replay.username} +{mods} on map {replay.map_id}")

        ur_result = ur_result or circleguard.ur(replay, single=True)
        ur = round(ur_result.ur, 2)
        ur = self.maybe_highlight(ur, self.UR_YELLOW_THRESH, self.UR_RED_THRESH)
        # highlight ucvUR in the same way as ur or the user will get confused
        # (ie these should always be the same color)
        ucv_ur = round(ur_result.ucv_ur, 2)
        ucv_ur = self.maybe_highlight(ucv_ur, convert_statistic(self.UR_YELLOW_THRESH, replay.mods, to="ucv"), convert_statistic(self.UR_RED_THRESH, replay.mods, to="ucv"))

        ur_label = QLabel(f"<b>cvUR:</b> {ur} ({ucv_ur} ucv)")

        frametime_result = frametime_result or circleguard.frametime(replay, single=True)
        frametime = round(frametime_result.frametime, 2)
        frametime = self.maybe_highlight(frametime, self.FRAMETIME_YELLOW_THRESH, self.FRAMETIME_RED_THRESH)
        frametime_label = QLabel(f"<b>cv frametime:</b> {frametime}")

        events_label = QLabel("Events Table")

        events = []
        snaps_result = snaps_result or circleguard.snaps(replay, single=True)
        snaps = snaps_result.snaps

        hits = hits or circleguard.hits(replay)
        edge_hits = []
        for hit in hits:

            hitobj_xy = np.array([hit.hitobject.position.x, hit.hitobject.position.y])
            # value is negative if we're inside the hitobject, so take abs
            dist = abs(np.linalg.norm(hit.xy - hitobj_xy) - hitcircle_radius)

            if dist < self.EDGE_HIT_THRESH:
                edge_hits.append(hit)

        events.extend(snaps)
        events.extend(edge_hits)

        events_table = EventsTable(events)
        events_table.jump_button_clicked.connect(self.seek_to)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_button_clicked)
        close_button.setMaximumWidth(80)
        # don't let ourselves get a horizontal scrollbar on the table by being
        # too small, + 60 to account for the vertical scrollbar I think?
        self.setMinimumWidth(events_table.horizontalHeader().length() + events_table.verticalHeader().width() + 60)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(info_label)
        layout.addWidget(ur_label)
        layout.addWidget(frametime_label)
        layout.addSpacing(180)
        layout.addWidget(events_label)
        layout.addWidget(events_table)
        layout.addWidget(close_button)
        self.setLayout(layout)

    def maybe_highlight(self, statistic, yellow_threshold, red_threshold):
        """
        Colors `statistic` yellow (with html attributes) if it falls between the
        yellow and red thresholds and red if it falls under the red threshold.
        Otherwise `statistic` is returned unchanged.

        This is intended for use with statistics where low values raises alarm,
        such as ur or frametime.
        """
        if red_threshold < statistic < yellow_threshold:
            statistic = f"<font color='yellow'>{statistic}</font>"
        elif statistic < red_threshold:
            statistic = f"<font color='red'>{statistic}</font>"
        return statistic

    def __eq__(self, other):
        if not isinstance(other, ReplayInfo):
            return False
        return self.replay == other.replay

class EventsTable(QTableWidget):
    jump_button_clicked = pyqtSignal(int) # time (ms)

    def __init__(self, events):
        super().__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Type", "Time (ms)", "Jump To"])
        # https://forum.qt.io/topic/82749/how-to-make-qtablewidget-read-only
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # use monospaced font for the table, otherwise some timestamps are
        # smaller than others even though they have the same number of digits
        # https://stackoverflow.com/a/1835938/12164878

        # Later note: turns out the default monospaced font on windows (and
        # mac?) looks pretty bad, so leave as is for now. Don't want to have to
        # deal with font specification (which would entail supporting
        # computers that don't have that font) yet.

        # font = QFont("Monospace")
        # font.setStyleHint(QFont.TypeWriter)
        # self.setFont(font)


        self.setRowCount(len(events))

        for i, event in enumerate(events):
            if isinstance(event, Snap):
                type_string = "snap"
                time = event.time
            if isinstance(event, Hit):
                type_string = "edge hit"
                time = event.t

            item = QTableWidgetItem(type_string)
            self.setItem(i, 0, item)

            item = QTableWidgetItem(str(time))
            self.setItem(i, 1, item)

            # we need to embed the button in a widget (or frame) so we can set
            # its contents margins. Otherwise the button is massive
            button_widget = QFrame()

            jump_to_button = QPushButton("Jump")
            jump_to_button.setMaximumWidth(60)
            layout = QVBoxLayout()
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(15, 3, 15, 3)
            layout.addWidget(jump_to_button)
            button_widget.setLayout(layout)

            jump_to_button.clicked.connect(partial(self.jump_button_clicked.emit, time))
            self.setCellWidget(i, 2, button_widget)

        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 70)
        self.setColumnWidth(2, 90)

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     self.setColumnWidth(0, self.width() / 3 - 20)
    #     self.setColumnWidth(1, self.width() / 3 - 20)
    #     self.setColumnWidth(2, self.width() / 3 - 20)
