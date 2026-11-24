# Fuzzy Macro benchmarks

Performance tests that run the real code from four Fuzzy Macro builds side by side:

| Label | Git ref | Notes |
|---|---|---|
| Fuzzy Version 1 (1.0.0a) | `1.0.0a` | |
| Existance Macro (latest) | `25c9d35d` | The last commit by existancepy. Its `main.py` doesn't compile, so `patches/existance-last-tab-fix.patch` re-indents three tab-indented blocks. Nothing else changes. |
| Fuzzy Version 1.3.5 | `1.3.4` | |
| 1.4.0 | `a3568593` | 1.4.0c plus the fixes that keep the macro out of the main window process and speed up settings |

## Results

Apple M4, macOS, Python 3.9.8. Each number is the median of 3 runs.

| Test | Fuzzy Version 1 (1.0.0a) | Existance Macro (latest) | Fuzzy Version 1.3.5 | 1.4.0 |
|---|---|---|---|---|
| Total app memory (all four processes) | 625 MB | 615 MB | 660 MB | **456 MB** |
| Main window process memory | 152 MB | 150 MB | 159 MB | **113 MB** |
| Main window process load time | 0.71 s | 0.67 s | 0.66 s | **0.42 s** |
| Helper process memory (Manager) | 153 MB | 150 MB | 160 MB | **28 MB** |
| Macro process startup time | 0.67 s | 0.69 s | 0.68 s | 0.66 s |
| Macro process memory | 153 MB | 151 MB | 166 MB | 155 MB |
| Discord bot process memory | 167 MB | 165 MB | 176 MB | 161 MB |
| Discord bot stall during /screenshot | 380 ms | 301 ms | 414 ms | **59 ms** |
| Night check while converting | 187 ms | 180 ms | 182 ms | **1.8 ms** |
| Night check while gathering | 27 ms | 25 ms | 26 ms | 24 ms |
| Blue-text OCR reads per background tick | n/a | n/a | 4 | **1** |
| Fight check pass, 2 messages | 50 ms | 44 ms | 68 ms | 48 ms |
| Fight check pass, 3 messages (Mondo) | 68 ms | 67 ms | 105 ms | 65 ms |
| Screenshots in the 3 s respawn wait | crashes | crashes | 187 | **38** |
| Settings load time | 1.2 ms | 0.7 ms | 7.2 ms | **0.3 ms** |
| Settings save time | 0.5 ms | 0.7 ms | 0.6 ms | 0.8 ms |
| Settings app size on disk | 10.2 MB | 1.0 MB | 11.0 MB | 2.6 MB |

The settings app size comes from `du` on `src/webapp`, not from `run.py`.

What the numbers mean:

- **Helper process** is the Manager child, started with `spawn`, which re-runs `main.py`'s top level. Before 1.4.0 that loaded the whole macro (OCR, Vision, cv2, pyautogui) into it.
- **Total app memory** adds the main window, the Manager, the macro process after Start and the Discord bot process. The bot is imported but not logged in.
- **Macro process** runs `main.py`'s top level like `spawn` does, then builds the macro object with each build's fresh default settings. Every build loads the full macro here, so time and memory barely change.
- **Discord bot stall** runs each build's own `/screenshot` handler with a fake Discord interaction and measures the longest gap in a 5 ms heartbeat on the bot's event loop. While the loop is stuck, the bot can't answer other commands. 1.4.0 captures the screen on a worker thread. It still encodes the PNG on the loop, so the stall isn't zero.
- **Settings load and save** call `loadAllSettings` and `saveProfileSetting` on each build's own fresh settings. 1.4.0 has about 1,600 settings, 6x more than the oldest builds. It used to parse every line with `ast.literal_eval` on each load, which took about 7 ms. It now parses numbers, True/False/None and plain words directly and reuses the parse of an unchanged file. A save is still a little slower than the old builds because it writes a temporary file, syncs it to disk and swaps it in, so a crash mid-save can't leave a half-written settings file.
- **Night check while converting** scans the sky for a black 15×15 square. Older builds loop over it in Python. 1.4.0 uses a summed-area table. The test frame is a daytime 1512×945 Retina screen, so every build scans the whole strip.
- **Blue-text OCR** turns on the guiding star, unusual sprout, windy bee and sticker sprout pings. Fuzzy Version 1.3.5 reads the text once per detector. 1.4.0 reads it once and shares it. One read takes about 46 ms on this machine. Fuzzy Version 1 (1.0.0a) and Existance Macro (latest) don't have these pings.
- **Fight check pass** uses real screen captures. 1.4.0 takes one screenshot per pass instead of one per message. It beats Fuzzy Version 1.3.5 and roughly ties the two older builds. Each search tries the template at 100%, 95% and 105% size so a slightly scaled window still matches. The old builds tried only 100%.
- **Respawn wait** runs the "wait for the empty health bar" loop after a reset. Fuzzy Version 1.3.5 has no pause in it. Fuzzy Version 1 (1.0.0a) and Existance Macro (latest) raise `TemplateTooLargeError` on a Retina screen. Their screenshot comes back at half size (150×60), smaller than the 226×38 health bar image.
- **Settings app size.** Existance Macro (latest) is the smallest because it has no cheat sheet images. Fuzzy Version 1 (1.0.0a) and Fuzzy Version 1.3.5 ship them as PNGs (about 9 MB). 1.4.0 ships them as WebP (about 1 MB).

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
