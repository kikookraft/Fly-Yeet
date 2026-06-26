from __future__ import annotations

import os
import random
from typing import Any, Callable, Dict, Optional, Protocol

import pygame
import math

pygame.init()
CELLS = 50


class _Drawable(Protocol):
    """Protocol for objects that can be drawn by the renderer."""

    def draw(self, *args: Any, **kwargs: Any) -> None:
        """Draw the object using the provided window."""


def bezier(x: float) -> float:
    """calculate bezier curve for smooth moves or transitions"""
    return 3 * x**2 - 2 * x**3

# =============================================================================
# Validation functions
# =============================================================================


def _ensure_number(
    value: float,
    name: str,
    *,
    positive: bool = False,
) -> float:
    """Validate a numeric value."""
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a number")
    numeric_value = float(value)
    if positive and numeric_value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return numeric_value


def _ensure_int(
    value: float,
    name: str,
    *,
    minimum: int | None = None,
) -> int:
    """Validate an integer value."""
    numeric_value = _ensure_number(value, name)
    if not numeric_value.is_integer():
        raise ValueError(f"{name} must be an integer")
    integer_value = int(numeric_value)
    if minimum is not None and integer_value < minimum:
        raise ValueError(f"{name} must be greater than or equal to {minimum}")
    return integer_value


def _ensure_color(
    color: tuple[int, int, int],
    name: str = "color",
) -> tuple[int, int, int]:
    """Validate an RGB color."""
    if type(color) is not tuple or len(color) != 3:
        raise TypeError(f"{name} must be a tuple of 3 integers")
    red = _ensure_int(color[0], f"{name} channel", minimum=0)
    green = _ensure_int(color[1], f"{name} channel", minimum=0)
    blue = _ensure_int(color[2], f"{name} channel", minimum=0)
    if any(channel > 255 for channel in (red, green, blue)):
        raise ValueError(f"{name} channels must be between 0 and 255")
    return (red, green, blue)


def _ensure_point(
    point: tuple[float, float],
    name: str = "position",
) -> tuple[float, float]:
    """Validate a 2D point."""
    if type(point) is not tuple or len(point) != 2:
        raise TypeError(f"{name} must be a tuple of 2 numbers")
    return (
        _ensure_number(point[0], f"{name} x"),
        _ensure_number(point[1], f"{name} y"),
    )


def _ensure_image_path(image_path: str) -> str:
    """Validate an image path."""
    if type(image_path) is not str:
        raise TypeError("image_path must be a string")
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"image_path does not exist: {image_path}")
    return image_path


# =============================================================================
# GUI Classes
# =============================================================================


class Window:
    def __init__(
            self,
            width: int = 3000,
            height: int = 1500,
            fps: int = 100) -> None:
        """Create a window."""
        self.width: int = _ensure_int(width, "width", minimum=1)
        self.height: int = _ensure_int(height, "height", minimum=1)
        self.fps: int = _ensure_int(fps, "fps", minimum=1)
        self.current_fps: float = 0
        self._zoom: float = 1.0
        self.offset: tuple[float, float] = (0, 0)
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.width, self.height), pygame.NOFRAME)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        pygame.display.set_caption("Fly YEEET")
        self.background_tile: pygame.Surface = pygame.image.load(
            "assets/tile.png").convert()
        self.bg_w: int = self.background_tile.get_width()
        self.bg_h: int = self.background_tile.get_height()
        # Mouse tracking (updated each frame by main loop)
        self.mouse_screen_pos: tuple[int, int] = (0, 0)
        self.mouse_world_pos: tuple[int, int] = (0, 0)

    def draw_background(self) -> None:
        """Draw the tiled background."""
        self.screen.fill((0, 0, 0))
        # Tile background infinitely based on camera offset and zoom
        scaled_w: int = int(self.bg_w * self._zoom)
        scaled_h: int = int(self.bg_h * self._zoom)
        if scaled_w <= 0 or scaled_h <= 0:
            return

        scaled_tile: pygame.Surface = pygame.transform.scale(
            self.background_tile, (scaled_w, scaled_h))

        start_x: int = int(self.offset[0] % scaled_w)
        if start_x > 0:
            start_x -= scaled_w
        start_y: int = int(self.offset[1] % scaled_h)
        if start_y > 0:
            start_y -= scaled_h

        for x in range(start_x, self.width, scaled_w):
            for y in range(start_y, self.height, scaled_h):
                self.screen.blit(scaled_tile, (x, y))

    def update(self) -> None:
        """Refresh the frame."""
        pygame.display.flip()
        self.clock.tick(self.fps)
        self.current_fps = math.floor(self.clock.get_fps())

    def screen_to_world(self, pos: tuple[float, float]) -> tuple[int, int]:
        """Convert screen coordinates to world coordinates."""
        return (int((pos[0] - self.offset[0]) / self._zoom),
                int((pos[1] - self.offset[1]) / self._zoom))

    def world_to_screen(self, pos: tuple[float, float]) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        return (int(pos[0] * self._zoom + self.offset[0]),
                int(pos[1] * self._zoom + self.offset[1]))

    def zoom(self, factor: float) -> None:
        """Apply a zoom factor."""
        factor = _ensure_number(factor, "factor", positive=True)
        self._zoom *= factor
        # Limit the unzoom to 3 times the original size
        if self._zoom < 0.33333333:
            self._zoom = 0.33333333
        elif self._zoom > 2:
            self._zoom = 2

    def set_zoom(self, zoom_value: float) -> None:
        """Set the zoom level."""
        self._zoom = _ensure_number(zoom_value, "zoom_value", positive=True)
        if self._zoom < 0.33333333:
            self._zoom = 0.33333333
        elif self._zoom > 2:
            self._zoom = 2

    def pan(self, dx: float, dy: float) -> None:
        """Move the camera offset."""
        dx = _ensure_number(dx, "dx")
        dy = _ensure_number(dy, "dy")
        self.offset = (self.offset[0] + dx, self.offset[1] + dy)

    def set_offset(self, x: float, y: float) -> None:
        """Set the camera offset."""
        x = _ensure_number(x, "x")
        y = _ensure_number(y, "y")
        self.offset = (x, y)

    def get_width(self) -> int:
        """Return the window width."""
        return self.width

    def get_height(self) -> int:
        """Return the window height."""
        return self.height

    def get_fps_limit(self) -> int:
        """Return the target frame rate."""
        return self.fps

    def get_screen(self) -> pygame.Surface:
        """Return the screen surface."""
        return self.screen

    def get_zoom(self) -> float:
        """Return the current zoom level."""
        return self._zoom

    def get_offset(self) -> tuple[float, float]:
        """Return the current camera offset."""
        return self.offset

    def get_fps(self) -> float:
        """Return the measured frame rate."""
        return self.current_fps


class Text:
    def __init__(
            self,
            x: float = 0,
            y: float = 0,
            size: int = 36,
            text: str = "",
            color: tuple[int, int, int] = (255, 255, 255),
            centered: bool = False,
            lock_to_screen: bool = True,
    ) -> None:
        """Create a text label."""
        self.x: float = _ensure_number(x, "x")
        self.y: float = _ensure_number(y, "y")
        self.size: int = _ensure_int(size, "size", minimum=1)
        self.text: str = text
        self.color: tuple[int, int, int] = _ensure_color(color)
        self.font: pygame.font.Font = pygame.font.SysFont(None, self.size)
        self.text_surface: pygame.Surface = self.font.render(
            self.text, True, self.color)
        self.centered: bool = centered
        # When True the text is drawn in screen-space (HUD).
        # When False the text follows world coordinates (affected by pan/zoom).
        self.lock_to_screen: bool = bool(lock_to_screen)

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the text label."""
        if self.centered:
            text_rect = self.text_surface.get_rect()
            text_rect.center = (int(self.x), int(self.y))
            screen.blit(self.text_surface, text_rect)
        else:
            screen.blit(self.text_surface, (self.x, self.y))

    def set_text(self, text: str) -> None:
        """Set the text content."""
        if type(text) is not str:
            raise TypeError("text must be a string")
        if text != self.text:
            self.text = text
            self.text_surface = self.font.render(
                self.text, True, self.color)

    def set_size(self, size: int) -> None:
        """Set the font size."""
        self.size = _ensure_int(size, "size", minimum=1)
        self.font = pygame.font.SysFont(None, self.size)
        self.text_surface = self.font.render(self.text, True, self.color)

    def set_color(self, color: tuple[int, int, int]) -> None:
        """Set the text color."""
        self.color = _ensure_color(color)
        self.text_surface = self.font.render(self.text, True, self.color)

    def set_pos(self, x: float | tuple[float, float], y: float | None = None
                ) -> None:
        """Set the text position."""
        if isinstance(x, tuple):
            self.x, self.y = _ensure_point(x, "position")
        else:
            self.x = _ensure_number(x, "x")
            if y is not None:
                self.y = _ensure_number(y, "y")

    def get_pos(self) -> tuple[float, float]:
        """Return the text position."""
        return (self.x, self.y)

    def get_text(self) -> str:
        """Return the text content."""
        return self.text

    def get_size(self) -> tuple[int, int]:
        """Return the text surface size."""
        return (self.text_surface.get_width(), self.text_surface.get_height())

    def get_font_size(self) -> int:
        """Return the font size."""
        return self.size

    def get_color(self) -> tuple[int, int, int]:
        """Return the text color."""
        return self.color


class Button:
    def __init__(self,
                 x: float,
                 y: float,
                 width: float,
                 height: float,
                 text: Text | str,
                 radius: int = 0) -> None:
        """Create a button."""
        self.x: float = _ensure_number(x, "x")
        self.y: float = _ensure_number(y, "y")
        self.width: float = _ensure_number(width, "width", positive=True)
        self.height: float = _ensure_number(height, "height", positive=True)
        self.text: Text = text if isinstance(text, Text) else Text(text=text)
        self.radius: int = _ensure_int(radius, "radius", minimum=0)
        self.enabled: bool = True
        self.color: tuple[int, int, int] = (100, 100, 100)
        self.disabled_color: tuple[int, int, int] = (150, 150, 150)
        self.hover_color: tuple[int, int, int] = (175, 175, 175)
        self.hovered: bool = False
        self.prev_hovered: bool = False
        self.hook: Callable[[], None] = lambda: None
        self.hook_args: Dict[str, object] = {}
        self.anim_time: float = .15
        self.start_time: float = 0
        self.end_time: float = 0
        self._center_text()

    def _center_text(self) -> None:
        """Center the label inside the button."""
        self.text.x = self.x - self.text.text_surface.get_width() / 2
        self.text.y = self.y - self.text.text_surface.get_height() / 2

    def set_pos(self, x: float | tuple[float, float], y: float | None = None
                ) -> None:
        """Set the button position."""
        if isinstance(x, tuple):
            self.x, self.y = _ensure_point(x, "position")
        else:
            self.x = _ensure_number(x, "x")
            if y is not None:
                self.y = _ensure_number(y, "y")
        self._center_text()

    def get_pos(self) -> tuple[float, float]:
        """Return the button position."""
        return (self.x, self.y)

    def get_width(self) -> float:
        """Return the button width."""
        return self.width

    def set_width(self, width: float) -> None:
        """Set the button width."""
        self.width = _ensure_number(width, "width", positive=True)

    def get_height(self) -> float:
        """Return the button height."""
        return self.height

    def set_height(self, height: float) -> None:
        """Set the button height."""
        self.height = _ensure_number(height, "height", positive=True)

    def get_radius(self) -> int:
        """Return the button radius."""
        return self.radius

    def set_radius(self, radius: int) -> None:
        """Set the button radius."""
        self.radius = _ensure_int(radius, "radius", minimum=0)

    def get_text(self) -> str:
        """Return the button label."""
        return self.text.get_text()

    def set_text(self, text: Text | str) -> None:
        """Set the button label."""
        if isinstance(text, Text):
            self.text = text
        elif type(text) is str:
            self.text.set_text(text)
        else:
            raise TypeError("text must be a Text or string")
        self._center_text()

    def get_text_object(self) -> Text:
        """Return the text object."""
        return self.text

    def get_enabled(self) -> bool:
        """Return whether the button is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        """Set whether the button is enabled."""
        if type(enabled) is not bool:
            raise TypeError("enabled must be a bool")
        self.enabled = enabled

    def get_color(self) -> tuple[int, int, int]:
        """Return the base color."""
        return self.color

    def set_color(self, color: tuple[int, int, int]) -> None:
        """Set the base color."""
        self.color = _ensure_color(color)

    def get_disabled_color(self) -> tuple[int, int, int]:
        """Return the disabled color."""
        return self.disabled_color

    def set_disabled_color(self, color: tuple[int, int, int]) -> None:
        """Set the disabled color."""
        self.disabled_color = _ensure_color(color)

    def get_hover_color(self) -> tuple[int, int, int]:
        """Return the hover color."""
        return self.hover_color

    def set_hover_color(self, color: tuple[int, int, int]) -> None:
        """Set the hover color."""
        self.hover_color = _ensure_color(color)

    def get_hook(self) -> Callable[..., None]:
        """Return the button hook."""
        return self.hook

    def set_hook(self, hook: Callable[..., None]) -> None:
        """Set the button hook."""
        if not callable(hook):
            raise TypeError("hook must be callable")
        self.hook = hook

    def get_hook_args(self) -> Dict[str, object]:
        """Return the button hook arguments."""
        return self.hook_args

    def set_hook_args(self, hook_args: Dict[str, object]) -> None:
        """Set the button hook arguments."""
        if type(hook_args) is not dict:
            raise TypeError("hook_args must be a dictionary")
        self.hook_args = hook_args

    def get_anim_time(self) -> float:
        """Return the hover animation time."""
        return self.anim_time

    def set_anim_time(self, anim_time: float) -> None:
        """Set the hover animation time."""
        self.anim_time = _ensure_number(anim_time, "anim_time", positive=True)

    def is_hovered(self, mouse_pos: tuple[int, int]) -> bool:
        """Return whether the button is hovered."""
        if not self.enabled:
            return False
        validated_mouse_x, validated_mouse_y = _ensure_point(
            mouse_pos, "mouse_pos")
        cx: float = self.center()[0]
        cy: float = self.center()[1]
        self.hovered = (
            cx <= validated_mouse_x <= cx + self.width and
            cy <= validated_mouse_y <= cy + self.height
        )
        if self.hovered != self.prev_hovered:
            self.start_time = pygame.time.get_ticks() / 1000
            self.end_time = self.start_time + self.anim_time
        self.prev_hovered = self.hovered
        return self.hovered

    def click(self, mouse_pos: tuple[int, int]) -> None:
        """Invoke the hook when clicked."""
        if self.enabled and self.is_hovered(mouse_pos):
            self.hook(**self.hook_args)

    def center(self) -> tuple[float, float]:
        """Return the top-left corner used for drawing."""
        return (self.x - self.width / 2, self.y - self.height / 2)

    def draw(self, window: 'Window') -> None:
        """Draw the button."""
        if not self.enabled:
            return
        # detect hover animation
        actual_color: tuple[int, int, int]
        if pygame.time.get_ticks() / 1000 < self.end_time:
            completion: float = (
                pygame.time.get_ticks() / 1000 - self.start_time
            ) / self.anim_time
            completion = max(0, min(1, completion))
            if self.hovered:
                target_color = self.hover_color
                from_color = self.color
            else:
                target_color = self.color
                from_color = self.hover_color
            actual_color = (
                int(
                    bezier(completion) * target_color[0]
                    + (1 - bezier(completion)) * from_color[0]
                ),
                int(
                    bezier(completion) * target_color[1]
                    + (1 - bezier(completion)) * from_color[1]
                ),
                int(
                    bezier(completion) * target_color[2]
                    + (1 - bezier(completion)) * from_color[2]
                ),
            )
        else:
            if self.hovered:
                actual_color = self.hover_color
            else:
                actual_color = self.color

        cx, cy = self.center()
        scx, scy = window.world_to_screen((cx, cy))
        sw: int = int(self.width * window.get_zoom())
        sh: int = int(self.height * window.get_zoom())

        pygame.draw.rect(window.screen, actual_color,
                         (scx, scy, sw, sh),
                         border_radius=int(self.radius * window.get_zoom()))

        # update and adapt text to screen settings
        old_size: int = self.text.size
        self.text.set_size(int(old_size * window.get_zoom()))
        self.text.set_pos(window.world_to_screen((self.text.get_pos())))
        self.text.draw(window.screen)

        # restore
        self.text.set_size(old_size)
        self._center_text()


class ImageObject:
    def __init__(self,
                 image_path: str,
                 x: float,
                 y: float,
                 scale: float = 1,
                 absolute_size: bool = False) -> None:
        """Create an image object."""
        self.image_path: str = _ensure_image_path(image_path)
        self.image: pygame.Surface = pygame.image.load(
            self.image_path).convert_alpha()
        self.x: float = _ensure_number(x, "x")
        self.y: float = _ensure_number(y, "y")
        self.scale: float = _ensure_number(scale, "scale", positive=True)
        self.absolute_size: bool = absolute_size
        self.rotation: float = 0
        self.dummy: float = 0
        self._last_rotation: float | None = None
        self._last_zoom: float | None = None
        self._cached_image: pygame.Surface | None = None

    def draw(self, window: 'Window') -> None:
        """Draw the image object."""
        z = window.get_zoom()
        if (self._last_rotation != self.rotation
                or self._last_zoom != z
                or self._cached_image is None):
            rotated_image: pygame.Surface = pygame.transform.rotate(
                self.image, self.rotation)
            if not self.absolute_size:
                w = int(rotated_image.get_width() * self.scale * z)
                h = int(rotated_image.get_height() * self.scale * z)
            else:
                w = int(self.scale)
                h = int(self.scale)
            if w > 0 and h > 0:
                self._cached_image = pygame.transform.scale(
                    rotated_image, (w, h)
                )
            else:
                self._cached_image = None
            self._last_rotation = self.rotation
            self._last_zoom = z

        if self._cached_image:
            sx, sy = window.world_to_screen((self.x, self.y))
            window.screen.blit(self._cached_image, (
                sx - self._cached_image.get_width() / 2,
                sy - self._cached_image.get_height() / 2))

    def move(self, x: float, y: float) -> None:
        """Move the image object."""
        self.x = _ensure_number(x, "x")
        self.y = _ensure_number(y, "y")

    def get_pos(self) -> tuple[float, float]:
        """Return the image position."""
        return (self.x, self.y)

    def set_pos(self, x: float, y: float) -> None:
        """Set the image position."""
        self.move(x, y)

    def get_scale(self) -> float:
        """Return the image scale."""
        return self.scale

    def set_scale(self, scale: float) -> None:
        """Set the image scale."""
        self.scale = _ensure_number(scale, "scale", positive=True)

    def get_rotation(self) -> float:
        """Return the image rotation."""
        return self.rotation

    def set_rotation(self, rotation: float) -> None:
        """Set the image rotation."""
        self.rotation = _ensure_number(rotation, "rotation")

    def get_image_path(self) -> str:
        """Return the image path."""
        return self.image_path

    def set_image_path(self, image_path: str) -> None:
        """Set the image path."""
        self.image_path = _ensure_image_path(image_path)
        self.image = pygame.image.load(self.image_path).convert_alpha()
        self._last_rotation = None
        self._last_zoom = None
        self._cached_image = None


class Rect:
    def __init__(self,
                 x: float,
                 y: float,
                 width: float,
                 height: float,
                 radius: int = 0,
                 color: tuple[int, int, int] = (50, 150, 70),
                 alpha: int = 255,
                 debug: bool = False) -> None:
        """Create a rectangle object."""
        self.x: float = _ensure_number(x, "x")
        self.y: float = _ensure_number(y, "y")
        self.z: float = 0
        self.vel_x: float = 0
        self.vel_y: float = 0
        self.vel_z: float = 0
        self.width: float = _ensure_number(width, "width")
        self.height: float = _ensure_number(height, "height")
        if self.width < 0 or self.height < 0:
            raise ValueError("width and height must be non-negative")
        self.color: tuple[int, int, int] = _ensure_color(color)
        self.alpha: int = _ensure_int(alpha, "alpha", minimum=0)
        if self.alpha > 255:
            raise ValueError("alpha must be less than or equal to 255")
        self.is_mooving: bool = False
        self.target_x: float = self.x
        self.target_y: float = self.y
        self.target_z: float = self.z
        self.friction: float = .7
        self.move_power: float = 1.5
        self.radius: int = _ensure_int(radius, "radius", minimum=0)
        self.debug: bool = debug
        self.alive: bool = True
        self.rect: pygame.Surface = pygame.Surface(
            (int(self.width), int(self.height)), pygame.SRCALPHA)
        self.rotated_img: pygame.Surface = self.rect
        if debug and self.alive:
            self.debug_img: pygame.Surface = pygame.transform.scale(
                pygame.image.load("assets/up.png").convert_alpha(),
                (int(self.width), int(self.height)))
            self.rotated_img = self.debug_img

        self._last_zoom: float | None = None
        self._last_z: float | None = None
        self._last_width: float | None = None
        self._last_height: float | None = None
        self._last_radius: int | None = None
        self._last_color: tuple[int, int, int] | None = None
        self._last_alpha: int | None = None
        self._last_debug: bool | None = None
        self._cached_rect_image: pygame.Surface | None = None

    def center(self) -> tuple[float, float]:
        """Return the rectangle center."""
        return (self.x - self.width / 2, self.y - self.height / 2)

    def rotate(self, angle: float) -> None:
        """Set the rotation angle."""
        self.z = _ensure_number(angle, "angle")

    def get_z(self) -> float:
        """Return the rotation."""
        return self.z

    def get_width(self) -> float:
        """Return the width."""
        return self.width

    def set_width(self, width: float) -> None:
        """Set the width."""
        self.width = _ensure_number(width, "width")
        if self.width < 0:
            raise ValueError("width must be non-negative")

    def get_height(self) -> float:
        """Return the height."""
        return self.height

    def set_height(self, height: float) -> None:
        """Set the height."""
        self.height = _ensure_number(height, "height")
        if self.height < 0:
            raise ValueError("height must be non-negative")

    def get_color(self) -> tuple[int, int, int]:
        """Return the color."""
        return self.color

    def set_color(self, color: tuple[int, int, int]) -> None:
        """Set the color."""
        self.color = _ensure_color(color)

    def get_alpha(self) -> int:
        """Return the alpha value."""
        return self.alpha

    def set_alpha(self, alpha: int) -> None:
        """Set the alpha value."""
        self.alpha = _ensure_int(alpha, "alpha", minimum=0)
        if self.alpha > 255:
            raise ValueError("alpha must be less than or equal to 255")

    def get_is_mooving(self) -> bool:
        """Return whether the object is moving."""
        return self.is_mooving

    def get_friction(self) -> float:
        """Return the friction."""
        return self.friction

    def set_friction(self, friction: float) -> None:
        """Set the friction."""
        self.friction = _ensure_number(friction, "friction", positive=True)

    def get_move_power(self) -> float:
        """Return the move power."""
        return self.move_power

    def set_move_power(self, move_power: float) -> None:
        """Set the move power."""
        self.move_power = _ensure_number(
            move_power, "move_power", positive=True)

    def get_radius(self) -> int:
        """Return the radius."""
        return self.radius

    def set_radius(self, radius: int) -> None:
        """Set the radius."""
        self.radius = _ensure_int(radius, "radius", minimum=0)

    def get_debug(self) -> bool:
        """Return whether debug mode is enabled."""
        return self.debug

    def set_debug(self, debug: bool) -> None:
        """Set whether debug mode is enabled."""
        if type(debug) is not bool:
            raise TypeError("debug must be a bool")
        self.debug = debug

    def get_alive(self) -> bool:
        """Return whether the object is alive."""
        return self.alive

    def set_alive(self, alive: bool) -> None:
        """Set whether the object is alive."""
        if type(alive) is not bool:
            raise TypeError("alive must be a bool")
        self.alive = alive

    def get_pos(self) -> tuple[float, float]:
        """Return the position."""
        return (self.x, self.y)

    def rotate_focus(self, x: float, y: float) -> None:
        """Rotate toward a point."""
        self.target_z = math.atan2(y - self.center()[1], x - self.center()[0])

    def move_rel(self, dx: float, dy: float) -> None:
        """Update the target relative to the current position."""
        dx = _ensure_number(dx, "dx")
        dy = _ensure_number(dy, "dy")
        self.is_mooving = True
        self.target_x = self.x + dx
        self.target_y = self.y + dy
        self.rotate_focus(self.target_x, self.target_y)

    def move(self, x: float, y: float) -> None:
        """Move to a fixed position."""
        x = _ensure_number(x, "x")
        y = _ensure_number(y, "y")
        self.is_mooving = True
        self.target_x = x
        self.target_y = y
        self.rotate_focus(self.target_x, self.target_y)

    def tp(self, x: float, y: float) -> None:
        """Teleport to a fixed position."""
        self.x = _ensure_number(x, "x")
        self.y = _ensure_number(y, "y")

    def handle_moves(self) -> None:
        """Advance movement physics."""
        diff_x: float = self.target_x - self.x
        diff_y: float = self.target_y - self.y
        diff_z: float = (
            (self.target_z - self.z + math.pi) % (2 * math.pi) - math.pi)
        self.vel_x += diff_x * 0.05 * self.move_power
        self.vel_y += diff_y * 0.05 * self.move_power
        self.vel_z += diff_z * 0.05 * self.move_power
        self.vel_x *= self.friction
        self.vel_y *= self.friction
        self.vel_z *= self.friction
        self.x += self.vel_x
        self.y += self.vel_y
        self.rotate(self.z + self.vel_z)

        if (
            abs(diff_x) < 0.5
            and abs(diff_y) < 0.5
            and abs(diff_z) < 0.5
            and abs(self.vel_x) < 0.5
            and abs(self.vel_y) < 0.5
            and abs(self.vel_z) < 0.5
        ):
            self.x = self.target_x
            self.y = self.target_y
            self.z = self.target_z
            self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
            self.is_mooving = False

    def draw(self, window: 'Window') -> None:
        """Draw the rectangle."""
        if not self.alive:
            return
        if self.is_mooving:
            self.handle_moves()

        z = window.get_zoom()

        if (
            self._last_zoom != z or self._last_z != self.z
            or self._last_width != self.width
            or self._last_height != self.height
            or self._last_radius != self.radius
            or self._last_color != self.color
            or self._last_alpha != self.alpha
            or self._last_debug != self.debug
            or self._cached_rect_image is None
        ):
            sw = int(self.width * z)
            sh = int(self.height * z)
            if sw > 0 and sh > 0:
                scaled_rect = pygame.Surface((sw, sh), pygame.SRCALPHA)
                rgba_color = (
                    self.color[0],
                    self.color[1],
                    self.color[2],
                    self.alpha,
                )
                if self.radius:
                    pygame.draw.rect(scaled_rect,
                                     rgba_color,
                                     (0, 0, sw, sh),
                                     border_radius=int(self.radius * z))
                else:
                    scaled_rect.fill(rgba_color)

                if self.debug and self.alive:
                    if hasattr(self, "debug_img"):
                        scaled_debug = pygame.transform.scale(
                            pygame.image.load("assets/up.png").convert_alpha(),
                            (int(self.width), int(self.height)))
                        scaled_rect.blit(scaled_debug, (0, 0))

                self._cached_rect_image = pygame.transform.rotate(
                    scaled_rect,
                    (self.z * -57.2958) - 90,
                )
            else:
                self._cached_rect_image = None

            self._last_zoom = z
            self._last_z = self.z
            self._last_width = self.width
            self._last_height = self.height
            self._last_radius = self.radius
            self._last_color = self.color
            self._last_alpha = self.alpha
            self._last_debug = self.debug

        if self._cached_rect_image:
            sx, sy = window.world_to_screen((self.x, self.y))
            new_rect: pygame.Rect = self._cached_rect_image.get_rect(
                center=(sx, sy))
            window.screen.blit(self._cached_rect_image, new_rect.topleft)

        if self.debug and self.alive:
            sx, sy = window.world_to_screen((self.x, self.y))
            stx, sty = window.world_to_screen((self.target_x, self.target_y))
            pygame.draw.line(
                window.screen,
                (255, 255, 255),
                (sx, sy),
                (stx, sty),
            )

    def kill(self) -> None:
        """Disable the rectangle."""
        self.alive = False

    def god_touch(self) -> None:
        """Re-enable the rectangle."""
        self.alive = True


class Drone(Rect):
    _rotation_cache: dict[str, dict[int, pygame.Surface]] = {}

    def __init__(self,
                 x: float,
                 y: float,
                 debug: bool,
                 cooldown: float = .5,
                 image_path: str = "assets/drone2.png") -> None:
        """Create a drone."""
        super().__init__(x, y, 50, 50, alpha=255, debug=debug)
        self.friction = .9
        self.move_power = 0.1
        self.wander_margin: float = .8
        self.moove_cooldown: float = cooldown
        self.last_mooved: float = 0
        self.scale: float = 3.0
        self.image_path: str = image_path

        self._last_z_deg: int | None = None
        self._last_zoom: float | None = None
        self._cached_drone_img: pygame.Surface | None = None

        # Initialize dictionary of 360 rotated versions ONCE for each image
        # this allow to avoid calling pygame.rotate for every images
        if image_path not in Drone._rotation_cache:
            Drone._rotation_cache[image_path] = {}
            base_img: pygame.Surface = pygame.transform.scale(
                pygame.image.load(image_path).convert_alpha(),
                (int(self.width * self.scale),
                    int(self.height * self.scale)))
            for angle in range(360):
                Drone._rotation_cache[image_path][angle] = \
                    pygame.transform.rotate(base_img, angle)

    def move(self, x: float, y: float) -> None:
        """Move the drone and refresh its cooldown."""
        self.last_mooved = pygame.time.get_ticks() / 1000
        return super().move(x, y)

    def handle_collisions(
            self,
            all_drones: list["Drone"]) -> None:
        """Apply drone collision forces."""
        if not self.alive:
            return
        hitbox_radius: float = 70  # Safe distance between drones

        for other in all_drones:  # collision with other
            if other is self or other.alive is False:
                continue

            dx: float = self.x - other.x
            dy: float = self.y - other.y
            dist: float = math.hypot(dx, dy)
            if dist < hitbox_radius:
                if dist == 0:
                    # drone have the exact same pos, nudge them apart
                    dx = random.uniform(-1, 1)
                    dy = random.uniform(-1, 1)
                    dist = math.hypot(dx, dy) or 1.0

                overlap: float = hitbox_radius - dist  # how much they overlap
                nx: float = dx / dist  # calculate direction
                ny: float = dy / dist
                force: float = overlap * 0.2  # transfer force
                self.vel_x += nx * force
                self.vel_y += ny * force
                self.is_mooving = True  # continue physics for both of them
                other.is_mooving = True

    def wander(self, window: Window) -> None:
        """Send the drone to a random target."""
        if not self.alive or self.moove_cooldown < 0:
            return
        if (
            pygame.time.get_ticks() / 1000 - self.last_mooved
            > self.moove_cooldown
        ):
            self.move(
                random.random() * self.wander_margin * window.width + (
                    window.width * (1 - self.wander_margin)) / 2,
                random.random() * self.wander_margin * window.height + (
                    window.height * (1 - self.wander_margin)) / 2,
            )

    def draw(self, window: 'Window') -> None:
        """Draw the drone."""
        if not self.alive:
            return
        if self.is_mooving:
            self.handle_moves()

        degrees: int = int((self.z * -57.2958) - 90) % 360
        z = window.get_zoom()

        if (
            not hasattr(self, '_last_z_deg')
            or self._last_z_deg != degrees
            or not hasattr(self, '_last_zoom')
            or self._last_zoom != z
            or not hasattr(self, '_cached_drone_img')
            or self._cached_drone_img is None
        ):
            self.rotated_img = Drone._rotation_cache[self.image_path][degrees]

            sw = int(self.rotated_img.get_width() * z)
            sh = int(self.rotated_img.get_height() * z)

            if sw > 0 and sh > 0:
                self._cached_drone_img = pygame.transform.scale(
                    self.rotated_img, (sw, sh))
            else:
                self._cached_drone_img = None

            self._last_z_deg = degrees
            self._last_zoom = z

        if hasattr(self, '_cached_drone_img') and self._cached_drone_img:
            sx, sy = window.world_to_screen((self.x, self.y))
            new_rect: pygame.Rect = self._cached_drone_img.get_rect(
                center=(sx, sy))
            window.screen.blit(self._cached_drone_img, new_rect.topleft)

        if self.debug and self.alive:
            sx, sy = window.world_to_screen((self.x, self.y))
            stx, sty = window.world_to_screen((self.target_x, self.target_y))
            pygame.draw.line(
                window.screen,
                (255, 255, 255),
                (sx, sy),
                (stx, sty),
            )


class Hub_gui(Rect):
    def __init__(
            self,
            x: int,
            y: int,
            name: str,
            color: tuple[int, int, int],
            max_drones: int,
            zone_type: str,
            is_start: bool,
            is_end: bool
            ) -> None:
        """Create a hub."""
        self.name: str = name
        self.max_drones: int = max_drones
        self.zone_type: str = zone_type
        self.is_start: bool = is_start
        self.is_end: bool = is_end
        self.color: tuple[int, int, int] = color
        self.margin: int = 200
        self.size: int = 150
        self.x: float = x * (self.size + self.margin)
        self.y: float = y * (self.size + self.margin)
        super().__init__(self.x, self.y,
                         self.size, self.size,
                         radius=self.size//2, color=color)
        self.init_image()
        self.current_drones: list[object] = []
        # Connections attached to this hub (wired by Map_gui.build_adjacency)
        self.connections: list[Connection_gui] = []
        # Hover state for debug (set by main loop)
        self._hovered: bool = False

        # Cached count label (lazy-init, reused across frames)
        self._count_text: Optional[Text] = None
        self._count_last: str = ""

    def init_image(self) -> None:
        """Initialize the hub image."""
        if self.is_start:
            img_path = "assets/home.png"
        elif self.is_end:
            img_path = "assets/point.png"
        elif self.zone_type == "restricted":
            img_path = "assets/warning.png"
        elif self.zone_type == "priority":
            img_path = "assets/plus.png"
        elif self.zone_type == "blocked" \
                or (self.color == (255, 0, 0) and self.name != "slow_path2"):
            img_path = "assets/cross.png"
        else:
            img_path = "assets/circle.png"
        self.image: ImageObject = ImageObject(
            img_path, self.x, self.y, scale=self.size * 0.5,
            absolute_size=True)
        self._base_img_scale: float = self.size * 0.5

    def draw(self, window: Window) -> None:
        super().draw(window)
        # Scale icon with zoom (absolute_size → scale is pixel size)
        self.image.scale = self._base_img_scale * window.get_zoom()
        self.image.draw(window)
        if self._hovered:
            self._draw_count_text(window)

    def _draw_count_text(self, window: Window) -> None:
        """Draw a cached white count label above the hub (no background)."""
        count_str: str = f"{len(self.current_drones)}/{self.max_drones}"

        if self._count_text is None:
            self._count_text = Text(
                text="", color=(255, 255, 255),
                centered=True, lock_to_screen=False,
            )

        # Only re-render font surface when text changes
        if count_str != self._count_last:
            self._count_text.set_text(count_str)
            self._count_last = count_str

        z: float = window.get_zoom()
        self._count_text.set_size(max(32, int(14 * z)))
        sx, sy = window.world_to_screen((
            self.x,
            self.y - self.size // 2 - 20,
        ))
        self._count_text.set_pos(sx, sy)
        self._count_text.draw(window.screen)

    def get_position(self) -> tuple[float, float]:
        """Return the hub position."""
        return (self.x, self.y)

    def can_accept_drone(self) -> bool:
        """Return whether a drone can enter the hub.

        Start and end hubs are exempt from capacity limits (per subject
        rules: start may share initially, end receives all drones).
        """
        if self.is_start or self.is_end:
            return True
        return len(self.current_drones) < self.max_drones

    def update_drone_goal(self, drone: Drone) -> None:
        """Set the visual drone destination to this hub (smooth move)."""
        drone.move(self.x, self.y)

    def add_drone(self, drone: object) -> None:
        """Register a drone as occupying this hub (unconditional).

        Capacity enforcement happens at the simulation level via
        :meth:`can_accept_drone` — this method always appends so that
        spawning and undo work correctly.
        """
        self.current_drones.append(drone)

    def remove_drone(self, drone: object) -> None:
        """Remove a drone from this hub's occupancy list."""
        if drone in self.current_drones:
            self.current_drones.remove(drone)

    def get_connection_to(self, target: Hub_gui) -> Optional[Connection_gui]:
        """Return the connection linking self to *target*, or ``None``."""
        for conn in self.connections:
            if conn.connects(self.name, target.name):
                return conn
        return None


class Connection_gui:
    """Visual line between two :class:`Hub_gui` objects.

    Stores references to both hubs so the line always tracks their
    current world positions, respecting zoom and pan.
    """

    def __init__(
        self,
        hub_a: "Hub_gui",
        hub_b: "Hub_gui",
        max_link_capacity: int = 1,
        color: tuple[int, int, int] = (200, 150, 0),
    ) -> None:
        """Create a connection line.

        Args:
            hub_a: First hub reference.
            hub_b: Second hub reference.
            max_link_capacity: Capacity value (used for line thickness).
            color: RGB colour of the line.
        """
        self.hub_a: Hub_gui = hub_a
        self.hub_b: Hub_gui = hub_b
        self.max_link_capacity: int = max_link_capacity
        self.color: tuple[int, int, int] = _ensure_color(color)
        self.color_from_capacity()  # Set color based on capacity
        # Drones currently traversing this connection (restricted-zone transit)
        self.traversing_drones: list[object] = []

    # ------------------------------------------------------------------
    # Drone movement helpers
    # ------------------------------------------------------------------

    def can_traverse(self) -> bool:
        """Return ``True`` if a drone may enter this connection."""
        return len(self.traversing_drones) < self.max_link_capacity

    def traverse(self, drone: object) -> None:
        """Mark *drone* as traversing this connection."""
        if not self.can_traverse():
            raise ValueError("Connection at capacity")
        self.traversing_drones.append(drone)

    def release(self, drone: object) -> None:
        """Remove *drone* from this connection."""
        if drone in self.traversing_drones:
            self.traversing_drones.remove(drone)

    def connects(self, name_a: str, name_b: str) -> bool:
        """Return ``True`` if this connection links the two named hubs."""
        return {self.hub_a.name, self.hub_b.name} == {name_a, name_b}

    def other_end(self, hub: Hub_gui) -> Hub_gui:
        """Return the hub at the opposite end of this connection."""
        if hub is self.hub_a:
            return self.hub_b
        return self.hub_a

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def draw(self, window: Window) -> None:
        """Draw the line between the two hubs on *window*."""
        # Hub positions are their centres (set in Hub_gui / Rect)
        sax, say = window.world_to_screen((self.hub_a.x, self.hub_a.y))
        sbx, sby = window.world_to_screen((self.hub_b.x, self.hub_b.y))

        line_w: int = max(5, int(self.max_link_capacity * 30
                                 * window.get_zoom()))
        # Draw directly on screen — simple, no offset issues
        pygame.draw.line(
            window.screen, self.color,
            (sax, say), (sbx, sby),
            line_w,
        )

    def color_from_capacity(self) -> None:
        """Set the line color based on a capacity value."""
        if self.max_link_capacity <= 1:
            self.color = (200, 150, 0)  # Green for medium capacity
        elif self.max_link_capacity <= 2:
            self.color = (150, 200, 0)  # Dark green for high capacity
        else:
            self.color = (100, 250, 0)  # Bright green for very high capacity


class Map_gui:
    """Container that renders a complete parsed map.

    Holds all :class:`Hub_gui` and :class:`Connection_gui` objects.
    Drawing order: connections first (lines behind), then hubs on top.
    """

    def __init__(self) -> None:
        self.hubs: dict[str, Hub_gui] = {}
        self.connections: list[Connection_gui] = []
        self.debug: bool = False

    def add_hub(self, hub: Hub_gui) -> None:
        """Register a hub GUI object."""
        self.hubs[hub.name] = hub

    def add_connection(self, conn: Connection_gui) -> None:
        """Register a connection GUI object."""
        self.connections.append(conn)

    def build_adjacency(self) -> None:
        """Wire every hub with the connections attached to it."""
        for hub in self.hubs.values():
            hub.connections.clear()
        for conn in self.connections:
            conn.hub_a.connections.append(conn)
            conn.hub_b.connections.append(conn)

    def get_neighbors(self, hub_name: str) -> list[Hub_gui]:
        """Return hubs directly connected to *hub_name*."""
        hub = self.hubs.get(hub_name)
        if hub is None:
            return []
        result: list[Hub_gui] = []
        for conn in hub.connections:
            result.append(conn.other_end(hub))
        return result

    def draw(self, window: Window) -> None:
        """Render connections first, then hubs on top."""
        for conn in self.connections:
            conn.draw(window)
        for hub in self.hubs.values():
            hub.draw(window)

    def set_debug(self, debug: bool) -> None:
        """Set debug mode for all hubs."""
        self.debug = debug
        for hub in self.hubs.values():
            hub.set_debug(debug)


class LayeredRenderer:
    """Simple layered renderer/scene manager.

    Objects are drawn in ascending layer order (lower first).
    Any object placed in layers must implement a `draw(window)` method.
    For menu background behavior, `update(window)` will call simple
    helpers on objects: `handle_collisions(all_drones)` and `wander(window)`
    when Drone instances are present.
    """

    def __init__(self) -> None:
        self._layers: dict[int, list[_Drawable]] = {}

    def add(self, obj: _Drawable, layer: int = 0) -> None:
        """Add an object to a given layer."""
        if type(layer) is not int:
            raise TypeError("layer must be an int")
        self._layers.setdefault(layer, []).append(obj)

    def remove(self, obj: _Drawable) -> None:
        """Remove object from any layer where it exists."""
        for lst in self._layers.values():
            if obj in lst:
                lst.remove(obj)

    def clear_layer(self, layer: int) -> None:
        """Clear all objects from a specific layer."""
        if layer in self._layers:
            self._layers[layer].clear()

    def draw(self, window: Window) -> None:
        """Draw all layers in ascending order."""
        for layer in sorted(self._layers.keys()):
            for obj in list(self._layers[layer]):
                try:
                    # Text.draw expects a Surface; others expect Window
                    if isinstance(obj, Text):
                        if getattr(obj, "lock_to_screen", True):
                            obj.draw(window.get_screen())
                        else:
                            # draw text at world position transformed to screen
                            old_x, old_y = obj.x, obj.y
                            old_size = obj.size
                            sx, sy = window.world_to_screen((old_x, old_y))
                            zoomed_size = max(
                                1,
                                int(old_size * window.get_zoom()),
                            )
                            obj.set_size(zoomed_size)
                            obj.x, obj.y = sx, sy
                            obj.draw(window.get_screen())
                            obj.set_size(old_size)
                            obj.x, obj.y = old_x, old_y
                    else:
                        obj.draw(window)
                except Exception:
                    # keep rendering even if one object fails
                    continue

    def update(self, window: Window) -> None:
        """Perform simple per-frame updates for scene objects.

        - Handle drone collisions among all Drone instances.
        - Call `wander(window)` on drones when idle.
        """
        # gather drones
        all_drones: list[Drone] = []
        for lst in self._layers.values():
            for obj in lst:
                if isinstance(obj, Drone):
                    all_drones.append(obj)

        # collisions
        for d in all_drones:
            try:
                d.handle_collisions(all_drones)
            except Exception:
                pass

        # wandering
        for d in all_drones:
            try:
                d.wander(window)
            except Exception:
                pass


if __name__ == "__main__":
    window = Window()
    running = True
    stick = False
    lead_drone: Drone = Drone(
        100, 100, debug=True, image_path="assets/drone.png")
    logo: ImageObject = ImageObject(
        "assets/logo.png", window.width / 2, 100, scale=1)
    marker: Rect = Rect(30, 30, 0, 0, radius=0, color=(255, 255, 255))
    drones: list[Drone] = [Drone(
        300, 300, debug=True, cooldown=random.uniform(0.1, 2.0),
        image_path="assets/drone2.png"
        ) for _ in range(10)]
    fps = Text(10, 10, 24, "FPS: 0")
    spawn_button = Button(100, 100, 200, 50, "Spawn Drones", 5)

    def spawn_more_drones() -> None:
        """Spawn a batch of drones."""
        drones.extend([Drone(
            300, 300, debug=True, cooldown=random.uniform(0.1, 2.0)
        ) for _ in range(10)])

    spawn_button.hook = spawn_more_drones
    objects: list[Rect | ImageObject | Button] = [
        lead_drone,
        logo,
        marker,
        spawn_button,
    ]
    drones_count = Text(10, 40, 24, f"Drones: {len(drones)}")
    pan_active = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_p:
                    stick = not stick
                if event.key == pygame.K_d:
                    lead_drone.debug = not lead_drone.debug
                    if lead_drone.debug:
                        lead_drone.color = (255, 255, 255)
                        lead_drone.alpha = 0
                    else:
                        lead_drone.color = (50, 150, 70)
                        lead_drone.alpha = 255
            if event.type == pygame.MOUSEWHEEL:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                world_x, world_y = window.screen_to_world((mouse_x, mouse_y))
                if event.y > 0:
                    window.zoom(1.1)
                elif event.y < 0:
                    window.zoom(1 / 1.1)
                window.set_offset(
                    mouse_x - world_x * window.get_zoom(),
                    mouse_y - world_y * window.get_zoom()
                )
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:
                    pan_active = True
                if event.button == 1:  # Left mouse button
                    world_pos = window.screen_to_world(event.pos)
                    if spawn_button.is_hovered(world_pos):
                        spawn_button.click(world_pos)
                    else:
                        lead_drone.move(world_pos[0], world_pos[1])
                        marker.radius = 15
                        marker.width = 30
                        marker.height = 30
                        marker.tp(world_pos[0], world_pos[1])
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    pan_active = False
            if event.type == pygame.MOUSEMOTION:
                if pan_active:
                    window.pan(event.rel[0], event.rel[1])
            if stick:
                world_pos = window.screen_to_world(pygame.mouse.get_pos())
                lead_drone.move(world_pos[0], world_pos[1])
        all_game_drones = [lead_drone] + drones
        for d in all_game_drones:
            d.handle_collisions(all_game_drones)

        window.draw_background()

        for obj in objects:
            if isinstance(obj, Button):
                obj.is_hovered(window.screen_to_world(pygame.mouse.get_pos()))
            obj.draw(window)
        for drone in drones:
            drone.draw(window)
            if (
                pygame.time.get_ticks() / 1000 - drone.last_mooved
                > drone.moove_cooldown + 2
            ):
                drone.wander(window)
        logo.dummy += 0.05
        logo.rotation = math.sin(logo.dummy) * 20
        if marker.radius > 0:
            marker.radius -= 1
            marker.width -= 2
            marker.height -= 2

        fps.set_text(f"FPS: {window.get_fps()}")
        drones_count.set_text(f"Drones: {len(drones)}")
        fps.draw(window.screen)
        drones_count.draw(window.screen)
        window.update()
    pygame.quit()
