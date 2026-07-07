"""
Turn-by-turn simulation engine for the Fly-Yeet drone routing system.

Owns drone state, moves drones step-by-step, and produces the
simulation output format required by the subject.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import gui

if TYPE_CHECKING:
    import algo


# ---------------------------------------------------------------------------
# SimDrone — a drone with simulation state
# ---------------------------------------------------------------------------

@dataclass
class SimDrone:
    """A drone tracked by the simulation."""

    drone_id: int
    current_hub: gui.Hub_gui
    # Full path of hub names from start to end
    path: list[str] = field(default_factory=list)
    # Index in *path* of the next hub to move toward
    path_index: int = 0
    # > 0 when traversing a restricted-zone connection (turns remaining)
    transit_turns: int = 0
    # The connection being traversed (restricted zones only)
    transit_connection: Optional[gui.Connection_gui] = None
    # Set when the drone has reached the end hub
    arrived: bool = False
    # pygame tick (ms) when the drone arrived at the end (for visual cooldown)
    arrival_tick: float = 0.0
    # Visual drone (set by main.py after spawning)
    current_drone_gui: object = field(default=None, repr=False)

    @property
    def next_hub_name(self) -> Optional[str]:
        """Name of the next hub on the path, if any."""
        if self.path_index < len(self.path):
            return self.path[self.path_index]
        return None


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

class Simulation:
    """Manages turn-by-turn drone movement on a :class:`~gui.Map_gui`.

    Usage::

        sim = Simulation(map_gui, algo)
        sim.spawn_drones(nb_drones)
        while not sim.is_finished():
            log = sim.step()
            print(log)
    """

    def __init__(
        self,
        map_gui_obj: gui.Map_gui,
        pathfinder: algo.Pathfinder,
    ) -> None:
        self.map_gui: gui.Map_gui = map_gui_obj
        self.pathfinder = pathfinder
        self.turn: int = 0
        self.drones: list[SimDrone] = []
        self._turn_history: list[list[SimDrone]] = []
        self._log_history: list[list[str]] = []
        # Track drones in transit toward each hub (reserves capacity)
        self._transit_incoming: dict[str, int] = {}

        # Ensure adjacency is built
        self.map_gui.build_adjacency()

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def spawn_drones(self, count: int) -> None:
        """Create *count* drones at the start, distributed across
        multiple edge-disjoint paths when available."""
        start = self.map_gui.hubs.get(self._find_start_name())
        end_name = self._find_end_name()
        if start is None or end_name is None:
            raise RuntimeError("Map missing start or end hub")

        # Compute diverse paths for multi-drone distribution
        paths: list[list[str]] = self.pathfinder.all_paths(
            start.name, end_name
        )
        if not paths:
            raise RuntimeError(
                f"No path exists from start '{start.name}' "
                f"to end '{end_name}'. The map may have all routes "
                f"blocked or the end hub may be unreachable."
            )
        if count > 500:
            print(
                f"Warning: spawning {count} drones may be slow.",
                file=sys.stderr,
            )

        # Distribute drones round-robin across available paths
        for drone_id in range(1, count + 1):
            path_index: int = (drone_id - 1) % len(paths)
            path: list[str] = list(paths[path_index])
            sd = SimDrone(
                drone_id=drone_id,
                current_hub=start,
                path=path,
                path_index=1,  # first element is current, next is target
            )
            self.drones.append(sd)
            start.add_drone(sd)

    def _find_start_name(self) -> str:
        for hub in self.map_gui.hubs.values():
            if hub.is_start:
                return hub.name
        raise RuntimeError("No start hub found")

    def _find_end_name(self) -> str:
        for hub in self.map_gui.hubs.values():
            if hub.is_end:
                return hub.name
        raise RuntimeError("No end hub found")

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def is_finished(self) -> bool:
        """Return ``True`` when all drones have arrived at the end."""
        return all(d.arrived for d in self.drones)

    def step(self) -> list[str]:
        """Advance one simulation turn.

        Uses a single-pass approach: for each drone, check whether a
        move is possible, reserve both the target zone slot and the
        connection slot atomically, then execute all reservations.

        Returns:
            A list of movement strings in the format ``D<id>-<zone>``
            or ``D<id>-<connection>`` (for in-transit restricted moves).
        """
        self.turn += 1

        # Save state for potential undo
        self._turn_history.append(
            [SimDrone(
                drone_id=d.drone_id,
                current_hub=d.current_hub,
                path=list(d.path),
                path_index=d.path_index,
                transit_turns=d.transit_turns,
                transit_connection=d.transit_connection,
                arrived=d.arrived,
            ) for d in self.drones]
        )

        movements: list[str] = []
        just_arrived: set[int] = set()  # drone_ids that finished transit

        # ---- Phase 1: complete in-transit restricted moves ----
        for sd in self.drones:
            if sd.transit_turns > 0:
                sd.transit_turns -= 1
                if sd.transit_turns == 0:
                    dest_name = sd.next_hub_name
                    dest = self.map_gui.hubs.get(dest_name or "")
                    if (dest is not None
                            and sd.transit_connection is not None):
                        sd.transit_connection.release(sd)
                        sd.transit_connection = None
                        # Decrement transit reservation
                        self._transit_incoming[dest.name] = (
                            self._transit_incoming.get(dest.name, 1) - 1
                        )
                        # Per subject rules the drone MUST arrive;
                        # capacity should have been guaranteed upstream.
                        if not dest.can_accept_drone():
                            raise RuntimeError(
                                f"Drone D{sd.drone_id} completed "
                                f"restricted transit but destination "
                                f"'{dest.name}' is at capacity — "
                                f"this is a scheduling bug."
                            )
                        sd.current_hub.remove_drone(sd)
                        sd.current_hub = dest
                        dest.add_drone(sd)
                        sd.path_index += 1
                        just_arrived.add(sd.drone_id)
                        movements.append(f"D{sd.drone_id}-{dest.name}")
                        if dest.is_end:
                            sd.arrived = True
                            sd.arrival_tick = (
                                gui.pygame.time.get_ticks() / 1000.0
                            )
                else:
                    # Still in transit
                    conn_name = (
                        f"{sd.current_hub.name}-"
                        f"{sd.next_hub_name}"
                    )
                    movements.append(f"D{sd.drone_id}-{conn_name}")

        # ---- Phase 2: single-pass reservation + execution ----
        # Track removals/additions dynamically (not pre-counted) so
        # drones that fail to move don't inflate the leaving count.
        removed: dict[str, int] = {}  # hub_name → drones removed this turn
        added: dict[str, int] = {}    # hub_name → drones added this turn
        reserved_conn: dict[
            tuple[str, str], int
        ] = {}  # (hub_a, hub_b) → drones traversing

        # Drones that completed transit in Phase 1 must not move again
        # in the same turn — they already spent their turn "arriving".
        already_acted: set[int] = set(just_arrived)

        # Build list of candidate moves
        candidates: list[tuple[SimDrone, gui.Hub_gui, gui.Connection_gui]] = []
        for sd in self.drones:
            if sd.arrived or sd.transit_turns > 0:
                continue
            if sd.drone_id in already_acted:
                continue
            target_name = sd.next_hub_name
            if target_name is None:
                continue
            target = self.map_gui.hubs.get(target_name)
            if target is None:
                continue
            conn = sd.current_hub.get_connection_to(target)
            if conn is None:
                continue

            move_cost = self.pathfinder.movement_cost(target_name)
            if move_cost >= 999_999:
                continue

            candidates.append((sd, target, conn))

        # Sort candidates so drones furthest along their path move first.
        # This maximises pipeline throughput — front drones free up
        # capacity for trailing drones in the same turn.
        candidates.sort(key=lambda c: (-c[0].path_index, c[0].drone_id))

        for sd, target, conn in candidates:
            move_cost = self.pathfinder.movement_cost(target.name)

            # --- check target zone capacity ---
            # Effective = current occupants − already-removed-this-turn
            #             + already-added-this-turn
            #             + drones in transit toward this hub
            effective: int = (
                len(target.current_drones)
                - removed.get(target.name, 0)
                + added.get(target.name, 0)
                + self._transit_incoming.get(target.name, 0)
            )
            if not target.is_start and not target.is_end:
                if effective >= target.max_drones:
                    continue

            # --- check connection capacity (including reservations) ---
            edge: tuple[str, str] = (
                (conn.hub_a.name, conn.hub_b.name)
                if conn.hub_a.name < conn.hub_b.name
                else (conn.hub_b.name, conn.hub_a.name)
            )
            conn_reserved: int = reserved_conn.get(edge, 0)
            if (len(conn.traversing_drones) + conn_reserved
                    >= conn.max_link_capacity):
                continue

            # --- reserve ---
            added[target.name] = added.get(target.name, 0) + 1
            removed[sd.current_hub.name] = (
                removed.get(sd.current_hub.name, 0) + 1
            )
            reserved_conn[edge] = conn_reserved + 1

            # --- execute ---
            sd.current_hub.remove_drone(sd)
            conn.traverse(sd)

            if move_cost == 2:
                # Restricted zone: drone in transit for 2 turns.
                # Reserve a slot in the destination for when it arrives.
                sd.transit_turns = 1
                sd.transit_connection = conn
                self._transit_incoming[target.name] = (
                    self._transit_incoming.get(target.name, 0) + 1
                )
                conn_name = f"{sd.current_hub.name}-{target.name}"
                movements.append(f"D{sd.drone_id}-{conn_name}")
            else:
                # Normal / priority: instant arrival
                conn.release(sd)
                sd.current_hub = target
                target.add_drone(sd)
                sd.path_index += 1
                movements.append(f"D{sd.drone_id}-{target.name}")
                if target.is_end:
                    sd.arrived = True
                    sd.arrival_tick = (
                        gui.pygame.time.get_ticks() / 1000.0
                    )

        self._log_history.append(movements)

        # Print the required terminal output
        if movements:
            print(" ".join(movements))
        else:
            print("(no movement)")
        sys.stdout.flush()

        return movements

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def step_back(self) -> bool:
        """Undo the last turn.  Returns ``True`` on success."""
        if not self._turn_history:
            return False

        previous = self._turn_history.pop()
        if self._log_history:
            self._log_history.pop()

        # 1. Remove every drone from its current hub / transit connection
        for sd in self.drones:
            sd.current_hub.remove_drone(sd)
            if sd.transit_connection is not None:
                sd.transit_connection.release(sd)

        # 2. Restore all fields from the snapshot
        for i, sd in enumerate(self.drones):
            prev = previous[i]
            sd.current_hub = prev.current_hub
            sd.path = prev.path
            sd.path_index = prev.path_index
            sd.transit_turns = prev.transit_turns
            sd.transit_connection = prev.transit_connection
            sd.arrived = prev.arrived

        # 3. Re-add every drone to its restored hub
        for sd in self.drones:
            sd.current_hub.add_drone(sd)

        # 4. Rebuild transit reservations from restored drone states
        self._transit_incoming.clear()
        for sd in self.drones:
            if sd.transit_turns > 0 and sd.next_hub_name:
                dest = sd.next_hub_name
                self._transit_incoming[dest] = (
                    self._transit_incoming.get(dest, 0) + 1
                )

        self.turn -= 1
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active_drones(self) -> list[SimDrone]:
        """Return drones that haven't arrived yet."""
        return [sd for sd in self.drones if not sd.arrived]

    def turn_log(self, turn_index: int) -> list[str]:
        """Return the movement log for a past turn (0-indexed)."""
        if 0 <= turn_index < len(self._log_history):
            return self._log_history[turn_index]
        return []
