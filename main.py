"""Application entry that builds a layered menu using the gui library.

This creates a simple menu mode (with placeholders) and a map mode stub.
It uses the LayeredRenderer from `gui.py` to manage draw order.
"""
from typing import Callable, Optional

import math
import random

import pygame

import gui


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
        self._build_root_menu()

        self.fps = gui.Text(10, 10, 24, "FPS: 0")
        self.state_text = gui.Text(10, 40, 20, "State: menu")

    def _clear_menu_layers(self) -> None:
        self.renderer.clear_layer(1)
        self.renderer.clear_layer(2)
        self.renderer.clear_layer(3)
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
        self.bg_drones: list[gui.Drone] = [
            gui.Drone(
                random.uniform(100, 800),
                random.uniform(100, 600),
                debug=False,
                cooldown=random.uniform(0.2, 1.0),
                image_path="assets/drone2.png",
            )
            for _ in range(8)
        ]
        for d in self.bg_drones:
            self.renderer.add(d, layer=0)

    def _build_root_menu(self) -> None:
        self.state = "menu"
        self.menu_level = "root"
        self.selected_difficulty = None
        self.selected_map = None
        self._clear_menu_layers()
        self._build_background()

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
        self.btn_quit = make_button(start_y + spacing * 3, "Quit", quit_app)

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
            map_name = f"{difficulty}_map_{index}"

            def select_map() -> None:
                self.selected_map = map_name
                self.state = "map"

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

        for index in range(1, 4):
            make_map_button(index)

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

            if self.state == "map":
                placeholder = gui.Text(
                    self.window.width / 2 - 240,
                    self.window.height - 120,
                    28,
                    f"Map mode: {self.selected_map} (placeholder)",
                )
                placeholder.draw(self.window.get_screen())

            self.window.update()


if __name__ == "__main__":
    app = App()
    app.run()
