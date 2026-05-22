import random
from typing import Callable, Dict

import pygame
import math

pygame.init()
CELLS = 25


def bezier(x: float) -> float:
    """calculate bezier curve for smooth moves or transitions"""
    return 3 * x**2 - 2 * x**3


class Window:
    def __init__(
            self,
            width: int = 3000,
            height: int = 1500,
            fps: int = 100) -> None:
        self.current_fps: float = 0
        self.width: int = width
        self.height: int = height
        self.fps: int = fps
        self._zoom: float = 1.0
        self.offset: tuple[float, float] = (0, 0)
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.width, self.height), pygame.NOFRAME)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        pygame.display.set_caption("Fly YEEET")
        self.background_tile: pygame.Surface = pygame.image.load(
            "assets/tile.png").convert()
        self.bg_w = self.background_tile.get_width()
        self.bg_h = self.background_tile.get_height()

    def draw_background(self) -> None:
        self.screen.fill((0, 0, 0))
        # Tile background infinitely based on camera offset and zoom
        scaled_w = int(self.bg_w * self._zoom)
        scaled_h = int(self.bg_h * self._zoom)
        if scaled_w <= 0 or scaled_h <= 0:
            return
        
        scaled_tile = pygame.transform.scale(self.background_tile, (scaled_w, scaled_h))
        
        start_x = int(self.offset[0] % scaled_w)
        if start_x > 0: start_x -= scaled_w
        start_y = int(self.offset[1] % scaled_h)
        if start_y > 0: start_y -= scaled_h

        for x in range(start_x, self.width, scaled_w):
            for y in range(start_y, self.height, scaled_h):
                self.screen.blit(scaled_tile, (x, y))

    def update(self) -> None:
        pygame.display.flip()
        self.clock.tick(self.fps)
        self.current_fps = math.floor(self.clock.get_fps())

    def screen_to_world(self, pos: tuple[float, float]) -> tuple[int, int]:
        return (int((pos[0] - self.offset[0]) / self._zoom),
                int((pos[1] - self.offset[1]) / self._zoom))

    def world_to_screen(self, pos: tuple[float, float]) -> tuple[int, int]:
        return (int(pos[0] * self._zoom + self.offset[0]),
                int(pos[1] * self._zoom + self.offset[1]))

    def zoom(self, factor: float) -> None:
        self._zoom *= factor
        # Limit the unzoom to 3 times the original size
        if self._zoom < 0.33333333:
            self._zoom = 0.33333333

    def pan(self, dx: float, dy: float) -> None:
        self.offset = (self.offset[0] + dx, self.offset[1] + dy)

    def set_offset(self, x: float, y: float) -> None:
        self.offset = (x, y)

    def get_zoom(self) -> float:
        return self._zoom

    def get_offset(self) -> tuple[float, float]:
        return self.offset

    def get_fps(self) -> float:
        return self.current_fps


class Text:
    def __init__(self,
                 x: float = 0,
                 y: float = 0,
                 size: int = 36,
                 text: str = "",
                 color: tuple[int, int, int] = (255, 255, 255)) -> None:
        self.x: float = x
        self.y: float = y
        self.size: int = size
        self.text: str = text
        self.font: pygame.font.Font = pygame.font.SysFont(None, self.size)
        self.text_surface: pygame.Surface = self.font.render(
            self.text, True, color)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.text_surface, (self.x, self.y))

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.text_surface = self.font.render(
                self.text, True, (255, 255, 255))

    def set_size(self, size: int) -> None:
        self.size = size
        self.font = pygame.font.SysFont(None, self.size)
        self.text_surface = self.font.render(self.text, True, (255, 255, 255))

    def set_color(self, color: tuple[int, int, int]) -> None:
        self.text_surface = self.font.render(self.text, True, color)


class Button:
    def __init__(self,
                 x: float,
                 y: float,
                 width: float,
                 height: float,
                 text: Text | str,
                 radius: int = 0) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.height: float = height
        self.text: Text = text if isinstance(text, Text) else Text(
            x=0, y=0, text=text)
        self.text.x = self.x - self.text.text_surface.get_width() / 2
        self.text.y = self.y - self.text.text_surface.get_height() / 2
        self.radius: int = radius
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

    def is_hovered(self, mouse_pos: tuple[int, int]) -> bool:
        if not self.enabled:
            return False
        cx, cy = self.center()
        self.hovered = (cx <= mouse_pos[0] <= cx + self.width and
                        cy <= mouse_pos[1] <= cy + self.height)
        if self.hovered != self.prev_hovered:
            self.start_time = pygame.time.get_ticks() / 1000
            self.end_time = self.start_time + self.anim_time
        self.prev_hovered = self.hovered
        return self.hovered

    def click(self, mouse_pos: tuple[int, int]) -> None:
        if self.enabled and self.is_hovered(mouse_pos):
            self.hook(**self.hook_args)

    def center(self) -> tuple[float, float]:
        return (self.x - self.width / 2, self.y - self.height / 2)

    def draw(self, window: 'Window') -> None:
        if not self.enabled:
            return
        # detect hover animation
        if pygame.time.get_ticks() / 1000 < self.end_time:
            completion: float = (
                pygame.time.get_ticks() / 1000 - self.start_time
                ) / self.anim_time
            completion = max(0, min(1, completion))
            if self.hovered:
                target_color: tuple[int, int, int] = self.hover_color
                from_color: tuple[int, int, int] = self.color
            else:
                target_color: tuple[int, int, int] = self.color
                from_color: tuple[int, int, int] = self.hover_color
            actual_color: tuple[int, int, int] = (
                int(bezier(completion) * target_color[0] + (
                    1 - bezier(completion)) * from_color[0]),
                int(bezier(completion) * target_color[1] + (
                    1 - bezier(completion)) * from_color[1]),
                int(bezier(completion) * target_color[2] + (
                    1 - bezier(completion)) * from_color[2])
            )
        else:
            if self.hovered:
                actual_color: tuple[int, int, int] = self.hover_color
            else:
                actual_color: tuple[int, int, int] = self.color

        cx, cy = self.center()
        scx, scy = window.world_to_screen((cx, cy))
        sw = int(self.width * window.get_zoom())
        sh = int(self.height * window.get_zoom())
        
        pygame.draw.rect(window.screen, actual_color,
                         (scx, scy, sw, sh),
                         border_radius=int(self.radius * window.get_zoom()))
        
        # simple scale for text position
        stx, sty = window.world_to_screen((self.text.x, self.text.y))
        
        # update font size based on zoom temporarily
        old_size = self.text.size
        self.text.set_size(int(old_size * window.get_zoom()))
        self.text.x, self.text.y = stx, sty
        self.text.draw(window.screen)
        
        # restore
        self.text.set_size(old_size)
        self.text.x, self.text.y = cx + self.width / 2 - self.text.text_surface.get_width() / 2, cy + self.height / 2 - self.text.text_surface.get_height() / 2


class ImageObject:
    def __init__(self,
                 image_path: str,
                 x: float,
                 y: float,
                 scale: float = 1) -> None:
        self.image: pygame.Surface = pygame.image.load(
            image_path).convert_alpha()
        self.x: float = x
        self.y: float = y
        self.scale: float = scale
        self.rotation: float = 0
        self.dummy: float = 0
        self._last_rotation = None
        self._last_zoom = None
        self._cached_image = None

    def draw(self, window: 'Window') -> None:
        z = window.get_zoom()
        if (self._last_rotation != self.rotation or self._last_zoom != z 
                or self._cached_image is None):
            rotated_image: pygame.Surface = pygame.transform.rotate(
                self.image, self.rotation)
            w = int(rotated_image.get_width() * self.scale * z)
            h = int(rotated_image.get_height() * self.scale * z)
            if w > 0 and h > 0:
                self._cached_image = pygame.transform.scale(rotated_image, (w, h))
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
        self.x = x
        self.y = y


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
        self.x: float = x
        self.y: float = y
        self.z: float = 0  # rotation -- looking up by default
        self.vel_x: float = 0
        self.vel_y: float = 0
        self.vel_z: float = 0
        self.width: float = width
        self.height: float = height
        self.color: tuple[int, int, int] = color
        self.alpha: int = alpha
        self.is_mooving: bool = False
        self.target_x: float = x
        self.target_y: float = y
        self.target_z: float = self.z
        self.friction: float = .7
        self.move_power: float = 1.5
        self.radius: int = radius
        self.debug: bool = debug
        self.alive: bool = True
        self.rect: pygame.Surface = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA)
        if debug and self.alive:
            self.debug_img: pygame.Surface = pygame.transform.scale(
                pygame.image.load("assets/up.png").convert_alpha(),
                (int(self.width), int(self.height)))
            self.rotated_img: pygame.Surface = self.debug_img
        else:
            self.rotated_img: pygame.Surface = self.rect

        self._last_zoom = None
        self._last_z = None
        self._last_width = None
        self._last_height = None
        self._last_radius = None
        self._last_color = None
        self._last_alpha = None
        self._last_debug = None
        self._cached_rect_image = None

    def center(self) -> tuple[float, float]:
        return (self.x - self.width / 2, self.y - self.height / 2)

    def rotate(self, angle: float) -> None:
        self.z = angle

    def get_pos(self) -> tuple[float, float]:
        return (self.x, self.y)

    def rotate_focus(self, x: float, y: float) -> None:
        """make the object rotate to face a specific point"""
        self.target_z = math.atan2(y - self.center()[1], x - self.center()[0])

    def move_rel(self, dx: float, dy: float) -> None:
        """Update the target to move towards. Velocity is inherited"""
        self.is_mooving = True
        self.target_x: float = self.x + dx
        self.target_y: float = self.y + dy
        self.rotate_focus(self.target_x, self.target_y)

    def move(self, x: float, y: float) -> None:
        """Move to a fixed position."""
        self.is_mooving = True
        self.target_x: float = x
        self.target_y: float = y
        self.rotate_focus(self.target_x, self.target_y)

    def tp(self, x: float, y: float) -> None:
        """Teleport to a fixed position."""
        self.x = x
        self.y = y

    def handle_moves(self) -> None:
        diff_x: float = self.target_x - self.x  # distance
        diff_y: float = self.target_y - self.y
        diff_z: float = (self.target_z - self.z + math.pi) % (
            2 * math.pi) - math.pi  # shortest angular diatnce
        self.vel_x += diff_x * 0.05 * self.move_power  # velocity
        self.vel_y += diff_y * 0.05 * self.move_power
        self.vel_z += diff_z * 0.05 * self.move_power
        self.vel_x *= self.friction  # friction (limit wobble)
        self.vel_y *= self.friction
        self.vel_z *= self.friction
        self.x += self.vel_x  # update position
        self.y += self.vel_y
        self.rotate(self.z + self.vel_z)

        # Snap when movement finished
        if (abs(diff_x) < 0.5 and abs(diff_y) < 0.5 and abs(diff_z) < 0.5 and
                abs(self.vel_x) < 0.5 and abs(self.vel_y) < 0.5 and abs(self.vel_z) < 0.5):
            self.x = self.target_x
            self.y = self.target_y
            self.z = self.target_z
            self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
            self.is_mooving = False

    def draw(self, window: 'Window') -> None:
        if not self.alive:
            return
        if self.is_mooving:
            self.handle_moves()

        z = window.get_zoom()
        
        if (self._last_zoom != z or self._last_z != self.z or
            self._last_width != self.width or self._last_height != self.height or
            self._last_radius != self.radius or self._last_color != self.color or
            self._last_alpha != self.alpha or self._last_debug != self.debug or
            self._cached_rect_image is None):
            
            sw = int(self.width * z)
            sh = int(self.height * z)
            if sw > 0 and sh > 0:
                scaled_rect = pygame.Surface((sw, sh), pygame.SRCALPHA)
                if self.radius:
                    pygame.draw.rect(scaled_rect,
                                     (self.color[0], self.color[1], self.color[2], self.alpha),
                                     (0, 0, sw, sh),
                                     border_radius=int(self.radius * z))
                else:
                    scaled_rect.fill((self.color[0], self.color[1], self.color[2], self.alpha))
                    
                if self.debug and self.alive:
                    scaled_debug = pygame.transform.scale(self.debug_img, (sw, sh))
                    scaled_rect.blit(scaled_debug, (0, 0))
                    
                self._cached_rect_image = pygame.transform.rotate(
                    scaled_rect, (self.z * -57.2958) - 90)  # Convert radians to deg
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
            new_rect: pygame.Rect = self._cached_rect_image.get_rect(center=(sx, sy))
            window.screen.blit(self._cached_rect_image, new_rect.topleft)
            
        if self.debug and self.alive:
            sx, sy = window.world_to_screen((self.x, self.y))
            stx, sty = window.world_to_screen((self.target_x, self.target_y))
            pygame.draw.line(window.screen, (255, 255, 255), (sx, sy), (stx, sty))

    def kill(self) -> None:
        self.alive = False

    def god_touch(self) -> None:
        self.alive = True


class Drone(Rect):
    _rotation_cache: dict[str, dict[int, pygame.Surface]] = {}

    def __init__(self,
                 x: float,
                 y: float,
                 debug: bool,
                 cooldown: float = .5,
                 image_path: str = "assets/drone2.png") -> None:
        super().__init__(x, y, 50, 50, alpha=255, debug=debug)
        self.friction = .9
        self.move_power = 0.1
        self.wander_margin: float = .8
        self.moove_cooldown: float = cooldown
        self.last_mooved: float = 0
        self.scale: float = 3.0
        self.image_path: str = image_path

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
        self.last_mooved = pygame.time.get_ticks() / 1000
        return super().move(x, y)

    def handle_collisions(
            self,
            all_drones: list["Drone"],
            window_width: int,
            window_height: int) -> None:
        if not self.alive:
            return
        hitbox_radius: float = 100  # Safe distance between drones

        # Border collision
        border_radius: float = hitbox_radius / 2.0
        if self.x < border_radius:
            self.vel_x += (border_radius - self.x) * 0.2
            self.is_mooving = True
        elif self.x > window_width - border_radius:
            self.vel_x -= (self.x - (window_width - border_radius)) * 0.2
            self.is_mooving = True

        if self.y < border_radius:
            self.vel_y += (border_radius - self.y) * 0.2
            self.is_mooving = True
        elif self.y > window_height - border_radius:
            self.vel_y -= (self.y - (window_height - border_radius)) * 0.2
            self.is_mooving = True

        for other in all_drones:  # collision with other
            if other is self:
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
        if not self.alive:
            return
        if pygame.time.get_ticks() / 1000 - \
                self.last_mooved > self.moove_cooldown:
            # find a random position and go to it
            self.move(
                (random.random() * self.wander_margin * window.width + (
                    window.width * (1-self.wander_margin)) / 2),
                (random.random() * self.wander_margin * window.height + (
                    window.height * (1-self.wander_margin)) / 2))

    def draw(self, window: 'Window') -> None:
        if not self.alive:
            return
        if self.is_mooving:
            self.handle_moves()

        degrees: int = int((self.z * -57.2958) - 90) % 360
        z = window.get_zoom()

        if (not hasattr(self, '_last_z_deg') or self._last_z_deg != degrees or 
            not hasattr(self, '_last_zoom') or self._last_zoom != z or 
            not hasattr(self, '_cached_drone_img') or self._cached_drone_img is None):

            # Fetch the pre-rotated image directly from cache in O(1) time
            self.rotated_img = Drone._rotation_cache[self.image_path][degrees]

            sw = int(self.rotated_img.get_width() * z)
            sh = int(self.rotated_img.get_height() * z)
            
            if sw > 0 and sh > 0:
                self._cached_drone_img = pygame.transform.scale(self.rotated_img, (sw, sh))
            else:
                self._cached_drone_img = None

            self._last_z_deg = degrees
            self._last_zoom = z
            
        if hasattr(self, '_cached_drone_img') and self._cached_drone_img:
            sx, sy = window.world_to_screen((self.x, self.y))
            new_rect: pygame.Rect = self._cached_drone_img.get_rect(center=(sx, sy))
            window.screen.blit(self._cached_drone_img, new_rect.topleft)

        if self.debug and self.alive:
            sx, sy = window.world_to_screen((self.x, self.y))
            stx, sty = window.world_to_screen((self.target_x, self.target_y))
            pygame.draw.line(window.screen, (255, 255, 255), (sx, sy), (stx, sty))


if __name__ == "__main__":
    window = Window()
    running = True
    stick = False
    objects: list[any] = [
        Drone(100, 100, debug=True, image_path="assets/drone.png")]
    objects.append(ImageObject(
        "assets/logo.png", window.width/2, 100, scale=1))
    objects.append(Rect(30, 30, 0, 0, radius=0, color=(255, 255, 255)))
    drones: list[Drone] = [Drone(
        300, 300, debug=True, cooldown=random.uniform(0.1, 2.0),
        image_path="assets/drone2.png"
        ) for _ in range(10)]
    fps = Text(10, 10, 24, "FPS: 0")
    spawn_button = Button(100, 100, 200, 50, "Spawn Drones", 5)
    def spawn_more_drones():
        drones.extend([Drone(
            300, 300, debug=True, cooldown=random.uniform(0.1, 2.0)
        ) for _ in range(10)])
    spawn_button.hook = spawn_more_drones
    objects.append(spawn_button)
    drones_count = Text(10, 40, 24, f"Drones: {len(drones)}")
    pan_active = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_p:
                    stick: bool = not stick
                if event.key == pygame.K_d:
                    objects[0].debug = not objects[0].debug
                    if objects[0].debug:
                        objects[0].color = (255, 255, 255)
                        objects[0].alpha = 0
                    else:
                        objects[0].color = (50, 150, 70)
                        objects[0].alpha = 255
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
                    if isinstance(objects[3], Button) and objects[3].is_hovered(world_pos):
                        objects[3].click(world_pos)
                    else:
                        objects[0].move(world_pos[0], world_pos[1])
                        objects[2].radius = 15
                        objects[2].width = 30
                        objects[2].height = 30
                        objects[2].tp(world_pos[0], world_pos[1])
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    pan_active = False
            if event.type == pygame.MOUSEMOTION:
                if pan_active:
                    window.pan(event.rel[0], event.rel[1])
            if stick:
                world_pos = window.screen_to_world(pygame.mouse.get_pos())
                objects[0].move(world_pos[0], world_pos[1])
        all_game_drones = [objects[0]] + drones
        for d in all_game_drones:
            d.handle_collisions(all_game_drones, window.width, window.height)

        window.draw_background()

        for obj in objects:
            if isinstance(obj, Button):
                obj.is_hovered(window.screen_to_world(pygame.mouse.get_pos()))
            obj.draw(window)
        for drone in drones:
            drone.draw(window)
            if pygame.time.get_ticks() / 1000 - drone.last_mooved > drone.moove_cooldown + 2:
                drone.wander(window)
        objects[1].dummy += 0.05
        objects[1].rotation = math.sin(objects[1].dummy) * 20
        if objects[2].radius > 0:
            objects[2].radius -= 1
            objects[2].width -= 2
            objects[2].height -= 2

        fps.set_text(f"FPS: {window.get_fps()}")
        drones_count.set_text(f"Drones: {len(drones)}")
        fps.draw(window.screen)
        drones_count.draw(window.screen)
        window.update()
    pygame.quit()
