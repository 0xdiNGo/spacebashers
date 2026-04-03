#!/usr/bin/env python3
"""SpaceBashers Network Multiplayer - Hungry Hungry Hippos Edition.

Usage:
  python3 netplay.py host [--port 7777]
  python3 netplay.py join <ip> [--port 7777] [--name YourName]

Host supports 1-4 players. Start solo by pressing SPACE with no one joined.
"""

import curses
import time
import random
import math
import json
import socket
import select
import threading
import struct
import wave
import tempfile
import os
import subprocess
import atexit
import sys

DEFAULT_PORT = 7777
TICK_RATE = 60
SNAPSHOT_RATE = 20
COLS = 80
ROWS = 40
SHIP_W = 5
INV_W = 4
TOTAL_WAVES = 5

PLAYER_CONFIGS = [
    {"name": "P1", "color": "green",   "ship": " /^\\ "},
    {"name": "P2", "color": "cyan",    "ship": " /^\\ "},
    {"name": "P3", "color": "yellow",  "ship": " /^\\ "},
    {"name": "P4", "color": "magenta", "ship": " /^\\ "},
]

SPRITES_POOL = ["(@@)", "<**>", "/\\/\\", "{##}", "[@@]", "<==>", "(##)", "<@@>"]

BONUS_TYPES = [
    {"char": "+", "color": "green",   "effect": "hp"},
    {"char": "x", "color": "yellow",  "effect": "double"},
    {"char": "!", "color": "red",     "effect": "rapid"},
    {"char": "*", "color": "magenta", "effect": "steal"},
]

# ─── Sound Engine (from spacebashers.py) ─────────────────────────────────────

class SoundEngine:
    def __init__(self):
        self._tmpdir = tempfile.mkdtemp(prefix="spacebashers_snd_")
        self._channels = {}
        self._enabled = True
        self._sounds = {}
        self._generate_all()
        atexit.register(self.cleanup)

    def _make_wav(self, name, samples, sample_rate=22050):
        path = os.path.join(self._tmpdir, f"{name}.wav")
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        self._sounds[name] = path

    def _tone(self, freq, dur, vol=0.5, decay=True):
        n = int(22050 * dur)
        samples = []
        for i in range(n):
            t = i / 22050
            env = 1.0 - (i / n) if decay else 1.0
            val = math.sin(2 * math.pi * freq * t) * vol * env
            samples.append(max(-32767, min(32767, int(val * 32767))))
        return samples

    def _noise(self, dur, vol=0.4):
        n = int(22050 * dur)
        samples = []
        for i in range(n):
            env = 1.0 - (i / n)
            val = random.uniform(-1, 1) * vol * env
            samples.append(max(-32767, min(32767, int(val * 32767))))
        return samples

    def _generate_all(self):
        s = self._tone(880, 0.08, 0.3) + self._tone(440, 0.04, 0.2)
        self._make_wav("shoot", s)

        s = self._tone(600, 0.05, 0.3, False) + self._tone(300, 0.05, 0.3, False) + self._noise(0.06, 0.3)
        self._make_wav("kill", s)

        s = self._noise(0.3, 0.5)
        m = self._tone(100, 0.3, 0.3)
        for i in range(min(len(s), len(m))):
            s[i] = max(-32767, min(32767, s[i] + m[i]))
        self._make_wav("player_hit", s)

        s = self._tone(1200, 0.08, 0.2)
        self._make_wav("bonus_drop", s)

        s = self._tone(523, 0.06, 0.3, False) + self._tone(784, 0.06, 0.3, False) + self._tone(1047, 0.08, 0.3)
        self._make_wav("bonus_grab", s)

        s = self._tone(200, 0.1, 0.2) + self._tone(150, 0.1, 0.15)
        self._make_wav("steal", s)

        s = self._tone(262, 0.08, 0.3, False) + self._tone(330, 0.08, 0.3, False) + self._tone(392, 0.08, 0.3, False) + self._tone(523, 0.12, 0.3)
        self._make_wav("wave_start", s)

        s = self._tone(523, 0.1, 0.3, False) + self._tone(659, 0.1, 0.3, False) + self._tone(784, 0.1, 0.3, False) + self._tone(1047, 0.3, 0.3)
        self._make_wav("round_end", s)

        s = self._tone(440, 0.15, 0.25)
        self._make_wav("countdown", s)

        s = self._tone(880, 0.3, 0.3)
        self._make_wav("countdown_go", s)

        s = self._tone(440, 0.2, 0.3, False) + self._tone(370, 0.2, 0.3, False) + self._tone(330, 0.2, 0.3, False) + self._tone(262, 0.4, 0.3)
        self._make_wav("game_over", s)

    def play(self, name):
        if not self._enabled or name not in self._sounds:
            return
        prev = self._channels.get(name)
        if prev and prev.poll() is None:
            if name in ("shoot", "kill"):
                return
            try:
                prev.kill()
            except Exception:
                pass
        try:
            p = subprocess.Popen(["afplay", self._sounds[name]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._channels[name] = p
        except FileNotFoundError:
            self._enabled = False

    def toggle(self):
        self._enabled = not self._enabled

    @property
    def enabled(self):
        return self._enabled

    def cleanup(self):
        for p in self._channels.values():
            try:
                p.kill()
            except Exception:
                pass
        try:
            import shutil
            shutil.rmtree(self._tmpdir, ignore_errors=True)
        except Exception:
            pass


sfx = SoundEngine()

# ─── Protocol ─────────────────────────────────────────────────────────────────

def send_msg(sock, obj):
    try:
        data = json.dumps(obj, separators=(",", ":")).encode() + b"\n"
        sock.sendall(data)
        return True
    except (BrokenPipeError, ConnectionResetError, OSError):
        return False


def recv_msgs(sock, buf, timeout=0.005):
    msgs = []
    try:
        ready, _, _ = select.select([sock], [], [], timeout)
        if ready:
            data = sock.recv(65536)
            if not data:
                return None  # disconnected
            buf.extend(data)
    except (ConnectionResetError, OSError):
        return None

    while b"\n" in buf:
        line, _, rest = buf.partition(b"\n")
        buf.clear()
        buf.extend(rest)
        try:
            msgs.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return msgs


# ─── Game State (authoritative simulation) ────────────────────────────────────

class GameState:
    def __init__(self):
        self.state = "lobby"
        self.players = []
        self.invaders = []
        self.bullets = []
        self.enemy_bullets = []
        self.bonuses = []
        self.explosions = []
        self.wave = 0
        self.invaders_to_spawn = 0
        self.spawn_timer = 0
        self.spawn_interval = 0.5
        self.countdown_start = 0
        self.countdown_num = 3
        self.wave_end_time = 0
        self.last_enemy_shot = 0
        self.player_inputs = {}
        self.pending_sounds = []

    def add_player(self, name=None):
        if len(self.players) >= 4:
            return None
        pid = len(self.players)
        cfg = PLAYER_CONFIGS[pid]
        spacing = COLS / (4 + 1)  # pre-space for up to 4
        p = {
            "id": pid,
            "name": name or cfg["name"],
            "color": cfg["color"],
            "ship": cfg["ship"],
            "x": spacing * (pid + 1) - SHIP_W / 2,
            "y": ROWS - 3,
            "hp": 10, "mhp": 10,
            "score": 0, "kills": 0,
            "alive": True,
            "last_fire": 0,
            "fire_cd": 0.15,
            "pw": None, "pw_timer": 0,
            "combo": 0, "last_kill": 0,
            "ammo": 7, "max_ammo": 7, "last_reload": 0,
        }
        self.players.append(p)
        self.player_inputs[pid] = {"l": False, "r": False, "f": False}
        return pid

    def remove_player(self, pid):
        if pid < len(self.players):
            self.players[pid]["alive"] = False
            self.players[pid]["hp"] = 0

    def reposition_players(self):
        alive = [p for p in self.players if True]  # all players get positions
        n = len(alive)
        if n == 0:
            return
        spacing = COLS / (n + 1)
        for i, p in enumerate(alive):
            p["x"] = spacing * (i + 1) - SHIP_W / 2

    def start_countdown(self):
        self.state = "countdown"
        self.countdown_start = time.time()
        self.countdown_num = 3
        self.wave = 0
        for p in self.players:
            p["score"] = 0
            p["kills"] = 0
            p["hp"] = p["mhp"]
            p["alive"] = True
            p["pw"] = None
            p["combo"] = 0
        self.bullets = []
        self.invaders = []
        self.enemy_bullets = []
        self.bonuses = []
        self.explosions = []
        self.reposition_players()

    def start_wave(self):
        self.wave += 1
        self.state = "playing"
        self.bullets = []
        self.invaders = []
        self.enemy_bullets = []
        self.bonuses = []
        self.last_enemy_shot = time.time()
        self.invaders_to_spawn = 15 + self.wave * 8
        self.spawn_interval = max(0.15, 0.6 - self.wave * 0.06)
        self.spawn_timer = time.time()
        self.reposition_players()
        for p in self.players:
            p["combo"] = 0
            if p["hp"] <= 0:
                p["alive"] = False
        self.pending_sounds.append("wave_start")

    def spawn_invader(self):
        sprite = random.choice(SPRITES_POOL)
        row_type = random.randint(0, 2)
        x = 2 + random.random() * (COLS - 6)
        base_speed = 0.02 + self.wave * 0.005
        speed = base_speed + random.random() * 0.02
        wobble = (random.random() - 0.5) * 0.05
        colors = ["white", "cyan", "yellow"]
        points = [30, 20, 10]
        self.invaders.append({
            "x": x, "y": -1,
            "sp": sprite,
            "hp": 1 + self.wave // 3,
            "mhp": 1 + self.wave // 3,
            "pts": points[row_type],
            "speed": speed,
            "wobble": wobble,
            "wphase": random.random() * math.pi * 2,
            "color": colors[row_type],
            "active": True,
        })

    def tick(self, dt):
        t = time.time()

        if self.state == "countdown":
            elapsed = t - self.countdown_start
            new_num = 3 - int(elapsed)
            if new_num != self.countdown_num and new_num >= 0:
                self.countdown_num = new_num
                self.pending_sounds.append("countdown" if new_num > 0 else "countdown_go")
            if elapsed >= 3.5:
                self.start_wave()
            return

        if self.state == "wave_end":
            if t - self.wave_end_time >= 3:
                if self.wave >= TOTAL_WAVES or all(not p["alive"] for p in self.players):
                    self.state = "results"
                    self.pending_sounds.append("game_over")
                else:
                    self.start_wave()
            return

        if self.state != "playing":
            return

        # Player movement and firing
        for p in self.players:
            if not p["alive"]:
                continue
            inp = self.player_inputs.get(p["id"], {})
            if inp.get("l"):
                p["x"] = max(0, p["x"] - 0.45 * dt * 60)
            if inp.get("r"):
                p["x"] = min(COLS - SHIP_W - 1, p["x"] + 0.45 * dt * 60)

            # Powerup expiry
            if p["pw"] and t > p["pw_timer"]:
                p["pw"] = None

            cd = 0.06 if p["pw"] == "rapid" else p["fire_cd"]
            reload_interval = cd * 1.67

            # Magazine reload
            if p["ammo"] < p["max_ammo"] and t - p["last_reload"] >= reload_interval:
                p["ammo"] += 1
                p["last_reload"] = t

            # Fire (requires ammo)
            if inp.get("f") and p["ammo"] > 0 and t - p["last_fire"] >= cd:
                bx = round(p["x"]) + SHIP_W // 2
                self.bullets.append({"x": bx, "y": p["y"] - 1, "owner": p["id"], "color": p["color"]})
                self.pending_sounds.append("shoot")
                p["last_fire"] = t
                p["ammo"] -= 1
                if p["ammo"] < p["max_ammo"] and p["last_reload"] < t - reload_interval:
                    p["last_reload"] = t

        # Spawn invaders
        if self.invaders_to_spawn > 0 and t - self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = t
            self.spawn_invader()
            self.invaders_to_spawn -= 1

        # Move bullets
        self.bullets = [b for b in self.bullets if self._move_bullet(b, dt)]

        # Move invaders
        for inv in self.invaders:
            if not inv["active"]:
                continue
            inv["y"] += inv["speed"] * dt * 60
            inv["wphase"] += 0.1 * dt * 60
            inv["x"] += math.sin(inv["wphase"]) * inv["wobble"] * dt * 60
            inv["x"] = max(0, min(COLS - INV_W, inv["x"]))

        # Move bonuses
        self.bonuses = [bd for bd in self.bonuses if self._move_bonus(bd, dt)]

        # Invader shooting (random, not aimed)
        shot_interval = max(0.3, 1.2 - self.wave * 0.1)
        if t - self.last_enemy_shot >= shot_interval:
            self.last_enemy_shot = t
            shooters = [inv for inv in self.invaders if inv["active"] and 2 < inv["y"] < ROWS - 5]
            if shooters:
                shooter = random.choice(shooters)
                self.enemy_bullets.append({
                    "x": round(shooter["x"]) + INV_W // 2,
                    "y": shooter["y"] + 1,
                })

        # Move enemy bullets down
        self.enemy_bullets = [b for b in self.enemy_bullets if self._move_enemy_bullet(b, dt)]

        # Enemy bullets vs invaders (friendly fire!)
        for bi in range(len(self.enemy_bullets) - 1, -1, -1):
            if bi >= len(self.enemy_bullets):
                continue
            b = self.enemy_bullets[bi]
            for inv in self.invaders:
                if not inv["active"]:
                    continue
                ix, iy = round(inv["x"]), round(inv["y"])
                by = round(b["y"])
                if b["x"] >= ix and b["x"] <= ix + INV_W and by >= iy - 1 and by <= iy:
                    inv["hp"] -= 1
                    self.enemy_bullets.pop(bi)
                    if inv["hp"] <= 0:
                        inv["active"] = False
                        self.explosions.append({"x": ix, "y": iy, "f": 0, "color": "red"})
                        self.pending_sounds.append("kill")
                    break

        # Enemy bullets vs players
        for bi in range(len(self.enemy_bullets) - 1, -1, -1):
            if bi >= len(self.enemy_bullets):
                continue
            b = self.enemy_bullets[bi]
            for p in self.players:
                if not p["alive"]:
                    continue
                px = round(p["x"])
                by = round(b["y"])
                if by >= p["y"] - 1 and by <= p["y"] and b["x"] >= px and b["x"] <= px + SHIP_W:
                    p["hp"] -= 3
                    self.explosions.append({"x": px, "y": p["y"], "f": 0, "color": "red"})
                    self.pending_sounds.append("player_hit")
                    self.enemy_bullets.pop(bi)
                    if p["hp"] <= 0:
                        p["hp"] = 0
                        p["alive"] = False
                    break

        # Explosions
        self.explosions = [e for e in self.explosions if self._tick_explosion(e)]

        # Collision: bullets vs invaders
        for bi in range(len(self.bullets) - 1, -1, -1):
            if bi >= len(self.bullets):
                continue
            b = self.bullets[bi]
            for inv in self.invaders:
                if not inv["active"]:
                    continue
                ix, iy = round(inv["x"]), round(inv["y"])
                by = round(b["y"])
                if b["x"] >= ix and b["x"] <= ix + INV_W and by >= iy - 1 and by <= iy:
                    inv["hp"] -= 1
                    self.bullets.pop(bi)
                    if inv["hp"] <= 0:
                        inv["active"] = False
                        p = self.players[b["owner"]]
                        pts = inv["pts"]
                        # Combo
                        if t - p["last_kill"] < 1.5:
                            p["combo"] = min(p["combo"] + 1, 10)
                        else:
                            p["combo"] = 1
                        p["last_kill"] = t
                        pts *= 2 if p["pw"] == "double" else 1
                        pts += (p["combo"] - 1) * 5
                        # Steal
                        if p["pw"] == "steal":
                            richest = max((op for op in self.players if op["id"] != p["id"] and op["alive"]), key=lambda x: x["score"], default=None)
                            if richest and richest["score"] > 0:
                                stolen = max(1, int(richest["score"] * 0.03))
                                richest["score"] -= stolen
                                pts += stolen
                                self.pending_sounds.append("steal")
                        p["score"] += pts
                        p["kills"] += 1
                        self.explosions.append({"x": ix, "y": iy, "f": 0, "color": p["color"]})
                        self.pending_sounds.append("kill")
                        # Random bonus
                        if random.random() < 0.12:
                            bt = random.choice(BONUS_TYPES)
                            self.bonuses.append({"x": ix + INV_W // 2, "y": iy, "char": bt["char"], "color": bt["color"], "effect": bt["effect"]})
                            self.pending_sounds.append("bonus_drop")
                    break

        # Collision: bonuses vs players
        for bi in range(len(self.bonuses) - 1, -1, -1):
            if bi >= len(self.bonuses):
                continue
            bd = self.bonuses[bi]
            for p in self.players:
                if not p["alive"]:
                    continue
                px = round(p["x"])
                bdy = round(bd["y"])
                if bdy >= p["y"] - 1 and bdy <= p["y"] and bd["x"] >= px and bd["x"] <= px + SHIP_W:
                    if bd["effect"] == "hp":
                        p["hp"] = min(p["mhp"], p["hp"] + 3)
                    else:
                        p["pw"] = bd["effect"]
                        p["pw_timer"] = t + 6
                    self.pending_sounds.append("bonus_grab")
                    self.bonuses.pop(bi)
                    break

        # Invaders reaching bottom
        for inv in self.invaders:
            if not inv["active"]:
                continue
            if inv["y"] >= ROWS - 2:
                inv["active"] = False
                closest = min((p for p in self.players if p["alive"]), key=lambda p: abs(p["x"] + SHIP_W / 2 - inv["x"] - INV_W / 2), default=None)
                if closest:
                    closest["hp"] -= 2
                    self.explosions.append({"x": round(closest["x"]), "y": closest["y"], "f": 0, "color": "red"})
                    self.pending_sounds.append("player_hit")
                    if closest["hp"] <= 0:
                        closest["hp"] = 0
                        closest["alive"] = False

        # Clean dead invaders
        self.invaders = [inv for inv in self.invaders if inv["active"] and inv["y"] < ROWS]

        # Wave end check
        if self.invaders_to_spawn <= 0 and not any(inv["active"] for inv in self.invaders):
            self.state = "wave_end"
            self.wave_end_time = t
            self.pending_sounds.append("round_end")

        # All players dead
        if all(not p["alive"] for p in self.players):
            self.state = "wave_end"
            self.wave_end_time = t

    def _move_bullet(self, b, dt):
        b["y"] -= 0.6 * dt * 60
        return b["y"] >= 0

    def _move_enemy_bullet(self, b, dt):
        b["y"] += 0.25 * dt * 60
        return b["y"] < ROWS

    def _move_bonus(self, bd, dt):
        bd["y"] += 0.15 * dt * 60
        return bd["y"] < ROWS

    def _tick_explosion(self, e):
        e["f"] += 1
        return e["f"] < 8

    def snapshot(self):
        snap = {
            "t": "state",
            "st": self.state,
            "wave": self.wave,
            "tw": TOTAL_WAVES,
            "players": [{
                "id": p["id"], "name": p["name"], "color": p["color"],
                "ship": p["ship"],
                "x": round(p["x"], 1), "y": p["y"],
                "hp": p["hp"], "mhp": p["mhp"],
                "score": p["score"], "kills": p["kills"],
                "alive": p["alive"],
                "pw": p["pw"], "combo": p["combo"],
                "last_kill": round(p.get("last_kill", 0), 1),
                "ammo": p["ammo"], "max_ammo": p["max_ammo"],
            } for p in self.players],
            "invaders": [{
                "x": round(inv["x"], 1), "y": round(inv["y"], 1),
                "sp": inv["sp"], "hp": inv["hp"], "mhp": inv["mhp"],
                "color": inv["color"],
            } for inv in self.invaders if inv["active"]],
            "bullets": [{"x": b["x"], "y": round(b["y"], 1), "owner": b["owner"], "color": b["color"]} for b in self.bullets],
            "ebullets": [{"x": b["x"], "y": round(b["y"], 1)} for b in self.enemy_bullets],
            "bonuses": [{"x": bd["x"], "y": round(bd["y"], 1), "char": bd["char"], "color": bd["color"]} for bd in self.bonuses],
            "explosions": [{"x": e["x"], "y": e["y"], "f": e["f"], "color": e["color"]} for e in self.explosions],
            "snd": self.pending_sounds[:],
        }
        self.pending_sounds.clear()
        return snap


# ─── Renderer ─────────────────────────────────────────────────────────────────

COLOR_MAP = {
    "green": 1, "white": 2, "cyan": 3, "yellow": 4,
    "red": 5, "magenta": 6, "dim": 7, "orange": 4,
}


class Renderer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
        curses.init_pair(7, 8 if curses.COLORS > 8 else curses.COLOR_WHITE, -1)
        self.h, self.w = stdscr.getmaxyx()

    def _attr(self, color_name, bold=False):
        pair = COLOR_MAP.get(color_name, 2)
        a = curses.color_pair(pair)
        if bold:
            a |= curses.A_BOLD
        return a

    def _put(self, y, x, s, attr=0):
        try:
            if 0 <= y < self.h and x < self.w:
                ml = self.w - x - 1
                if ml > 0:
                    self.stdscr.addstr(y, max(0, x), s[:ml], attr)
        except curses.error:
            pass

    def _put_centered(self, y, s, attr=0):
        self._put(y, max(0, self.w // 2 - len(s) // 2), s, attr)

    def draw_lobby(self, player_names, msg):
        self.stdscr.erase()
        self._put_centered(2, "SPACEBASHERS", self._attr("green", True))
        self._put_centered(3, "Hungry Hungry Hippos Edition", self._attr("magenta", True))
        self._put_centered(6, "Players:", self._attr("white", True))
        for i, name in enumerate(player_names):
            cfg = PLAYER_CONFIGS[i] if i < len(PLAYER_CONFIGS) else PLAYER_CONFIGS[0]
            self._put_centered(8 + i, f"  {name}  ", self._attr(cfg["color"], True))
        self._put_centered(14, msg, self._attr("yellow"))
        self._put_centered(16, "M: Toggle Sound", self._attr("dim"))
        self.stdscr.refresh()

    def draw_state(self, snap, my_id):
        self.stdscr.erase()
        self.h, self.w = self.stdscr.getmaxyx()
        st = snap["st"]

        if st in ("playing", "wave_end", "results"):
            self._draw_hud(snap)
            self._draw_invaders(snap)
            self._draw_bonuses(snap)
            self._draw_players(snap, my_id)
            self._draw_bullets(snap)
            self._draw_explosions(snap)

        if st == "countdown":
            self._draw_players_preview(snap)
            elapsed = time.time()  # we use countdown_num from snap
            cn = snap.get("cn", 0)
            if cn > 0:
                self._put_centered(ROWS // 2, str(cn), self._attr("white", True))
            else:
                self._put_centered(ROWS // 2, "GO!", self._attr("yellow", True))
            self._put_centered(ROWS // 2 + 2, f"Wave {snap['wave'] + 1} of {snap['tw']}", self._attr("dim"))

        if st == "wave_end":
            self._draw_wave_end(snap)

        if st == "results":
            self._draw_results(snap)

        self.stdscr.refresh()

    def _draw_hud(self, snap):
        players = snap["players"]
        n = len(players)
        if n == 0:
            return
        seg = self.w // n
        for i, p in enumerate(players):
            sx = i * seg + 1
            info = f"{p['name']}: {p['score']}"
            self._put(0, sx, info, self._attr(p["color"] if p["alive"] else "dim", True))
            filled = max(0, round((p["hp"] / max(1, p["mhp"])) * 6))
            hp_bar = "\u2588" * filled + "\u2591" * (6 - filled)
            hp_col = "green" if p["hp"] > 6 else "yellow" if p["hp"] > 3 else "red"
            self._put(0, sx + len(info) + 1, "[", self._attr("dim"))
            self._put(0, sx + len(info) + 2, hp_bar, self._attr(hp_col if p["alive"] else "dim"))
            self._put(0, sx + len(info) + 8, "]", self._attr("dim"))
            if p.get("pw"):
                labels = {"double": "x2", "rapid": "!!", "steal": "$$"}
                self._put(0, sx + len(info) + 10, labels.get(p["pw"], ""), self._attr("magenta", True))
            if p.get("combo", 0) > 1:
                self._put(0, sx + len(info) + 13, f"{p['combo']}x", self._attr("yellow", True))

        wave_info = f"Wave {snap['wave']}/{snap['tw']}"
        snd = "ON" if sfx.enabled else "OFF"
        ri = f"{wave_info}  Snd:{snd}"
        self._put(0, max(0, self.w - len(ri) - 2), ri, self._attr("dim"))
        self._put(1, 0, "\u2500" * (self.w - 1), self._attr("dim"))

    def _draw_invaders(self, snap):
        for inv in snap.get("invaders", []):
            ix, iy = round(inv["x"]), round(inv["y"])
            if iy < 1 or iy >= ROWS:
                continue
            col = "red" if inv["hp"] < inv["mhp"] and inv["hp"] <= 1 else inv["color"]
            self._put(iy, ix, inv["sp"], self._attr(col, inv["hp"] == inv["mhp"]))
            if inv["mhp"] > 1:
                pips = "." * inv["hp"]
                self._put(iy - 1, ix, pips, self._attr("dim"))

    def _draw_bonuses(self, snap):
        pulse = math.sin(time.time() * 8) > 0
        for bd in snap.get("bonuses", []):
            col = bd["color"] if pulse else "white"
            self._put(round(bd["y"]), round(bd["x"]), bd["char"], self._attr(col, True))

    def _draw_players(self, snap, my_id):
        t = time.time()
        for p in snap.get("players", []):
            px, py = round(p["x"]), p["y"]
            if not p["alive"]:
                self._put(py, px, "XXXXX", self._attr("dim"))
                continue
            attr = self._attr(p["color"], True)
            # Flash on powerup
            if p.get("pw") and math.sin(t * 12) > 0:
                attr = self._attr("white", True)
            # Highlight own ship
            if p["id"] == my_id:
                self._put(py + 1, px + 1, f"[{p['name']}]", self._attr(p["color"]))
            self._put(py, px, p["ship"], attr)
            # Ammo pips
            ammo = p.get("ammo", 7)
            max_ammo = p.get("max_ammo", 7)
            pips = "|" * ammo + "." * (max_ammo - ammo)
            ammo_col = p["color"] if ammo > 3 else "yellow" if ammo > 1 else "red"
            self._put(py + 1, px - 1, pips, self._attr(ammo_col if p["alive"] else "dim"))

    def _draw_bullets(self, snap):
        for b in snap.get("bullets", []):
            self._put(round(b["y"]), round(b["x"]), "|", self._attr(b["color"], True))
        for b in snap.get("ebullets", []):
            self._put(round(b["y"]), round(b["x"]), "!", self._attr("red", True))

    def _draw_explosions(self, snap):
        boom = ["*", "\\*/", " . "]
        for e in snap.get("explosions", []):
            f = min(e["f"] // 2, len(boom) - 1)
            self._put(e["y"], e["x"], boom[f], self._attr(e.get("color", "red"), True))

    def _draw_players_preview(self, snap):
        for p in snap.get("players", []):
            self._put(p["y"], round(p["x"]), p["ship"], self._attr(p["color"], True))
            self._put(p["y"] + 1, round(p["x"]) + 1, p["name"], self._attr(p["color"]))

    def _draw_wave_end(self, snap):
        y = ROWS // 2 - 2
        is_final = snap["wave"] >= snap["tw"] or all(not p["alive"] for p in snap["players"])
        msg = "FINAL ROUND COMPLETE!" if is_final else f"Wave {snap['wave']} Complete!"
        self._put_centered(y, msg, self._attr("yellow", True))
        ranked = sorted(snap["players"], key=lambda p: p["score"], reverse=True)
        for i, p in enumerate(ranked):
            medal = ">> " if i == 0 else "   "
            line = f"{medal}{p['name']}: {p['score']} ({p['kills']} kills)"
            self._put_centered(y + 2 + i, line, self._attr(p["color"], i == 0))

    def _draw_results(self, snap):
        y = ROWS // 2 - 6
        self._put_centered(y, "GAME OVER", self._attr("red", True))
        ranked = sorted(snap["players"], key=lambda p: p["score"], reverse=True)
        if ranked:
            self._put_centered(y + 2, f"{ranked[0]['name']} WINS!", self._attr(ranked[0]["color"], True))
        self._put_centered(y + 4, "FINAL SCORES", self._attr("white", True))
        self._put(y + 5, max(0, self.w // 2 - 18), "\u2500" * 36, self._attr("dim"))
        ranks = ["1st", "2nd", "3rd", "4th"]
        top_score = max((p["score"] for p in ranked), default=1) or 1
        for i, p in enumerate(ranked):
            bar_len = max(1, round(p["score"] / top_score * 16))
            bar = "\u2588" * bar_len
            line = f" {ranks[i]}  {p['name']}  {str(p['score']).rjust(6)}  {bar}  ({p['kills']} kills)"
            self._put_centered(y + 6 + i * 2, line, self._attr(p["color"], i == 0))
        self._put_centered(y + 6 + len(ranked) * 2 + 1, "SPACE: Rematch  |  Q: Quit", self._attr("yellow"))


# ─── Host Server ──────────────────────────────────────────────────────────────

class HostServer:
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.game = GameState()
        self.clients = {}  # pid -> {"sock", "buf", "lock"}
        self.clients_lock = threading.Lock()
        self.running = True
        self.latest_snap = None
        self.local_input = {"l": False, "r": False, "f": False}
        self.my_id = self.game.add_player("Host")

    def run(self, stdscr):
        renderer = Renderer(stdscr)

        # Print host IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "unknown"

        # Start server socket
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(4)
        srv.settimeout(1)

        # Start threads
        accept_t = threading.Thread(target=self._accept_loop, args=(srv,), daemon=True)
        accept_t.start()
        game_t = threading.Thread(target=self._game_loop, daemon=True)
        game_t.start()

        lobby_msg = f"Waiting... Join: python3 netplay.py join {local_ip}"

        try:
            while self.running:
                # Drain all keys this frame -- set flags if any relevant key seen
                frame_input = {"l": False, "r": False, "f": False}
                key = stdscr.getch()
                while key != -1:
                    if key == ord("q"):
                        self.running = False
                        return
                    elif key == ord("m"):
                        sfx.toggle()
                    elif key == ord(" ") or key == ord("\n"):
                        if self.game.state == "lobby" and len(self.game.players) >= 1:
                            self.game.start_countdown()
                        elif self.game.state == "results":
                            self.game.start_countdown()
                        else:
                            frame_input["f"] = True
                    elif key == curses.KEY_LEFT or key == ord("a"):
                        frame_input["l"] = True
                    elif key == curses.KEY_RIGHT or key == ord("d"):
                        frame_input["r"] = True
                    elif key == ord("w") or key == curses.KEY_UP:
                        frame_input["f"] = True
                    key = stdscr.getch()

                self.game.player_inputs[self.my_id] = frame_input

                # Draw
                if self.game.state == "lobby":
                    names = [p["name"] for p in self.game.players]
                    need = "Press SPACE to start!" if len(names) >= 1 else "Waiting for players..."
                    renderer.draw_lobby(names, f"{lobby_msg}\n{need}")
                elif self.latest_snap:
                    renderer.draw_state(self.latest_snap, self.my_id)
                    for snd in self.latest_snap.get("snd", []):
                        sfx.play(snd)

                curses.napms(16)
        finally:
            self.running = False
            srv.close()

    def _accept_loop(self, srv):
        while self.running:
            try:
                conn, addr = srv.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(2)
                buf = bytearray()
                msgs = recv_msgs(conn, buf, timeout=2)
                if msgs is None or not msgs:
                    conn.close()
                    continue
                msg = msgs[0]
                if msg.get("t") != "join":
                    conn.close()
                    continue
                if self.game.state != "lobby":
                    send_msg(conn, {"t": "kicked", "reason": "Game in progress"})
                    conn.close()
                    continue
                name = msg.get("name", "")
                pid = self.game.add_player(name)
                if pid is None:
                    send_msg(conn, {"t": "kicked", "reason": "Game full"})
                    conn.close()
                    continue
                conn.settimeout(None)
                send_msg(conn, {"t": "assign", "id": pid, "name": self.game.players[pid]["name"]})
                with self.clients_lock:
                    self.clients[pid] = {"sock": conn, "buf": bytearray(), "lock": threading.Lock()}
                # Start receiver thread
                t = threading.Thread(target=self._client_recv, args=(pid,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _client_recv(self, pid):
        while self.running:
            with self.clients_lock:
                client = self.clients.get(pid)
            if not client:
                break
            msgs = recv_msgs(client["sock"], client["buf"], timeout=0.05)
            if msgs is None:
                # Disconnected
                self.game.remove_player(pid)
                with self.clients_lock:
                    self.clients.pop(pid, None)
                break
            for msg in msgs:
                if msg.get("t") == "input":
                    self.game.player_inputs[pid] = {"l": msg.get("l", False), "r": msg.get("r", False), "f": msg.get("f", False)}
                elif msg.get("t") == "quit":
                    self.game.remove_player(pid)
                    with self.clients_lock:
                        self.clients.pop(pid, None)
                    return

    def _game_loop(self):
        last_tick = time.time()
        snap_accum = 0
        while self.running:
            now = time.time()
            dt = min(now - last_tick, 0.05)  # cap dt
            last_tick = now

            self.game.tick(dt)
            snap_accum += dt

            if snap_accum >= 1.0 / SNAPSHOT_RATE:
                snap_accum = 0
                snap = self.game.snapshot()
                # Add countdown number
                if self.game.state == "countdown":
                    snap["cn"] = self.game.countdown_num
                self.latest_snap = snap
                self._broadcast(snap)

            elapsed = time.time() - now
            sleep_time = (1.0 / TICK_RATE) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _broadcast(self, msg):
        with self.clients_lock:
            dead = []
            for pid, client in self.clients.items():
                if not send_msg(client["sock"], msg):
                    dead.append(pid)
            for pid in dead:
                self.game.remove_player(pid)
                self.clients.pop(pid, None)


# ─── Client ───────────────────────────────────────────────────────────────────

class NetClient:
    def __init__(self, host_ip, port=DEFAULT_PORT, name=""):
        self.host_ip = host_ip
        self.port = port
        self.name = name
        self.my_id = -1
        self.latest_snap = None
        self.snap_lock = threading.Lock()
        self.local_input = {"l": False, "r": False, "f": False}
        self.running = True
        self.sock = None
        self.connected = False
        self.error_msg = ""

    def run(self, stdscr):
        renderer = Renderer(stdscr)

        # Connect
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.settimeout(5)
            self.sock.connect((self.host_ip, self.port))
            send_msg(self.sock, {"t": "join", "name": self.name})
            self.sock.settimeout(5)
            buf = bytearray()
            msgs = recv_msgs(self.sock, buf, timeout=5)
            if msgs is None or not msgs:
                self.error_msg = "No response from host"
                self._show_error(stdscr, renderer)
                return
            msg = msgs[0]
            if msg.get("t") == "kicked":
                self.error_msg = msg.get("reason", "Kicked")
                self._show_error(stdscr, renderer)
                return
            if msg.get("t") == "assign":
                self.my_id = msg["id"]
                self.name = msg.get("name", self.name)
            self.sock.settimeout(None)
            self.connected = True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            self.error_msg = f"Cannot connect to {self.host_ip}:{self.port} - {e}"
            self._show_error(stdscr, renderer)
            return

        # Start network thread
        net_t = threading.Thread(target=self._network_loop, args=(buf,), daemon=True)
        net_t.start()

        try:
            while self.running:
                key = stdscr.getch()
                input_frame = {"l": False, "r": False, "f": False}
                while key != -1:
                    if key == ord("q"):
                        send_msg(self.sock, {"t": "quit"})
                        self.running = False
                        return
                    elif key == ord("m"):
                        sfx.toggle()
                    elif key == curses.KEY_LEFT or key == ord("a"):
                        input_frame["l"] = True
                    elif key == curses.KEY_RIGHT or key == ord("d"):
                        input_frame["r"] = True
                    elif key == ord("w") or key == curses.KEY_UP or key == ord(" "):
                        input_frame["f"] = True
                    key = stdscr.getch()

                self.local_input = input_frame

                with self.snap_lock:
                    snap = self.latest_snap

                if snap:
                    renderer.draw_state(snap, self.my_id)
                    for snd in snap.get("snd", []):
                        sfx.play(snd)
                else:
                    renderer.draw_lobby([self.name], f"Connected as {self.name}. Waiting for host...")

                if self.error_msg:
                    self._show_error(stdscr, renderer)
                    return

                curses.napms(16)
        finally:
            self.running = False
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass

    def _network_loop(self, buf):
        last_send = 0
        while self.running:
            t = time.time()
            # Send input at 20Hz
            if t - last_send >= 0.05:
                inp = self.local_input
                if not send_msg(self.sock, {"t": "input", "l": inp["l"], "r": inp["r"], "f": inp["f"]}):
                    self.error_msg = "Disconnected from host"
                    self.running = False
                    return
                last_send = t

            # Receive
            msgs = recv_msgs(self.sock, buf, timeout=0.01)
            if msgs is None:
                self.error_msg = "Host disconnected"
                self.running = False
                return
            for msg in msgs:
                if msg.get("t") == "state":
                    with self.snap_lock:
                        self.latest_snap = msg
                elif msg.get("t") == "kicked":
                    self.error_msg = msg.get("reason", "Kicked")
                    self.running = False
                    return

    def _show_error(self, stdscr, renderer):
        stdscr.nodelay(False)
        stdscr.erase()
        renderer._put_centered(ROWS // 2, self.error_msg, renderer._attr("red", True))
        renderer._put_centered(ROWS // 2 + 2, "Press any key to exit", renderer._attr("dim"))
        stdscr.refresh()
        stdscr.getch()


# ─── Main ─────────────────────────────────────────────────────────────────────

def print_usage():
    print("SpaceBashers Network Multiplayer")
    print()
    print("Usage:")
    print("  python3 netplay.py host [--port 7777]")
    print("  python3 netplay.py join <ip> [--port 7777] [--name YourName]")


def parse_args():
    args = sys.argv[1:]
    if not args or args[0] not in ("host", "join"):
        print_usage()
        sys.exit(1)

    mode = args[0]
    port = DEFAULT_PORT
    name = ""
    host_ip = ""

    i = 1
    if mode == "join":
        if len(args) < 2:
            print_usage()
            sys.exit(1)
        host_ip = args[1]
        i = 2

    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2
        else:
            i += 1

    return mode, host_ip, port, name


if __name__ == "__main__":
    mode, host_ip, port, name = parse_args()

    if mode == "host":
        def run_host(stdscr):
            HostServer(port).run(stdscr)
        try:
            curses.wrapper(run_host)
        except (KeyboardInterrupt, SystemExit):
            pass
    else:
        def run_client(stdscr):
            NetClient(host_ip, port, name).run(stdscr)
        try:
            curses.wrapper(run_client)
        except (KeyboardInterrupt, SystemExit):
            pass
    sfx.cleanup()
