from PyQt6.QtWidgets import (QFrame, QGridLayout, QLabel, QVBoxLayout)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from circleguard import Mod, Replay

from circlevis.utils import resource_path
from circlevis.widgets import (JumpSlider, PushButton, CheckboxSetting,
    ComboBoxSetting, SliderSetting, ComboBox)

class VisualizerControls(QFrame):
    raw_view_changed = pyqtSignal(bool)
    only_color_keydowns_changed = pyqtSignal(bool)
    hitobjects_changed = pyqtSignal(bool)
    approach_circles_changed = pyqtSignal(bool)
    num_frames_changed = pyqtSignal(int)
    draw_hit_error_bar_changed = pyqtSignal(bool)
    circle_size_mod_changed = pyqtSignal(str)

    show_info_for_replay = pyqtSignal(Replay)

    def __init__(self, speed, mods, replays):
        super().__init__()
        self.replays = replays
        self.time_slider = JumpSlider(Qt.Orientation.Horizontal)
        self.time_slider.setValue(0)
        self.time_slider.setFixedHeight(20)
        self.time_slider.setStyleSheet("outline: none;")

        self.play_reverse_button = PushButton()
        self.play_reverse_button.setIcon(QIcon(resource_path("play_reverse.png")))
        self.play_reverse_button.setFixedSize(20, 20)
        self.play_reverse_button.setToolTip("Play in reverse")

        self.play_normal_button = PushButton()
        self.play_normal_button.setIcon(QIcon(resource_path("play_normal.png")))
        self.play_normal_button.setFixedSize(20, 20)
        self.play_normal_button.setToolTip("Play normally")

        self.next_frame_button = PushButton()
        self.next_frame_button.setIcon(QIcon(resource_path("frame_next.png")))
        self.next_frame_button.setFixedSize(20, 20)
        self.next_frame_button.setToolTip("Move forward one frame")

        self.previous_frame_button = PushButton()
        self.previous_frame_button.setIcon(QIcon(resource_path("frame_back.png")))
        self.previous_frame_button.setFixedSize(20, 20)
        self.previous_frame_button.setToolTip("Move backward one frame")

        self.pause_button = PushButton()
        self.pause_button.setIcon(QIcon(resource_path("pause.png")))
        self.pause_button.setFixedSize(20, 20)
        self.pause_button.setToolTip("Pause / Play")

        self.copy_to_clipboard_button = PushButton()
        self.copy_to_clipboard_button.setIcon(QIcon(resource_path("clipboard.svg")))
        self.copy_to_clipboard_button.setFixedSize(20, 20)
        self.copy_to_clipboard_button.setToolTip("Copy timestamped url to clipboard")

        self.speed_label = QLabel(f"{speed}x")
        self.speed_label.setFixedSize(40, 20)
        self.speed_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

        # info widget is a button when we only have one replay, and a combobox
        # otherwise to let the user choose which replay to see the info for
        if len(replays) == 1:
            self.info_widget = PushButton()
            self.info_widget.setIcon(QIcon(resource_path("info.png")))
            self.info_widget.setFixedSize(20, 20)
            self.info_widget.setToolTip("Replay information")
            self.info_widget.clicked.connect(self.info_button_clicked)
        else:
            self.info_widget = ComboBox()
            self.info_widget.setInsertPolicy(ComboBox.InsertPolicy.NoInsert)
            self.info_widget.addItem(QIcon(resource_path("info.png")), "")
            self.info_widget.setFixedSize(45, 20)
            self.info_widget.setToolTip("Replay information")
            self.info_widget.activated.connect(self.info_combobox_activated)
            for replay in replays:
                self.info_widget.addItem(replay.username, replay)


        self.settings_button = PushButton()
        self.settings_button.setIcon(QIcon(resource_path("settings_wheel.png")))
        self.settings_button.setFixedSize(20, 20)
        self.settings_button.setToolTip("Open settings")
        self.settings_button.clicked.connect(self.settings_button_clicked)

        self.settings_popup = SettingsPopup(self, mods)
        self.settings_popup.raw_view_changed.connect(self.raw_view_changed)
        self.settings_popup.only_color_keydowns_changed.connect(self.only_color_keydowns_changed)
        self.settings_popup.hitobjects_changed.connect(self.hitobjects_changed)
        self.settings_popup.approach_circles_changed.connect(self.approach_circles_changed)
        self.settings_popup.num_frames_changed.connect(self.num_frames_changed)
        self.settings_popup.draw_hit_error_bar_changed.connect(self.draw_hit_error_bar_changed)
        self.settings_popup.circle_size_mod_changed.connect(self.circle_size_mod_changed)

        self.speed_up_button = PushButton()
        self.speed_up_button.setIcon(QIcon(resource_path("speed_up.png")))
        self.speed_up_button.setFixedSize(20, 20)
        self.speed_up_button.setToolTip("Increase speed")

        self.speed_down_button = PushButton()
        self.speed_down_button.setIcon(QIcon(resource_path("speed_down.png")))
        self.speed_down_button.setFixedSize(20, 20)
        self.speed_down_button.setToolTip("Decrease speed")

        layout = QGridLayout()
        layout.addWidget(self.play_reverse_button, 16, 0, 1, 1)
        layout.addWidget(self.previous_frame_button, 16, 1, 1, 1)
        layout.addWidget(self.pause_button, 16, 2, 1, 1)
        layout.addWidget(self.next_frame_button, 16, 3, 1, 1)
        layout.addWidget(self.play_normal_button, 16, 4, 1, 1)
        layout.addWidget(self.speed_down_button, 16, 5, 1, 1)
        layout.addWidget(self.speed_up_button, 16, 6, 1, 1)
        layout.addWidget(self.speed_label, 16, 7, 1, 1)
        layout.addWidget(self.time_slider, 16, 8, 1, 9)
        layout.addWidget(self.info_widget, 16, 17, 1, 1)
        layout.addWidget(self.settings_button, 16, 18, 1, 1)
        layout.addWidget(self.copy_to_clipboard_button, 16, 19, 1, 1)
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
        self.settings_popup.setGeometry(
            int(global_pos.x() - (popup_width / 2) - 44),
            int(global_pos.y() - popup_height - 6),
            popup_width, popup_height
        )

    def info_combobox_activated(self):
        # don't do anything if they selected the default entry
        if self.info_widget.currentIndex() == 0:
            return
        replay = self.info_widget.currentData()
        # reset to default entry
        self.info_widget.setCurrentIndex(0)
        self.show_info_for_replay.emit(replay)


class SettingsPopup(QFrame):
    raw_view_changed = pyqtSignal(bool)
    only_color_keydowns_changed = pyqtSignal(bool)
    hitobjects_changed = pyqtSignal(bool)
    approach_circles_changed = pyqtSignal(bool)
    num_frames_changed = pyqtSignal(int)
    draw_hit_error_bar_changed = pyqtSignal(bool)
    circle_size_mod_changed = pyqtSignal(str)

    def __init__(self, parent, mods):
        super().__init__(parent)
        # we're technically a window, but we don't want to be shown as such to
        # the user, so hide our window features (like the top bar)
        self.setWindowFlags(Qt.WindowType.Popup)

        self.setMaximumWidth(300)
        self.setMaximumHeight(100)

        self.raw_view_cb = CheckboxSetting("Raw view:", False)
        self.raw_view_cb.state_changed.connect(self.raw_view_changed)

        self.only_color_keydowns = CheckboxSetting("Only color keydowns:", False)
        self.only_color_keydowns.state_changed.connect(self.only_color_keydowns_changed)

        self.hitobjects_cb = CheckboxSetting("Draw hitobjects:", True)
        self.hitobjects_cb.state_changed.connect(self.hitobjects_changed)

        self.approach_circles_cb = CheckboxSetting("Draw approach circles:", True)
        self.approach_circles_cb.state_changed.connect(self.approach_circles_changed)

        start_circle_size = "EZ" if Mod.EZ in mods else "HR" if Mod.HR in mods else "NM"
        self.circle_size_mod_cmb = ComboBoxSetting("Adjust mods:", start_circle_size, ["EZ", "NM", "HR"])
        self.circle_size_mod_cmb.value_changed.connect(self.circle_size_mod_changed)

        self.num_frames_slider = SliderSetting("Num. frames:", 15, 1, 30)
        self.num_frames_slider.value_changed.connect(self.num_frames_changed)

        self.hit_error_bar_cb = CheckboxSetting("Draw hit error bar:", True)
        self.hit_error_bar_cb.state_changed.connect(self.draw_hit_error_bar_changed)

        layout = QVBoxLayout()
        layout.addWidget(self.raw_view_cb)
        layout.addWidget(self.only_color_keydowns)
        layout.addWidget(self.hitobjects_cb)
        layout.addWidget(self.approach_circles_cb)
        layout.addWidget(self.hit_error_bar_cb)
        layout.addWidget(self.circle_size_mod_cmb)
        layout.addWidget(self.num_frames_slider)
        self.setLayout(layout)
