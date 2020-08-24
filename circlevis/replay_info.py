from functools import partial

from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QFrame,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from circleguard import KeylessCircleguard, Snap

class ReplayInfoWindow(QMainWindow):
    def __init__(self, replay):
        super().__init__()
        replay_info = ReplayInfo(replay)
        self.setCentralWidget(replay_info)


class ReplayInfo(QFrame):
    seek_to = pyqtSignal(int)

    def __init__(self, replay):
        super().__init__()
        # replay is already loaded so we don't need an api key
        circleguard = KeylessCircleguard()

        mods = replay.mods.short_name()

        info_label = QLabel(f"{replay.username} +{mods} on map {replay.map_id}")

        ur = circleguard.ur(replay, single=True).ur
        ur_label = QLabel(f"<b>cvUR:</b> {ur:0.2f}")

        frametime = circleguard.frametime(replay, single=True).frametime
        frametime_label = QLabel(f"<b>cv frametime:</b> {frametime:0.2f}")

        events = []
        snaps = circleguard.snaps(replay, single=True).snaps

        events.extend(snaps)

        events_table = EventsTable(events)
        events_table.jump_button_clicked.connect(self.seek_to)

        # don't let ourselves get a horizontal scrollbar on the table by being
        # too small, + 54 to account for the vertical scrollbar I think?
        self.setMinimumWidth(events_table.horizontalHeader().length() + events_table.verticalHeader().width() + 54)

        layout = QVBoxLayout()
        layout.addWidget(info_label)
        layout.addWidget(ur_label)
        layout.addWidget(frametime_label)
        layout.addSpacing(180)
        layout.addWidget(events_table)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)


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
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)

        type_dict = {
            Snap: "snap"
        }

        self.setRowCount(len(events))

        for i, event in enumerate(events):
            type_string = type_dict[type(event)]
            item = QTableWidgetItem(type_string)
            self.setItem(i, 0, item)

            item = QTableWidgetItem(str(event.time))
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

            jump_to_button.clicked.connect(partial(self.jump_button_clicked.emit, event.time))
            self.setCellWidget(i, 2, button_widget)

        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 70)
        self.setColumnWidth(2, 90)

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     self.setColumnWidth(0, self.width() / 3 - 20)
    #     self.setColumnWidth(1, self.width() / 3 - 20)
    #     self.setColumnWidth(2, self.width() / 3 - 20)
