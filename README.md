# SpaceBashers

A terminal Space Invaders game built with Python curses. No dependencies required.

![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue)
![macOS](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)

## Quick Start

```bash
python3 spacebashers.py
```

## Controls

| Key | Action |
|---|---|
| `←` `→` or `A` `D` | Move ship |
| `Space` | Fire (hold to rapid-fire) |
| `P` | Pause |
| `M` | Toggle sound |
| `Q` | Quit |

Move and fire work simultaneously.

## Features

- 5 rows of invaders with different sprites and point values (10/20/30 pts)
- Mystery ship flyovers for bonus points (50-300 pts)
- 4 destructible barriers with arch cutouts
- HP system with a color-coded health bar (survives 3 hits)
- Invaders speed up as you destroy them
- Procedurally generated retro sound effects (macOS `afplay`)
- Level progression with increasing difficulty

## Requirements

- Python 3.6+
- A terminal that supports curses (most do)
- macOS for sound effects (game works silently on other platforms)

## License

MIT
