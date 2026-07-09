"""
Parser module for the Fly-Yeet drone routing simulation.

Parses map files defining hubs (zones), connections, and drone counts.
Provides comprehensive validation with error collection — all errors are
collected before exiting, and printed in red to the terminal.

Usage as script:
    python parser.py maps/easy/01_linear_path.txt
"""

from __future__ import annotations

import os
import re
import sys
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# Default gray
COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "blue": (0, 0, 255),
    "brown": (139, 69, 19),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "darkred": (139, 0, 0),
    "gold": (255, 215, 0),
    "gray": (128, 128, 128),
    "green": (0, 255, 0),
    "lime": (50, 205, 50),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "rainbow": (255, 255, 255),
    "red": (255, 0, 0),
    "violet": (238, 130, 238),
    "yellow": (255, 255, 0),
}


# =============================================================================
# Enums
# =============================================================================

class ZoneType(str, Enum):
    """Zone type determines movement cost and pathfinding behaviour."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


# =============================================================================
# Pydantic Models
# =============================================================================

class Color(BaseModel):
    """A validated color pairing a name with its RGB components."""

    name: str
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)

    @model_validator(mode="after")
    def _check_name_known(self) -> "Color":
        """Ensure the color name exists in COLOR_RGB."""
        if self.name not in COLOR_RGB:
            raise ValueError(
                f"Unknown color '{self.name}'. "
                f"Known: {', '.join(sorted(COLOR_RGB.keys()))}"
            )
        return self

    @property
    def rgb_tuple(self) -> tuple[int, int, int]:
        """Return the RGB values as a (r, g, b) tuple."""
        return (self.r, self.g, self.b)


class Position(BaseModel):
    """2D coordinates with validated bounds."""

    x: int = Field(ge=-100, le=100)
    y: int = Field(ge=-100, le=100)


class Hub(BaseModel):
    """A zone (hub) in the drone network."""

    name: str
    color: Color
    max_drones: int = Field(default=1, gt=0)
    zone_type: ZoneType = Field(default=ZoneType.NORMAL)
    position: Position
    is_start: bool = False
    is_end: bool = False


class Connection(BaseModel):
    """A bidirectional edge between two hubs."""

    from_hub: str
    to_hub: str
    max_link_capacity: int = Field(default=1, gt=0)


class Map(BaseModel):
    """Complete parsed map: hubs, connections, drone count, and metadata."""

    nb_drones: int = Field(gt=0)
    start_hub: Hub
    end_hub: Hub
    hubs: list[Hub]
    connections: list[Connection]

    @model_validator(mode="after")
    def _validate_global_state(self) -> "Map":
        """Run entity validations (unique names, positions, references)."""
        errors: list[str] = []

        all_hubs: list[Hub] = self.hubs + [self.start_hub, self.end_hub]

        # --- unique hub names ---
        seen: set[str] = set()
        for h in all_hubs:
            if h.name in seen:
                errors.append(f"Duplicate hub name: '{h.name}'")
            seen.add(h.name)
        hub_names: set[str] = seen

        # --- coordinate superposition ---
        coord_map: dict[tuple[int, int], list[str]] = {}
        for h in all_hubs:
            key = (h.position.x, h.position.y)
            coord_map.setdefault(key, []).append(h.name)
        for (cx, cy), names in coord_map.items():
            if len(names) > 1:
                errors.append(
                    f"Coordinate superposition at ({cx}, {cy}): "
                    f"{', '.join(names)}"
                )

        # --- connections reference existing hubs ---
        for conn in self.connections:
            if conn.from_hub not in hub_names:
                errors.append(
                    f"Connection '{conn.from_hub}-{conn.to_hub}' "
                    f"references unknown hub: '{conn.from_hub}'"
                )
            if conn.to_hub not in hub_names:
                errors.append(
                    f"Connection '{conn.from_hub}-{conn.to_hub}' "
                    f"references unknown hub: '{conn.to_hub}'"
                )

        # --- duplicate connections ---
        pairs: set[tuple[str, str]] = set()
        for conn in self.connections:
            a, b = conn.from_hub, conn.to_hub
            pair: tuple[str, str] = (a, b) if a <= b else (b, a)
            if pair in pairs:
                errors.append(
                    f"Duplicate connection: '{conn.from_hub}-{conn.to_hub}'"
                )
            pairs.add(pair)

        if errors:
            raise ValueError("\n".join(errors))
        return self

    # ------------------------------------------------------------------
    # Convenience helpers for the simulation / GUI
    # ------------------------------------------------------------------

    @property
    def all_hubs(self) -> list[Hub]:
        """Return every hub including start and end."""
        return self.hubs + [self.start_hub, self.end_hub]

    def hub_by_name(self, name: str) -> Optional[Hub]:
        """Look up a hub by name (O(n), fine for typical map sizes)."""
        for h in self.all_hubs:
            if h.name == name:
                return h
        return None


# =============================================================================
# Color scanning utility
# =============================================================================

def scan_all_color_names(maps_dir: str = "maps") -> set[str]:
    """Walk *maps/*.txt* and return every ``color=…`` value found.

    Useful for discovering new colors to add to :data:`COLOR_RGB`.
    """
    colors: set[str] = set()
    if not os.path.isdir(maps_dir):
        return colors

    color_re = re.compile(r"\[.*?color=(\w+).*?\]")
    for root, _dirs, files in os.walk(maps_dir):
        for filename in files:
            if not filename.endswith(".txt"):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    for line in fh:
                        m = color_re.search(line)
                        if m:
                            colors.add(m.group(1))
            except OSError:
                continue
    return colors


# =============================================================================
# Error collector
# =============================================================================

class ParseErrorCollector:
    """Collects line-numbered errors and prints them in red."""

    RED: str = "\033[91m"
    RESET: str = "\033[0m"

    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, line_num: int, message: str) -> None:
        """Record an error for *line_num* (0 = global / not line-specific)."""
        if line_num > 0:
            self.errors.append(f"Line {line_num}: {message}")
        else:
            self.errors.append(f"Global: {message}")

    def has_errors(self) -> bool:
        """Return ``True`` when at least one error has been recorded."""
        return len(self.errors) > 0

    def print_all(self) -> None:
        """Print every collected error in red to stderr."""
        for err in self.errors:
            print(f"{self.RED}{err}{self.RESET}", file=sys.stderr)

    def raise_if_any(self) -> None:
        """Print all errors and raise `ValueError` if any were collected.

        The exception message contains every error joined by newlines so
        the GUI can display them individually.
        """
        if self.errors:
            self.print_all()
            raise ValueError("\n".join(self.errors))


# =============================================================================
# Internal helpers
# =============================================================================

def _parse_metadata_block(raw: str) -> tuple[dict[str, str], list[str]]:
    """Turn ``[key=val key2=val2]`` into a dict.

    Returns metadata and duplicate keys encountered in the same block.
    """
    result: dict[str, str] = {}
    duplicate_keys: list[str] = []
    # Metadata content is already extracted from the outer [ ... ] by regex.
    # Any bracket that remains here means malformed syntax (e.g. []color=...]).
    if "[" in raw or "]" in raw:
        raise ValueError(f"Invalid metadata block: '{raw}'")
    inner = raw.strip().strip("[]").strip()
    if not inner:
        return result, duplicate_keys
    for token in inner.split():
        if "=" in token:
            key, _, val = token.partition("=")
            if key in result:
                duplicate_keys.append(key)
            result[key] = val
    return result, duplicate_keys


def _make_color(color_name: str) -> Color:
    """Build a :class:`Color` from a name; records errors on failure.

    Returns a fallback gray ``Color`` when the name is unknown.
    """
    rgb = COLOR_RGB.get(color_name)
    if rgb is None:
        return Color(name="gray", r=128, g=128, b=128)
    return Color(name=color_name, r=rgb[0], g=rgb[1], b=rgb[2])


def _default_color() -> Color:
    """Gray default when no color is specified."""
    return Color(name="gray", r=128, g=128, b=128)


# =============================================================================
# Public API
# =============================================================================

def parse_map_file(filepath: str) -> Map:
    """Parse a map file and return a fully-validated :class:`Map`.

    All syntax and semantic errors are collected before the function raises,
    so the caller sees every issue in one pass.

    Args:
        filepath: Path to a ``.txt`` map file.

    Returns:
        A validated :class:`Map` instance.

    Raises:
        FileNotFoundError: If *filepath* does not exist.
        IsADirectoryError: If *filepath* is a directory.
        ValueError: If any parsing or validation errors are encountered.
    """
    ec = ParseErrorCollector()

    # --- validate the file path itself ---
    if not isinstance(filepath, str):
        raise TypeError(
            f"filepath must be a string, got {type(filepath).__name__}"
        )
    if not filepath:
        raise ValueError("filepath must not be empty")
    if os.path.isdir(filepath):
        raise IsADirectoryError(f"'{filepath}' is a directory, not a file")
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Map file not found: '{filepath}'")

    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            raw_text: str = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"Cannot read map file '{filepath}': {exc}"
        ) from exc

    # --- empty / comment-only file check ---
    stripped: str = raw_text.strip()
    if not stripped:
        raise ValueError(
            f"Map file '{filepath}' is empty or contains only whitespace"
        )
    # Check if every non-blank line is a comment
    non_comment: list[str] = [
        ln for ln in stripped.split("\n")
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not non_comment:
        raise ValueError(
            f"Map file '{filepath}' contains only comments — "
            f"no definitions found"
        )

    lines: list[str] = raw_text.split("\n")

    # ---- accumulators ----
    nb_drones: Optional[int] = None
    start_hub: Optional[Hub] = None
    end_hub: Optional[Hub] = None
    hubs: list[Hub] = []
    connections: list[Connection] = []
    hub_names_seen: set[str] = set()

    # ---- regex patterns ----
    # in readme explain rules of these regex
    hub_re = re.compile(
        r"^(start_hub|end_hub|hub):\s+"
        r"(\S+)\s+"
        r"(-?\d+)\s+"
        r"(-?\d+)"
        r"(?:\s+\[(.+?)\])?\s*$"
    )
    conn_re = re.compile(
        r"^connection:\s+"
        r"(\S+)-(\S+)"
        r"(?:\s+\[(.+?)\])?\s*$"
    )
    nb_re = re.compile(r"^nb_drones:\s+(-?\d+)\s*$")

    # The first effective config line must define the drone count.
    first_non_comment_line_num: int = 0
    first_non_comment_line: str = ""
    for i, raw_line in enumerate(lines, start=1):
        stripped_line = raw_line.strip()
        if stripped_line and not stripped_line.startswith("#"):
            first_non_comment_line_num = i
            first_non_comment_line = stripped_line
            break
    if first_non_comment_line and not nb_re.match(first_non_comment_line):
        ec.add(
            first_non_comment_line_num,
            "First non-comment line must be nb_drones: <positive integer>",
        )

    # ---- line-by-line parsing ----
    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip blanks and comments
        if not line or line.startswith("#"):
            continue

        # -- nb_drones --
        m = nb_re.match(line)
        if m:
            if nb_drones is not None:
                ec.add(i, "Duplicate nb_drones definition")
            else:
                val = int(m.group(1))
                if val <= 0:
                    ec.add(i, f"nb_drones must be positive, got {val}")
                    nb_drones = val  # prevent "Missing" message
                elif val > 1000:
                    ec.add(
                        i,
                        f"nb_drones is unreasonably large ({val}). "
                        f"Maximum allowed is 1000.",
                    )
                else:
                    nb_drones = val
            continue

        # -- hub definitions (start_hub / end_hub / hub) --
        m = hub_re.match(line)
        if m:
            hub_type: str = m.group(1)
            name: str = m.group(2)
            x: int = int(m.group(3))
            y: int = int(m.group(4))
            raw_meta: str = m.group(5) or ""
            meta: dict[str, str]
            duplicate_meta_keys: list[str]
            try:
                meta, duplicate_meta_keys = _parse_metadata_block(raw_meta)
            except ValueError as exc:
                ec.add(i, str(exc))
                continue
            for meta_key in sorted(set(duplicate_meta_keys)):
                ec.add(
                    i,
                    f"Duplicate metadata attribute '{meta_key}' "
                    f"for hub '{name}'",
                )

            # --- name validation ---
            if "-" in name or " " in name:
                ec.add(
                    i,
                    f"Hub name '{name}' contains invalid characters "
                    f"(dashes/spaces are forbidden)",
                )
                continue
            if name in hub_names_seen:
                ec.add(i, f"Duplicate hub name: '{name}'")
                continue
            hub_names_seen.add(name)

            # --- zone type ---
            zone_str: str = meta.get("zone", "normal")
            try:
                zone_type: ZoneType = ZoneType(zone_str)
            except ValueError:
                ec.add(
                    i,
                    f"Invalid zone type '{zone_str}' for hub '{name}'. "
                    f"Must be one of: normal, blocked, restricted, priority",
                )
                zone_type = ZoneType.NORMAL

            # --- color ---
            color_str: str = meta.get("color", "")
            color: Color
            if color_str:
                color = _make_color(color_str)
            else:
                color = _default_color()

            # --- max_drones ---
            max_d: int = 1
            if "max_drones" in meta:
                try:
                    max_d = int(meta["max_drones"])
                except ValueError:
                    ec.add(
                        i,
                        f"Invalid max_drones '{meta['max_drones']}' "
                        f"for hub '{name}'",
                    )
                if max_d <= 0:
                    ec.add(
                        i,
                        f"max_drones must be positive for hub "
                        f"'{name}', got {max_d}",
                    )
                    max_d = 1

            # --- bounds check ---
            if not (-100 <= x <= 100 and -100 <= y <= 100):
                ec.add(
                    i,
                    f"Coordinates ({x}, {y}) out of range "
                    f"[-100, 100] for hub '{name}'",
                )

            position: Position = Position(x=x, y=y)
            hub: Hub = Hub(
                name=name,
                color=color,
                max_drones=max_d,
                zone_type=zone_type,
                position=position,
                is_start=(hub_type == "start_hub"),
                is_end=(hub_type == "end_hub"),
            )

            if hub_type == "start_hub":
                if start_hub is not None:
                    ec.add(i, "Duplicate start_hub definition")
                start_hub = hub
            elif hub_type == "end_hub":
                if end_hub is not None:
                    ec.add(i, "Duplicate end_hub definition")
                end_hub = hub
            else:
                hubs.append(hub)
            continue

        # -- connection definitions --
        m = conn_re.match(line)
        if m:
            from_name: str = m.group(1)
            to_name: str = m.group(2)
            raw_meta_conn: str = m.group(3) or ""
            meta_conn: dict[str, str]
            duplicate_conn_keys: list[str]
            try:
                meta_conn, duplicate_conn_keys = _parse_metadata_block(
                    raw_meta_conn
                )
            except ValueError as exc:
                ec.add(i, str(exc))
                continue
            for conn_key in sorted(set(duplicate_conn_keys)):
                ec.add(
                    i,
                    f"Duplicate metadata attribute '{conn_key}' "
                    f"for connection '{from_name}-{to_name}'",
                )

            max_lc: int = 1
            if "max_link_capacity" in meta_conn:
                try:
                    max_lc = int(meta_conn["max_link_capacity"])
                except ValueError:
                    ec.add(
                        i,
                        f"Invalid max_link_capacity "
                        f"'{meta_conn['max_link_capacity']}' "
                        f"for connection '{from_name}-{to_name}'",
                    )
                if max_lc <= 0:
                    ec.add(
                        i,
                        f"max_link_capacity must be positive for "
                        f"connection '{from_name}-{to_name}', got {max_lc}",
                    )
                    max_lc = 1

            connections.append(
                Connection(
                    from_hub=from_name,
                    to_hub=to_name,
                    max_link_capacity=max_lc,
                )
            )
            continue

        # -- unrecognised line --
        ec.add(i, f"Unrecognised line format: '{line}'")

    # ---- post-loop global checks ----
    if nb_drones is None:
        ec.add(0, "Missing nb_drones definition")
    if start_hub is None:
        ec.add(0, "Missing start_hub definition")
    if end_hub is None:
        ec.add(0, "Missing end_hub definition")

    # ---- connection → hub references ----
    if start_hub:
        hub_names_seen.add(start_hub.name)
    if end_hub:
        hub_names_seen.add(end_hub.name)

    for conn in connections:
        if conn.from_hub not in hub_names_seen:
            ec.add(
                0,
                f"Connection '{conn.from_hub}-{conn.to_hub}' "
                f"references undefined hub: '{conn.from_hub}'",
            )
        if conn.to_hub not in hub_names_seen:
            ec.add(
                0,
                f"Connection '{conn.from_hub}-{conn.to_hub}' "
                f"references undefined hub: '{conn.to_hub}'",
            )

    # ---- duplicate connections ----
    pairs: set[tuple[str, str]] = set()
    for conn in connections:
        a, b = conn.from_hub, conn.to_hub
        pair: tuple[str, str] = (a, b) if a <= b else (b, a)
        if pair in pairs:
            ec.add(
                0,
                f"Duplicate connection: '{conn.from_hub}-{conn.to_hub}'",
            )
        pairs.add(pair)

    # ---- coordinate superposition ----
    all_hubs_list: list[Hub] = list(hubs)
    if start_hub:
        all_hubs_list.append(start_hub)
    if end_hub:
        all_hubs_list.append(end_hub)

    coord_map: dict[tuple[int, int], list[str]] = {}
    for h in all_hubs_list:
        key = (h.position.x, h.position.y)
        coord_map.setdefault(key, []).append(h.name)
    for (cx, cy), names in coord_map.items():
        if len(names) > 1:
            ec.add(
                0,
                f"Coordinate superposition at ({cx}, {cy}): "
                f"{', '.join(names)}",
            )

    # ---- finalise ----
    ec.raise_if_any()

    # All guards satisfied → build Map
    assert nb_drones is not None
    assert start_hub is not None
    assert end_hub is not None

    return Map(
        nb_drones=nb_drones,
        start_hub=start_hub,
        end_hub=end_hub,
        hubs=hubs,
        connections=connections,
    )


# =============================================================================
# Standalone usage
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <map_file>", file=sys.stderr)
        sys.exit(1)

    try:
        result: Map = parse_map_file(sys.argv[1])
        print(f"✓ Successfully parsed '{sys.argv[1]}'")
        print(f"  Drones: {result.nb_drones}")
        print(f"  Start:  {result.start_hub.name}")
        print(f"  End:    {result.end_hub.name}")
        print(f"  Hubs:   {len(result.hubs)} (+ start/end)")
        print(f"  Edges:  {len(result.connections)}")
    except ValueError:
        # Errors already printed in red by ParseErrorCollector
        sys.exit(1)
    except FileNotFoundError:
        print(f"\033[91mFile not found: ' \
              {sys.argv[1]}'\033[0m", file=sys.stderr)
        sys.exit(1)
