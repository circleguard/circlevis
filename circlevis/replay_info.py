from functools import partial

from PyQt6.QtWidgets import (QLabel, QVBoxLayout, QFrame, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from circleguard import KeylessCircleguard, JudgmentType, convert_statistic

from circlevis.widgets import CheckboxSetting, PushButton


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
        info_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        info_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        info_label.setOpenExternalLinks(True)
        info_label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

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
        ur_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        ur_label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        frametime = frametime or circleguard.frametime(replay)
        frametime = round(frametime, 2)
        frametime = self.maybe_highlight(frametime,
            self.FRAMETIME_YELLOW_THRESH, self.FRAMETIME_RED_THRESH)
        frametime_label = QLabel(f"<b>cv frametime:</b> {frametime}")
        frametime_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        frametime_label.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        events_label = QLabel("Events Table")

        self.table_filters_popup = EventsTableFilters(self)
        self.table_filters_popup.edge_hit_filter_signal.connect(partial(self.toggle_filter_item, EdgeHitEvent))
        self.table_filters_popup.snaps_filter_signal.connect(partial(self.toggle_filter_item, SnapEvent))
        self.table_filters_popup.misses_filter_signal.connect(partial(self.toggle_filter_item, MissEvent))
        self.table_filters_popup.hit_100_filter_signal.connect(partial(self.toggle_filter_item, Hit100Event))
        self.table_filters_popup.hit_50_filter_signal.connect(partial(self.toggle_filter_item, Hit50Event))

        self.events_filter_button = PushButton("Filter Events")
        self.events_filter_button.clicked.connect(self.show_filters)

        self.active_filters = [EdgeHitEvent, SnapEvent, MissEvent, Hit100Event, Hit50Event]

        self.events = []
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

        self.events.extend(snap_events)
        self.events.extend(edge_hits)
        self.events.extend(misses)
        self.events.extend(hit100s)
        self.events.extend(hit50s)

        self.events_table = EventsTable(self.events)
        self.events_table.jump_button_clicked.connect(self.seek_to)

        close_button = PushButton("Close")
        close_button.clicked.connect(self.close_button_clicked)
        close_button.setMaximumWidth(80)
        # don't let ourselves get a horizontal scrollbar on the table by being
        # too small, + 60 to account for the vertical scrollbar I think?
        self.setMinimumWidth(self.events_table.horizontalHeader().length() +
            self.events_table.verticalHeader().width() + 60)

        self.events_label_frame = QFrame()
        events_label_layout = QGridLayout()
        events_label_layout.setContentsMargins(0, 0, 0, 0)
        events_label_layout.addWidget(events_label, 0, 0, 1, 1)
        events_label_layout.addWidget(self.events_filter_button, 0, 1, 1, 1)
        self.events_label_frame.setLayout(events_label_layout)


        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(info_label)
        layout.addWidget(ur_label)
        layout.addWidget(frametime_label)
        layout.addSpacing(180)
        layout.addWidget(self.events_label_frame)
        layout.addWidget(self.events_table)
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

    def show_filters(self):
        # have to show before setting its geometry because it has some default
        # geometry that doesn't reflect its actual proportions until it's shown
        self.table_filters_popup.show()
        global_pos = self.mapToGlobal(self.events_filter_button.pos())
        popup_height = self.table_filters_popup.size().height()
        popup_width = self.table_filters_popup.size().width()

        # `y + 16` to account for the size of the filter button
        self.table_filters_popup.setGeometry(
            int(global_pos.x()),
            int(global_pos.y() + (popup_height / 2) + 16),
            popup_width, popup_height
        )

    def toggle_filter_item(self, filter_item):
        if filter_item in self.active_filters:
            self.active_filters.remove(filter_item)
        else:
            self.active_filters.append(filter_item)

        filtered_events = list(filter(lambda e: type(e) in self.active_filters, self.events))
        self.events_table.set_events(filtered_events)

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
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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

        self.set_events(events)

        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 70)
        self.setColumnWidth(2, 90)

    def set_events(self, events):
        self.clear()

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
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(15, 3, 15, 3)
            layout.addWidget(jump_to_button)
            button_widget.setLayout(layout)

            jump_to_button.clicked.connect(
                partial(self.jump_button_clicked.emit, event.time))
            self.setCellWidget(i, 2, button_widget)

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     self.setColumnWidth(0, self.width() / 3 - 20)
    #     self.setColumnWidth(1, self.width() / 3 - 20)
    #     self.setColumnWidth(2, self.width() / 3 - 20)

class EventsTableFilters(QFrame):
    edge_hit_filter_signal = pyqtSignal(bool)
    snaps_filter_signal = pyqtSignal(bool)
    misses_filter_signal = pyqtSignal(bool)
    hit_100_filter_signal = pyqtSignal(bool)
    hit_50_filter_signal = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.Popup)

        self.setMaximumWidth(300)
        self.setMaximumHeight(100)

        edge_hit_cb = CheckboxSetting("Edge hits:", True)
        edge_hit_cb.state_changed.connect(self.edge_hit_filter_signal)

        snaps_cb = CheckboxSetting("Snaps:", True)
        snaps_cb.state_changed.connect(self.snaps_filter_signal)

        misses_cb = CheckboxSetting("Misses:", True)
        misses_cb.state_changed.connect(self.misses_filter_signal)

        hit_100_cb = CheckboxSetting("100s:", True)
        hit_100_cb.state_changed.connect(self.hit_100_filter_signal)

        hit_50_cb = CheckboxSetting("50s:", True)
        hit_50_cb.state_changed.connect(self.hit_50_filter_signal)

        layout = QVBoxLayout()
        layout.addWidget(edge_hit_cb)
        layout.addWidget(snaps_cb)
        layout.addWidget(misses_cb)
        layout.addWidget(hit_100_cb)
        layout.addWidget(hit_50_cb)
        self.setLayout(layout)
