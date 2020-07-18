from PyQt5.QtWidgets import QVBoxLayout, QWidget

from circlevis.renderer import Renderer
from circlevis.visualizer_controls import VisualizerControls

class Interface(QWidget):
    def __init__(self, beatmap_info, replays, events, library, speeds, start_speed, paint_info):
        super().__init__()
        self.speeds = speeds

        self.renderer = Renderer(beatmap_info, replays, events, library, start_speed, paint_info)
        self.renderer.update_time_signal.connect(self.update_slider)

        self.controls = VisualizerControls(start_speed)
        self.controls.pause_button.clicked.connect(self.pause)
        self.controls.play_reverse_button.clicked.connect(self.play_reverse)
        self.controls.play_normal_button.clicked.connect(self.play_normal)
        self.controls.next_frame_button.clicked.connect(lambda: self.change_frame(reverse=False))
        self.controls.previous_frame_button.clicked.connect(lambda: self.change_frame(reverse=True))
        self.controls.speed_up_button.clicked.connect(self.increase_speed)
        self.controls.speed_down_button.clicked.connect(self.lower_speed)
        self.controls.slider.sliderMoved.connect(self.renderer.seek_to)
        self.controls.slider.setRange(0, self.renderer.playback_len)

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
        self.controls.slider.setValue(value)

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
