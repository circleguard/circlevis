from PyQt5.QtWidgets import (QFrame, QPushButton, QSlider, QGridLayout, QLabel,
    QVBoxLayout, QCheckBox, QHBoxLayout, QSpinBox, QComboBox)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from circleguard import Mod, Replay

from circlevis.utils import resource_path

class VisualizerControls(QFrame):
    raw_view_changed = pyqtSignal(bool)
    only_embolden_keydowns_changed = pyqtSignal(bool)
    hitobjects_changed = pyqtSignal(bool)
    approach_circles_changed = pyqtSignal(bool)
    num_frames_changed = pyqtSignal(int)
    circle_size_mod_changed = pyqtSignal(str)

    show_info_for_replay = pyqtSignal(Replay)

    def __init__(self, speed, mods, replays):
        super().__init__()
        self.replays = replays

        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setValue(0)
        self.time_slider.setFixedHeight(20)
        self.time_slider.setStyleSheet("outline: none;")

        self.play_reverse_button = QPushButton()
        self.play_reverse_button.setIcon(QIcon(resource_path("play_reverse.png")))
        self.play_reverse_button.setFixedSize(20, 20)
        self.play_reverse_button.setToolTip("Play in reverse")

        self.play_normal_button = QPushButton()
        self.play_normal_button.setIcon(QIcon(resource_path("play_normal.png")))
        self.play_normal_button.setFixedSize(20, 20)
        self.play_normal_button.setToolTip("Play normally")

        self.next_frame_button = QPushButton()
        self.next_frame_button.setIcon(QIcon(resource_path("frame_next.png")))
        self.next_frame_button.setFixedSize(20, 20)
        self.next_frame_button.setToolTip("Move forward one frame")

        self.previous_frame_button = QPushButton()
        self.previous_frame_button.setIcon(QIcon(resource_path("frame_back.png")))
        self.previous_frame_button.setFixedSize(20, 20)
        self.previous_frame_button.setToolTip("Move backward one frame")

        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon(resource_path("pause.png")))
        self.pause_button.setFixedSize(20, 20)
        self.pause_button.setToolTip("Pause / Play")

        self.copy_to_clipboard_button = QPushButton()
        self.copy_to_clipboard_button.setIcon(QIcon(resource_path("clipboard.svg")))
        self.copy_to_clipboard_button.setFixedSize(20, 20)
        self.copy_to_clipboard_button.setToolTip("Copy timestamped url to clipboard")

        self.speed_label = QLabel(f"{speed}x")
        self.speed_label.setFixedSize(40, 20)
        self.speed_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        self.info_button = QPushButton()
        self.info_button.setIcon(QIcon(resource_path("info")))
        self.info_button.setFixedSize(20, 20)
        self.info_button.setToolTip("Replay information")
        self.info_button.clicked.connect(self.info_button_clicked)

        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(resource_path("settings_wheel.png")))
        self.settings_button.setFixedSize(20, 20)
        self.settings_button.setToolTip("Open settings")
        self.settings_button.clicked.connect(self.settings_button_clicked)

        self.settings_popup = SettingsPopup(mods)
        self.settings_popup.raw_view_changed.connect(self.raw_view_changed)
        self.settings_popup.only_embolden_keydowns_changed.connect(self.only_embolden_keydowns_changed)
        self.settings_popup.hitobjects_changed.connect(self.hitobjects_changed)
        self.settings_popup.approach_circles_changed.connect(self.approach_circles_changed)
        self.settings_popup.num_frames_changed.connect(self.num_frames_changed)
        self.settings_popup.circle_size_mod_changed.connect(self.circle_size_mod_changed)

        self.speed_up_button = QPushButton()
        self.speed_up_button.setIcon(QIcon(resource_path("speed_up.png")))
        self.speed_up_button.setFixedSize(20, 20)
        self.speed_up_button.setToolTip("Increase speed")

        self.speed_down_button = QPushButton()
        self.speed_down_button.setIcon(QIcon(resource_path("speed_down.png")))
        self.speed_down_button.setFixedSize(20, 20)
        self.speed_down_button.setToolTip("Decrease speed")

        layout = QGridLayout()
        layout.addWidget(self.play_reverse_button, 16, 0, 1, 1)
        layout.addWidget(self.previous_frame_button, 16, 1, 1, 1)
        layout.addWidget(self.pause_button, 16, 2, 1, 1)
        layout.addWidget(self.next_frame_button, 16, 3, 1, 1)
        layout.addWidget(self.play_normal_button, 16, 4, 1, 1)
        layout.addWidget(self.copy_to_clipboard_button, 16, 5, 1, 1)
        layout.addWidget(self.time_slider, 16, 6, 1, 9)
        layout.addWidget(self.speed_label, 16, 15, 1, 1)
        layout.addWidget(self.info_button, 16, 16, 1, 1)
        layout.addWidget(self.settings_button, 16, 17, 1, 1)
        layout.addWidget(self.speed_down_button, 16, 18, 1, 1)
        layout.addWidget(self.speed_up_button, 16, 19, 1, 1)
        layout.setContentsMargins(5, 0, 5, 5)
        self.setLayout(layout)
        self.setFixedHeight(25)

    def set_paused_state(self, paused):
        icon = "play.png" if paused else "pause.png"
        self.pause_button.setIcon(QIcon(resource_path(icon)))

    def info_button_clicked(self):
        replay = self.replays[0]
        self.show_info_for_replay.emit(replay)

    def settings_button_clicked(self):
        # have to show before setting its geometry because it has some default
        # geometry that doesn't reflect its actual proportions until it's shown
        self.settings_popup.show()
        global_pos = self.mapToGlobal(self.settings_button.pos())
        popup_height = self.settings_popup.size().height()
        popup_width = self.settings_popup.size().width()

        # `x - 44` to not make the popup hang over the right side of the window
        # (aftering centering it horizontally), and `y - 6` to account for the
        # space between the button and the top of the controls row
        self.settings_popup.setGeometry(global_pos.x() - (popup_width / 2) - 44,\
            global_pos.y() - popup_height - 6, popup_width, popup_height)



class SettingsPopup(QFrame):
    raw_view_changed = pyqtSignal(bool)
    only_embolden_keydowns_changed = pyqtSignal(bool)
    hitobjects_changed = pyqtSignal(bool)
    approach_circles_changed = pyqtSignal(bool)
    num_frames_changed = pyqtSignal(int)
    circle_size_mod_changed = pyqtSignal(str)

    def __init__(self, mods):
        super().__init__()
        # we're technically a window, but we don't want to be shown as such to
        # the user, so hide our window features (like the top bar)
        self.setWindowFlags(Qt.Popup)

        self.setMaximumWidth(300)
        self.setMaximumHeight(100)

        self.raw_view_cb = CheckboxSetting("Raw view:", False)
        self.raw_view_cb.state_changed.connect(self.raw_view_changed)

        self.only_embolden_keydowns = CheckboxSetting("Only embolden keydowns:", False)
        self.only_embolden_keydowns.state_changed.connect(self.only_embolden_keydowns_changed)

        self.hitobjects_cb = CheckboxSetting("Draw hitobjects:", True)
        self.hitobjects_cb.state_changed.connect(self.hitobjects_changed)

        self.approach_circles_cb = CheckboxSetting("Draw approach circles:", True)
        self.approach_circles_cb.state_changed.connect(self.approach_circles_changed)

        start_circle_size = "EZ" if Mod.EZ in mods else "HR" if Mod.HR in mods else "NM"
        self.circle_size_mod_cmb = ComboBoxSetting("Adjust circle size:", start_circle_size, ["EZ", "NM", "HR"])
        self.circle_size_mod_cmb.value_changed.connect(self.circle_size_mod_changed)

        self.num_frames_slider = SliderSetting("Num. frames:", 15, 1, 30)
        self.num_frames_slider.value_changed.connect(self.num_frames_changed)

        layout = QVBoxLayout()
        layout.addWidget(self.raw_view_cb)
        layout.addWidget(self.only_embolden_keydowns)
        layout.addWidget(self.hitobjects_cb)
        layout.addWidget(self.approach_circles_cb)
        layout.addWidget(self.circle_size_mod_cmb)
        layout.addWidget(self.num_frames_slider)
        self.setLayout(layout)


class CheckboxSetting(QFrame):
    state_changed = pyqtSignal(bool)

    def __init__(self, text, start_state):
        super().__init__()

        label = QLabel(text)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(start_state)
        self.checkbox.stateChanged.connect(self._state_changed)

        layout = QHBoxLayout()
        layout.addWidget(label, 3)
        layout.addWidget(self.checkbox, 1)
        layout.setContentsMargins(0, 3, 0, 3)
        self.setLayout(layout)

    def checked(self):
        return self.checkbox.isChecked()

    def _state_changed(self, state):
        # convert from qt's CheckState enum to a bool
        self.state_changed.emit(state == Qt.CheckState.Checked) # pylint: disable=no-member


class SliderSetting(QFrame):
    value_changed = pyqtSignal(int)

    def __init__(self, text, start_value, min_, max_):
        super().__init__()

        label = QLabel(text)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setValue(start_value)
        self.slider.setRange(min_, max_)
        self.slider.valueChanged.connect(self._value_changed)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(min_, max_)
        self.spinbox.setSingleStep(1)
        self.spinbox.setValue(start_value)
        self.spinbox.valueChanged.connect(self._value_changed)

        layout = QHBoxLayout()
        layout.addWidget(label, 1)
        layout.addWidget(self.slider, 2)
        layout.addWidget(self.spinbox, 1)
        layout.setContentsMargins(0, 3, 0, 3)
        self.setLayout(layout)

    def _value_changed(self, new_value):
        # keep slider and spinbox in sync
        self.spinbox.setValue(new_value)
        self.slider.setValue(new_value)
        self.value_changed.emit(new_value)


class ComboBoxSetting(QFrame):
    value_changed = pyqtSignal(str)

    def __init__(self, text, start_option, options):
        super().__init__()

        label = QLabel(text)
        self.combobox = QComboBox(self)
        self.combobox.setInsertPolicy(QComboBox.NoInsert)
        self.combobox.setMaximumWidth(70)
        for option in options:
            self.combobox.addItem(option, option)

        index = options.index(start_option)
        self.combobox.setCurrentIndex(index)

        self.combobox.currentIndexChanged.connect(self._value_changed)

        layout = QHBoxLayout()
        layout.addWidget(label, 1)
        layout.addWidget(self.combobox, 3)
        layout.setContentsMargins(0, 3, 0, 3)
        self.setLayout(layout)

    def _value_changed(self):
        self.value_changed.emit(self.combobox.currentData())
