from __future__ import annotations

import math
import time

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QVector3D
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

try:
    import pyqtgraph.opengl as gl
    _HAS_OPENGL = True
except ImportError:
    gl = None
    _HAS_OPENGL = False

ALT_SCALE = 10.0


if _HAS_OPENGL:

    class BlenderStyleGLViewWidget(gl.GLViewWidget):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._zoom_anim_timer: QTimer | None = None
            self._zoom_target: float = 55.0
            self._default_opts: dict | None = None
            self.setMouseTracking(True)

        def _store_defaults(self) -> None:
            self._default_opts = {
                'center': QVector3D(self.opts['center']),
                'distance': self.opts['distance'],
                'elevation': self.opts['elevation'],
                'azimuth': self.opts['azimuth'],
            }
            self._zoom_target = self.opts['distance']

        def reset_view(self) -> None:
            if self._default_opts is None:
                return
            self.setCameraPosition(
                pos=QVector3D(self._default_opts['center']),
                distance=self._default_opts['distance'],
                elevation=self._default_opts['elevation'],
                azimuth=self._default_opts['azimuth'],
            )
            self.opts['fov'] = 60
            self._zoom_target = self._default_opts['distance']

        def mousePressEvent(self, ev) -> None:
            lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
            self.mousePos = lpos

        def mouseMoveEvent(self, ev) -> None:
            lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
            if not hasattr(self, 'mousePos'):
                self.mousePos = lpos
                return
            diff = lpos - self.mousePos
            self.mousePos = lpos

            buttons = ev.buttons()
            mods = ev.modifiers()

            if buttons == Qt.MouseButton.MiddleButton and not mods:
                self.orbit(-diff.x(), diff.y())
            elif buttons == Qt.MouseButton.MiddleButton and mods & Qt.KeyboardModifier.ShiftModifier:
                self.pan(diff.x(), diff.y(), 0, relative='view-upright')
            elif buttons == Qt.MouseButton.MiddleButton and mods & Qt.KeyboardModifier.ControlModifier:
                self._zoom_target *= (1 + diff.y() * 0.005)
                self._zoom_target = max(1.0, min(500.0, self._zoom_target))
                self._start_zoom_anim()
            elif buttons == Qt.MouseButton.RightButton:
                self.pan(diff.x(), diff.y(), 0, relative='view-upright')

        def mouseDoubleClickEvent(self, ev) -> None:
            if ev.button() == Qt.MouseButton.MiddleButton:
                self.reset_view()
            super().mouseDoubleClickEvent(ev)

        def wheelEvent(self, ev) -> None:
            delta = ev.angleDelta().x()
            if delta == 0:
                delta = ev.angleDelta().y()
            if ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.opts['fov'] *= 0.999 ** delta
            else:
                self._zoom_target *= 0.999 ** delta
                self._zoom_target = max(1.0, min(500.0, self._zoom_target))
                self._start_zoom_anim()
            self.update()

        def _start_zoom_anim(self) -> None:
            if self._zoom_anim_timer is not None and self._zoom_anim_timer.isActive():
                return
            self._zoom_anim_timer = QTimer()
            self._zoom_anim_timer.timeout.connect(self._tick_zoom)
            self._zoom_anim_timer.start(8)

        def _tick_zoom(self) -> None:
            cur = self.opts['distance']
            tgt = self._zoom_target
            diff = tgt - cur
            if abs(diff) < 0.01:
                self.opts['distance'] = tgt
                self._zoom_anim_timer.stop()
                self._zoom_anim_timer = None
                self.update()
                return
            self.opts['distance'] += diff * 0.18
            self.update()


def _cylinder_mesh(radius: float, height: float, rows: int = 10, cols: int = 20) -> tuple[np.ndarray, np.ndarray]:
    verts = []
    for i in range(rows + 1):
        y = -height / 2.0 + i * height / rows
        for j in range(cols):
            theta = 2.0 * math.pi * j / cols
            x = radius * math.cos(theta)
            z = radius * math.sin(theta)
            verts.append([x, y, z])
    verts = np.array(verts, dtype=float)

    faces = []
    for i in range(rows):
        for j in range(cols):
            a = i * cols + j
            b = i * cols + (j + 1) % cols
            c = (i + 1) * cols + j
            d = (i + 1) * cols + (j + 1) % cols
            faces.append([a, b, d])
            faces.append([a, d, c])

    idx = len(verts)
    verts = np.vstack([verts, [[0.0, height / 2.0, 0.0]]])
    for j in range(cols):
        a = rows * cols + j
        b = rows * cols + (j + 1) % cols
        faces.append([a, b, idx])

    idx = len(verts)
    verts = np.vstack([verts, [[0.0, -height / 2.0, 0.0]]])
    for j in range(cols):
        a = j
        b = (j + 1) % cols
        faces.append([a, idx, b])

    return verts, np.array(faces, dtype=int)


def _cone_mesh(radius: float, height: float, cols: int = 20) -> tuple[np.ndarray, np.ndarray]:
    verts = [[0.0, height / 2.0, 0.0]]
    for j in range(cols):
        theta = 2.0 * math.pi * j / cols
        x = radius * math.cos(theta)
        z = radius * math.sin(theta)
        verts.append([x, -height / 2.0, z])
    verts = np.array(verts, dtype=float)

    faces = []
    for j in range(cols):
        a, b, c = 0, 1 + j, 1 + (j + 1) % cols
        faces.append([a, c, b])

    idx = len(verts)
    verts = np.vstack([verts, [[0.0, -height / 2.0, 0.0]]])
    for j in range(cols):
        a, b = 1 + j, 1 + (j + 1) % cols
        faces.append([a, idx, b])

    return verts, np.array(faces, dtype=int)


def _fin_mesh(span: float, length: float, thickness: float) -> tuple[np.ndarray, np.ndarray]:
    h = thickness / 2.0
    verts = np.array(
        [
            [0, -length / 2, 0],
            [span, -length / 2, 0],
            [span, length / 2, 0],
            [0, length / 2, 0],
            [0, -length / 2, thickness],
            [span, -length / 2, thickness],
            [span, length / 2, thickness],
            [0, length / 2, thickness],
        ],
        dtype=float,
    )
    verts[:, 0] -= span / 2.0
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
        ],
        dtype=int,
    )
    return verts, faces


class _Part:
    __slots__ = ("item", "offset")

    def __init__(self, item: gl.GLMeshItem, offset: np.ndarray) -> None:
        self.item = item
        self.offset = offset


class ThreeDVisualizer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(220)

        self.label = QLabel("3D CanSat Visualization")
        self.label.setStyleSheet("color: #888; font-size: 10pt; padding: 2px;")
        layout.addWidget(self.label)

        if _HAS_OPENGL:
            self.view = BlenderStyleGLViewWidget()
            self.view.setBackgroundColor("#1a1a2e")
            self.view.setCameraPosition(pos=QVector3D(0, 0, 0), distance=45, elevation=15, azimuth=0)
            self.view._store_defaults()
            layout.addWidget(self.view)
            self._build_scene()
        else:
            fallback = QLabel("OpenGL not available\n3D view disabled")
            fallback.setStyleSheet("color: #888; font-size: 12pt; padding: 20px;")
            fallback.setAlignment(0x0084)
            layout.addWidget(fallback)
            self.view = fallback

        self._altitude_display = 0.0
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self._auto_yaw = 0.0
        self._last_orientation_update = 0.0
        self._auto_spin_enabled = True

        if _HAS_OPENGL:
            self._auto_spin_timer = QTimer(self)
            self._auto_spin_timer.timeout.connect(self._auto_spin_tick)
            self._auto_spin_timer.start(33)

    def _auto_spin_tick(self) -> None:
        if not _HAS_OPENGL or not self._parts:
            return
        elapsed = time.monotonic() - self._last_orientation_update
        if elapsed < 2.0:
            self._auto_spin_enabled = False
            return
        self._auto_spin_enabled = True
        self._auto_yaw = (self._auto_yaw + 0.5) % 360.0
        self._apply_transform(self._auto_yaw, 0.0, 0.0, self._altitude_display)

    def _apply_transform(self, yaw: float, pitch: float, roll: float, altitude: float) -> None:
        cy = math.cos(math.radians(yaw))
        sy = math.sin(math.radians(yaw))
        cp = math.cos(math.radians(pitch))
        sp = math.sin(math.radians(pitch))
        cr = math.cos(math.radians(roll))
        sr = math.sin(math.radians(roll))

        R = np.array(
            [
                [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                [-sp, cp * sr, cp * cr],
            ],
            dtype=float,
        )
        t = np.array([0.0, altitude, 0.0], dtype=float)

        for part in self._parts:
            M = np.eye(4)
            M[:3, :3] = R
            M[:3, 3] = R @ part.offset + t
            part.item.setTransform(M)

        self._update_ref_line()

    def _build_scene(self) -> None:
        if not _HAS_OPENGL:
            return
        self._build_ground()
        self._build_launch_pad()
        self._build_cansat()
        self._build_reference_line()
        self._build_atmosphere()

    def _build_ground(self) -> None:
        grid = gl.GLGridItem()
        grid.setSize(80, 80)
        grid.setSpacing(2, 2)
        grid.setColor((0.15, 0.25, 0.15, 0.6))
        self.view.addItem(grid)

    def _build_launch_pad(self) -> None:
        v, f = _cylinder_mesh(radius=2.5, height=0.3, rows=3, cols=24)
        pad = gl.GLMeshItem(
            vertexes=v, faces=f, color=(0.25, 0.25, 0.28, 1),
            smooth=True, shader="shaded", glOptions="opaque",
        )
        pad.translate(0, -0.15, 0)
        self.view.addItem(pad)

        v, f = _cylinder_mesh(radius=0.6, height=0.31, rows=2, cols=20)
        ring = gl.GLMeshItem(
            vertexes=v, faces=f, color=(1, 0.3, 0.1, 1),
            smooth=True, shader="shaded", glOptions="opaque",
        )
        ring.translate(0, -0.15, 0)
        self.view.addItem(ring)

        v, f = _cylinder_mesh(radius=0.35, height=0.32, rows=2, cols=20)
        inner = gl.GLMeshItem(
            vertexes=v, faces=f, color=(0.1, 0.8, 0.1, 1),
            smooth=True, shader="shaded", glOptions="opaque",
        )
        inner.translate(0, -0.15, 0)
        self.view.addItem(inner)

    def _build_cansat(self) -> None:
        self._parts: list[_Part] = []

        v, f = _cylinder_mesh(radius=0.35, height=0.8, rows=8, cols=16)
        self._add_part(v, f, (0, 0.4, 0), (0.08, 0.45, 0.92, 1), True)
        self._add_stripe(0.15)
        self._add_stripe(0.55)
        self._add_nose()
        self._add_fins()

    def _add_part(
        self, verts: np.ndarray, faces: np.ndarray,
        offset: tuple[float, float, float],
        color: tuple[float, float, float, float],
        smooth: bool = True,
    ) -> None:
        item = gl.GLMeshItem(
            vertexes=verts, faces=faces, color=color,
            smooth=smooth, shader="shaded", glOptions="opaque",
        )
        self.view.addItem(item)
        self._parts.append(_Part(item, np.array(offset, dtype=float)))

    def _add_stripe(self, y: float) -> None:
        v, f = _cylinder_mesh(radius=0.36, height=0.06, rows=2, cols=16)
        item = gl.GLMeshItem(
            vertexes=v, faces=f, color=(1, 1, 1, 0.9),
            smooth=True, shader="shaded", glOptions="translucent",
        )
        self.view.addItem(item)
        self._parts.append(_Part(item, np.array([0, y, 0], dtype=float)))

    def _add_nose(self) -> None:
        v, f = _cone_mesh(radius=0.35, height=0.35, cols=16)
        item = gl.GLMeshItem(
            vertexes=v, faces=f, color=(0.9, 0.15, 0.1, 1),
            smooth=True, shader="shaded", glOptions="opaque",
        )
        self.view.addItem(item)
        self._parts.append(_Part(item, np.array([0, 0.975, 0], dtype=float)))

    def _add_fins(self) -> None:
        fv, ff = _fin_mesh(span=0.4, length=0.25, thickness=0.02)
        for i in range(4):
            angle = 2.0 * math.pi * i / 4
            cx = 0.35 * math.cos(angle)
            cz = 0.35 * math.sin(angle)
            item = gl.GLMeshItem(
                vertexes=fv, faces=ff, color=(0.9, 0.15, 0.1, 1),
                smooth=False, shader="shaded", glOptions="opaque",
            )
            self.view.addItem(item)
            self._parts.append(_Part(item, np.array([cx, -0.35, cz], dtype=float)))

    def _build_reference_line(self) -> None:
        pts = np.array([[0, 0, 0], [0, 30, 0]], dtype=float)
        self._alt_line = gl.GLLinePlotItem(
            pos=pts, color=(0.2, 0.5, 1, 0.15),
            width=1, antialias=True, mode="line_strip",
        )
        self.view.addItem(self._alt_line)

        pts = np.array([[0, 0, 0], [0, 0.5, 0]], dtype=float)
        self._ref_line = gl.GLLinePlotItem(
            pos=pts, color=(0.3, 0.6, 1, 0.5),
            width=2, antialias=True, mode="line_strip",
        )
        self.view.addItem(self._ref_line)

    def _build_atmosphere(self) -> None:
        axis = gl.GLAxisItem()
        axis.setSize(3, 3, 3)
        axis.translate(-8, 0, -8)
        self.view.addItem(axis)

    def update_orientation(self, roll: float, pitch: float, yaw: float, altitude: float) -> None:
        if not _HAS_OPENGL:
            return
        self._roll = roll
        self._pitch = pitch
        self._yaw = yaw
        self._altitude_display = altitude / ALT_SCALE
        self._last_orientation_update = time.monotonic()
        self._apply_transform(yaw, pitch, roll, self._altitude_display)

    def _update_ref_line(self) -> None:
        y = self._altitude_display
        pts = np.array([[0, 0, 0], [0, y, 0]], dtype=float)
        self._ref_line.setData(pos=pts)

    def set_daylight(self, enabled: bool) -> None:
        if not _HAS_OPENGL:
            return
        if enabled:
            self.view.setBackgroundColor("#cce0ff")
            self.label.setStyleSheet("color: #000; font-size: 10pt; padding: 2px;")
        else:
            self.view.setBackgroundColor("#1a1a2e")
            self.label.setStyleSheet("color: #888; font-size: 10pt; padding: 2px;")
