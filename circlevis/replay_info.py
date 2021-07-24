from functools import partial

from PyQt5.QtWidgets import (QLabel, QVBoxLayout, QFrame, QAbstractItemView,
    QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor
from circleguard import KeylessCircleguard, JudgmentType, Miss, convert_statistic

from circlevis.widgets import PushButton

class ReplayInfo(QFrame):
    seek_to = pyqtSignal(int)
    close_button_clicked = pyqtSignal()

    UR_YELLOW_THRESH = 60
    UR_RED_THRESH = 40
    FRAMETIME_YELLOW_THRESH = 14
    FRAMETIME_RED_THRESH = 11

    # in pixels
    EDGE_HIT_THRESH = 3

    def __init__(self, replay, slider_dir, ur=None, frametime=None, \
        snaps=None, judgments=None, snaps_args={}):
        """
        If passed, the `ur`, `frametime`, `snaps`, and
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

        mods = replay.mods.short_name()

        info_label = QLabel("<a href=\"https://osu.ppy.sh/scores/osu/"
            f"{replay.replay_id}\">{replay.username} +{mods}</a> "
            "on map "
            f"<a href=\"https://osu.ppy.sh/b/{replay.map_id}\">{replay.map_id}"
            "</a>")
        info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_label.setOpenExternalLinks(True)
        info_label.setCursor(QCursor(Qt.IBeamCursor))

        if circleguard.map_available(replay):
            ur = ur or circleguard.ur(replay)
            ucv_ur = round(convert_statistic(ur, replay.mods, to="ucv"), 2)
            ur = round(ur, 2)
            ur = self.maybe_highlight(ur, self.UR_YELLOW_THRESH,
                self.UR_RED_THRESH)
            # highlight ucvUR in the same way as ur or the user will get
            # confused (ie these should always be the same color)
            yellow_thresh = convert_statistic(self.UR_YELLOW_THRESH,
                replay.mods, to="ucv")
            red_thresh = convert_statistic(self.UR_RED_THRESH, replay.mods,
                to="ucv")
            ucv_ur = self.maybe_highlight(ucv_ur, yellow_thresh, red_thresh)
        else:
            ur = "Unknown"
            ucv_ur = "Unkown"

        ur_label = QLabel(f"<b>cvUR:</b> {ur} ({ucv_ur} ucv)")
        ur_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        ur_label.setCursor(QCursor(Qt.IBeamCursor))

        frametime = frametime or circleguard.frametime(replay)
        frametime = round(frametime, 2)
        frametime = self.maybe_highlight(frametime,
            self.FRAMETIME_YELLOW_THRESH, self.FRAMETIME_RED_THRESH)
        frametime_label = QLabel(f"<b>cv frametime:</b> {frametime}")
        frametime_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        frametime_label.setCursor(QCursor(Qt.IBeamCursor))

        events_label = QLabel("Events Table")

        events = []
        snaps = snaps or circleguard.snaps(replay, **snaps_args)
        snap_events = [SnapEvent(snap) for snap in snaps]

        edge_hits = []
        misses = []
        hit100s = []
        hit50s = []
        if circleguard.map_available(replay):
            judgments = judgments or circleguard.judgments(replay)
            for judgment in judgments:
                if judgment.type is JudgmentType.Miss:
                    misses.append(MissEvent(judgment))
                else:
                    if judgment.type is JudgmentType.Hit100:
                        hit100s.append(Hit100Event(judgment))
                    if judgment.type is JudgmentType.Hit50:
                        hit50s.append(Hit50Event(judgment))
                    if judgment.within(self.EDGE_HIT_THRESH):
                        edge_hits.append(EdgeHitEvent(judgment))

        events.extend(snap_events)
        events.extend(edge_hits)
        events.extend(misses)
        events.extend(hit100s)
        events.extend(hit50s)

        events_table = EventsTable(events)
        events_table.jump_button_clicked.connect(self.seek_to)

        close_button = PushButton("Close")
        close_button.clicked.connect(self.close_button_clicked)
        close_button.setMaximumWidth(80)
        # don't let ourselves get a horizontal scrollbar on the table by being
        # too small, + 60 to account for the vertical scrollbar I think?
        self.setMinimumWidth(events_table.horizontalHeader().length() +
            events_table.verticalHeader().width() + 60)

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


class Event:
    def __init__(self, label, time):
        self.label = label
        self.time = time

class SnapEvent(Event):
    def __init__(self, snap):
        super().__init__("snap", snap.time)

class EdgeHitEvent(Event):
    def __init__(self, judgment):
        super().__init__("edge hit", judgment.time)

class MissEvent(Event):
    def __init__(self, judgment):
        super().__init__("miss", judgment.hitobject.time)

class Hit100Event(Event):
    def __init__(self, judgment):
        super().__init__("100", judgment.time)

class Hit50Event(Event):
    def __init__(self, judgment):
        super().__init__("50", judgment.time)


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
            item = QTableWidgetItem(event.label)
            self.setItem(i, 0, item)

            item = QTableWidgetItem(str(event.time))
            self.setItem(i, 1, item)

            # we need to embed the button in a widget (or frame) so we can set
            # its contents margins. Otherwise the button is massive
            button_widget = QFrame()

            jump_to_button = PushButton("Jump")
            jump_to_button.setMaximumWidth(60)
            layout = QVBoxLayout()
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(15, 3, 15, 3)
            layout.addWidget(jump_to_button)
            button_widget.setLayout(layout)

            jump_to_button.clicked.connect(
                partial(self.jump_button_clicked.emit, event.time))
            self.setCellWidget(i, 2, button_widget)

        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 70)
        self.setColumnWidth(2, 90)

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     self.setColumnWidth(0, self.width() / 3 - 20)
    #     self.setColumnWidth(1, self.width() / 3 - 20)
    #     self.setColumnWidth(2, self.width() / 3 - 20)
