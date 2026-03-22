# Cryo-Corona — CryoGuard Anti-Cheat Agent v1.0
# Neural anti-cheat for game servers. Detects movement anomalies,
# speedhacks, teleportation, and aimbot via the Cryo Engine.
# Proprietary — Do not redistribute.

import os
import sys
import time
import math
import logging
from collections import defaultdict

# ── Import Cryo SDK ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
import cryo_pb2
import cryo_pb2_grpc
import grpc

def load_config():
    """Loads configuration from config.json if available."""
    import json
    config = {
        "server": "api.cryo-saas.com:50505",
        "api_key": "71e6236b046a8b8c72fee2dd5285a9c0",
        "threshold": 0.85
    }
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                loaded = json.load(f)
                config.update(loaded)
                print(f"[CryoGuard] Config loaded from {config_path}")
        except Exception as e:
            print(f"[CryoGuard] Error loading config: {e}")
    return config

# ── Configuration ───────────────────────────────────────────────
_CONFIG = load_config()
CRYO_SERVER = os.getenv("CRYO_SERVER", _CONFIG["server"])
CRYO_API_KEY = os.getenv("CRYO_API_KEY", _CONFIG["api_key"])
SURPRISE_THRESHOLD = float(os.getenv("CRYOGUARD_THRESHOLD", str(_CONFIG["threshold"])))

logging.basicConfig(level=logging.INFO, format="[CryoGuard] %(asctime)s %(message)s")
log = logging.getLogger("cryoguard")


class CryoGuard:
    """
    Neural Anti-Cheat Engine for Game Servers.
    
    Each player's movement is converted to a 5-float state vector and sent
    to the Cryo Engine. Anomalous movement patterns (speedhack, teleport,
    aimbot) trigger the surprise metric above threshold.
    
    Usage:
        guard = CryoGuard()
        
        # On match start
        guard.start_match("match_001", ["player_1", "player_2", ...])
        
        # On player movement (called every game tick)
        result = guard.on_move("player_1", x=120.5, y=10.0, z=-45.2, aim_delta=0.5)
        if result["flagged"]:
            kick_player("player_1", reason=result["reason"])
    """

    FLAG_REASONS = {
        0.85: "MOVEMENT_ANOMALY",
        0.90: "POSSIBLE_SPEEDHACK",
        0.95: "PROBABLE_TELEPORT_OR_AIMBOT"
    }

    def __init__(self, server=None, api_key=None, threshold=None):
        self.server = server or CRYO_SERVER
        self.api_key = api_key or CRYO_API_KEY
        self.threshold = threshold or SURPRISE_THRESHOLD

        self._channel = grpc.insecure_channel(self.server)
        self._stub = cryo_pb2_grpc.CryoEngineStub(self._channel)

        # Track player positions for velocity calculation
        self._last_pos = {}     # player_id -> (x, y, z, timestamp)
        self._flag_counts = defaultdict(int)
        self._session_id = None

        log.info(f"🎮 CryoGuard Anti-Cheat Online → {self.server}")

    # ── Public API ──────────────────────────────────────────────

    def start_match(self, match_id: str, player_ids: list):
        """
        Initialize a new match session and register all players.
        
        Args:
            match_id: Unique identifier for the match
            player_ids: List of player IDs participating
        """
        try:
            resp = self._stub.CreateSession(cryo_pb2.Empty(), timeout=10)
            self._session_id = resp.session_id
        except Exception as e:
            log.error(f"Session creation failed: {e}")
            self._session_id = f"cg_{match_id}_fallback"

        # Register all players
        try:
            pb_units = [
                cryo_pb2.UnitData(
                    unit_id=pid,
                    z_state=cryo_pb2.FloatArray(values=[0.0] * 5)
                ) for pid in player_ids
            ]
            req = cryo_pb2.FastStepRequest(
                api_key=self.api_key,
                session_id=self._session_id,
                register_units=pb_units
            )
            self._stub.FastStep(req, timeout=10)
            self._last_pos.clear()
            self._flag_counts.clear()
            log.info(f"Match {match_id} started with {len(player_ids)} players")
        except Exception as e:
            log.error(f"Match start failed: {e}")

    def on_move(self, player_id: str, x: float, y: float, z: float, aim_delta: float = 0.0) -> dict:
        """
        Process a player movement event.
        
        Args:
            player_id: The player's unique ID
            x, y, z: World position coordinates
            aim_delta: Angular change in aim direction (degrees)
        
        Returns:
            dict with 'flagged', 'surprise', 'reason', and 'flag_count'
        """
        now = time.time()
        velocity = 0.0

        # Calculate velocity from last known position
        if player_id in self._last_pos:
            lx, ly, lz, lt = self._last_pos[player_id]
            dt = now - lt
            if dt > 0:
                dist = math.sqrt((x - lx) ** 2 + (y - ly) ** 2 + (z - lz) ** 2)
                velocity = dist / dt

        self._last_pos[player_id] = (x, y, z, now)

        # Normalize values for the engine
        vector = [
            x / 1000.0,           # Position X (normalized)
            y / 1000.0,           # Position Y
            z / 1000.0,           # Position Z
            min(velocity / 50.0, 1.0),  # Velocity (50 units/s = max normal)
            min(aim_delta / 180.0, 1.0)  # Aim delta (normalized to max 180°)
        ]

        # Send to engine
        try:
            updates = {
                player_id: cryo_pb2.FloatArray(values=vector)
            }
            req = cryo_pb2.FastStepRequest(
                api_key=self.api_key,
                session_id=self._session_id,
                state_updates=updates
            )
            resp = self._stub.FastStep(req, timeout=5)
            surprise = resp.surprise
        except Exception as e:
            log.error(f"Engine call failed for {player_id}: {e}")
            return {"flagged": False, "surprise": 0.0, "reason": None, "flag_count": 0}

        # Determine flag level
        flagged = surprise > self.threshold
        reason = None
        if flagged:
            self._flag_counts[player_id] += 1
            # Determine severity
            for threshold_level in sorted(self.FLAG_REASONS.keys(), reverse=True):
                if surprise >= threshold_level:
                    reason = self.FLAG_REASONS[threshold_level]
                    break
            log.warning(f"🚨 {player_id} FLAGGED | surprise={surprise:.3f} | reason={reason} | "
                        f"velocity={velocity:.1f} | aim_delta={aim_delta:.1f} | "
                        f"total_flags={self._flag_counts[player_id]}")

        return {
            "flagged": flagged,
            "surprise": surprise,
            "reason": reason,
            "velocity": velocity,
            "flag_count": self._flag_counts[player_id]
        }

    def batch_update(self, positions: dict) -> dict:
        """
        Update multiple players at once (efficient for high tick-rate servers).
        
        Args:
            positions: {"player_id": {"x": f, "y": f, "z": f, "aim_delta": f}, ...}
        
        Returns:
            dict with global surprise and per-player flag status
        """
        results = {}
        for pid, pos in positions.items():
            results[pid] = self.on_move(
                pid,
                pos.get("x", 0), pos.get("y", 0), pos.get("z", 0),
                pos.get("aim_delta", 0)
            )
        return results

    def get_flagged_players(self, min_flags=3) -> list:
        """Return list of players flagged more than min_flags times."""
        return [
            {"player_id": pid, "flag_count": count}
            for pid, count in self._flag_counts.items()
            if count >= min_flags
        ]

    def end_match(self) -> dict:
        """End the match and return final anti-cheat report."""
        report = {
            "total_players": len(self._last_pos),
            "flagged_players": self.get_flagged_players(min_flags=1),
            "clean_players": len(self._last_pos) - len(self._flag_counts),
            "total_flags": sum(self._flag_counts.values())
        }
        log.info(f"Match ended: {report['total_flags']} flags, "
                 f"{len(report['flagged_players'])} suspicious players")
        return report

    def __del__(self):
        if hasattr(self, '_channel'):
            self._channel.close()


# ── Standalone Demo ─────────────────────────────────────────────
if __name__ == "__main__":
    import random

    print("=" * 60)
    print("  CryoGuard Anti-Cheat — Demo Mode")
    print("=" * 60)

    guard = CryoGuard()
    players = [f"player_{i}" for i in range(5)]
    guard.start_match("demo_match", players)

    print("\n🕹️  Simulating 20 game ticks...\n")

    for tick in range(20):
        for p in players:
            # Normal movement
            x = tick * 2.0 + random.gauss(0, 0.5)
            y = 10.0 + random.gauss(0, 0.1)
            z = tick * 1.5 + random.gauss(0, 0.3)
            aim = random.gauss(2.0, 1.0)

            # Simulate cheater on player_0 (teleportation at tick 15)
            if p == "player_0" and tick == 15:
                x += 800  # Teleport!
                aim = 180  # Snap aim

            result = guard.on_move(p, x, y, z, aim)
            if result["flagged"] or (p == "player_0" and tick == 15):
                print(f"  🚨 Tick {tick}: {p} → {result['reason']} (surprise={result['surprise']:.3f})")


        time.sleep(0.1)

    print("\n📊 Final Report:")
    report = guard.end_match()
    print(f"  Total flags: {report['total_flags']}")
    for fp in report["flagged_players"]:
        print(f"  ⚠️  {fp['player_id']}: {fp['flag_count']} flags")

    print("\n✅ Demo complete.")
