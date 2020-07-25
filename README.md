# Circlevis

Circlevis is the replay viewer (aka visualizer) in [Circleguard](https://github.com/circleguard/circleguard). It was split off into its own repository to allow other projects to use it, should they so choose.

Circlevis is a [Qt](https://doc.qt.io/) widget, and will only work if you are using the Qt (or [pyqt](https://pypi.org/project/PyQt5/), as we are) GUI framwork.

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
from circleguard import *
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

## Advanced Usage

You may have noticed that both `VisualizerApp` and `Visualizer` take several arguments beyond just a `BeatmapInfo` and list of `Replay`s. A short explanation of each follows:

* events - a list of timestamps (in ms). If a frame with that timestamp is found in the replay, it is colored gold
* library - A [slider](https://github.com/llllllllll/slider) `Library` class, which will be used instead of creating a new one if passed
* speeds - a list of possible speeds the visualizer can play at. These can be switched between in real time with the speed up or speed down icons on the visualizer, or by pressing the up or down keys
* start_speed - which speed to start playback at. This value must be in `speeds`
* paint_info - whether to draw information about the map and replays in the upper left hand corner
