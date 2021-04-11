from PyQt5.QtWidgets import (QFrame, QPushButton, QSlider, QLabel, QCheckBox,
    QHBoxLayout, QSpinBox, QComboBox, QStyle)
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt, pyqtSignal

# we want most of our clickable widgets to have a pointing hand cursor on hover

class PushButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))

# TODO set pointer cursor on combobox popup list as well, I tried
# https://stackoverflow.com/a/44525625/12164878 but couldn't get it to work
class ComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        # remove WheelFocus from the combobox's focus policy
        # https://stackoverflow.com/a/19382766/12164878
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        # we never want wheel events to scroll the combobox
        event.ignore()

class CheckBox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))


class CheckboxSetting(QFrame):
    state_changed = pyqtSignal(bool)

    def __init__(self, text, start_state):
        super().__init__()

        label = QLabel(text)
        self.checkbox = CheckBox()
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
        self.slider = JumpSlider(Qt.Horizontal)
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
        self.combobox = ComboBox(self)
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


# A slider which moves directly to the clicked position when clicked
# Implementation from https://stackoverflow.com/a/29639127/12164878
class JumpSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mousePressEvent(self, event):
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(),
            self.maximum(), event.x(), self.width()))
        # our code relies on `sliderMoved` in order to only trigger on user
        # input and not when we change the slider's value from the code (we
        # update the slider's value every frame as we progress along the
        # replay). Since the user *has* initiated this movement, emit
        # `sliderMoved` to let our code know.
        # TODO This should probably be done via a custom qsignal
        # (userChangedValue) instead of re-purposing an existing one that wasn't
        # meant for that purpose.
        self.sliderMoved.emit(self.value())

    def mouseMoveEvent(self, event):
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(),
            self.maximum(), event.x(), self.width()))
        self.sliderMoved.emit(self.value())
