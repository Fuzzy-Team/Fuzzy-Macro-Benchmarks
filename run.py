"""Check out each Fuzzy Macro build, run every benchmark in bench.py on it, and write results.json.

Usage: python run.py /path/to/Fuzzy-Macro [--python /path/to/python]
"""
import argparse
import json
import os
import statistics
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# label -> (git ref, patch to apply or None)
BUILDS = {
    "1.0.0a": ("1.0.0a", None),
    # The last Existance commit doesn't compile (mixed tabs in main.py); the patch only re-indents those lines.
    "Existance last": ("25c9d35d", "patches/existance-last-tab-fix.patch"),
    "1.3.4": ("1.3.4", None),
    # 1.4.0c plus the fix that keeps the macro out of the main window process.
    "1.4.0": ("5668ba78", None),
}

TESTS = ["spawn_child", "gui_process", "night_sky", "night_grass", "blue_text_ocr",
         "blue_pass_2", "blue_pass_3", "respawn_wait"]
RUNS = 3


def run_test(python, src, test):
    runs = []
    for _ in range(1 if test == "blue_text_ocr" else RUNS):
        p = subprocess.run([python, os.path.join(HERE, "bench.py"), src, test], capture_output=True, text=True)
        line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
        if not line:
            return {"error": (p.stderr.strip().splitlines() or ["no output"])[-1]}
        runs.append(json.loads(line[0][len("RESULT "):]))
    # median of each numeric field
    return {k: statistics.median(r[k] for r in runs)
            if isinstance(v, (int, float)) and not isinstance(v, bool) else v
            for k, v in runs[0].items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="a Fuzzy Macro git checkout")
    parser.add_argument("--python", default=os.path.expanduser("~/fuzzy-macro-env/bin/python"))
    args = parser.parse_args()

    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for label, (ref, patch) in BUILDS.items():
            tree = os.path.join(tmp, ref)
            subprocess.run(["git", "-C", args.repo, "worktree", "add", "-q", "--detach", tree, ref], check=True)
            try:
                if patch:
                    subprocess.run(["git", "-C", tree, "apply", os.path.join(HERE, patch)], check=True)
                results[label] = {}
                for test in TESTS:
                    results[label][test] = run_test(args.python, os.path.join(tree, "src"), test)
                    print(label, test, results[label][test], flush=True)
            finally:
                subprocess.run(["git", "-C", args.repo, "worktree", "remove", "--force", tree])

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
