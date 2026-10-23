import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    target = Path(__file__).resolve().parent / "seed__curriculum.py"

    if not target.exists():
        print("Missing seed__curriculum.py; nothing to run.")
        return

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    args = [sys.executable, str(target)] + sys.argv[1:]
    subprocess.run(args, check=False)


if __name__ == "__main__":
    main()
