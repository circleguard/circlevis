from PyQt5.QtWidgets import (QFrame, QPushButton, QSlider, QGridLayout, QLabel,
    QVBoxLayout, QCheckBox, QHBoxLayout)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal

from circlevis.utils import resource_path

class VisualizerControls(QFrame):
    raw_view_changed = pyqtSignal(bool)

    def __init__(self, speed):
        super().__init__()
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setValue(0)
        self.time_slider.setFixedHeight(20)
        self.time_slider.setStyleSheet("outline: none;")

        self.play_reverse_button = QPushButton()
        self.play_reverse_button.setIcon(QIcon(resource_path("play_reverse.png")))
        self.play_reverse_button.setFixedSize(20, 20)
        self.play_reverse_button.setToolTip("Plays visualization in reverse")

        self.play_normal_button = QPushButton()
        self.play_normal_button.setIcon(QIcon(resource_path("play_normal.png")))
        self.play_normal_button.setFixedSize(20, 20)
        self.play_normal_button.setToolTip("Plays visualization in normally")

        self.next_frame_button = QPushButton()
        self.next_frame_button.setIcon(QIcon(resource_path("frame_next.png")))
        self.next_frame_button.setFixedSize(20, 20)
        self.next_frame_button.setToolTip("Displays next frame")

        self.previous_frame_button = QPushButton()
        self.previous_frame_button.setIcon(QIcon(resource_path("frame_back.png")))
        self.previous_frame_button.setFixedSize(20, 20)
        self.previous_frame_button.setToolTip("Displays previous frame")

        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon(resource_path("pause.png")))
        self.pause_button.setFixedSize(20, 20)
        self.pause_button.setToolTip("Pause visualization")

        self.copy_to_clipboard_button = QPushButton()
        self.copy_to_clipboard_button.setIcon(QIcon(resource_path("clipboard.svg")))
        self.copy_to_clipboard_button.setFixedSize(20, 20)
        self.copy_to_clipboard_button.setToolTip("Copy timestamped url to clipboard")

        self.speed_label = QLabel(f"{speed}x")
        self.speed_label.setFixedSize(40, 20)
        self.speed_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(20, 20)
        self.settings_button.setToolTip("Open settings")
        self.settings_button.clicked.connect(self.settings_button_clicked)

        self.settings_popup = SettingsPopup()
        self.settings_popup.raw_view_changed.connect(self.raw_view_changed)

        self.speed_up_button = QPushButton()
        self.speed_up_button.setIcon(QIcon(resource_path("speed_up.png")))
        self.speed_up_button.setFixedSize(20, 20)
        self.speed_up_button.setToolTip("Speed up")

        self.speed_down_button = QPushButton()
        self.speed_down_button.setIcon(QIcon(resource_path("speed_down.png")))
        self.speed_down_button.setFixedSize(20, 20)
        self.speed_down_button.setToolTip("Speed down")

        layout = QGridLayout()
        layout.addWidget(self.play_reverse_button, 16, 0, 1, 1)
        layout.addWidget(self.previous_frame_button, 16, 1, 1, 1)
        layout.addWidget(self.pause_button, 16, 2, 1, 1)
        layout.addWidget(self.next_frame_button, 16, 3, 1, 1)
        layout.addWidget(self.play_normal_button, 16, 4, 1, 1)
        layout.addWidget(self.copy_to_clipboard_button, 16, 5, 1, 1)
        layout.addWidget(self.time_slider, 16, 6, 1, 9)
        layout.addWidget(self.speed_label, 16, 15, 1, 1)
        layout.addWidget(self.settings_button, 16, 16, 1, 1)
        layout.addWidget(self.speed_down_button, 16, 17, 1, 1)
        layout.addWidget(self.speed_up_button, 16, 18, 1, 1)
        layout.setContentsMargins(5, 0, 5, 5)
        self.setLayout(layout)
        self.setFixedHeight(25)

    def set_paused_state(self, paused):
        icon = "play.png" if paused else "pause.png"
        self.pause_button.setIcon(QIcon(resource_path(icon)))

    def settings_button_clicked(self):
        global_pos = self.mapToGlobal(self.settings_button.pos())
        self.settings_popup.setGeometry(global_pos.x() - (SettingsPopup.WIDTH / 2),\
            global_pos.y() - ((25 / 2) + SettingsPopup.HEIGHT), SettingsPopup.WIDTH,\
            SettingsPopup.HEIGHT)
        self.settings_popup.show()


class SettingsPopup(QFrame):
    raw_view_changed = pyqtSignal(bool)

    WIDTH = 200
    HEIGHT = 60

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Popup)
        self.raw_view_checkbox = CheckboxSetting("Raw view:")
        self.raw_view_checkbox.state_changed.connect(self.raw_view_changed)
        self.settings_slider = QSlider(Qt.Horizontal)

        layout = QVBoxLayout()
        layout.addWidget(self.raw_view_checkbox)
        layout.addWidget(self.settings_slider)
        self.setLayout(layout)


class CheckboxSetting(QFrame):
    state_changed = pyqtSignal(bool)

    def __init__(self, text):
        super().__init__()

        label = QLabel(text)
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._state_changed)

        layout = QHBoxLayout()
        layout.addWidget(label, 3)
        layout.addWidget(self.checkbox, 1)
        self.setLayout(layout)

    def checked(self):
        return self.checkbox.isChecked()

    def _state_changed(self, state):
        # convert from qt's CheckState enum to a bool
        self.state_changed.emit(state == Qt.CheckState.Checked) # pylint: disable=no-member
