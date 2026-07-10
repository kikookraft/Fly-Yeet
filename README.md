*This project has been created as part of the 42 curriculum by tobesson.*

# Fly-Yeet

## Description

Fly-Yeet is a Python 3.10+ drone routing simulator built for the 42 Fly-in subject.
It parses map files describing hubs, connections, zone types, and drone counts,
builds a visual representation of the network, and simulates drone movement turn by
turn.

The current implementation focuses on three core parts:

- Parsing map files and validating their structure.
- Building a pygame-based visual scene for hubs, links, drones, and menus.
- Running a turn-based simulation with a shortest-path route for each drone.

The project uses `pydantic` for structured validation and `pygame-ce` for the
interface.

## Instructions

### Requirements

- Python 3.10 or later
- `uv`

### Install

```bash
make install
```

This creates a local virtual environment and installs the project dependencies used
by the current codebase.

### Run

Launch the application with the menu:

```bash
make run
```

Visualize a map directly without the menu:

```bash
uv run python main.py maps/easy/01_linear_path.txt
```

### Debug

```bash
make debug
```

### Lint

```bash
make lint
```

Optional stricter checks:

```bash
make lint-strict
```

### Clean

```bash
make clean
```

## Algorithm

The pathfinder in `algo.py` uses Dijkstra's algorithm to compute shortest paths
weighted by zone-type movement costs (restricted = 2 turns, normal/priority = 1 turn).
Blocked zones are excluded from traversal.

For multi-drone scenarios, `Pathfinder.all_paths()` discovers up to 20
edge-disjoint paths by iteratively removing edges of previously found routes.
Drones are distributed round-robin across these paths at spawn time, which
maximises throughput and helps meet the subject's performance benchmarks.

The simulation in `simulation.py` handles the turn loop with a single-pass
reservation system. Each turn, candidate moves are collected, shuffled for
fairness, and atomically reserved (checking both zone and connection capacity
against current occupancy plus in-turn reservations). This avoids the race
condition present in simpler two-phase approaches.

Movement logs are printed to the terminal each turn in the required format
(``D<id>-<zone>`` space-separated per line) and also returned for GUI use.

## Visual Representation

The interface is built in `gui.py` and rendered with pygame.

- The background is tiled and the camera supports zoom and panning.
- Connections are drawn behind hubs, and drones are layered above the map.
- Hover and debug behaviour can reveal extra state during the simulation.
- The menu lets you browse map groups and load a map directly into the simulator.

The visual layer is used both for presentation and for interaction: the renderer keeps
the scene organized, while the `Window` object manages screen-space and world-space
coordinates so the map can be inspected comfortably.

## Resources

- 42 Fly-in subject (`subject.txt`)
- Pygame documentation: https://www.pygame.org/docs/
- Pydantic documentation: https://docs.pydantic.dev/
- Python typing documentation: https://docs.python.org/3/library/typing.html
- BFS / shortest-path background: https://en.wikipedia.org/wiki/Breadth-first_search

### AI Usage

AI was used to help structure and rewrite this README, summarize the current module
responsibilities, and align the documentation with the implementation already present
in the repository. The code itself and the final verification of the behaviour were
reviewed manually.

## Code Structure

This section explains how the functions and classes in the project interact.

### `parser.py`

- `parse_map_file(filepath)` is the main entry point for map loading.  
  It reads a map file, validates `nb_drones`, hub definitions, metadata, and
	connections, then returns a validated `Map` object.
- `ParseErrorCollector` gathers parsing problems and prints them together so the
	caller can show a complete error report.
- `Color`, `Position`, `Hub`, `Connection`, and `Map` are the validated data models
	used by the rest of the project.
- `_parse_metadata_block`, `_make_color`, and `_default_color` are internal helpers
	used during parsing.
- `scan_all_color_names()` is a utility for discovering color values used in the map
	files.

### `gui.py`

- `Window` owns the pygame surface, camera zoom, and camera offset.
- `Text`, `Button`, `ImageObject`, and `Rect` are reusable drawing primitives.
- `Drone`, `Hub_gui`, and `Connection_gui` are the map-specific visual objects.
- `Map_gui` stores all hubs and connections and builds adjacency between them.
- `LayeredRenderer` is the scene manager. It draws objects layer by layer and updates
	moving drone objects every frame.
- The helper functions at the top of the module validate numbers, points, colors, and
	image paths before objects are created.

### `algo.py`

- `Pathfinder` is responsible for graph traversal using Dijkstra's algorithm.
- `Pathfinder._build_adjacency()` turns the rendered map into a neighbor lookup table.
- `Pathfinder.get_neighbors()` returns connected hubs for a given hub name.
- `Pathfinder.shortest_path()` finds the lowest-cost route from start to end,
  optionally avoiding a set of blocked edges.
- `Pathfinder.all_paths()` discovers up to 20 edge-disjoint paths for
  multi-drone distribution.
- `Pathfinder.movement_cost()` returns the turn cost for entering a destination hub.

### `simulation.py`

- `SimDrone` stores the state of one drone during the simulation.
- `Simulation` owns the full turn sequence and the list of active drones.
- `Simulation.spawn_drones()` creates drones at the start hub and assigns them paths.
- `Simulation.step()` advances the simulation by one turn and returns the movement
	log for that turn.
- `Simulation.step_back()` restores the previous turn.
- `Simulation.is_finished()`, `active_drones()`, and `turn_log()` provide status
	queries for the UI.

### `main.py`

- `build_map_gui()` converts parsed map data into renderable GUI objects.
- `App` is the main interactive application. It builds the menus, loads maps, creates
	the pathfinder and simulation, and drives the event loop.
- `_show_error_overlay()` displays parser errors directly on screen.
- `_center_view()` computes the zoom and offset needed to fit a map on screen.
- `_quick_view()` skips the menu and opens a single map directly.
- The `__main__` block decides whether to launch the menu UI or open a provided map
	path immediately.

### Runtime Flow

1. `main.py` loads a map with `parser.parse_map_file()`.
2. `build_map_gui()` converts the parsed map into `gui.Map_gui` objects.
3. `algo.Pathfinder` builds adjacency and computes a route for the drones.
4. `simulation.Simulation` spawns drones and advances them turn by turn.
5. `gui.LayeredRenderer` draws the background, map, drones, and HUD.
6. The `App` event loop wires user input to the simulation, camera, and menu.
