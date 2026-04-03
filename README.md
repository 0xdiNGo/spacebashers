# SpaceBashers

A terminal Space Invaders game built with Python curses. No dependencies required.

![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue)
![macOS](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)

### [>>> PLAY IN YOUR BROWSER <<<](https://0xdingo.github.io/spacebashers/)

## Quick Start (Terminal)

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

---

## Commit Log

What follows is the unabridged development history of SpaceBashers, reconstructed from git, Jira, Slack archives, two restraining orders, and one therapist's notes (shared with written consent).

```
commit a1b2c3d
Author: diNGo <dingo@usomad.me>
Date:   Mon Jan 6 02:14:33 2021 -0500

    initial commit: how hard could space invaders be lol

 A spacebashers.py | 14 ++++++++++++++
 1 file changed, 14 insertions(+)
```

```
commit e4f5a6b
Author: diNGo <dingo@usomad.me>
Date:   Mon Jan 6 02:17:01 2021 -0500

    add game loop (print + sleep based, looks incredible)

    it flickers a little. or a lot. we'll fix it later.
```

```
commit c7d8e9f
Author: diNGo <dingo@usomad.me>
Date:   Tue Jan 7 14:30:00 2021 -0500

    we will not fix it later

    the flickering is load-bearing. if you remove the sleep(0.1)
    the invaders move at the speed of light and the game ends in
    0.003 seconds. leaving it.
```

```
commit 0a1b2c3
Author: Marcus <marcus@spacebashers.dev>
Date:   Fri Mar 14 09:12:44 2021 -0500

    RFC: propose migration to curses for terminal rendering

    see attached 47-page design document. i believe this is the
    correct path forward and i will die on this hill.
```

```
commit d4e5f6a
Author: Jennifer <jennifer@spacebashers.dev>
Date:   Fri Mar 14 09:13:02 2021 -0500

    absolutely not
```

```
commit b7c8d9e
Author: Marcus <marcus@spacebashers.dev>
Date:   Fri Mar 14 09:13:58 2021 -0500

    it's either curses or pygame and i know where you live
```

```
commit f0a1b2c
Author: Jennifer <jennifer@spacebashers.dev>
Date:   Fri Mar 14 09:15:30 2021 -0500

    fine. but i'm starting the UX research on ship sprites NOW
    and nobody is rushing me
```

```
commit 3d4e5f6
Author: Marcus <marcus@spacebashers.dev>
Date:   Sat Nov 13 23:58:01 2021 -0500

    begin curses migration

    this is going to be clean. this is going to be elegant.
    this is going to be the best terminal renderer anyone has
    ever seen. i can feel it.
```

```
commit a7b8c9d
Author: Marcus <marcus@spacebashers.dev>
Date:   Sun Nov 14 04:22:17 2021 -0500

    why does addstr crash when you write to the bottom-right cell

    spent five hours on this. turns out it's a "known behavior"
    since 1992. curses writes the character, advances the cursor
    past the screen boundary, and panics. KNOWN. BEHAVIOR.
```

```
commit e0f1a2b
Author: Marcus <marcus@spacebashers.dev>
Date:   Sun Nov 14 04:23:45 2021 -0500

    wrap everything in try/except curses.error

    i am not proud of this commit. but i am alive.
```

```
commit 2c3d4e5
Author: diNGo <dingo@usomad.me>
Date:   Mon Nov 15 10:00:12 2021 -0500

    marcus are you okay

    your last three commits were between midnight and 4am
    and the last one just says "i am alive"
```

```
commit f6a7b8c
Author: Marcus <marcus@spacebashers.dev>
Date:   Mon Nov 15 10:47:33 2021 -0500

    i have mass-resigned. addstr() is morally correct and the team
    chose addch(). i cannot be part of this. do not contact me.

    p.s. i'm keeping the YubiKey
```

```
commit 9d0e1f2
Author: diNGo <dingo@usomad.me>
Date:   Mon Nov 15 11:02:00 2021 -0500

    revoke marcus's access, he took the yubikey

    also we were using addstr the whole time. i don't know
    what he was looking at. godspeed marcus.
```

```
commit a3b4c5d
Author: Jennifer <jennifer@spacebashers.dev>
Date:   Wed May 18 16:00:00 2022 -0500

    UX research complete: ship sprite recommendation

    after 11 weeks of A/B testing across 340 participants,
    cognitive load analysis, and a focus group in denver,
    the two finalists are:

    Option A:  ^
    Option B:  /^\

    full report attached (198 pages + appendices)
```

```
commit e6f7a8b
Author: diNGo <dingo@usomad.me>
Date:   Wed May 18 16:04:22 2022 -0500

    team vote: 4-4 tie on ship sprite. deadlocked.

    jennifer is not taking this well
```

```
commit 9c0d1e2
Author: Jennifer <jennifer@spacebashers.dev>
Date:   Tue May 24 08:00:00 2022 -0500

    final ship sprite proposal: " /^\ " (with padding)

    i have published my paper "The Semiotics of ASCII Spacecraft:
    A Phenomenological Inquiry" to resolve this once and for all.

    this is also my last commit. i am mass-resigning effective
    immediately. i have lost faith in collaborative creative
    processes. i am taking the espresso machine. do not try to
    stop me.
```

```
commit f3a4b5c
Author: diNGo <dingo@usomad.me>
Date:   Tue May 24 09:30:00 2022 -0500

    she took the espresso machine. she actually took it.

    using her sprite though. it's good.
```

```
commit 6d7e8f9
Author: Tomás <tomas@spacebashers.dev>
Date:   Mon Sep 5 11:00:00 2022 -0500

    feat: add sound engine - procedural WAV generation

    custom FM synthesis generating 8 retro sound effects at runtime.
    shoot, kill, explosion, mystery, march, etc. all pure python,
    no dependencies. plays via afplay on macOS.

    i'm actually pretty proud of this one.
```

```
commit 0a1b2c3
Author: Tomás <tomas@spacebashers.dev>
Date:   Mon Sep 5 14:33:17 2022 -0500

    fix: sounds now actually sound like things

    turns out i had the sample rate wrong and everything sounded
    like dial-up internet. which, in fairness, some people on
    the team called "retro" and "intentional." it was not.
```

```
commit d4e5f6a
Author: diNGo <dingo@usomad.me>
Date:   Thu Oct 20 19:44:00 2022 -0500

    HOTFIX: game spawns 400 afplay processes after 60 seconds

    players are reporting that their laptops sound like
    jet engines and then the game freezes. one user said
    their macbook "achieved liftoff." two machines confirmed
    dead from thermal events. devops is not speaking to us.

    root cause: we spawn a new afplay process for every sound
    and never kill or reap them. the march sound alone fires
    20 times per second in late game. oops.
```

```
commit b7c8d9e
Author: Tomás <tomas@spacebashers.dev>
Date:   Thu Oct 20 20:01:33 2022 -0500

    i expected better. goodbye.

 D src/sound/engine.py
 D src/sound/synthesis.py
 D src/sound/channels.py
 D src/sound/README.md
 D .tomas_was_here

    he deleted his own files on the way out. respect honestly.
```

```
commit f0a1b2c
Author: diNGo <dingo@usomad.me>
Date:   Fri Oct 21 03:00:00 2022 -0500

    fix: channel-based sound with max 1 process per sound type

    rewrote the entire sound engine at 3am because tomas rage-quit
    and deleted everything. each sound gets one channel. new play
    kills the old process. march sound skips if still playing.
    max 8 concurrent afplay processes. laptops will survive.

    tomas if you're reading this: NASA called, they want to
    know how you made a laptop achieve escape velocity
```

```
commit 3d4e5f6
Author: Rachel <rachel@spacebashers.dev>
Date:   Fri Feb 3 10:00:00 2023 -0500

    SPBASH-4471: propose HP system instead of lives

    opening this ticket for discussion. i think hit points
    would feel better than 3 discrete lives. thoughts?
```

```
commit a7b8c9d
Author: Rachel <rachel@spacebashers.dev>
Date:   Fri Feb 3 10:00:01 2023 -0500

    this will be a calm and productive discussion
```

```
commit e0f1a2b
Author: diNGo <dingo@usomad.me>
Date:   Sat Aug 19 02:00:00 2023 -0500

    SPBASH-4471: close after 847 comments, 3 executive meetings

    for the record:
    - rachel wanted 2 damage from 8 max HP
    - derek wanted 3 damage from 10 max HP
    - rachel and derek were engaged
    - "were" is doing a lot of work in that sentence
    - the wedding is off
    - the registry gifts had already shipped
    - it was a whole thing

    going with 3 from 10. adding color-coded HP bar.
    green > 6, yellow > 3, red <= 3.

    i'm not putting the ticket number in this commit message
    because i never want to see it again.
```

```
commit 2c3d4e5
Author: Derek <derek@spacebashers.dev>
Date:   Sat Aug 19 02:04:00 2023 -0500

    for the record i was right about 3 from 10
```

```
commit f6a7b8c
Author: Rachel <rachel@spacebashers.dev>
Date:   Sat Aug 19 02:04:30 2023 -0500

    for the record i am mass-keeping the ring
```

```
commit 9d0e1f2
Author: Kevin <kevin@spacebashers.dev>
Date:   Thu Nov 2 15:30:00 2023 -0500

    RFC: barriers should be procedurally generated based on
    the current phase of the moon

    hear me out
```

```
commit a3b4c5d
Author: diNGo <dingo@usomad.me>
Date:   Thu Nov 2 15:31:00 2023 -0500

    kevin no
```

```
commit e6f7a8b
Author: Kevin <kevin@spacebashers.dev>
Date:   Thu Nov 2 15:31:30 2023 -0500

    kevin yes. i have a working prototype. it uses the
    ephem library and renders barriers as voronoi diagrams
    seeded by lunar declination. on a full moon you get
    maximum coverage. new moon = no barriers. it's thematic.
```

```
commit 9c0d1e2
Author: diNGo <dingo@usomad.me>
Date:   Thu Nov 2 15:45:00 2023 -0500

    kevin we are keeping the arches. please take some PTO.

    kevin is going through some things. we are giving
    kevin space. kevin will be okay.
```

```
commit f3a4b5c
Author: Kevin <kevin@spacebashers.dev>
Date:   Fri Nov 3 09:00:00 2023 -0500

    taking PTO. sorry about the moon thing. i'm going to
    a cabin for a while. no wifi. no lunar ephemeris data.
    just trees.
```

```
commit 6d7e8f9
Author: Kevin <kevin@spacebashers.dev>
Date:   Mon Nov 6 08:00:00 2023 -0500

    i'm back. the cabin had wifi. i made a moon-based
    tetris clone. it's on my github. i'm doing better now.
```

```
commit 0b1c2d3
Author: Dr. Elena Voss <consultant@philosophy.edu>
Date:   Mon Mar 4 12:00:00 2024 -0500

    add white paper: epistemology of keyboard state in
    non-blocking I/O systems (peer reviewed)

    can a key that is not currently pressed still be said
    to be "held"? if the terminal cannot detect key-up
    events, does the concept of "holding" a key have any
    ontological grounding? (90 pages, 212 citations)

    this work was commissioned after the team spent 47 weeks
    arguing about simultaneous movement and firing.

    A docs/keyboard_epistemology.pdf | Bin 0 -> 4.7M
```

```
commit e4f5a6b
Author: diNGo <dingo@usomad.me>
Date:   Mon Mar 4 12:15:00 2024 -0500

    yes we hired a philosophy consultant. no we will not be
    taking questions.

    her paper won a minor award. we are proud and confused.
```

```
commit c7d8e9f
Author: diNGo <dingo@usomad.me>
Date:   Tue Mar 5 09:00:00 2024 -0500

    fix: simultaneous move and fire

    drain key buffer each frame. set movement and firing
    flags independently. apply all flags. done.

    6 lines of code. forty-seven weeks. one award-winning
    philosophy paper. this is game development.

 M spacebashers.py | 12 ++++++------
 1 file changed, 6 insertions(+), 6 deletions(-)
```

```
commit 0a1b2c3
Author: diNGo <dingo@usomad.me>
Date:   Fri Mar 7 22:00:00 2025 -0500

    remove docs/keyboard_epistemology.pdf

    it was 4.7 megabytes and git lfs is $14/month.
    the paper lives on in the journal of computational
    phenomenology, vol 12 issue 3. if you need it, you
    know where to look. you probably don't need it.
```

```
commit d4e5f6a
Author: diNGo <dingo@usomad.me>
Date:   Tue Mar 25 03:47:00 2025 -0500

    v1.0: it works. it actually works.

    the invaders march. the bullets fly. the barriers crumble.
    the mystery ship sails across with its little <-?-> and
    its eerie oscillating tone.

    someone cried. we will not say who. it was all of us.

    team started at 47 engineers. shipping with 5.
    marcus has alpacas. jennifer has a coffee shop.
    tomas put something in orbit. rachel kept the ring.
    derek mass-deleted his dating apps. kevin is doing better.
    dr. voss won another award.

    jira has 12,847 closed tickets.
    SPBASH-1 ("make space invaders game") remains open.
    it will always remain open.
```

```
commit b7c8d9e
Author: diNGo <dingo@usomad.me>
Date:   Wed Apr 1 19:22:00 2026 -0500

    push to github. mass-close jira. mass-delete slack.
    we're done. we're finally done.

    this game is one python file. zero dependencies.
    it took five and a half years.

    to everyone who committed, who believed, who argued
    about ASCII alignment in a terminal window at 2am:
    you are not forgotten. your commits live in the reflog
    even if they were squashed.

    marcus: the alpacas look great man. no hard feelings.

 =============================================
  spacebashers.py | 626 +++++++++++++++++++++
  1 file changed, 626 insertions(+)
 =============================================

    maintained by diNGo. the last one standing.
```

```
SPBASH-1  make space invaders game  ·  OPEN  ·  opened 2021-01-06
```

## License

MIT
