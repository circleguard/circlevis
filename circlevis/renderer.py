import math
import threading
from datetime import timedelta
from dataclasses import dataclass

import numpy as np
from scipy import interpolate
from PyQt5.QtGui import (QBrush, QPen, QColor, QPalette, QPainter, QPainterPath,
    QCursor)
from PyQt5.QtWidgets import QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF, QRectF, QRect
from slider.beatmap import Circle, Slider, Spinner
from circleguard import (Mod, Key, hitradius, hitwindows, JudgmentType,
    KeylessCircleguard)

from circlevis.clock import Timer
from circlevis.player import Player

WIDTH_LINE = 1
WIDTH_LINE_RAW_VIEW = 2
WIDTH_CROSS = 2
WIDTH_CIRCLE_BORDER = 6
LENGTH_CROSS = 6

PEN_WHITE = QPen(QColor(200, 200, 200))
PEN_GRAY = QPen(QColor(75, 75, 75))
PEN_GREY_INACTIVE = QPen(QColor(133, 125, 125))
PEN_HIGHLIGHT = QPen(QColor(230, 212, 92))
PEN_BLANK = QPen(QColor(0, 0, 0, 0))
# for missed hitobjs
PEN_RED_TINT = QPen(QColor(200, 150, 150))

# for hit error bar markers and regions

PEN_BLUE = QPen(QColor(93, 183, 223))
PEN_GREEN = QPen(QColor(127, 221, 71))
PEN_YELLOW = QPen(QColor(211, 175, 90))

BRUSH_BLUE = QBrush(QColor(93, 183, 223))
BRUSH_GREEN = QBrush(QColor(127, 221, 71))
BRUSH_YELLOW = QBrush(QColor(211, 175, 90))


BRUSH_WHITE = QBrush(QColor(200, 200, 200))
BRUSH_GRAY = QBrush(QColor(100, 100, 100))
BRUSH_DARKGRAY = QBrush(QColor(10, 10, 10))
BRUSH_BLANK = QBrush(QColor(0, 0, 0, 0))
# for missed hitobjs
BRUSH_GRAY_RED_TINT = QBrush(QColor(110, 80, 80))

# for judgment indicators. red, yellow, and blue respectively
# TODO use QRadialGradient for judgment brushes to more closely mimic karthy's
# skin, couldn't figure out how to use them though lol
BRUSH_JUDGMENT_MISS = QBrush(QColor(200, 27, 27))
BRUSH_JUDGMENT_50 = QBrush(QColor(24, 75, 242))
BRUSH_JUDGMENT_100 = QBrush(QColor(36, 181, 75))

GAMEPLAY_PADDING_WIDTH = 64 + 60
GAMEPLAY_PADDING_HEIGHT = 48 + 20
GAMEPLAY_WIDTH = 512
GAMEPLAY_HEIGHT = 384

# how high in pixels one half of the error bar should be (so the total height
# is twice this).
ERROR_BAR_HEIGHT = 3
# how wide in pixels the full error bar should be (not just half of the width)
ERROR_BAR_WIDTH = 170
# hitobjs which were hit less time ago than this threshold in ms will have an
# error bar marker shown to indicate the hit
ERROR_BAR_HIT_THRESHOLD = 4000
# width of each hit marker in pixels
ERROR_BAR_HIT_WIDTH = 2
ERROR_BAR_HIT_HEIGHT = 8

# radius of judgment indicator circles for 50s, 100s, 300s, misses
JUDGMENT_INDICATOR_RADIUS = 6

# hitobjs which were hit less time ago than this threshold in ms will have an
# error bar marker shown to indicate the hit
JUDGMENT_INDICATOR_THRESHOLD = 1000

SLIDER_TICKRATE = 50


class Renderer(QFrame):
    update_time_signal = pyqtSignal(int)
    pause_signal = pyqtSignal()
    loaded_signal = pyqtSignal()

    def __init__(self, beatmap, replays, events, start_speed, paint_info, \
        statistic_functions):
        super().__init__()
        self.setMinimumSize(GAMEPLAY_WIDTH + GAMEPLAY_PADDING_WIDTH * 2,
            GAMEPLAY_HEIGHT + GAMEPLAY_PADDING_HEIGHT * 2)
        self.beatmap = beatmap
        # list of timestamps to highlight the frames of in a different color
        self.events = events
        # whether to show some information about each player and their cursors
        self.should_paint_info = paint_info
        # functions to display info for in the visualizer
        self.statistic_functions = statistic_functions
        # whether we should paint the frametime graph
        self.paint_frametime = False
        self.painter = QPainter()
        self.scale = 1
        self.x_offset = 0
        self.y_offset = 0
        # a map of QRect to Player, where the rectangle is the location of the
        # player's info on the screen. Updated every frame (even though it's
        # currently static except for the width, it may differ from frame to
        # frame in the future)
        self.player_info_positions = {}
        # players that have been disabled by the users and we don't want to
        # draw cursor movements for
        self.disabled_players = []

        self.setMouseTracking(True)

        # hitobjs currently on screen
        self.hitobjs_to_draw = []
        # we actually care about more than just the hitobjs on screen when
        # drawing error bar markers, so keep track of those hitobjs here.
        # this will (should) be a superset of ``hitobjs_to_draw``
        self.hitobjs_to_draw_hits_for = []
        # and we care about *less* than the hitobjs in hitobjs_to_draw when
        # drawing judgment indicators, since these disappear sooner. This will
        # be a subset of ``hitobjs_to_draw``.
        # TODO clean up this code, these lists shouldn't exist, instead hitobjs
        # should be marked with ``draw_judgment_indicators_for`` attributes
        # or something
        self.hitobjs_to_draw_judgment_indicators_for = []

        self.use_hr = any(Mod.HR in replay.mods for replay in replays)
        self.use_ez = any(Mod.EZ in replay.mods for replay in replays)
        if beatmap:
            self.hit_objects = beatmap.hit_objects(hard_rock=self.use_hr,
                easy=self.use_ez)
            self.playback_end = self.get_hit_endtime(self.hit_objects[-1])

            ar = beatmap.ar(hard_rock=self.use_hr, easy=self.use_ez)
            od = beatmap.od(hard_rock=self.use_hr, easy=self.use_ez)
            cs = beatmap.cs(hard_rock=self.use_hr, easy=self.use_ez)
            # see https://osu.ppy.sh/help/wiki/Beatmapping/Approach_rate
            if ar <= 5:
                self.preempt = 1200 + 600 * (5 - ar) / 5
                self.fade_in = 800 + 400 * (5 - ar) / 5
            else:
                self.preempt = 1200 - 750 * (ar - 5) / 5
                self.fade_in = 800 - 500 * (ar - 5) / 5

            (hitwindow_50, hitwindow_100, hitwindow_300) = hitwindows(od)
            self.hitwindow_50 = hitwindow_50
            self.hitwindow_100 = hitwindow_100
            self.hitwindow_300 = hitwindow_300

            # how much to scale our error bar by from its 'standard' size, where
            # each ms of error is a pixel.
            self.error_bar_width_factor = ERROR_BAR_WIDTH / (hitwindow_50 * 2)

            self.hitcircle_radius = hitradius(cs)
            # loading stuff
            self.is_loading = True
            self.num_hitobjects = len(self.hit_objects)
            # not fully accurate, but good enough
            self.num_sliders = self.num_hitobjects
            self.sliders_current = 0
            self.thread = threading.Thread(target=self.process_sliders)
            self.thread.start()
            self.has_beatmap = True
        else:
            self.playback_end = 0
            self.is_loading = False
            self.has_beatmap = False

        # if this is nonnull, when we finish loading sliders we will seek to
        # this position. Set in ``seek_to`` if it is called when we're loading
        self.seek_to_when_loaded = None
        # whether the previous frame was a loading frame or not, used to
        # determine when we came out of a loading state
        self.previously_loading = False

        # replay stuff
        self.num_replays = len(replays)
        self.players = []
        for i, replay in enumerate(replays):
            color = QColor().fromHslF(i / self.num_replays, 0.75, 0.5)
            player = Player(replay=replay, pen=QPen(color))
            self.players.append(player)

        self.playback_start = 0
        if self.num_replays > 0:
            self.playback_start = min(min(player.t) for player in self.players)
            self.playback_end = max(max(player.t) for player in self.players)

        # always start at 0, unless our playback_start is negative (meaning we
        # have negative frames)
        self.playback_start = min(self.playback_start, 0)

        # if our hitobjs are hard_rock versions, flip any player *without* hr
        # so they match other hr players.
        if self.use_hr:
            for player in self.players:
                if Mod.HardRock not in player.mods:
                    for d in player.xy:
                        d[1] = 384 - d[1]

        # clock stuff
        self.clock = Timer(start_speed, self.playback_start)
        self.paused = False
        self.play_direction = 1

        # render stuff
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame_from_timer)
        # 62 fps (1000ms / 60frames but the result can only be a integer)
        self.timer.start(1000/60)

        # black background
        pal = QPalette()
        pal.setColor(QPalette.Background, Qt.black)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        # Settings that are changeable from the control's setting button.
        # If `True`, don't draw crosses, and draw the line in grey if the user
        # was not pressing any keys in the start frame of that line.
        self.raw_view = False
        self.draw_hitobjects = True
        self.draw_approach_circles = True
        # how many frames for each replay to draw on screen at a time
        self.num_frames_on_screen = 15
        self.only_color_keydowns = False
        self.should_draw_hit_error_bar = True
        # TODO expose this as a setting somewhere? it's not toggleable anywhere
        # currently
        self.should_draw_judgment_indicators = True

        self.next_frame()

        self.hitobj_to_judgments = {}
        cg = KeylessCircleguard()
        self.can_access_judgments = self.num_replays == 1 and cg.map_available(replays[0])
        if self.can_access_judgments:
            r = replays[0]

            self.judgments = cg.judgments(r, beatmap=self.beatmap)
            # associate each hitobject with a judgment. Only hitobjs which are
            # spinners won't be associated in this mapping (since core doesn't
            # generate a judgment for them yet)
            for judgment in self.judgments:
                # use the hitobj time as our key. This will work fine for ranked
                # maps (no two hitobjs can be placed at the same time) but may
                # break for aspire, loved, or crazy graveyarded maps. Needs
                # testing.
                # A way around this is to simply store the slider hitobj in
                # circlecore's hitobjs, or convert core to using slider's
                # hitobjs again (or make them subclasses, or some such)
                self.hitobj_to_judgments[judgment.hitobject.t] = judgment


    def resizeEvent(self, event):
        width = event.size().width() - GAMEPLAY_PADDING_WIDTH * 2
        height = event.size().height() - GAMEPLAY_PADDING_HEIGHT * 2
        y_scale = height / GAMEPLAY_HEIGHT
        x_scale = width / GAMEPLAY_WIDTH
        if GAMEPLAY_WIDTH * y_scale > width:
            self.scale = x_scale
            self.y_offset = (height - GAMEPLAY_HEIGHT * x_scale) / 2
            self.x_offset = 0
        else:
            self.scale = y_scale
            self.y_offset = 0
            self.x_offset = (width - GAMEPLAY_WIDTH * y_scale) / 2

    def _x(self, position):
        return (self.x_offset + GAMEPLAY_PADDING_WIDTH +
            self.scaled_number(position))

    def _y(self, position):
        return (self.y_offset + GAMEPLAY_PADDING_HEIGHT +
            self.scaled_number(position))

    def scaled_point(self, x, y):
        return QPointF(self._x(x), self._y(y))

    def scaled_number(self, n):
        return n * self.scale

    def next_frame_from_timer(self):
        """
        Has the same effect as next_frame except if paused, where it returns.
        This is to allow the back/forward buttons to advance frame by frame
        while still paused (as they connect directly to next and previous
        frame), while still pausing the automatic timer advancement.
        """
        if self.paused:
            # ignore our paused state if we're still loading sliders, or else if
            # we pause before the sliders are done loading we'll deadlock
            # ourselves
            if self.is_loading:
                self.update()
                return
            # if we wanted to seek to somewhere while we were loaded, and we
            # have just come out of a loading state, ignore paused and seek to
            # that position
            if self.previously_loading and self.seek_to_when_loaded:
                self.seek_to(self.seek_to_when_loaded)
                self.previously_loading = False
            return
        if not self.is_loading and self.previously_loading:
            self.loaded_signal.emit()
            self.previously_loading = False

        self.next_frame()

    def next_frame(self, stepping_backwards=False):
        """
        Prepares the next frame.

        If we have just set our current time to be less than what it was the
        previous time next_frame was called, pass stepping_backwards=True so
        the correct frame can be chosen when searching the frame list.
        """
        # just update the frame if currently loading
        if self.is_loading:
            self.previously_loading = True
            self.update()
            return

        current_time = self.clock.get_time()
        # if we're at the end of the track or are at the beginning of the track
        # (and thus are reversing), pause and dont update
        if current_time > self.playback_end or current_time < self.playback_start:
            self.pause_signal.emit()
            return

        # This is the solution to the issue of stepping forward/backwards
        # getting stuck on certain frames - we can fix it for stepping forward
        # by always preferring the right side when searching our array, but when
        # stepping backwards we need to prefer the left side instead.
        side = "left" if stepping_backwards else "right"
        for player in self.players:
            player.end_pos = np.searchsorted(player.t, current_time, side)
            # for some reason side=right and side=left differ by 1 even when
            # the array has no duplicates, so only account for that in the
            # right side case
            if side == "right":
                player.end_pos -= 1

            player.start_pos = 0
            if player.end_pos >= self.num_frames_on_screen:
                player.start_pos = player.end_pos - self.num_frames_on_screen

        if self.has_beatmap:
            self.get_hitobjects()
        self.update_time_signal.emit(current_time)
        self.update()

    def get_hitobjects(self):
        # get currently visible hitobjects
        current_time = self.clock.get_time()
        found_all = False
        # TODO optimize this by tracking our current hitobj index, this iterates
        # through half the hitobjects of the map on average (O(1) best case and
        # O(n) worst case) which can't be good for performance
        index = 0
        self.hitobjs_to_draw = []
        self.hitobjs_to_draw_hits_for = []
        self.hitobjs_to_draw_judgment_indicators_for = []
        while not found_all:
            current_hitobj = self.hit_objects[index]
            hit_t = current_hitobj.time.total_seconds() * 1000
            if isinstance(current_hitobj, (Slider, Spinner)):
                hit_end = self.get_hit_endtime(current_hitobj) + self.fade_in
            else:
                hit_end = hit_t + self.hitwindow_50 + self.fade_in
            if hit_t > current_time - JUDGMENT_INDICATOR_THRESHOLD:
                self.hitobjs_to_draw_judgment_indicators_for.append(current_hitobj)
            if hit_t > current_time - ERROR_BAR_HIT_THRESHOLD:
                self.hitobjs_to_draw_hits_for.append(current_hitobj)
            if hit_t - self.preempt < current_time < hit_end:
                self.hitobjs_to_draw.append(current_hitobj)

            elif hit_t > current_time:
                found_all = True
            if index == self.num_hitobjects - 1:
                found_all = True
            index += 1

    def paintEvent(self, _event):
        """
        Called whenever self.update() is called
        """
        self.painter.begin(self)
        self.painter.setRenderHint(QPainter.TextAntialiasing, True)
        self.painter.setRenderHint(QPainter.Antialiasing, True)
        self.painter.setPen(PEN_WHITE)
        _pen = self.painter.pen()
        # loading screen
        if self.is_loading:
            if self.thread.is_alive():
                self.draw_loading_screen()
                self.painter.end()
                return
            else:
                self.is_loading = False
                self.clock.reset()
                self.painter.end()
                return
        # beatmap
        if self.has_beatmap:
            self.paint_beatmap()
        # cursors
        for player in self.players:
            self.paint_cursor(player)
        # other info
        self.painter.setPen(_pen)
        self.paint_border()
        if self.should_paint_info:
            self.paint_info()
        if self.paint_frametime:
            self.paint_frametime_graph()
        self.painter.end()

    def paint_border(self):
        PEN_WHITE.setWidth(self.scaled_number(1))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(0.25)
        self.painter.drawRect(QRectF(self.scaled_point(0, 0),
            self.scaled_point(GAMEPLAY_WIDTH, GAMEPLAY_HEIGHT)))

    def paint_cursor(self, player):
        """
        Draws a cursor.

        Arguments:
            Player player: player to draw the cursor of.
        """
        # don't draw anything if the player is disabled
        if player in self.disabled_players:
            return
        alpha_step = 1 / self.num_frames_on_screen
        pen = player.pen
        width = WIDTH_LINE_RAW_VIEW if self.raw_view else WIDTH_LINE
        pen.setWidth(self.scaled_number(width))
        PEN_HIGHLIGHT.setWidth(self.scaled_number(width))
        self.painter.setPen(pen)
        highlighted_pen = False
        for i in range(player.start_pos, player.end_pos):
            highlight = any((player.t[i + 1] in self.events, player.t[i] in
                self.events))
            if highlight and not highlighted_pen:
                self.painter.setPen(PEN_HIGHLIGHT)
                highlighted_pen = True
            elif not highlight and highlighted_pen:
                self.painter.setPen(pen)
                highlighted_pen = False
            grey_out = False
            # only grey out lines if we're in raw view (crosses are greyed out
            # instead in the normal view)
            if self.raw_view:
                # grey out if we don't have a keypress at the start
                if not bool(player.k[i]):
                    grey_out = True
                # grey out if we're only coloring keydowns and this is not a
                # keydown
                if self.only_color_keydowns and not bool(player.keydowns[i]):
                    grey_out = True
            self.draw_line((i - player.start_pos) * alpha_step, player.xy[i],
                    player.xy[i + 1], grey_out=grey_out)
        pen.setWidth(self.scaled_number(WIDTH_CROSS))
        self.painter.setPen(pen)
        for i in range(player.start_pos, player.end_pos+1):
            alpha = (i - player.start_pos) * alpha_step
            xy = player.xy[i]
            k = player.k[i]
            t = player.t[i]
            highlight = t in self.events
            # grey out only if no keys are held by default
            grey_out = not bool(k)
            # but override if we're only coloring keydowns and this is not a
            # keydown
            if self.only_color_keydowns and not bool(player.keydowns[i]):
                grey_out = True
            self.draw_cross(alpha, xy, grey_out=grey_out, highlight=highlight)
        # reset alpha
        self.painter.setOpacity(1)

    def paint_beatmap(self):
        # draw playfield judgment indicators (yellow/green/blue circles under
        # hitobjs) before drawing hitobjs so they don't cover hitobjs
        # (though to be honest it doesn't make much of a difference either way)

        if self.should_draw_judgment_indicators and self.can_access_judgments:
            for hitobj in self.hitobjs_to_draw_hits_for:
                if isinstance(hitobj, Spinner):
                    continue

                judgment = self.hitobj_to_judgments[self.get_hit_time(hitobj)]

                if judgment.type is JudgmentType.Miss:
                    # misses don't have an intrinsic event time, so just use
                    # their hitobj's time
                    t = judgment.hitobject.time
                else:
                    t = judgment.time

                # don't draw hits that haven't happened yet
                if t <= self.clock.get_time():
                    self.draw_judgment_indicator(hitobj, judgment)
            self.painter.setBrush(BRUSH_BLANK)

        for hitobj in self.hitobjs_to_draw[::-1]:
            self.draw_hitobject(hitobj)

        # only draw hit error bars if there's only one replay
        if self.should_draw_hit_error_bar and self.can_access_judgments:
            self.draw_hit_error_bar()

            for hitobj in self.hitobjs_to_draw_hits_for:
                # core doesn't calculate judgmnets for spinners yet, TODO
                # implement this when core does
                if isinstance(hitobj, Spinner):
                    continue

                judgment = self.hitobj_to_judgments[self.get_hit_time(hitobj)]
                # don't draw any judgment bars for misses
                if judgment.type is JudgmentType.Miss:
                    continue
                # don't draw hits that haven't happened yet
                if judgment.t <= self.clock.get_time():
                    self.draw_hit(hitobj, judgment)

    def paint_info(self):
        """
        Draws various info about the replays in the upper left corner.
        """
        # our current y coordinate for drawing info. Modified throughout this
        # function
        y = 15

        PEN_WHITE.setWidth(1)
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(1)
        ms = round(self.clock.get_time())
        text = f"{ms}"
        self.painter.drawText(5, y, text)
        # we don't use a monospaced font, so our ms text may vary by as much as
        # 10 pixels in width (possibly more, haven't checked rigorously). If
        # we just drew our minute:seconds text directly after it, the position
        # of that text would constantly flicker left and right, since the ms
        # text (and thus its width) changes every single frame. To fix this,
        # only increment widths in multiples of 10. (This will not fix the issue
        # if the text width happens to hover exactly around a multiple of 10,
        # but there's not much to be done in that case).
        text_width = self.painter.boundingRect(5, y, 0, 0, 0, text).width()
        if text_width < 50:
            x = 50
        elif text_width < 60:
            x = 60
        elif text_width < 70:
            x = 70
        elif text_width < 80:
            x = 80
        else:
            # something crazy is going on, give up and just use text_width
            x = text_width

        # now some dirty code to deal with negattive times
        minutes = int(ms / (1000 * 60))
        seconds = ms // 1000
        seconds_negative = seconds < 0
        # pytohn modulo returns positive even when ``seconds_total`` is negative
        seconds = seconds % 60
        if seconds_negative:
            # ``seconds`` can be 0 and 59 but not 60, so use 59 instead of 60
            seconds = 59 - seconds
        sign = ""
        if minutes < 0 or seconds_negative:
            sign = "-"
            minutes = abs(minutes)
            seconds = abs(seconds)

        self.painter.drawText(5 + 4 + x, y,
            f"ms ({sign}{minutes:01}:{seconds:02})")

        self.player_info_positions = {}
        if self.num_replays > 0:
            for player in self.players:
                def _set_opacity(opacity):
                    if player in self.disabled_players:
                        opacity /= 2.4
                    self.painter.setOpacity(opacity)

                y += 13
                pen = player.pen
                self.painter.setPen(PEN_BLANK)
                self.painter.setBrush(QBrush(pen.color()))
                keys = Key(int(player.k[player.end_pos]))
                _set_opacity(1 if Key.M1 in keys else 0.3)
                self.painter.drawRect(5, y - 9, 10, 10)
                _set_opacity(1 if Key.M2 in keys else 0.3)
                self.painter.drawRect(18, y - 9, 10, 10)
                _set_opacity(1)
                self.painter.setPen(pen)
                info_text = (f"{player.username} {player.mods.short_name()}: "
                    f"{player.xy[player.end_pos][0]:.2f}, "
                    f"{player.xy[player.end_pos][1]:.2f}")
                self.painter.drawText(31, y, info_text)
                # not sure why we need to do ``y - 9`` instead of 9 here,
                # our ``drawText`` call is perfectly happy to accept ``y`` but
                # we need to pass ``y - 9`` to our ``drawRect`` calls...maybe 9
                # was a manually determined number that causes the text to align
                # with the drawn boxes?
                info_pos = self.painter.boundingRect(5, y - 9, 0, 0, 0,
                    info_text)
                info_pos = Rect(info_pos.x(), info_pos.y(), info_pos.width(),
                    info_pos.height())
                # unfortunately the rects overlap if we don't make this manual
                # adjustment; would like to figure out why but this works for
                # now.
                info_pos.height -= 3
                # our bounding rect starts at 5 but the text starts at 31, so
                # we need to increase the width by the difference to account
                info_pos.width += 31 - 5
                self.player_info_positions[info_pos] = player

            self.painter.setOpacity(1)
            self.painter.setPen(PEN_WHITE)
            if self.num_replays == 2:
                try:
                    y += 13
                    p1 = self.players[0]
                    p2 = self.players[1]
                    distance = math.sqrt(((p1.xy[p1.end_pos][0] - p2.xy[p2.end_pos][0]) ** 2) +
                                         ((p1.xy[p1.end_pos][1] - p2.xy[p2.end_pos][1]) ** 2))
                    self.painter.drawText(5, y, f"{int(distance)}px apart")
                except IndexError:
                    # we may only have data from one cursor at the moment
                    pass

            if self.num_replays == 1 and self.has_beatmap:
                y += 13
                player = self.players[0]
                current_t = timedelta(milliseconds=int(self.clock.get_time()))
                closest_hitobj = self.beatmap.closest_hitobject(current_t)
                if self.use_hr:
                    closest_hitobj = closest_hitobj.hard_rock
                distance = self.distance_between(player.xy[player.end_pos],
                    closest_hitobj)

                # show "x px inside hitobj" instead of a negative distance
                inside = False
                if distance < 0:
                    inside = True
                    distance = abs(distance)

                inside_from = "inside" if inside else "from"
                text = f"{distance:0.2f}px {inside_from} closest hitobj"
                self.painter.drawText(5, y, text)

            for function in self.statistic_functions:
                y += 13
                xys = [player.xy for player in self.players]
                indices = [player.end_pos for player in self.players]
                result = function(xys, indices)
                self.painter.drawText(5, y, f"{function.__name__}: {result}")


    def draw_line(self, alpha, start, end, grey_out=False):
        """
        Draws a line at the given alpha level from the start point to the end
        point.

        Arguments:
            Float alpha: The alpha level (from 0.0 to 1.0) to set the line to.
            List start: The X&Y position of the start of the line.
            List end: The X&Y position of the end of the line.
            Boolean grey_out: Whether to grey out the line or not.
        """
        if grey_out:
            prev_pen = self.painter.pen()
            PEN_GREY_INACTIVE.setWidth(self.scaled_number(WIDTH_LINE_RAW_VIEW))
            self.painter.setPen(PEN_GREY_INACTIVE)

        self.painter.setOpacity(alpha)
        self.painter.drawLine(self.scaled_point(start[0], start[1]),
            self.scaled_point(end[0], end[1]))

        if self.raw_view and grey_out:
            self.painter.setPen(prev_pen)

    def draw_cross(self, alpha, point, grey_out, highlight):
        """
        Draws a cross.

        Args:
           Float alpha: The alpha level from 0.0-1.0 to set the cross to.
           List point: The X and Y position of the cross.
           Boolean grey_out: Whether to grey out the cross or not.
           Boolean highlight: Whether to highlight the cross or not. This takes
               precedence over ``grey_out`` if both are set.
        """
        # crosses can clutter the screen sometimes, don't draw them if raw view
        # is on
        if self.raw_view:
            return
        prev_pen = None
        if highlight:
            prev_pen = self.painter.pen()
            PEN_HIGHLIGHT.setWidth(self.scaled_number(WIDTH_CROSS))
            self.painter.setPen(PEN_HIGHLIGHT)
        elif grey_out:
            prev_pen = self.painter.pen()
            PEN_GREY_INACTIVE.setWidth(self.scaled_number(WIDTH_CROSS))
            self.painter.setPen(PEN_GREY_INACTIVE)
        half_width = LENGTH_CROSS/2
        x = point[0]
        y = point[1]
        x1 = x + half_width
        x2 = x - half_width
        y1 = y + half_width
        y2 = y - half_width

        self.draw_line(alpha, [x1, y1], [x2, y2])
        self.draw_line(alpha, [x2, y1], [x1, y2])
        if grey_out or highlight:
            self.painter.setPen(prev_pen)


    def draw_hitobject(self, hitobj):
        """
        Calls the corresponding function to draw ``hitobj``.
        """
        if not self.draw_hitobjects:
            return
        if isinstance(hitobj, Circle):
            self.draw_hitcircle(hitobj)
            self.draw_approachcircle(hitobj)
        if isinstance(hitobj, Slider):
            self.draw_slider(hitobj)
        if isinstance(hitobj, Spinner):
            self.draw_spinner(hitobj)

    def draw_hitcircle(self, hitobj):
        """
        Draws a circle hitobject.
        """
        current_time = self.clock.get_time()
        fade_out = max(0, ((current_time - self.get_hit_time(hitobj)) / self.hitwindow_50))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out))
        p = hitobj.position

        # the pen width grows outwards and inwards equally (preferring outwards
        # if the width is odd I think), so we need to tell it to start drawing
        # half of the pen's width away from the radius for the final circle to
        # have radius `self.hitcircle_radius`.
        r = self.scaled_number(self.hitcircle_radius - WIDTH_CIRCLE_BORDER / 2)

        # normal white hitobj
        pen = PEN_WHITE
        brush = BRUSH_GRAY

        if self.can_access_judgments:
            judgment = self.hitobj_to_judgments[self.get_hit_time(hitobj)]
            if judgment.type is JudgmentType.Miss:
                # hitobj was missed, tint red
                pen = PEN_RED_TINT
                brush = BRUSH_GRAY_RED_TINT

        pen.setWidth(self.scaled_number(WIDTH_CIRCLE_BORDER))
        self.painter.setPen(pen)
        self.painter.setOpacity(opacity)
        self.painter.setBrush(brush)

        self.painter.drawEllipse(self.scaled_point(p.x, p.y), r, r)
        self.painter.setBrush(BRUSH_BLANK)

    def draw_spinner(self, hitobj):
        """
        Draws a spinner hitobject.
        """
        current_time = self.clock.get_time()
        if self.get_hit_endtime(hitobj) - current_time < 0:
            return
        radius = GAMEPLAY_HEIGHT / 2
        fade_out = max(0, ((current_time - self.get_hit_endtime(hitobj)) / self.hitwindow_50))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out))
        scale = min(1, (self.get_hit_endtime(hitobj) - current_time) / (self.get_hit_endtime(hitobj) - self.get_hit_time(hitobj)))
        radius = radius * scale

        PEN_WHITE.setWidth(self.scaled_number(WIDTH_CIRCLE_BORDER / 2))
        self.painter.setPen(PEN_WHITE)
        self.painter.setOpacity(opacity)
        self.painter.drawEllipse(self.scaled_point(GAMEPLAY_WIDTH / 2, GAMEPLAY_HEIGHT / 2),
            self.scaled_number(radius), self.scaled_number(radius))

    def draw_approachcircle(self, hitobj):
        """
        Draws the approach circle of a circle hitobject.
        """
        if not self.draw_approach_circles:
            return
        current_time = self.clock.get_time()
        if self.get_hit_time(hitobj) - current_time < 0:
            return
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity))
        scale = max(1, ((self.get_hit_time(hitobj) - current_time) / self.preempt) * 3 + 1)
        p = hitobj.position
        r = self.scaled_number(self.hitcircle_radius * scale)

        pen = PEN_WHITE

        if self.can_access_judgments:
            judgment = self.hitobj_to_judgments[self.get_hit_time(hitobj)]
            if judgment.type is JudgmentType.Miss:
                # hitobj was missed, tint red
                pen = PEN_RED_TINT

        pen.setWidth(self.scaled_number(WIDTH_CIRCLE_BORDER / 2))
        self.painter.setPen(pen)
        self.painter.setOpacity(opacity)
        self.painter.drawEllipse(self.scaled_point(p.x, p.y), r, r)

    def draw_slider(self, hitobj):
        """
        Draws sliderbody, hitcircle, approachcircle if needed
        """
        self.draw_sliderbody(hitobj)
        self.draw_hitcircle(hitobj)
        self.draw_approachcircle(hitobj)

    def draw_sliderbody(self, hitobj):
        """
        Draws the sliderbody of a slider using a QpainterPath.
        """

        current_time = self.clock.get_time()
        fade_out = max(0, ((current_time - self.get_hit_endtime(hitobj)) / self.hitwindow_50))
        opacity = min(1, ((current_time - (self.get_hit_time(hitobj) - self.preempt)) / self.fade_in))
        opacity = max(0, min(1, opacity-fade_out)) * 0.75
        p = hitobj.position

        PEN_GRAY.setWidth(self.scaled_number(self.hitcircle_radius * 2))
        PEN_GRAY.setCapStyle(Qt.RoundCap)
        PEN_GRAY.setJoinStyle(Qt.RoundJoin)
        self.painter.setPen(PEN_GRAY)
        self.painter.setOpacity(opacity)

        sliderbody = QPainterPath()
        sliderbody.moveTo(self.scaled_point(p.x, p.y))
        for i in hitobj.slider_body:
            sliderbody.lineTo(self.scaled_point(i.x, i.y))
        self.painter.drawPath(sliderbody)

    def draw_hit_error_bar(self):
        mid_x = GAMEPLAY_WIDTH / 2
        y = GAMEPLAY_HEIGHT - ERROR_BAR_HIT_HEIGHT

        # draw the center white bar
        self.painter.setPen(PEN_WHITE)
        pen = self.painter.pen()
        pen.setWidth(ERROR_BAR_HIT_WIDTH)
        self.painter.setPen(pen)
        self.draw_line(1, [mid_x, y - ERROR_BAR_HIT_HEIGHT],
            [mid_x, y + ERROR_BAR_HIT_HEIGHT])

        # draw the three error zones as slightly transparent
        self.painter.setOpacity(0.65)
        self.painter.setPen(PEN_BLANK)

        hw300 = self.hitwindow_300 * self.error_bar_width_factor
        hw100 = self.hitwindow_100 * self.error_bar_width_factor
        hw50 = self.hitwindow_50 * self.error_bar_width_factor

        self.painter.setBrush(BRUSH_BLUE)
        p1 = self.scaled_point(mid_x - hw300, y - ERROR_BAR_HEIGHT)
        p2 = self.scaled_point(mid_x + hw300, y + ERROR_BAR_HEIGHT)
        self.painter.drawRect(QRectF(p1, p2))

        # draw two rects to avoid overlapping with hitwindow_300 in the center
        self.painter.setBrush(BRUSH_GREEN)
        p1 = self.scaled_point(mid_x - hw100, y - ERROR_BAR_HEIGHT)
        p2 = self.scaled_point(mid_x - hw300, y + ERROR_BAR_HEIGHT)
        self.painter.drawRect(QRectF(p1, p2))
        p1 = self.scaled_point(mid_x + hw300, y - ERROR_BAR_HEIGHT)
        p2 = self.scaled_point(mid_x + hw100, y + ERROR_BAR_HEIGHT)
        self.painter.drawRect(QRectF(p1, p2))

        self.painter.setBrush(BRUSH_YELLOW)
        p1 = self.scaled_point(mid_x - hw50, y - ERROR_BAR_HEIGHT)
        p2 = self.scaled_point(mid_x - hw100, y + ERROR_BAR_HEIGHT)
        self.painter.drawRect(QRectF(p1, p2))
        p1 = self.scaled_point(mid_x + hw100, y - ERROR_BAR_HEIGHT)
        p2 = self.scaled_point(mid_x + hw50, y + ERROR_BAR_HEIGHT)
        self.painter.drawRect(QRectF(p1, p2))

        self.painter.setBrush(BRUSH_BLANK)
        self.painter.setOpacity(1)

    def draw_hit(self, hitobj, hit):
        # TODO: avoid duplication in these constants between this and
        # `draw_hit_error_bar` - maybe just extract to globals?
        mid_x = GAMEPLAY_WIDTH / 2
        y = GAMEPLAY_HEIGHT - ERROR_BAR_HIT_HEIGHT

        if hit.type is JudgmentType.Hit300:
            pen = PEN_BLUE
        elif hit.type is JudgmentType.Hit100:
            pen = PEN_GREEN
        elif hit.type is JudgmentType.Hit50:
            pen = PEN_YELLOW

        self.painter.setPen(pen)
        pen = self.painter.pen()
        pen.setWidth(ERROR_BAR_HIT_WIDTH)
        self.painter.setPen(pen)

        current_time = self.clock.get_time()

        # positive is a late hit, negative is an early hit
        error = (hit.t - self.get_hit_time(hitobj)) * self.error_bar_width_factor
        start = [mid_x + error, y - ERROR_BAR_HIT_HEIGHT]
        end = [mid_x + error, y + ERROR_BAR_HIT_HEIGHT]

        time_passed = current_time - hit.t
        # how long in ms to display hits for before they disappear
        time_passed = min(time_passed, ERROR_BAR_HIT_THRESHOLD)
        # draw most recent hits as more visible (higher alpha) and old hits
        # as less visible (lower alpha)
        x_interp = [0, ERROR_BAR_HIT_THRESHOLD]
        y_interp = [1, 0]
        f = interpolate.interp1d(x_interp, y_interp)
        alpha = f(time_passed)
        self.draw_line(alpha, start, end)

    def draw_judgment_indicator(self, hitobj, judgment):
        if judgment.type is JudgmentType.Hit300:
            # don't draw anything for 300s
            return

        if judgment.type is JudgmentType.Miss:
            brush = BRUSH_JUDGMENT_MISS
            judgment_t = judgment.hitobject.time
        else:
            judgment_t = judgment.time
        if judgment.type is JudgmentType.Hit50:
            brush = BRUSH_JUDGMENT_50
        if judgment.type is JudgmentType.Hit100:
            brush = BRUSH_JUDGMENT_100

        self.painter.setPen(PEN_BLANK)
        self.painter.setBrush(brush)

        current_time = self.clock.get_time()

        time_passed = current_time - judgment_t
        time_passed = min(time_passed, JUDGMENT_INDICATOR_THRESHOLD)
        x_interp = [0, JUDGMENT_INDICATOR_THRESHOLD]
        y_interp = [1, 0]
        f = interpolate.interp1d(x_interp, y_interp)
        alpha = f(time_passed)

        self.painter.setOpacity(alpha)

        p = hitobj.position
        r = self.scaled_number(JUDGMENT_INDICATOR_RADIUS)
        self.painter.drawEllipse(self.scaled_point(p.x, p.y), r, r)

    def draw_progressbar(self, percentage):
        loading_bg = QPainterPath()
        loading_bar = QPainterPath()
        c = self.painter.pen().color()

        _pen = self.painter.pen()
        _pen.setWidth(5)
        _pen.setCapStyle(Qt.RoundCap)
        _pen.setJoinStyle(Qt.RoundJoin)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 25))
        self.painter.setPen(_pen)

        loading_bg.moveTo(self.width()/2 - 75, self.height() / 2)
        loading_bg.lineTo(self.width()/2 - 75 + 150, self.height() / 2)

        loading_bar.moveTo(self.width() / 2 - 75, self.height() / 2)
        loading_bar.lineTo(self.width() / 2 - 75 + percentage * 1.5,
            self.height() / 2)

        self.painter.drawPath(loading_bg)
        _pen.setColor(QColor(c.red(), c.green(), c.blue(), 255))
        self.painter.setPen(_pen)
        self.painter.drawPath(loading_bar)

    def draw_loading_screen(self):
        x = self.width() / 2 - 75
        y = self.height() / 2 - 10
        self.painter.drawText(x, y, "Calculating Sliders, please wait...")
        progress = int((self.sliders_current / self.num_sliders) * 100)
        self.draw_progressbar(progress)

    def process_sliders(self):
        for i, hitobj in enumerate(self.hit_objects):
            self.sliders_current = i
            if isinstance(hitobj, Slider):
                steps = max(2, int((self.get_hit_endtime(hitobj) - self.get_hit_time(hitobj)) / SLIDER_TICKRATE))
                # some sliders (see https://osu.ppy.sh/b/1853289 and
                # https://github.com/circleguard/circleguard/issues/177) set
                # slider durations of ridiculously long time periods, so
                # get_hit_endtime returns a time a hundred million milliseconds
                # in the future, causing our ``steps`` to be in the millions and
                # essentially never finish calculating. To prevent this, cap the
                # resolution of sliders to something really high, like 100.
                # I checked a crazy slider map like notch hell and the highest
                # ``steps`` went was 61, so 100 seems like a reasonable limit.
                steps = min(steps, 100)
                hitobj.slider_body = [hitobj.curve(i / steps) for i in range(steps + 1)]

    def search_nearest_frame(self, reverse=False):
        """
        Args
            Boolean reverse: whether to search backwards or forwards through
                time
        """
        if not reverse:
            next_frames = []
            for player in self.players:
                pos = player.end_pos + 1
                # stay at the end of the replay, avoid index error
                if pos == len(player.xy):
                    pos -= 1
                next_frames.append(player.t[pos])
            # if we're only visualizing a beatmap and there's no replays, and
            # someone tries to advance or retreat frames, min() / max() will
            # crash because next_frames is empty, so avoid this.
            if not next_frames:
                return
            self.seek_to(min(next_frames))
        else:
            prev_frames = []
            for player in self.players:
                pos = player.end_pos - 1
                # stay at the beginning of the replay, don't wrap around to end
                if pos == -1:
                    pos += 1
                prev_frames.append(player.t[pos])
            if not prev_frames:
                return
            self.seek_to(max(prev_frames), seeking_backwards=True)

    def seek_to(self, position, seeking_backwards=False):
        """
        Seeks to position if the change is bigger than ± 10.
        Also calls next_frame() so the correct frame is displayed.

        Args:
            Integer position: position to seek to in ms
            Boolean seeking_backwards: Whether we're seeking to a time before
                our current time.
        """
        self.clock.time_counter = position
        # if we want to seek somewhere while we're loading sliders, we store
        # that position so we can seek to it when loaded
        if self.is_loading:
            self.seek_to_when_loaded = position
        if self.paused:
            self.next_frame(stepping_backwards=seeking_backwards)

    def wheelEvent(self, event):
        # from the qt docs on pixelDelta: "This value is provided on platforms
        # that support high-resolution pixel-based delta values, such as macOS".
        # Since not every OS provides pixelDelta, we should use it if possible
        # but fall back to angleDelta. From my testing (sample size 1)
        # pixelDelta will have both x and y as zero if it's unsupported.
        if event.pixelDelta().x() == 0 and event.pixelDelta().y() == 0:
            # check both x and y to support users scrolling either vertically or
            # horizontally to move the timeline, just respect whichever is
            # greatest for that event.
            # this /5 is an arbitrary value to slow down scrolling to what
            # feels reasonable. TODO expose as a setting to the user ("scrolling
            # sensitivity")
            delta = max(event.angleDelta().x(), event.angleDelta().y(), key=abs) / 5
        else:
            delta = max(event.angleDelta().x(), event.angleDelta().y(), key=abs)

        self.seek_to(self.clock.time_counter + delta)

    def mouseMoveEvent(self, event):
        any_inside = False
        for rect in self.player_info_positions:
            qrect = rect.toQRect()
            if qrect.contains(event.pos()):
                any_inside = True
                self.setCursor(QCursor(Qt.PointingHandCursor))
        if not any_inside:
            self.setCursor(QCursor(Qt.ArrowCursor))
        return super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        for rect in self.player_info_positions:
            qrect = rect.toQRect()
            if qrect.contains(event.pos()):
                player = self.player_info_positions[rect]
                # toggle its membership in disabled_players, so users can click
                # a second time to re-enable a player
                if player in self.disabled_players:
                    self.disabled_players.remove(player)
                else:
                    self.disabled_players.append(player)
                self.update()
        return super().mousePressEvent(event)

    def get_hit_endtime(self, hitobj):
        if isinstance(hitobj, Circle):
            return self.get_hit_time(hitobj)
        t = hitobj.end_time.total_seconds() * 1000
        return int(round(t))

    def get_hit_time(self, hitobj):
        t = hitobj.time.total_seconds() * 1000
        # Due to floating point errors, ``t`` could actually be something
        # like ``129824.99999999999`` or ``128705.00000000001``, so round to the
        # nearest int.
        return int(round(t))

    def pause(self):
        """
        Set paused flag and pauses the clock.
        """
        self.paused = True
        self.clock.pause()

    def resume(self):
        """
        Removes paused flag and resumes the clock.
        """
        self.paused = False
        self.clock.resume()

    def toggle_frametime(self):
        self.paint_frametime = not self.paint_frametime

    def distance_between(self, point, hitobject):
        """
        The shortest distance between the given point and hitobject.
        """
        # TODO use numpy for these calculations
        x1 = point[0]
        y1 = point[1]
        x2 = hitobject.position.x
        y2 = hitobject.position.y
        r = self.hitcircle_radius
        return math.sqrt((((x2 - x1) ** 2) + (y2 - y1) ** 2)) - r

    def raw_view_changed(self, new_state):
        self.raw_view = new_state
        # redraw everything for the new raw view
        self.update()

    def only_color_keydowns_changed(self, new_state):
        self.only_color_keydowns = new_state
        self.update()

    def hitobjects_changed(self, new_state):
        self.draw_hitobjects = new_state
        self.update()

    def approach_circles_changed(self, new_state):
        self.draw_approach_circles = new_state
        self.update()

    def num_frames_changed(self, new_value):
        self.num_frames_on_screen = new_value
        self.update()

    def draw_hit_error_bar_changed(self, new_value):
        self.should_draw_hit_error_bar = new_value
        self.update()

    def circle_size_mod_changed(self, new_value):
        if not self.has_beatmap:
            # cs doesn't matter to us if we don't have a beatmap (and we don't
            # have the attributes necessary to compute it anyway)
            return
        use_hr = new_value == "HR"
        use_ez = new_value == "EZ"
        cs = self.beatmap.cs(hard_rock=use_hr, easy=use_ez)
        self.hitcircle_radius = hitradius(cs)
        self.update()


# not sure why dataclass won't generate a hash method for us automatically,
# we're not using anything mutable, just ints
@dataclass(unsafe_hash=True)
class Rect:
    """
    A dataclass which mimics ``QRect`` and only serves as a hashable liaison of
    ``QRect``.
    """
    x: int
    y: int
    width: int
    height: int

    def toQRect(self):
        return QRect(self.x, self.y, self.width, self.height)
