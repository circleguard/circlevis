from tempfile import TemporaryDirectory

from PyQt5.QtWidgets import QGridLayout, QWidget, QApplication, QSplitter, QFrame
from PyQt5.QtCore import Qt
from circleguard import Mod
from slider import Library, Beatmap

from circlevis.renderer import Renderer
from circlevis.controls import VisualizerControls
from circlevis.replay_info import ReplayInfo

class Interface(QWidget):
    def __init__(self, beatmap_info, replays, events, library, speeds, \
        start_speed, paint_info, statistic_functions):
        super().__init__()
        self.speeds = speeds
        self.replays = replays
        self.info_panel_showing = False

        self.beatmap = None
        if beatmap_info.path:
            self.beatmap = Beatmap.from_path(beatmap_info.path)
        elif beatmap_info.map_id:
            # library is nullable - None means we define our own (and don't care about saving)
            # TODO move temporary directory creation to slider probably, since
            # this logic is now duplicated here and in circlecore
            if library:
                self.beatmap = library.lookup_by_id(beatmap_info.map_id, download=True, save=True)
            else:
                temp_dir = TemporaryDirectory()
                self.beatmap = Library(temp_dir.name).lookup_by_id(beatmap_info.map_id, download=True)


        self.renderer = Renderer(self.beatmap, replays, events, library, \
            start_speed, paint_info, statistic_functions)
        self.renderer.update_time_signal.connect(self.update_slider)
        # if the renderer wants to pause itself (eg when the playback hits the
        # end of the replay), we kick it back to us (the `Interface`) so we can
        # also update the pause button's state.
        self.renderer.pause_signal.connect(self.pause)

        # we want to give `VisualizerControls` the union of all the replay's
        # mods
        mods = Mod.NM
        for replay in replays:
            mods += replay.mods

        self.controls = VisualizerControls(start_speed, mods, replays)
        self.controls.pause_button.clicked.connect(self.pause)
        self.controls.play_reverse_button.clicked.connect(self.play_reverse)
        self.controls.play_normal_button.clicked.connect(self.play_normal)
        self.controls.next_frame_button.clicked.connect(lambda: self.change_frame(reverse=False))
        self.controls.previous_frame_button.clicked.connect(lambda: self.change_frame(reverse=True))
        self.controls.speed_up_button.clicked.connect(self.increase_speed)
        self.controls.speed_down_button.clicked.connect(self.lower_speed)
        self.controls.copy_to_clipboard_button.clicked.connect(self.copy_to_clipboard)
        self.controls.time_slider.sliderMoved.connect(self.renderer.seek_to)
        self.controls.time_slider.setRange(0, self.renderer.playback_len)

        self.controls.raw_view_changed.connect(self.renderer.raw_view_changed)
        self.controls.only_embolden_keydowns_changed.connect(self.renderer.only_embolden_keydowns_changed)
        self.controls.hitobjects_changed.connect(self.renderer.hitobjects_changed)
        self.controls.approach_circles_changed.connect(self.renderer.approach_circles_changed)
        self.controls.num_frames_changed.connect(self.renderer.num_frames_changed)
        self.controls.circle_size_mod_changed.connect(self.renderer.circle_size_mod_changed)
        self.controls.show_info_for_replay.connect(self.show_info_panel)


        self.splitter = QSplitter()
        # splitter lays widgets horizontally by default, so combine renderer and
        # controls into one single widget vertically
        self.splitter.addWidget(Combined([self.renderer, self.controls], Qt.Vertical))

        layout = QGridLayout()
        layout.addWidget(self.splitter, 1, 0, 1, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def play_normal(self):
        self.renderer.resume()
        self.controls.set_paused_state(False)
        self.renderer.play_direction = 1
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_slider(self, value):
        self.controls.time_slider.setValue(value)

    def play_reverse(self):
        self.renderer.resume()
        self.controls.set_paused_state(False)
        self.renderer.play_direction = -1
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_speed(self, speed):
        self.renderer.clock.change_speed(speed * self.renderer.play_direction)

    def change_frame(self, reverse):
        # only change pause state if we're not paused, this way we don't unpause
        # when changing frames
        if not self.renderer.paused:
            self.pause()
        self.renderer.search_nearest_frame(reverse=reverse)

    def pause(self):
        if self.renderer.paused:
            self.controls.set_paused_state(False)
            self.renderer.resume()
        else:
            self.controls.set_paused_state(True)
            self.renderer.pause()

    def force_pause(self):
        self.controls.set_paused_state(True)
        self.renderer.pause()

    def force_unpause(self):
        self.controls.set_paused_state(False)
        self.renderer.resume()

    def lower_speed(self):
        index = self.speeds.index(abs(self.renderer.clock.current_speed))
        if index == 0:
            return
        speed = self.speeds[index - 1]
        self.controls.speed_label.setText(str(speed) + "x")
        self.update_speed(speed)

    def increase_speed(self):
        index = self.speeds.index(abs(self.renderer.clock.current_speed))
        if index == len(self.speeds) - 1:
            return
        speed = self.speeds[index + 1]
        self.controls.speed_label.setText(str(speed) + "x")
        self.update_speed(speed)

    def copy_to_clipboard(self):
        timestamp = int(self.renderer.clock.get_time())
        clipboard = QApplication.clipboard()

        # TODO accomodate arbitrary numbers of replays (including 0 replays)
        if len(self.replays) == 2:
            user_str = f"u={self.replays[0].user_id}&u2={self.replays[1].user_id}"
        else:
            user_str = f"u={self.replays[0].user_id}"

        clipboard.setText(f"circleguard://m={self.replays[0].map_id}&{user_str}&t={timestamp}")

    def show_info_panel(self, replay):
        """
        Shows an info panel containing stats about the replay to the left of the
        renderer. The visualizer window will expand to accomodate for this extra
        space.
        """
        # don't show two info panels at once
        if self.info_panel_showing:
            return

        replay_info = ReplayInfo(replay, self.beatmap)
        replay_info.seek_to.connect(self.renderer.seek_to)
        self.splitter.insertWidget(0, replay_info)
        self.info_panel_showing = True


class Combined(QFrame):
    def __init__(self, widgets, direction):
        """
        combines all the widgets in `widgets` according to `direction`, which is
        one of `Qt.Horizontal` or `Qt.Vertical`
        """
        super().__init__()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        if direction not in [Qt.Horizontal, Qt.Vertical]:
            raise ValueError("`direction` must be one of [Qt.Horizontal, "
                "Qt.Vertical]")

        for i, widget in enumerate(widgets):
            if direction == Qt.Horizontal:
                layout.addWidget(widget, 0, i, 1, 1)
            else:
                layout.addWidget(widget, i, 0, 1, 1)

        self.setLayout(layout)
