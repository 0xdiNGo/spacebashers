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

---

## The Story of SpaceBashers

### Preface

What you see before you is a single Python file. 600-odd lines. You could read it in ten minutes. But what you cannot see — what no `git log` will ever capture — is the mass of human wreckage that was left in its wake.

SpaceBashers was not built. It was *survived*.

### The Early Days (Week 1-47)

It started, as all doomed endeavors do, with a Slack message at 2 AM.

> "how hard could space invaders be lol"

Famous last words. The kind of sentence that, in retrospect, belongs on a tombstone. What followed was forty-seven weeks of architectural debates, mass refactors, mass re-refactors, mass re-re-refactors, three complete rewrites from scratch, and one mass that was held for the original codebase in a small church in Vermont.

The first prototype used `print()` statements and `time.sleep()`. It flickered like a dying fluorescent light in a gas station bathroom. We called it "beautiful." We were young. We were naive. We had not yet known loss.

### The Curses Migration (Week 48-91)

The decision to move to `curses` split the team in two. On one side: those who believed in the sacred promise of terminal-native rendering. On the other: those who had actually read the curses documentation.

The debates were vicious. Friendships that had weathered college, weddings, and shared Netflix passwords crumbled overnight. Marcus — our lead architect for fourteen years — left the project after a heated argument about whether `addstr()` or `addch()` was the morally correct way to draw a bullet character. He moved to a yurt in Montana. Last we heard, he raises alpacas now. He seems at peace. We do not speak of Marcus.

Jennifer, our UX researcher, spent eleven weeks conducting A/B tests on the player ship design. The final candidates were `^` and `/^\`. The team vote was deadlocked 4-4 for six days. On the seventh day, Jennifer presented a 200-page report titled "The Semiotics of ASCII Spacecraft: A Phenomenological Inquiry." She then resigned, citing "a fundamental loss of faith in collaborative creative processes." She took the office espresso machine with her. That was a dark Monday.

### The Sound Engine Incident (Week 92-156)

Adding sound nearly destroyed us.

The first approach — a custom FM synthesis engine written from scratch in pure Python — worked flawlessly in testing and produced a sound in production best described as "a modem falling down a staircase." We shipped it anyway. The bug reports were... colorful.

The `afplay` pivot seemed so elegant at first. "Just spawn a subprocess," they said. "What could go wrong," they said. What went wrong was that after sixty seconds of gameplay, the machine would be running four hundred concurrent `afplay` processes and the laptop would achieve liftoff. We lost two MacBook Pros to thermal events. DevOps still won't make eye contact with us.

The channel-based rewrite took eleven weeks and cost us our best systems engineer, Tomás, who mass-resigned after discovering we'd been spawning processes in a loop without a reap strategy. His resignation email was four words: "I expected better. Goodbye." He now works at NASA. We hear the rockets are more stable.

### The Great HP Debate (Week 157-203)

The original game had three lives. Simple. Clean. Elegant. And yet.

Someone — and to this day no one will admit who — opened a Jira ticket titled "SPBASH-4471: Consider hit points instead of lives for enhanced gameplay feel." That ticket would go on to accumulate 847 comments, spawn 12 sub-tasks, require 3 executive steering committee meetings, and end one engagement.

The engaged couple in question — both senior engineers on the project — found themselves on opposite sides of the "damage per hit" debate. She advocated for 2 HP per hit with a max of 8. He was firmly in the 3-damage-from-10 camp. The wedding was called off after a pull request review turned personal. The registry gifts had already shipped. It was a whole thing.

We went with 3 damage from 10. It was the right call. But at what cost.

### The Movement Refactor (Week 204-251)

"Players should be able to move and shoot at the same time."

This single sentence — spoken innocently during a Thursday standup — triggered what the team now refers to only as "The Dark Quarter." For forty-seven weeks, we grappled with the fundamental limitations of terminal input buffering, the philosophical implications of simultaneous intent, and the question of whether a key that is not currently being pressed can still be said to be "held."

Our philosophy consultant (yes, we hired a philosophy consultant; no, we will not be taking questions) wrote a 90-page white paper on the epistemology of keyboard state in non-blocking I/O systems. It was peer-reviewed. It was published. It won a minor award.

The actual fix was six lines of code.

### The Barrier Arch Controversy (Week 252-278)

Were the barriers supposed to have arches at the bottom? The original Space Invaders did. But were we bound by the conventions of 1978? Were we artists or were we archaeologists?

The team split into three factions: the Archists, the Anti-Archists, and a splinter group called the Arch-Agnostics who argued that the shape of the barrier should be procedurally generated at runtime based on the phase of the moon. That last group consisted of one person — Kevin — who was going through some things at the time. We gave Kevin some space. Kevin is doing better now.

We kept the arches.

### The Final Push (Week 279-283)

In the end, it came down to five of us in a room that smelled like cold pizza and broken dreams. The whiteboard was covered in diagrams. The floor was covered in energy drink cans. Someone had written "WHY" on the wall in dry-erase marker. No one remembered doing it.

At 3:47 AM on a Tuesday, the game ran. The invaders marched. The bullets flew. The barriers crumbled. The mystery ship sailed across the top of the screen with its little `<-?->` and its eerie oscillating tone, and for one perfect moment, everything was right in the world.

Someone cried. We will not say who. But it was all of us.

### Aftermath

SpaceBashers shipped as a single Python file with zero dependencies. The total development time, from first commit to final push, spanned roughly five and a half years. The team, originally forty-seven strong, finished with five. Some left for other projects. Some left for other careers. Marcus has his alpacas. Jennifer opened a coffee shop (she kept the espresso machine). Tomás put something in orbit, which is more than we can say.

The Jira board has 12,847 closed tickets and one open ticket — SPBASH-1, filed on day one: "Make space invaders game." It remains open. It will always remain open. Because SpaceBashers is not a product. It is a *journey*. And the journey never truly ends.

To everyone who contributed, who believed, who argued at 2 AM about pixel-perfect ASCII alignment in a terminal window: thank you. You are not forgotten. Your commits live on in the reflog, even if they were squashed.

And to Marcus specifically: the alpacas look great, man. No hard feelings.

### Dedication

*For the mass who never shipped their side project.*

*You are not alone.*

---

*SpaceBashers is maintained by diNGo, the last one standing.*

## License

MIT
