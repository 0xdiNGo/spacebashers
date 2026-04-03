#!/usr/bin/env python3
"""SpaceBashers - A CLI Space Invaders game using curses."""

import curses
import time
import random
import struct
import math
import wave
import tempfile
import os
import subprocess
import threading
import atexit

# Game constants
PLAYER_SHIP = " /^\\ "
PLAYER_SHIP_W = 5
BULLET_CHAR = "|"
ENEMY_BULLET = "!"
INVADER_ROWS = [
    ["(@@)", "(@@)", "(@@)", "(@@)", "(@@)", "(@@)", "(@@)", "(@@)"],
    ["<**>", "<**>", "<**>", "<**>", "<**>", "<**>", "<**>", "<**>"],
    ["<**>", "<**>", "<**>", "<**>", "<**>", "<**>", "<**>", "<**>"],
    ["/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\"],
    ["/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\", "/\\/\\"],
]
INVADER_W = 4
INVADER_SPACING_X = 6
INVADER_SPACING_Y = 2
BARRIER_CHAR = "#"
BARRIER_WIDTH = 8
BARRIER_HEIGHT = 3
NUM_BARRIERS = 4


class SoundEngine:
    """Generates retro sound effects as WAV files and plays them via afplay."""

    def __init__(self):
        self._tmpdir = tempfile.mkdtemp(prefix="spacebashers_snd_")
        self._channels = {}  # name -> Popen, one process per sound
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

    def _tone(self, freq, duration, volume=0.5, sample_rate=22050, decay=True):
        n = int(sample_rate * duration)
        samples = []
        for i in range(n):
            t = i / sample_rate
            env = 1.0 - (i / n) if decay else 1.0
            val = math.sin(2 * math.pi * freq * t) * volume * env
            samples.append(max(-32767, min(32767, int(val * 32767))))
        return samples

    def _noise(self, duration, volume=0.4, sample_rate=22050):
        n = int(sample_rate * duration)
        samples = []
        for i in range(n):
            env = 1.0 - (i / n)
            val = random.uniform(-1, 1) * volume * env
            samples.append(max(-32767, min(32767, int(val * 32767))))
        return samples

    def _generate_all(self):
        # Shoot: short high-pitched zap
        s = self._tone(880, 0.08, 0.3)
        s += self._tone(440, 0.04, 0.2)
        self._make_wav("shoot", s)

        # Invader killed: descending tone + noise burst
        s = self._tone(600, 0.05, 0.3, decay=False)
        s += self._tone(300, 0.05, 0.3, decay=False)
        s += self._noise(0.06, 0.3)
        self._make_wav("invader_kill", s)

        # Player hit: low explosion
        s = self._noise(0.3, 0.5)
        mixed = self._tone(100, 0.3, 0.3)
        for i in range(min(len(s), len(mixed))):
            s[i] = max(-32767, min(32767, s[i] + mixed[i]))
        self._make_wav("player_hit", s)

        # Mystery ship appear: oscillating eerie tone
        s = []
        sr = 22050
        dur = 0.4
        for i in range(int(sr * dur)):
            t = i / sr
            freq = 200 + 100 * math.sin(2 * math.pi * 6 * t)
            val = math.sin(2 * math.pi * freq * t) * 0.25
            s.append(max(-32767, min(32767, int(val * 32767))))
        self._make_wav("mystery", s)

        # Mystery ship hit: big reward sound
        s = self._tone(523, 0.08, 0.3, decay=False)
        s += self._tone(659, 0.08, 0.3, decay=False)
        s += self._tone(784, 0.08, 0.3, decay=False)
        s += self._tone(1047, 0.15, 0.3)
        self._make_wav("mystery_hit", s)

        # Invader march step: classic low thump
        s = self._tone(80, 0.06, 0.25, decay=False)
        s += self._tone(60, 0.04, 0.2)
        self._make_wav("march", s)

        # Game over: sad descending tones
        s = self._tone(440, 0.2, 0.3, decay=False)
        s += self._tone(370, 0.2, 0.3, decay=False)
        s += self._tone(330, 0.2, 0.3, decay=False)
        s += self._tone(262, 0.4, 0.3)
        self._make_wav("game_over", s)

        # Level up: ascending fanfare
        s = self._tone(523, 0.1, 0.3, decay=False)
        s += self._tone(659, 0.1, 0.3, decay=False)
        s += self._tone(784, 0.1, 0.3, decay=False)
        s += self._tone(1047, 0.3, 0.3)
        self._make_wav("level_up", s)

    def play(self, name):
        if not self._enabled or name not in self._sounds:
            return
        # Each sound name is its own channel — kill previous if still running
        prev = self._channels.get(name)
        if prev and prev.poll() is None:
            # Sound still playing — for short sfx just skip, don't pile up
            if name == "march":
                return  # march fires very often, just skip if still playing
            try:
                prev.kill()
            except Exception:
                pass
        try:
            p = subprocess.Popen(
                ["afplay", self._sounds[name]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
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


# Global sound engine
sfx = SoundEngine()


class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        self.h, self.w = stdscr.getmaxyx()

        # Colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # player
        curses.init_pair(2, curses.COLOR_WHITE, -1)    # invaders row 1
        curses.init_pair(3, curses.COLOR_CYAN, -1)     # invaders row 2-3
        curses.init_pair(4, curses.COLOR_YELLOW, -1)   # invaders row 4-5
        curses.init_pair(5, curses.COLOR_RED, -1)      # bullets / explosions
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # mystery ship
        curses.init_pair(7, curses.COLOR_GREEN, -1)    # barriers

        self.reset()

    def reset(self):
        self.player_x = self.w // 2 - PLAYER_SHIP_W // 2
        self.player_y = self.h - 3
        self.bullets = []
        self.enemy_bullets = []
        self.explosions = []  # (x, y, frame)
        self.score = 0
        self.hp = 10
        self.max_hp = 10
        self.level = 1
        self.game_over = False
        self.victory = False
        self.paused = False

        # Input state for simultaneous move + fire
        self.moving_left = False
        self.moving_right = False
        self.firing = False
        self.last_fire_time = 0
        self.fire_cooldown = 0.15  # seconds between shots
        self.ammo = 7
        self.max_ammo = 7
        self.last_reload = 0

        # Invader grid
        self.invaders = []
        self.invader_dir = 1  # 1 = right, -1 = left
        self.invader_speed = 0.5  # seconds between moves
        self.last_invader_move = time.time()
        self.invader_offset_x = 0
        self.invader_offset_y = 0
        self._init_invaders()

        # Mystery ship
        self.mystery_ship = None  # (x, dir)
        self.mystery_timer = time.time() + random.uniform(10, 25)

        # Barriers
        self.barriers = set()
        self._init_barriers()

        # Timing
        self.last_enemy_shot = time.time()
        self.enemy_shot_interval = 1.0

    def _init_invaders(self):
        self.invaders = []
        start_x = (self.w - (len(INVADER_ROWS[0]) * INVADER_SPACING_X)) // 2
        start_y = 3
        self.invader_base_x = start_x
        self.invader_base_y = start_y
        self.invader_offset_x = 0
        self.invader_offset_y = 0
        for r, row in enumerate(INVADER_ROWS):
            inv_row = []
            for c in range(len(row)):
                inv_row.append(True)  # alive
            self.invaders.append(inv_row)

    def _init_barriers(self):
        self.barriers = set()
        spacing = self.w // (NUM_BARRIERS + 1)
        for i in range(NUM_BARRIERS):
            bx = spacing * (i + 1) - BARRIER_WIDTH // 2
            by = self.player_y - 5
            for dy in range(BARRIER_HEIGHT):
                for dx in range(BARRIER_WIDTH):
                    # Arch shape - remove middle bottom
                    if dy == BARRIER_HEIGHT - 1 and BARRIER_WIDTH // 4 <= dx < BARRIER_WIDTH * 3 // 4:
                        continue
                    self.barriers.add((bx + dx, by + dy))

    def invader_pos(self, r, c):
        x = self.invader_base_x + c * INVADER_SPACING_X + self.invader_offset_x
        y = self.invader_base_y + r * INVADER_SPACING_Y + self.invader_offset_y
        return x, y

    def invader_color(self, r):
        if r == 0:
            return curses.color_pair(2) | curses.A_BOLD
        elif r <= 2:
            return curses.color_pair(3)
        else:
            return curses.color_pair(4)

    def invader_points(self, r):
        if r == 0:
            return 30
        elif r <= 2:
            return 20
        else:
            return 10

    def alive_count(self):
        return sum(1 for row in self.invaders for alive in row if alive)

    def run(self):
        self.show_title()
        while True:
            if self.game_over or self.victory:
                if not self.show_game_over():
                    break
                self.reset()
                continue
            self.update()
            self.draw()
            time.sleep(0.016)  # ~60fps

    def show_title(self):
        self.stdscr.clear()
        title = [
            "  ____                        ____            _                    ",
            " / ___| _ __   __ _  ___ ___ | __ )  __ _ ___| |__   ___ _ __ ___ ",
            " \\___ \\| '_ \\ / _` |/ __/ _ \\|  _ \\ / _` / __| '_ \\ / _ \\ '__/ __|",
            "  ___) | |_) | (_| | (_|  __/| |_) | (_| \\__ \\ | | |  __/ |  \\__ \\",
            " |____/| .__/ \\__,_|\\___\\___||____/ \\__,_|___/_| |_|\\___|_|  |___/",
            "       |_|                                                         ",
        ]
        cy = self.h // 2 - 6
        for i, line in enumerate(title):
            x = max(0, self.w // 2 - len(line) // 2)
            try:
                self.stdscr.addstr(cy + i, x, line[:self.w - 1], curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        instructions = [
            "",
            "← → or A/D  :  Move",
            "  SPACE      :  Fire",
            "    P        :  Pause",
            "    M        :  Toggle Sound",
            "    Q        :  Quit",
            "",
            "Press SPACE to start!",
        ]
        for i, line in enumerate(instructions):
            x = max(0, self.w // 2 - len(line) // 2)
            try:
                color = curses.color_pair(4) if i == len(instructions) - 1 else curses.color_pair(0)
                self.stdscr.addstr(cy + len(title) + i + 1, x, line, color)
            except curses.error:
                pass

        self.stdscr.refresh()
        self.stdscr.nodelay(False)
        while True:
            key = self.stdscr.getch()
            if key == ord(" "):
                break
            if key == ord("q"):
                raise SystemExit
        self.stdscr.nodelay(True)

    def show_game_over(self):
        self.stdscr.nodelay(False)
        sfx.play("level_up" if self.victory else "game_over")
        msg = "*** YOU WIN! ***" if self.victory else "*** GAME OVER ***"
        color = curses.color_pair(1) | curses.A_BOLD if self.victory else curses.color_pair(5) | curses.A_BOLD
        try:
            self.stdscr.addstr(self.h // 2, self.w // 2 - len(msg) // 2, msg, color)
            score_msg = f"Final Score: {self.score}"
            self.stdscr.addstr(self.h // 2 + 2, self.w // 2 - len(score_msg) // 2, score_msg)
            retry = "Press SPACE to play again, Q to quit"
            self.stdscr.addstr(self.h // 2 + 4, self.w // 2 - len(retry) // 2, retry, curses.color_pair(4))
        except curses.error:
            pass
        self.stdscr.refresh()
        while True:
            key = self.stdscr.getch()
            if key == ord(" "):
                return True
            if key == ord("q"):
                return False

    def update(self):
        # Drain all queued keys — track press/release state
        # Terminal can't detect key-up, so we reset directional state each
        # frame and re-set it if the key is still in the buffer.
        self.moving_left = False
        self.moving_right = False
        self.firing = False
        key = self.stdscr.getch()
        while key != -1:
            if key == curses.KEY_LEFT or key == ord("a"):
                self.moving_left = True
            elif key == curses.KEY_RIGHT or key == ord("d"):
                self.moving_right = True
            elif key == ord(" "):
                self.firing = True
            elif key == ord("p"):
                self.paused = not self.paused
            elif key == ord("m"):
                sfx.toggle()
            elif key == ord("q"):
                raise SystemExit
            key = self.stdscr.getch()

        if self.paused:
            return

        now = time.time()

        # Apply movement (works simultaneously with firing)
        if self.moving_left:
            self.player_x = max(0, self.player_x - 2)
        if self.moving_right:
            self.player_x = min(self.w - PLAYER_SHIP_W - 1, self.player_x + 2)

        # Magazine reload
        reload_interval = self.fire_cooldown * 1.67
        if self.ammo < self.max_ammo and now - self.last_reload >= reload_interval:
            self.ammo += 1
            self.last_reload = now

        # Apply firing with cooldown (requires ammo)
        if self.firing and self.ammo > 0 and now - self.last_fire_time >= self.fire_cooldown:
            bx = self.player_x + PLAYER_SHIP_W // 2
            self.bullets.append([bx, self.player_y - 1])
            sfx.play("shoot")
            self.last_fire_time = now
            self.ammo -= 1
            if self.ammo < self.max_ammo and self.last_reload < now - reload_interval:
                self.last_reload = now

        # Move bullets up
        new_bullets = []
        for b in self.bullets:
            b[1] -= 1
            if b[1] >= 0:
                new_bullets.append(b)
        self.bullets = new_bullets

        # Move enemy bullets down
        new_ebullets = []
        for b in self.enemy_bullets:
            b[1] += 1
            if b[1] < self.h:
                new_ebullets.append(b)
        self.enemy_bullets = new_ebullets

        # Update explosions
        new_exp = []
        for ex in self.explosions:
            if ex[2] < 4:
                new_exp.append((ex[0], ex[1], ex[2] + 1))
        self.explosions = new_exp

        # Move invaders
        if now - self.last_invader_move >= self.invader_speed:
            self.last_invader_move = now
            # Check boundaries
            leftmost = self.w
            rightmost = 0
            for r in range(len(self.invaders)):
                for c in range(len(self.invaders[r])):
                    if self.invaders[r][c]:
                        x, _ = self.invader_pos(r, c)
                        leftmost = min(leftmost, x)
                        rightmost = max(rightmost, x + INVADER_W)

            next_x = self.invader_offset_x + self.invader_dir * 2
            test_left = leftmost + self.invader_dir * 2
            test_right = rightmost + self.invader_dir * 2

            if test_left <= 1 or test_right >= self.w - 1:
                self.invader_offset_y += 1
                self.invader_dir *= -1
            else:
                self.invader_offset_x += self.invader_dir * 2

            sfx.play("march")

            # Speed up as invaders are destroyed
            total = len(self.invaders) * len(self.invaders[0])
            alive = self.alive_count()
            if alive > 0:
                self.invader_speed = max(0.05, 0.5 * (alive / total))

        # Enemy shooting
        if now - self.last_enemy_shot >= self.enemy_shot_interval:
            self.last_enemy_shot = now
            # Find bottom-most alive invader in each column
            shooters = []
            if self.invaders:
                for c in range(len(self.invaders[0])):
                    for r in range(len(self.invaders) - 1, -1, -1):
                        if self.invaders[r][c]:
                            shooters.append((r, c))
                            break
            if shooters:
                r, c = random.choice(shooters)
                x, y = self.invader_pos(r, c)
                self.enemy_bullets.append([x + INVADER_W // 2, y + 1])

        # Mystery ship
        if self.mystery_ship is None:
            if now >= self.mystery_timer:
                d = random.choice([-1, 1])
                sx = 0 if d == 1 else self.w - 7
                self.mystery_ship = [sx, d]
                sfx.play("mystery")
        else:
            self.mystery_ship[0] += self.mystery_ship[1]
            if self.mystery_ship[0] < -7 or self.mystery_ship[0] > self.w:
                self.mystery_ship = None
                self.mystery_timer = now + random.uniform(10, 25)

        # Collision: player bullets vs invaders
        for b in self.bullets[:]:
            hit = False
            for r in range(len(self.invaders)):
                for c in range(len(self.invaders[r])):
                    if not self.invaders[r][c]:
                        continue
                    ix, iy = self.invader_pos(r, c)
                    if ix <= b[0] <= ix + INVADER_W and b[1] == iy:
                        self.invaders[r][c] = False
                        self.score += self.invader_points(r)
                        self.explosions.append((ix, iy, 0))
                        sfx.play("invader_kill")
                        if b in self.bullets:
                            self.bullets.remove(b)
                        hit = True
                        break
                if hit:
                    break

            # Bullet vs mystery ship
            if not hit and self.mystery_ship is not None:
                mx = self.mystery_ship[0]
                if mx <= b[0] <= mx + 6 and b[1] <= 1:
                    pts = random.choice([50, 100, 150, 300])
                    self.score += pts
                    self.explosions.append((mx, 1, 0))
                    sfx.play("mystery_hit")
                    self.mystery_ship = None
                    self.mystery_timer = time.time() + random.uniform(10, 25)
                    if b in self.bullets:
                        self.bullets.remove(b)

        # Collision: bullets vs barriers
        for b in self.bullets[:]:
            bp = (b[0], b[1])
            if bp in self.barriers:
                self.barriers.discard(bp)
                if b in self.bullets:
                    self.bullets.remove(b)

        for b in self.enemy_bullets[:]:
            bp = (b[0], b[1])
            if bp in self.barriers:
                self.barriers.discard(bp)
                if b in self.enemy_bullets:
                    self.enemy_bullets.remove(b)

        # Collision: enemy bullets vs player
        for b in self.enemy_bullets[:]:
            if (self.player_y == b[1] and
                    self.player_x <= b[0] <= self.player_x + PLAYER_SHIP_W):
                self.hp -= 3
                self.enemy_bullets.remove(b)
                self.explosions.append((self.player_x, self.player_y, 0))
                sfx.play("player_hit")
                if self.hp <= 0:
                    self.hp = 0
                    self.game_over = True
                    return

        # Check invaders reaching player
        for r in range(len(self.invaders)):
            for c in range(len(self.invaders[r])):
                if self.invaders[r][c]:
                    _, iy = self.invader_pos(r, c)
                    if iy >= self.player_y - 2:
                        self.game_over = True
                        return

        # Check victory
        if self.alive_count() == 0:
            sfx.play("level_up")
            self.level += 1
            self._init_invaders()
            self.invader_speed = max(0.1, 0.5 - self.level * 0.05)
            self.enemy_shot_interval = max(0.3, 1.0 - self.level * 0.1)

    def draw(self):
        self.stdscr.erase()

        # HUD
        snd = "ON" if sfx.enabled else "OFF"
        filled = int((self.hp / self.max_hp) * 10)
        hp_bar = "█" * filled + "░" * (10 - filled)
        hud_left = f" Score: {self.score}  |  HP [{hp_bar}] {self.hp}/{self.max_hp}"
        hud_right = f"Level: {self.level}  |  Sound: {snd} "
        try:
            self.stdscr.addstr(0, 0, "─" * (self.w - 1), curses.color_pair(0))
            self.stdscr.addstr(0, 1, hud_left[:self.w // 2], curses.A_BOLD)
            # Color the HP bar based on health
            hp_start = hud_left.index("[") + 1
            if self.hp > 6:
                hp_color = curses.color_pair(1)  # green
            elif self.hp > 3:
                hp_color = curses.color_pair(4)  # yellow
            else:
                hp_color = curses.color_pair(5)  # red
            self.stdscr.addstr(0, 1 + hp_start, hp_bar, hp_color | curses.A_BOLD)
            self.stdscr.addstr(0, max(0, self.w - len(hud_right) - 1), hud_right, curses.A_BOLD)
        except curses.error:
            pass

        # Mystery ship
        if self.mystery_ship is not None:
            mx = self.mystery_ship[0]
            ship_str = "<-?->"
            self._safe_addstr(1, mx, ship_str, curses.color_pair(6) | curses.A_BOLD)

        # Invaders
        for r in range(len(self.invaders)):
            for c in range(len(self.invaders[r])):
                if self.invaders[r][c]:
                    x, y = self.invader_pos(r, c)
                    sprite = INVADER_ROWS[r][c]
                    self._safe_addstr(y, x, sprite, self.invader_color(r))

        # Barriers
        for bx, by in self.barriers:
            self._safe_addstr(by, bx, BARRIER_CHAR, curses.color_pair(7))

        # Player
        self._safe_addstr(self.player_y, self.player_x, PLAYER_SHIP, curses.color_pair(1) | curses.A_BOLD)

        # Ammo pips below ship
        ammo_pips = "|" * self.ammo + "." * (self.max_ammo - self.ammo)
        if self.ammo > 3:
            ammo_color = curses.color_pair(1)  # green
        elif self.ammo > 1:
            ammo_color = curses.color_pair(4)  # yellow
        else:
            ammo_color = curses.color_pair(5)  # red
        self._safe_addstr(self.player_y + 1, self.player_x - 1, ammo_pips, ammo_color)

        # Player bullets
        for b in self.bullets:
            self._safe_addstr(b[1], b[0], BULLET_CHAR, curses.color_pair(1) | curses.A_BOLD)

        # Enemy bullets
        for b in self.enemy_bullets:
            self._safe_addstr(b[1], b[0], ENEMY_BULLET, curses.color_pair(5) | curses.A_BOLD)

        # Explosions
        boom = ["*", "\\*/", " ' "]
        for ex in self.explosions:
            frame = min(ex[2], len(boom) - 1)
            self._safe_addstr(ex[1], ex[0], boom[frame], curses.color_pair(5) | curses.A_BOLD)

        # Pause overlay
        if self.paused:
            msg = " PAUSED - Press P to resume "
            self._safe_addstr(self.h // 2, self.w // 2 - len(msg) // 2, msg,
                              curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE)

        self.stdscr.refresh()

    def _safe_addstr(self, y, x, s, attr=0):
        try:
            if 0 <= y < self.h and x < self.w:
                max_len = self.w - x - 1
                if max_len > 0:
                    self.stdscr.addstr(y, max(0, x), s[:max_len], attr)
        except curses.error:
            pass


def main(stdscr):
    Game(stdscr).run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sfx.cleanup()
