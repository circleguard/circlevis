# Circlevis

Circlevis is the replay viewer (aka visualizer) in [Circleguard](https://github.com/circleguard/circleguard). It was split off into its own repository to allow other projects to use it, should they so choose.

Circlevis is a [Qt](https://doc.qt.io/) widget, and will only work if you are using the Qt (or [pyqt](https://pypi.org/project/PyQt5/), as we are) GUI framwork.

## Installation

Circlevis can be installed from pip:

```bash
pip install circlevis
```

## Usage

Circlevis can be used in two ways:

### VisualizerApp

The easiest way is to instantiate a `VisualizerApp`, which subclasses `QApplication` so you don't have to create a main application yourself. This is best for quick visualization, when you only want to open circlevis and nothing else.

```python
from circleguard import *
from circlevis import VisualizerApp, BeatmapInfo

cg = Circleguard("key")
r = ReplayMap(509610, 6304246)
# replays must be loaded before passed to the visualizer
cg.load(r)

# BeatmapInfo tells circlevis how it should load the beatmap before it displays
# it. You can pass either a map id (in which case circlevis will download the map
# from osu!'s servers) or a path to a .osu file (in which case circlevis will
# load the beatmap from that file).
# If you don't want any beatmap to be displayed, instantiate an empty BeatmapInfo
# (bm = BeatmapInfo()) and pass that to the visualizer.
bm = BeatmapInfo(map_id=r.map_id)
app = VisualizerApp(bm, replays=[r])
# this calls qt's `exec` function, which shows the application and enters the
# gui run loop, blocking any code after this call.
app.exec()
```

You can also visualize only a map, without any replay:

```python
from circlevis import VisualizerApp, BeatmapInfo

bm = BeatmapInfo(map_id=509610)
app = VisualizerApp(bm)
app.exec()
```

### Visualizer

If you want to integrate the visualizer into an existing project (which already has its own `QApplication`), you should instead instantiate the `Visualizer` class, which is a normal `Qt` widget and can be added to a layout like any other widget.

```python
from circleguard import *
from circlevis import Visualizer, BeatmapInfo

cg = Circleguard("key")
r = ReplayMap(509610, 6304246)
cg.load(r)

bm = BeatmapInfo(map_id=r.map_id)
visualizer_widget = Visualizer(bm, replays=[r])

# add visualizer_widget to your layout here
```

### Other Arguments

Both `VisualizerApp` and `Visualizer` can take several optional arguments:

* `events` - a list of timestamps (in ms). If a frame with that timestamp is found in the replay, it is colored gold
* `library` - A [slider](https://github.com/llllllllll/slider) `Library` class, which will be used instead of creating a new one if passed
* `speeds` - a list of possible speeds the visualizer can play at. These can be switched between in real time with the speed up or speed down icons on the visualizer, or by pressing the up or down keys
* `start_speed` - which speed to start playback at. This value must be in `speeds`
* `paint_info` - whether to draw information about the map and replays in the upper left hand corner

## Classifier

Circlevis also provides a `Classifier` class, which builds on the visualizer to provide an easy way to batch classify replays one at a time. For instance, imagine you want to go through a map's leaderboard and assign a "cursordance score" to each replay, depending on how often the user cursordanced.

To use, you need a list of hotkeys that you will use to control the classification of the replays, a circleguard instance, and a list of replays. Here's an example for the aforementioned "cursordance scoring" use case, where you can assign replays a score from 1 to 10:

```python
from collections import defaultdict
from circleguard import Circleguard
from circlevis import Classifier, ClassifierHotkey

cg = Circleguard("api_key")

class JudgeClassifier(Classifier):
    def __init__(self, replays, cg):

        self.scores = defaultdict(list)

        hotkeys = [
            ClassifierHotkey(Qt.Key_1, lambda r: self.assign_score(1, r)),
            ClassifierHotkey(Qt.Key_2, lambda r: self.assign_score(2, r)),
            ClassifierHotkey(Qt.Key_3, lambda r: self.assign_score(3, r)),
            ClassifierHotkey(Qt.Key_4, lambda r: self.assign_score(4, r)),
            ClassifierHotkey(Qt.Key_5, lambda r: self.assign_score(5, r)),
            ClassifierHotkey(Qt.Key_6, lambda r: self.assign_score(6, r)),
            ClassifierHotkey(Qt.Key_7, lambda r: self.assign_score(7, r)),
            ClassifierHotkey(Qt.Key_8, lambda r: self.assign_score(8, r)),
            ClassifierHotkey(Qt.Key_9, lambda r: self.assign_score(9, r)),
            ClassifierHotkey(Qt.Key_0, lambda r: self.assign_score(10, r)),
        ]
        super().__init__(replays, cg, hotkeys)

    def assign_score(self, score, replay):
        print(f"scoring {replay} as a {score}")
        self.scores[score].append(replay)
        # show the next replay now that we've scored this one
        self.next_replay()

    def done(self):
        print(f"final scores: {self.scores}")

replays = cg.Map(221777, "1-10")
classifier = JudgeClassifier(replays, cg)
classifier.start()
```
