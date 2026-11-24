# Fuzzy Macro benchmarks

Performance tests that run the real code from four Fuzzy Macro builds side by side:

| Label | Git ref | Notes |
|---|---|---|
| 1.0.0a | `1.0.0a` | |
| Existance last | `25c9d35d` | The last commit by existancepy. Its `main.py` doesn't compile, so `patches/existance-last-tab-fix.patch` re-indents three tab-indented blocks. Nothing else changes. |
| 1.3.4 | `1.3.4` | |
| 1.4.0 | `5668ba78` | 1.4.0c plus the fix that keeps the macro out of the main window process |

## Results

Apple M4, macOS, Python 3.9.8. Each number is the median of 3 runs.

| Test | 1.0.0a | Existance last | 1.3.4 | 1.4.0 |
|---|---|---|---|---|
| Main window process memory | 153 MB | 150 MB | 154 MB | **113 MB** |
| Main window process load time | 0.75 s | 0.77 s | 0.74 s | **0.40 s** |
| Helper process memory (Manager, Discord bot) | 153 MB | 150 MB | 159 MB | **28 MB** |
| Night check while converting | 197 ms | 194 ms | 189 ms | **1.8 ms** |
| Night check while gathering | 28 ms | 25 ms | 25 ms | 26 ms |
| Blue-text OCR reads per background tick | n/a | n/a | 4 | **1** |
| Fight check pass, 2 messages | 42 ms | 46 ms | 67 ms | 50 ms |
| Fight check pass, 3 messages (Mondo) | 66 ms | 66 ms | 99 ms | 66 ms |
| Screenshots in the 3 s respawn wait | crashes | crashes | 190 | **40** |
| Settings app size on disk | 10.2 MB | 1.0 MB | 11.0 MB | 2.6 MB |

The settings app size comes from `du` on `src/webapp`, not from `run.py`.

What the numbers mean:

- **Helper processes** are the children started with `spawn`, which re-runs `main.py`'s top level. Before 1.4.0 that loaded the whole macro (OCR, Vision, cv2, pyautogui) into every child.
- **Night check while converting** scans the sky for a black 15×15 square. Older builds loop over it in Python. 1.4.0 uses a summed-area table. The test frame is a daytime 1512×945 Retina screen, so every build scans the whole strip.
- **Blue-text OCR** turns on the guiding star, unusual sprout, windy bee and sticker sprout pings. 1.3.4 reads the text once per detector. 1.4.0 reads it once and shares it. One read takes about 46 ms on this machine. 1.0.0a and Existance last don't have these pings.
- **Fight check pass** uses real screen captures. 1.4.0 takes one screenshot per pass instead of one per message. It beats 1.3.4 but not the two older builds, because their image search did less work per check.
- **Respawn wait** runs the "wait for the empty health bar" loop after a reset. 1.3.4 has no pause in it. 1.0.0a and Existance last raise `TemplateTooLargeError` on a Retina screen. Their screenshot comes back at half size (150×60), smaller than the 226×38 health bar image.
- **Settings app size.** Existance last is the smallest because it has no cheat sheet images. 1.0.0a and 1.3.4 ship them as PNGs (about 9 MB). 1.4.0 ships them as WebP (about 1 MB).

## Running it

You need a Fuzzy Macro checkout with tags and a Python env that has the macro's dependencies. The old builds also need `imagehash`, which current installs don't include. Screen Recording permission is needed for the screen capture tests.

```sh
python run.py /path/to/Fuzzy-Macro --python /path/to/python
```

`run.py` makes a temporary git worktree for each build, applies the patch where needed, runs every test in `bench.py` in its own process, and writes `results.json`. Each test also runs on its own:

```sh
python bench.py /path/to/build/src night_sky
```

Model downloads at startup are skipped in every build so that network time doesn't count as startup time.
