from PyQt5.QtWidgets import QVBoxLayout, QWidget, QApplication

from circlevis.renderer import Renderer
from circlevis.controls import VisualizerControls

class Interface(QWidget):
    def __init__(self, beatmap_info, replays, events, library, speeds, \
        start_speed, paint_info, statistic_functions):
        super().__init__()
        self.speeds = speeds
        self.replays = replays

        self.renderer = Renderer(beatmap_info, replays, events, library, \
            start_speed, paint_info, statistic_functions)
        self.renderer.update_time_signal.connect(self.update_slider)
        # if the renderer wants to pause itself (eg when the playback hits the
        # end of the replay), we kick it back to us (the `Interface`) so we can
        # also update the pause button's state.
        self.renderer.pause_signal.connect(self.pause)

        self.controls = VisualizerControls(start_speed)
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
        self.controls.hitobjects_changed.connect(self.renderer.hitobjects_changed)
        self.controls.approach_circles_changed.connect(self.renderer.approach_circles_changed)
        self.controls.num_frames_changed.connect(self.renderer.num_frames_changed)


        layout = QVBoxLayout()
        layout.addWidget(self.renderer)
        layout.addWidget(self.controls)
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
