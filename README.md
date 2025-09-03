# 8bit Doom — PyOpenGL Arcade Dungeon Shooter

A fast-paced, 8-bit–style dungeon shooter built with **Python + PyOpenGL (GL/GLU/GLUT)**. Battle through 10 themed levels, switch between **first-person** and **third-person** cameras on the fly, collect perks, and chase a session-based Hall of Fame.

> 🎓 **Academic-ready**: This README explains setup, controls, features, level/enemy rules, and the code structure to help evaluators navigate the project quickly.

---

## Table of Contents
- [Features](#features)
- [Install & Run](#install--run)
- [Controls](#controls)
- [Gameplay Systems](#gameplay-systems)
  - [Scoring & Hall of Fame](#scoring--hall-of-fame)
  - [Perks](#perks)
  - [Enemy Rules (Damage & Toughness)](#enemy-rules-damage--toughness)
  - [Level Rules](#level-rules)
  - [Dungeon Themes & Colors](#dungeon-themes--colors)
  - [UI & Navigation](#ui--navigation)
- [Project Structure & Code Guide](#project-structure--code-guide)
- [Troubleshooting](#troubleshooting)
- [Planned Improvements](#planned-improvements)
- [License](#license)

---

## Features
- **Two camera modes**: First-person (precision) and Third-person (spatial awareness) with synced switching.
- **10 handcrafted levels** grouped into 4 biomes: Earth, Mud, Heaven, Hell.
- **Perk system**: instant full heal, score multiplier (x2), and rapid fire.
- **Immediate-mode UI**: main menu, level select, pause, Hall of Fame, and win/lose overlays.
- **Tuned enemy archetypes** with theme-based colors, simple pathing, ranged attacks, and subtle bob animation.
- **Session Hall of Fame (Top 3)** with recency tie-break (in-memory; no files).

---

## Install & Run

### 1) Prerequisites
- **Python 3.8+** (tested with modern 3.x)
- **OpenGL + GLUT runtime** on your system

**OS notes** (pick one approach that fits your setup):
- **Windows**
  - Have `freeglut.dll` available (in PATH or next to the script). You can install FreeGLUT via MSYS2 (`pacman -S mingw-w64-x86_64-freeglut`) or Chocolatey (`choco install freeglut`), or use any other distribution.
- **macOS**
  - Install FreeGLUT via Homebrew: `brew install freeglut`.
- **Linux (Debian/Ubuntu)**
  - `sudo apt install freeglut3 freeglut3-dev`

### 2) Python packages
```bash
pip install PyOpenGL PyOpenGL_accelerate
```
> `PyOpenGL_accelerate` is optional but recommended for performance.

### 3) Run
```bash
python 8bitdoom.py
```

---

## Controls

| Key | Action | Notes |
|---|---|---|
| **W / A / S / D** | Move | Relative to camera (TP) or player yaw (FP) |
| **Q / E** | Rotate player | Always available |
| **Left Click / Space** | Shoot | Aim-assist lightly aligns to nearest target |
| **Arrow Keys** | Camera adjust | FP: pitch; TP: orbit pitch/yaw |
| **V** | Toggle camera | First-person ↔ Third-person (yaw is synced) |
| **P** | Pause / Resume | Shows pause menu |
| **Esc** | Exit | From gameplay/menus |
| **H** | Activate **Health Perk** | Instant full heal (when available) |
| **F** | Activate **Score Perk** | x2 score for a short duration (when available) |
| **G** | Activate **Gun Perk** | Rapid fire for a short duration (when available) |
| **C** | Toggle **Cheat Mode** | Godmode + auto-fire every ~0.18s (debug/assist) |

---

## Gameplay Systems

### Scoring & Hall of Fame
- Earn points by defeating enemies (per-type values).
- **Score resets to 0** when you die, start a new game, or retry a level.
- Your score is recorded to the **Hall of Fame (Top 3)** on:
  - Death
  - Beating Level 10 (win screen)
  - Returning to Main Menu from Pause with non-zero score
  - Exiting from Main Menu with non-zero score
- Hall of Fame is **in-memory per session** only (no file I/O). On ties, **more recent** scores win.

### Perks
- **Health** (`H`): instantly restores full health.
- **Score x2** (`F`): doubles points for a limited time.
- **Rapid Fire** (`G`): drastically reduces shoot cooldown for a limited time.
- Perk availability is unlocked via kill counters and **timers don’t carry** between levels.

### Enemy Rules (Damage & Toughness)
Balanced values (as implemented in code):
- **Type 1**: 3 hits to defeat; **5 HP** damage per hit.
- **Type 2**: 4 hits; **6 HP** damage per hit.
- **Type 3**: 5 hits; **8 HP** damage per hit.
- **Mini Boss (Lv 5)**: 10 hits; **10 HP** damage per hit.
- **Boss (Lv 10)**: 15 hits; **12 HP** damage per hit.

### Level Rules
- **Lv 1**: total 5 × T1, max 1 active
- **Lv 2**: total 6 × T1, max 2 active
- **Lv 3**: total 9 × T1, max 3 active
- **Lv 4**: total 5 × T2, max 1 active
- **Lv 5**: total 7 (3 × T1, 3 × T2, 1 × Mini Boss), max 1 active
- **Lv 6**: total 9 × T2, max 3 active
- **Lv 7**: total 5 × T3, max 1 active
- **Lv 8**: total 6 × T3, max 2 active
- **Lv 9**: total 9 × T3, max 3 active
- **Lv 10**: total 16 (5 × T1, 5 × T2, 5 × T3, 1 × Boss), max 1 active

### Dungeon Themes & Colors
- **Lv 1–3**: *Earth* — lush greens
- **Lv 4–6**: *Mud* — rich browns/clay
- **Lv 7–9**: *Heaven* — soft blue/white tints
- **Lv 10**: *Hell* — crimson/embers Enemy tints adapt per theme; boss/miniboss use hellish reds.

### UI & Navigation
- **Main Menu**: Start New Game • Select Level • Hall of Fame • Exit
- **Pause**: Resume • Retry Level • Return to Main Menu
- **HUD**: Health, Score, Level, Perk banners, Cheat banner
- **Overlays**: “Level Completed”, “You died!”, “Congratulations! Game Finished”

---

## Project Structure & Code Guide

```
.
├── 8bitdoom.py         # Main game (rendering, input, AI, UI, state machine)
└── README.md           # This file
```

Key areas (all in `8bitdoom.py`):

- **Globals/constants**: window sizes, states, player/bullet/world/camera constants
- **Level configs**: `init_level_configs()`
- **Player bootstrap**: `init_player()`
- **Level load/reset**: `init_level(level_num)`
- **Enemy archetypes**: `get_enemy_definition(enemy_type_id)`
- **Enemy spawn/move/shoot**: `update_enemies(delta_time)`
- **Enemy death → score/perk**: `handle_enemy_death(enemy)`
- **Player damage/death**: `handle_player_hit(damage)`
- **Perk availability**: `update_perks()`
- **Bullets**: `create_bullet(...)`, `update_bullets(delta_time)`
- **Progression/win**: `check_level_completion()`
- **State tick**: `update_game_state(delta_time)`
- **World/Models**: `draw_dungeon()`, `draw_player()`, `draw_wolf(...)`
- **UI primitives & system**: `draw_text*`, `ui_add_button`, `draw_ui()`
- **Camera & frame**: `display()`, `reshape()`
- **Input callbacks**: `keyboard`, `keyboard_up`, `special_keys_*`, `mouse_click`
- **Entry point**: `main()`

> The project uses **fixed-function OpenGL** (GL/GLU/GLUT) for simplicity in an academic context.

---

## Troubleshooting

- **`ImportError: OpenGL`**   Install packages: `pip install PyOpenGL PyOpenGL_accelerate`

- **GLUT/FreeGLUT not found (window fails to open / crashes)**   Ensure FreeGLUT is installed and discoverable by your OS (see **Install & Run**). On Windows, having `freeglut.dll` alongside `8bitdoom.py` often resolves it.

- **Blank window or no input**   Make sure the GLUT window is focused; some window managers suppress inputs when unfocused.

- **Performance tips**   Install `PyOpenGL_accelerate`, close other GPU-heavy apps, and avoid very high-DPI scaling if you see slowdowns.

---

## Planned Improvements
- Optional file-backed high score persistence.
- Audio cues for hits, perks, and transitions.
- Better obstacle layouts and enemy pathing (basic steering/avoidance is already included).
- Configurable key-bindings and difficulty presets.

---

## License
Specify a license for your repository (e.g., MIT).

---

### Acknowledgements
Built with **Python, PyOpenGL, GLUT**. No third-party game assets are bundled; all models are procedural/primitive-based.

---

**Happy hacking & have fun blasting!**
