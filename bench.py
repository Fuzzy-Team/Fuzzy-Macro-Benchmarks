"""Run one benchmark against one Fuzzy Macro source tree. Prints a JSON result line."""
import json
import os
import resource
import runpy
import sys
import time
import types

src, test = sys.argv[1], sys.argv[2]
sys.path.insert(0, src)
os.chdir(src)


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024  # macOS reports bytes


def emit(**kw):
    print("RESULT " + json.dumps(kw))


def stub_model_download():
    # Startup model download/cleanup is network work, not import cost. Skip it in every version.
    try:
        import modules.misc.modelManager as mm
    except ImportError:
        return  # versions before the model manager don't download at startup
    mm.ensure_missing_supported_models = lambda: None


def macro_class():
    try:
        from modules.macro.events import EventDetectionMixin as cls
        import modules.macro.events as mod
    except ImportError:
        import modules.macro as mod
        cls = mod.macro
    return cls, mod


if test == "spawn_child":
    # What every spawned child (Manager, Discord bot) runs: main.py's top level as __mp_main__.
    stub_model_download()
    base = len(sys.modules)
    t = time.perf_counter()
    runpy.run_path(os.path.join(src, "main.py"), run_name="__mp_main__")
    emit(seconds=time.perf_counter() - t, rss_mb=rss_mb(), modules=len(sys.modules) - base,
         heavy=sorted(m for m in ("cv2", "pyautogui", "Vision", "Quartz", "modules.macro", "modules.screen.ocr") if m in sys.modules))

elif test == "gui_process":
    # The GUI process up to the point it opens the window.
    stub_model_download()
    t = time.perf_counter()
    if os.path.exists(os.path.join(src, "modules", "app.py")):
        import modules.app as app

        class Opened(Exception):
            pass

        def runApp(_macro):
            raise Opened()
        app.runApp = runApp
        try:
            runpy.run_path(os.path.join(src, "main.py"), run_name="__main__")
        except Opened:
            pass
    else:
        runpy.run_path(os.path.join(src, "main.py"), run_name="__mp_main__")
    emit(seconds=time.perf_counter() - t, rss_mb=rss_mb(),
         heavy=sorted(m for m in ("cv2", "pyautogui", "Vision", "Quartz", "modules.macro", "modules.screen.ocr") if m in sys.modules))

elif test in ("night_sky", "night_grass"):
    import numpy as np
    cls, mod = macro_class()
    # Daytime 1512x945 window on a Retina display (2x). Sky is blue, so no 15x15 black square:
    # the sky check has to scan the whole strip, which is what happens every check during the day.
    frame = np.zeros((1890, 3024, 4), dtype=np.uint8)
    frame[:, :] = (235, 206, 135, 255)
    frame[900:, :] = (40, 140, 60, 255)  # field grass, not one of the exact day colours
    mod.mssScreenshotNP = lambda *a, **k: frame
    self = types.SimpleNamespace(
        robloxWindow=types.SimpleNamespace(mx=0, my=0, mw=1512, mh=945, multi=2),
        converting=(test == "night_sky"), canDetectNight=True, nightDetectStreaks=0, night=False)
    cls.detectNight(self)  # warm up
    runs = 20
    t = time.perf_counter()
    for _ in range(runs):
        cls.detectNight(self)
    emit(ms=(time.perf_counter() - t) / runs * 1000)

elif test == "blue_text_ocr":
    # One background tick with guiding star, unusual sprout, windy bee and sticker sprout pings on.
    import modules.macro as mod
    import modules.screen.ocr as ocr
    cls = mod.macro
    calls = {"n": 0}

    def imToString(*a, **k):
        calls["n"] += 1
        return ""
    ocr.imToString = imToString
    ocr.readBlueText = imToString
    setdat = {"ping_guiding_star": True, "guiding_star_announcements": True, "ping_unusual_sprouts": True, "ping_windy_bee": True,
              "sticker_sprout_watch": True, "macro_mode": "normal"}

    class Self(types.SimpleNamespace):
        def __getattr__(self, name):
            fn = getattr(cls, name, None)
            if callable(fn):
                return types.MethodType(fn, self)
            return 0
    self = Self(setdat=setdat, status=types.SimpleNamespace(value="running"), lastBlueTextScan=0,
                serverGeneration=0, scanGeneration=0, logger=types.SimpleNamespace(webhook=lambda *a, **k: None))
    if hasattr(cls, "scanBlueTextAnnouncements"):
        cls.scanBlueTextAnnouncements(self)
    else:
        for name in ("detectGuidingStarAnnouncement", "detectUnusualSproutAnnouncement",
                     "detectWindyBeeAnnouncement", "detectStickerSproutAnnouncement"):
            if hasattr(cls, name):
                try:
                    getattr(cls, name)(self)
                except Exception as e:
                    print(name, "error", repr(e), file=sys.stderr)
    emit(ocr_calls=calls["n"])

elif test in ("blue_pass_2", "blue_pass_3", "respawn_wait"):
    import modules.macro as mod
    import modules.screen.imageSearch as imageSearch
    from modules.misc.imageManipulation import adjustImage
    cls = mod.macro
    captures = {"n": 0}
    import modules.screen.screenshot as shot
    real = shot.mssScreenshot
    def counted(*a, **k):
        captures["n"] += 1
        return real(*a, **k)
    shot.mssScreenshot = counted
    imageSearch.mssScreenshot = counted
    win = types.SimpleNamespace(mx=0, my=0, mw=1512, mh=945, multi=2, display_type="retina")

    class Self(types.SimpleNamespace):
        def __getattr__(self, name):
            fn = getattr(cls, name, None)
            if callable(fn):
                return types.MethodType(fn, self)
            raise AttributeError(name)
    self = Self(robloxWindow=win, setdat={"display_type": "retina"}, newUI=True)

    if test == "respawn_wait":
        # The "wait for the empty health bar" loop after a reset, exactly as each version writes it.
        # Nothing matches on this screen, so it runs the full 3 seconds.
        # Use the health bar image each version picks: old builds default newUI to False.
        import re
        if os.path.exists("modules/macro/hive.py"):
            image = "emptyhealth_new"
        else:
            image = "emptyhealth_new" if re.search(r"self\.newUI = True", open("modules/macro.py").read()) else "emptyhealth"
        emptyHealth = adjustImage("./images/menu", image, "retina")
        sleeps = "time.sleep(0.05)" in open(sys.modules[cls.__module__].__file__ if not os.path.exists("modules/macro/hive.py") else "modules/macro/hive.py").read().split("if locateImageOnScreen(emptyHealth")[1][:200]
        cpu0, t0 = time.process_time(), time.time()
        while time.time() - t0 < 3:
            if imageSearch.locateImageOnScreen(emptyHealth, win.mx + (win.mw - 150), win.my, 150, 60, 0.8):
                break
            if sleeps:
                time.sleep(0.05)
        wall = time.time() - t0
        emit(cpu_percent=(time.process_time() - cpu0) / wall * 100, captures=captures["n"], sleeps=sleeps)
    else:
        # One pass of a boss/mob fight loop: died + defeated (+ mondo for Mondo).
        names = ["died", "defeated", "mondo"][: int(test[-1])]
        shared = hasattr(cls, "blueTextScreen")
        def one_pass():
            if shared:
                screen = self.blueTextScreen()
                for n in names:
                    self.blueTextImageSearch(n, screen=screen)
            else:
                for n in names:
                    self.blueTextImageSearch(n)
        one_pass()
        captures["n"] = 0
        runs = 30
        t = time.perf_counter()
        for _ in range(runs):
            one_pass()
        emit(ms=(time.perf_counter() - t) / runs * 1000, captures_per_pass=captures["n"] / runs)
