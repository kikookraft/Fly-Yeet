"""Application entry that builds a layered menu using the gui library.

This creates a simple menu mode (with placeholders) and a map mode stub.
It uses the LayeredRenderer from `gui.py` to manage draw order.

Direct test mode:
    python main.py maps/easy/01_linear_path.txt
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Optional

import math
import random

import pygame

import gui
import parser


# ---------------------------------------------------------------------------
# Layer constants (draw order: lower number = behind)
# ---------------------------------------------------------------------------

LAYER_BG: int = 0           # tiled background / ambient drones
LAYER_CONNECTIONS: int = 1  # connection lines between hubs
LAYER_HUBS: int = 2         # hub circles + icons
LAYER_MISC: int = 3         # info popups / tooltips (future)
LAYER_DRONES: int = 4       # simulation drones
LAYER_MENU: int = 5         # buttons, HUD, overlays


# ---------------------------------------------------------------------------
# Helper: parse → GUI conversion
# ---------------------------------------------------------------------------

# Map (difficulty, index) → disk filename
_MAP_INDEX: dict[tuple[str, int], str] = {
    ("easy", 1): "01_linear_path.txt",
    ("easy", 2): "02_simple_fork.txt",
    ("easy", 3): "03_basic_capacity.txt",
    ("medium", 1): "01_dead_end_trap.txt",
    ("medium", 2): "02_circular_loop.txt",
    ("medium", 3): "03_priority_puzzle.txt",
    ("hard", 1): "01_maze_nightmare.txt",
    ("hard", 2): "02_capacity_hell.txt",
    ("hard", 3): "03_ultimate_challenge.txt",
    ("challenger", 1): "01_the_impossible_dream.txt",
}


def build_map_gui(map_data: parser.Map) -> gui.Map_gui:
    """Convert a parsed :class:`parser.Map` into renderable GUI objects.

    Creates :class:`gui.Hub_gui` for every hub and
    :class:`gui.Connection_gui` for every connection, wiring them together.
    """
    map_gui = gui.Map_gui()

    # 1. Create all hubs
    for hub in map_data.all_hubs:
        hub_gui_obj = gui.Hub_gui(
            x=hub.position.x,
            y=hub.position.y,
            name=hub.name,
            color=hub.color.rgb_tuple,
            max_drones=hub.max_drones,
            zone_type=hub.zone_type.value,
            is_start=hub.is_start,
            is_end=hub.is_end,
        )
        map_gui.add_hub(hub_gui_obj)

    # 2. Create connections (wire hub references)
    for conn in map_data.connections:
        hub_a = map_gui.hubs.get(conn.from_hub)
        hub_b = map_gui.hubs.get(conn.to_hub)
        if hub_a is not None and hub_b is not None:
            conn_gui = gui.Connection_gui(
                hub_a=hub_a,
                hub_b=hub_b,
                max_link_capacity=conn.max_link_capacity,
            )
            map_gui.add_connection(conn_gui)

    return map_gui


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class App:
    def __init__(self) -> None:
        self.window = gui.Window()
        self.renderer = gui.LayeredRenderer()
        self.running: bool = True
        self.state: str = "menu"
        self.menu_level: str = "root"
        self.selected_map: Optional[str] = None
        self.selected_difficulty: Optional[str] = None
        self.pan_active: bool = False
        self.logo_phase: float = 0.0

        self.interactives: list[gui.Button] = []
        self._map_gui: Optional[gui.Map_gui] = None
        self._build_root_menu()

        self.fps = gui.Text(10, 10, 24, "FPS: 0")
        self.state_text = gui.Text(10, 40, 20, "State: menu")

    def _clear_menu_layers(self) -> None:
        self.renderer.clear_layer(1)
        self.renderer.clear_layer(2)
        self.renderer.clear_layer(3)
        self.renderer.clear_layer(4)
        self.renderer.clear_layer(5)
        self.interactives = []

    def _register_button(
        self,
        button: gui.Button,
        layer: int = 2,
    ) -> gui.Button:
        self.renderer.add(button, layer=layer)
        self.interactives.append(button)
        return button

    def _build_background(self) -> None:
        self.renderer.clear_layer(0)
        self.bg_drones: list[gui.Drone] = []
        for i in range(8):
            if i % 2 == 0:
                self.bg_drones.append(
                    gui.Drone(
                        random.uniform(500, self.window.width - 500),
                        random.uniform(300, self.window.height - 300),
                        debug=False,
                        cooldown=-1,
                        image_path="assets/cardbox.png",
                    )
                )
            self.bg_drones.append(
                gui.Drone(
                    random.uniform(300, self.window.width - 300),
                    random.uniform(300, self.window.height - 300),
                    debug=False,
                    cooldown=random.uniform(0.2, 1.0),
                    image_path="assets/drone2.png",
                ))
        for d in self.bg_drones:
            self.renderer.add(d, layer=0)

    def _build_root_menu(self) -> None:
        self.state = "menu"
        self.menu_level = "root"
        self.selected_difficulty = None
        self.selected_map = None
        self._clear_menu_layers()
        self._build_background()

        # Reset view
        self.window.set_zoom(1.0)
        self.window.set_offset(0, 0)

        self.logo = gui.ImageObject(
            "assets/logo.png",
            self.window.width / 2,
            130,
            scale=1,
        )
        self.renderer.add(self.logo, layer=1)

        center_x = self.window.width / 2
        start_y = 380
        spacing = 82

        def make_button(
            y: float,
            text: str,
            hook: Callable[[], None],
        ) -> gui.Button:
            btn = gui.Button(
                center_x,
                y,
                420,
                60,
                gui.Text(0, 0, 36, text),
                radius=8,
            )
            btn.set_hook(hook)
            return self._register_button(btn)

        def start_easy() -> None:
            self._build_difficulty_menu("easy")

        def start_medium() -> None:
            self._build_difficulty_menu("medium")

        def start_hard() -> None:
            self._build_difficulty_menu("hard")

        def start_challenger() -> None:
            self._build_difficulty_menu("challenger")

        def quit_app() -> None:
            self.running = False

        self.btn_easy = make_button(start_y, "Easy Levels", start_easy)
        self.btn_medium = make_button(
            start_y + spacing,
            "Medium Levels",
            start_medium,
        )
        self.btn_hard = make_button(
            start_y + spacing * 2,
            "Hard Levels",
            start_hard,
        )
        self.btn_challenger = make_button(
            start_y + spacing * 3,
            "Challenger Levels",
            start_challenger,
        )
        self.btn_quit = make_button(start_y + spacing * 4, "Quit", quit_app)

        title = gui.Text(
            self.window.width / 2,
            300,
            48,
            "Welcome to Fly YEEET!",
            centered=True,
            lock_to_screen=False
        )
        self.renderer.add(title, layer=3)

        attrib = gui.Text(
            self.window.width - 150,
            self.window.height - 50,
            36,
            "Made by Tobesson!",
            centered=True
        )
        self.renderer.add(attrib, layer=3)

    def _build_difficulty_menu(self, difficulty: str) -> None:
        self.state = "menu"
        self.menu_level = difficulty
        self.selected_difficulty = difficulty
        self.selected_map = None
        self._clear_menu_layers()
        self._build_background()

        # Reset view
        self.window.set_zoom(1.0)
        self.window.set_offset(0, 0)

        title = gui.Text(
            self.window.width / 2,
            180,
            42,
            f"{difficulty.title()} maps",
            centered=True,
            lock_to_screen=False
        )
        self.renderer.add(title, layer=1)

        center_x = self.window.width / 2
        start_y = 350
        spacing = 90

        def make_map_button(index: int) -> gui.Button:
            filename: str = _MAP_INDEX.get((difficulty, index), "")
            map_path: str = os.path.join("maps", difficulty, filename)

            def select_map() -> None:
                self.selected_map = map_path
                self.state = "map"
                self._enter_map_mode(map_path)

            button = gui.Button(
                center_x,
                start_y + spacing * (index - 1),
                420,
                60,
                gui.Text(0, 0, 28, f"{difficulty.title()} map {index}"),
                radius=8,
            )
            button.set_hook(select_map)
            return self._register_button(button)

        if difficulty in ("easy", "medium", "hard"):
            for index in range(1, 4):
                make_map_button(index)
        elif difficulty == "challenger":
            make_map_button(1)

        def go_back() -> None:
            self._build_root_menu()

        back_button = gui.Button(
            center_x,
            start_y + spacing * 3.5,
            420,
            60,
            gui.Text(0, 0, 28, "Back"),
            radius=8,
        )
        back_button.set_hook(go_back)
        self._register_button(back_button)

    def _enter_map_mode(self, map_path: str) -> None:
        """Parse *map_path* and populate the renderer with the map."""
        # Clear previous map layers and menu artefacts
        self.renderer.clear_layer(LAYER_BG)
        self.renderer.clear_layer(LAYER_CONNECTIONS)
        self.renderer.clear_layer(LAYER_HUBS)
        self._clear_menu_layers()

        try:
            parsed = parser.parse_map_file(map_path)
            self._map_gui = build_map_gui(parsed)
            # Add connections (lines behind) and hubs on dedicated layers
            for conn in self._map_gui.connections:
                self.renderer.add(conn, layer=LAYER_CONNECTIONS)
            for hub_obj in self._map_gui.hubs.values():
                self.renderer.add(hub_obj, layer=LAYER_HUBS)

            # Center the map in the view
            self._center_map_view()

            # Show map name as overlay
            label = gui.Text(
                self.window.width // 2,
                30,
                32,
                os.path.basename(map_path),
                centered=True,
                lock_to_screen=True,
            )
            self.renderer.add(label, layer=LAYER_MENU)
        except (ValueError, FileNotFoundError) as exc:
            _show_error_overlay(self.renderer, self.window, str(exc))

    def _center_map_view(self) -> None:
        """Set zoom and offset so the current map fits centred on screen."""
        if self._map_gui is not None:
            _center_view(self.window, self._map_gui)

    def _handle_menu_escape(self) -> None:
        if self.menu_level == "root":
            self.running = False
        else:
            self._build_root_menu()

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        if self.state == "map":
                            self._build_difficulty_menu(
                                self.selected_difficulty or "easy",
                            )
                        else:
                            self._handle_menu_escape()
                    if event.key == pygame.K_SPACE:
                        if self.state == "map":
                            self._center_map_view()
                        else:
                            self.window.set_zoom(1.0)
                            self.window.set_offset(0, 0)
                if event.type == pygame.MOUSEWHEEL:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    world_x, world_y = self.window.screen_to_world(
                        (mouse_x, mouse_y),
                    )
                    if event.y > 0:
                        self.window.zoom(1.1)
                    elif event.y < 0:
                        self.window.zoom(1 / 1.1)
                    self.window.set_offset(
                        mouse_x - world_x * self.window.get_zoom(),
                        mouse_y - world_y * self.window.get_zoom(),
                    )
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 2:
                        self.pan_active = True
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    world_pos = self.window.screen_to_world(event.pos)
                    for it in self.interactives:
                        if it.is_hovered(world_pos):
                            it.click(world_pos)

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 2:
                        self.pan_active = False

                if event.type == pygame.MOUSEMOTION:
                    if self.pan_active:
                        self.window.pan(event.rel[0], event.rel[1])

                    world_pos = self.window.screen_to_world(event.pos)
                    for it in self.interactives:
                        it.is_hovered(world_pos)

            if self.menu_level == "root":
                self.logo_phase += 0.075
                self.logo.set_rotation(math.sin(self.logo_phase) * 25)

            self.renderer.update(self.window)

            self.window.draw_background()
            self.renderer.draw(self.window)

            self.fps.set_text(f"FPS: {self.window.get_fps()}")
            self.fps.draw(self.window.get_screen())
            if self.state == "map":
                self.state_text.set_text(
                    f"Map mode: {self.selected_map or 'none'}",
                )
            elif self.menu_level == "root":
                self.state_text.set_text("State: menu")
            else:
                self.state_text.set_text(
                    f"State: {self.menu_level} submenu",
                )
            self.state_text.draw(self.window.get_screen())

            self.window.update()


# ---------------------------------------------------------------------------
# Direct test mode:  python main.py <map_file>
# ---------------------------------------------------------------------------

def _show_error_overlay(
    renderer: gui.LayeredRenderer,
    window: gui.Window,
    error_message: str,
) -> None:
    """Display parser errors as a stacked list of red labels with a backdrop."""
    error_lines: list[str] = error_message.split("\n")
    line_height: int = 26
    title_height: int = 36
    pad: int = 24

    # Box dimensions
    box_w: int = max(600, min(1200, window.width - 200))
    box_h: int = title_height + len(error_lines) * line_height + pad * 2

    # Box centre fixed at screen centre
    cx: int = window.width // 2
    cy: int = window.height // 2

    # Top of the content area (title)
    content_top: int = cy - box_h // 2 + pad

    # Dark semi-transparent backdrop
    backdrop = gui.Rect(
        cx, cy, box_w, box_h,
        color=(20, 20, 30),
        alpha=210,
        radius=12,
    )
    renderer.add(backdrop, layer=LAYER_MENU)

    # Title
    title_err = gui.Text(
        cx,
        content_top,
        32,
        "--  Parsing Errors  --",
        color=(255, 100, 100),
        centered=True,
        lock_to_screen=False,
    )
    renderer.add(title_err, layer=LAYER_MENU)

    # Each error line
    for idx, err_line in enumerate(error_lines):
        label = gui.Text(
            cx,
            content_top + title_height + idx * line_height,
            22,
            err_line.strip(),
            color=(255, 160, 140),
            centered=True,
            lock_to_screen=False,
        )
        renderer.add(label, layer=LAYER_MENU)


def _center_view(window: gui.Window, map_gui_obj: gui.Map_gui) -> None:
    """Set *window* zoom and offset so *map_gui_obj* fits centred."""
    hubs = list(map_gui_obj.hubs.values())
    if not hubs:
        return

    min_x: float = min(h.x for h in hubs)
    max_x: float = max(h.x for h in hubs)
    min_y: float = min(h.y for h in hubs)
    max_y: float = max(h.y for h in hubs)

    cx: float = (min_x + max_x) / 2.0
    cy: float = (min_y + max_y) / 2.0
    hub_size: float = float(hubs[0].size)

    world_w: float = (max_x - min_x) + hub_size * 2
    world_h: float = (max_y - min_y) + hub_size * 2

    margin: float = 0.85
    zoom_x: float = window.width / max(world_w, 1) * margin
    zoom_y: float = window.height / max(world_h, 1) * margin
    zoom: float = min(zoom_x, zoom_y)
    zoom = max(0.34, min(2.0, zoom))

    offset_x: float = window.width / 2.0 - cx * zoom
    offset_y: float = window.height / 2.0 - cy * zoom

    window.set_zoom(zoom)
    window.set_offset(offset_x, offset_y)


def _quick_view(map_path: str) -> None:
    """Bypass the menu and render a single map directly."""
    window = gui.Window()
    renderer = gui.LayeredRenderer()

    # Parse and build (may fail gracefully)
    map_gui_obj: Optional[gui.Map_gui] = None
    try:
        parsed = parser.parse_map_file(map_path)
        map_gui_obj = build_map_gui(parsed)

        for conn in map_gui_obj.connections:
            renderer.add(conn, layer=LAYER_CONNECTIONS)
        for hub_obj in map_gui_obj.hubs.values():
            renderer.add(hub_obj, layer=LAYER_HUBS)

        # Center the view
        _center_view(window, map_gui_obj)
    except (ValueError, FileNotFoundError) as exc:
        _show_error_overlay(renderer, window, str(exc))

    if map_gui_obj is not None:
        title = gui.Text(
            window.width // 2, 30, 32,
            os.path.basename(map_path),
            centered=True,
        )
        renderer.add(title, layer=LAYER_MENU)
    hint = gui.Text(
        window.width // 2, window.height - 50, 24,
        "ESC / Q = quit  |  scroll = zoom  |  " +
        "middle-drag = pan  |  SPACE = reset view",
        centered=True,
    )
    renderer.add(title, layer=LAYER_MENU)
    renderer.add(hint, layer=LAYER_MENU)

    fps_text = gui.Text(10, 10, 24, "FPS: 0")

    pan_active = False
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                if event.key == pygame.K_SPACE and map_gui_obj is not None:
                    _center_view(window, map_gui_obj)
            if event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                wx, wy = window.screen_to_world((mx, my))
                if event.y > 0:
                    window.zoom(1.1)
                elif event.y < 0:
                    window.zoom(1 / 1.1)
                window.set_offset(
                    mx - wx * window.get_zoom(),
                    my - wy * window.get_zoom(),
                )
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                pan_active = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                pan_active = False
            if event.type == pygame.MOUSEMOTION and pan_active:
                window.pan(event.rel[0], event.rel[1])

        window.draw_background()
        renderer.draw(window)

        fps_text.set_text(f"FPS: {window.get_fps()}")
        fps_text.draw(window.get_screen())
        window.update()

    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Direct test: python main.py <map_file>
        _quick_view(sys.argv[1])
    else:
        App().run()
        pygame.quit()
