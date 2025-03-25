from tempfile import TemporaryDirectory
from threading import Thread

from PyQt6.QtWidgets import QGridLayout, QWidget, QApplication, QSplitter, QFrame
from PyQt6.QtCore import Qt
from circleguard import Mod, KeylessCircleguard
from slider import Library, Beatmap

from circlevis.renderer import Renderer
from circlevis.controls import VisualizerControls
from circlevis.replay_info import ReplayInfo


class Interface(QWidget):
    def __init__(
        self,
        beatmap_info,
        replays,
        events,
        library,
        speeds,
        start_speed,
        paint_info,
        statistic_functions,
        snaps_args,
    ):
        super().__init__()
        self.speeds = speeds
        self.replays = replays
        self.library = library
        self.snaps_args = snaps_args
        self.current_replay_info = None
        # maps `circleguard.Replay` to `circlevis.ReplayInfo`, as its creation
        # is relatively expensive and users might open and close the same info
        # panel multiple times
        self.replay_info_cache = {}

        # we calculate some statistics in the background so users aren't hit
        # with multi-second wait times when accessing replay info. Initialize
        # with `None` so if the replay info *is* accessed before we calculate
        # everything, no harm - `ReplayInfo` will calculate it instead.
        self.replay_statistics_precalculated = {}
        for replay in replays:
            self.replay_statistics_precalculated[replay] = (None, None, None, None)

        # only precalculate statistics if we're visualizing 5 or fewer replays.
        # Otherwise, the thread is too overworked and lags the main draw thread
        # significantly until all statistics are precalculated.
        # TODO This may be resolved properly by using a QThread with a low
        # priority instead, so as not to starve the draw thread. We should be
        # using QThreads instead of python threads regardless.

        if len(replays) <= 5 and False:
            # and here's the thread which will actually start those calculations
            cg_statistics_worked = Thread(target=self.calculate_cg_statistics)
            # allow users to quit before we're done calculating
            cg_statistics_worked.daemon = True
            cg_statistics_worked.start()

        # create our own library in a temp dir if one wasn't passed
        if not self.library:
            # keep a reference so it doesn't get deleted
            self.temp_dir = TemporaryDirectory()
            self.library = Library(self.temp_dir.name)

        self.beatmap = None
        if beatmap_info.beatmap:
            self.beatmap = beatmap_info.beatmap
        elif beatmap_info.path:
            self.beatmap = Beatmap.from_path(beatmap_info.path)
        elif beatmap_info.map_id:
            # TODO move temporary directory creation to slider probably, since
            # this logic is now duplicated here and in circlecore
            self.beatmap = self.library.lookup_by_id(
                beatmap_info.map_id, download=True, save=True
            )

        dt_enabled = any(Mod.DT in replay.mods for replay in replays)
        ht_enabled = any(Mod.HT in replay.mods for replay in replays)
        if dt_enabled:
            start_speed = 1.5
        if ht_enabled:
            start_speed = 0.75

        self.renderer = Renderer(
            self.beatmap, replays, events, start_speed, paint_info, statistic_functions
        )
        self.renderer.update_time_signal.connect(self.update_slider)
        # if the renderer wants to pause itself (eg when the playback hits the
        # end of the replay), we kick it back to us (the `Interface`) so we can
        # also update the pause button's state.
        self.renderer.pause_signal.connect(self.toggle_pause)

        # we want to give `VisualizerControls` the union of all the replay's
        # mods
        mods = Mod.NM
        for replay in replays:
            mods += replay.mods

        self.controls = VisualizerControls(start_speed, mods, replays)
        self.controls.pause_button.clicked.connect(self.toggle_pause)
        self.controls.play_reverse_button.clicked.connect(self.play_reverse)
        self.controls.play_normal_button.clicked.connect(self.play_normal)
        self.controls.next_frame_button.clicked.connect(
            lambda: self.change_frame(reverse=False)
        )
        self.controls.previous_frame_button.clicked.connect(
            lambda: self.change_frame(reverse=True)
        )
        self.controls.speed_up_button.clicked.connect(self.increase_speed)
        self.controls.speed_down_button.clicked.connect(self.lower_speed)
        self.controls.copy_to_clipboard_button.clicked.connect(self.copy_to_clipboard)
        self.controls.time_slider.sliderMoved.connect(self.renderer.seek_to)
        self.controls.time_slider.setRange(
            self.renderer.playback_start, self.renderer.playback_end
        )

        self.controls.raw_view_changed.connect(self.renderer.raw_view_changed)
        self.controls.only_color_keydowns_changed.connect(
            self.renderer.only_color_keydowns_changed
        )
        self.controls.hitobjects_changed.connect(self.renderer.hitobjects_changed)
        self.controls.approach_circles_changed.connect(
            self.renderer.approach_circles_changed
        )
        self.controls.num_frames_changed.connect(self.renderer.num_frames_changed)
        self.controls.draw_hit_error_bar_changed.connect(
            self.renderer.draw_hit_error_bar_changed
        )
        self.controls.circle_size_mod_changed.connect(
            self.renderer.circle_size_mod_changed
        )
        self.controls.show_info_for_replay.connect(self.show_info_panel)

        self.splitter = QSplitter()
        # splitter lays widgets horizontally by default, so combine renderer and
        # controls into one single widget vertically
        self.splitter.addWidget(
            Combined([self.renderer, self.controls], Qt.Orientation.Vertical)
        )

        layout = QGridLayout()
        layout.addWidget(self.splitter, 1, 0, 1, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def play_normal(self):
        self.unpause()
        self.renderer.play_direction = 1
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_slider(self, value):
        self.controls.time_slider.setValue(value)

    def change_by(self, delta):
        self.pause()
        self.renderer.seek_to(self.renderer.clock.time_counter + delta)

    def play_reverse(self):
        self.unpause()
        self.renderer.play_direction = -1
        self.update_speed(abs(self.renderer.clock.current_speed))

    def update_speed(self, speed):
        self.renderer.clock.change_speed(speed * self.renderer.play_direction)

    def change_frame(self, reverse):
        self.pause()
        self.renderer.search_nearest_frame(reverse=reverse)

    def toggle_pause(self):
        if self.renderer.paused:
            self.unpause()
        else:
            self.pause()

    def pause(self):
        self.controls.set_paused_state(True)
        self.renderer.pause()

    def unpause(self):
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
        r1 = self.replays[0]
        if len(self.replays) == 2:
            r2 = self.replays[1]
            user_str = f"u={r1.user_id}&m1={r1.mods.short_name()}&u2={r2.user_id}&m2={r2.mods.short_name()}"
        else:
            user_str = f"u={r1.user_id}&m1={r1.mods.short_name()}"

        clipboard.setText(f"circleguard://m={r1.map_id}&{user_str}&t={timestamp}")

    def show_info_panel(self, replay):
        """
        Shows an info panel containing stats about the replay to the left of the
        renderer. The visualizer window will expand to accomodate for this extra
        space.
        """
        if replay in self.replay_info_cache:
            replay_info = self.replay_info_cache[replay]
            replay_info.show()
        else:
            ur, frametime, snaps, judgments = self.replay_statistics_precalculated[
                replay
            ]
            replay_info = ReplayInfo(
                replay,
                self.library.path,
                ur,
                frametime,
                snaps,
                judgments,
                self.snaps_args,
            )
            replay_info.seek_to.connect(self.seek_to)

        # don't show two of the same info panels at once
        if self.current_replay_info is not None:
            # if they're the same, don't change anything
            if replay_info == self.current_replay_info:
                return
            # Otherwise, close the current one and show the new one.
            # simulate a "close" button press
            self.current_replay_info.close_button_clicked.emit()

        def remove_replay_info():
            replay_info.hide()
            self.current_replay_info = None

        replay_info.close_button_clicked.connect(remove_replay_info)
        self.splitter.insertWidget(0, replay_info)
        self.current_replay_info = replay_info
        self.replay_info_cache[replay] = replay_info

    def seek_to(self, time):
        self.pause()
        self.renderer.seek_to(time)

    def calculate_cg_statistics(self):
        cg = KeylessCircleguard()
        for replay in self.replays:
            ur = None
            judgments = None
            if cg.map_available(replay):
                ur = cg.ur(replay)
                judgments = cg.judgments(replay)

            frametime = cg.frametime(replay)
            snaps = cg.snaps(replay, **self.snaps_args)
            self.replay_statistics_precalculated[replay] = (
                ur,
                frametime,
                snaps,
                judgments,
            )


class Combined(QFrame):
    def __init__(self, widgets, direction):
        """
        combines all the widgets in `widgets` according to `direction`, which is
        one of `Qt.Orientation.Horizontal` or `Qt.Orientation.Vertical`
        """
        super().__init__()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        if direction not in [Qt.Orientation.Horizontal, Qt.Orientation.Vertical]:
            raise ValueError(
                "`direction` must be one of [Qt.Orientation.Horizontal, "
                "Qt.Orientation.Vertical]"
            )

        for i, widget in enumerate(widgets):
            if direction == Qt.Orientation.Horizontal:
                layout.addWidget(widget, 0, i, 1, 1)
            else:
                layout.addWidget(widget, i, 0, 1, 1)

        self.setLayout(layout)
