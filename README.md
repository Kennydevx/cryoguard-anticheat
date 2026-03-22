<div align="center">
  <img src="https://raw.githubusercontent.com/kennydevx/cryoguard/main/assets/cryoguard_logo.png" width="300" alt="CryoGuard Logo" />
  <h1>🎮 CryoGuard Anti-Cheat</h1>
  <p><b>Neural Movement Anomaly Detection for Game Servers</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
  [![CryoEngine](https://img.shields.io/badge/Powered%20By-Cryo%20Engine%20v3-7000ff?style=flat-square)](https://cryo-corona.com)
</div>

---

## What is CryoGuard?

CryoGuard is a server-side **Neural Anti-Cheat** middleware designed to catch movement-based cheats perfectly, without touching the client's memory. Instead of intrusive kernel-level drivers, CryoGuard analyzes the mathematics of player movement over time.

It detects:
- **Speedhacks**: Traveling faster than the engine allows.
- **Teleportation**: Impossible Euclidean distance jumps.
- **Aimbots / Snap-aim**: Instantaneous angular `aim_delta` changes impossible for human wrists.

## 🚀 Quick Start (For Server Admins)

No coding required to get started. Use the built-in wizard:

1. Clone the repo.
2. Run the wizard:
   ```bash
   python setup_wizard.py
   ```
3. Set your threshold (Strict = 0.80, Normal = 0.85, Tolerant = 0.90).

## 💻 Developer Integration

Integrating CryoGuard into your Python-based game server (e.g., Godot headless server, Unity Python-bridge, or custom socket servers).

### 1. Start a Match
```python
from cryoguard import CryoGuard

guard = CryoGuard()
players = ["STEAM_0:1:123456", "STEAM_0:1:654321"]

# Initialize tracking (resets velocity calculations)
guard.start_match("match_alpha", players)
```

### 2. On Player Tick / Move Event
```python
def on_player_update(player_id, x, y, z, aim_yaw, aim_pitch):
    # Calculate angular change since last tick (aim_delta)
    aim_change = calculate_delta(aim_yaw, aim_pitch)
    
    # Push to CryoGuard
    result = guard.on_move(player_id, x, y, z, aim_delta=aim_change)
    
    if result["flagged"]:
        print(f"⚠️ {player_id} flagged for {result['reason']} (Score: {result['surprise']})")
        
        # Action logic
        if result["flag_count"] >= 3:
            server.kick(player_id, reason="Anti-Cheat Violation")
```

### 3. Match Report
At the end of the round, get a beautiful automated report:
```python
report = guard.end_match()
print(f"Clean Players: {report['clean_players']}")
print(f"Banned: {len(report['flagged_players'])}")
```

## 🛠️ How it Works

1. CryoGuard calculates the 3D velocity vector `v = d / dt` based on the timestamps of your incoming updates.
2. It builds a 5-dimension tensor: `[X_norm, Y_norm, Z_norm, Velocity_norm, Aim_Delta_norm]`.
3. The **Cryo-Corona Neural Engine** processes the tensor via gRPC. 
4. If the movement deviates from learned human limits (the KL-Divergence / Surprise threshold), it triggers a flag.

## 🤝 Contributing
Open source contributions are highly encouraged for game engine specific integrations (Unreal Engine plugins, Godot nodes, etc).

## 📄 License
[MIT](https://choosealicense.com/licenses/mit/)
