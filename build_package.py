"""Build a client package that runs without a Python installation.

Run this script from the project virtual environment on Windows. The output
is a folder under dist that can be copied to a client laptop or Citrix host.
"""

from pathlib import Path
import argparse
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build" / "pyinstaller"
OUTPUT = ROOT / "dist" / "elt_client"


def run(command):
    """Run a build command and stop immediately when it fails."""
    print("+", " ".join(map(str, command)))
    subprocess.run(command, cwd=ROOT, check=True)


def copy_runtime_assets():
    """Copy editable client settings and dbt assets into the package."""
    shutil.copytree(ROOT / "config", OUTPUT / "config", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "dbt",
        OUTPUT / "dbt",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("target", "logs", "dbt_packages"),
    )
    for folder in ("source", "database", "exports", "logs"):
        (OUTPUT / folder).mkdir(parents=True, exist_ok=True)


def build():
    """Build the ELT executable and the bundled dbt executable."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keep-build",
        action="store_true",
        help="Keep intermediate PyInstaller files for troubleshooting.",
    )
    args = parser.parse_args()

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required. Install it with: "
            f"{sys.executable} -m pip install -r requirements-build.txt"
        ) from exc

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    pyinstaller = [sys.executable, "-m", "PyInstaller"]
    main_dist = BUILD / "elt_runner-dist"
    run(
        pyinstaller
        + [
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name",
            "elt_runner",
            "--distpath",
            str(main_dist),
            "--workpath",
            str(BUILD / "elt_runner-work"),
            "--specpath",
            str(BUILD),
            str(ROOT / "main.py"),
        ]
    )

    dbt_entry = BUILD / "dbt_entry.py"
    dbt_entry.write_text(
        "from dbt.cli.main import cli\n\nif __name__ == '__main__':\n    cli()\n",
        encoding="utf-8",
    )
    dbt_dist = BUILD / "dbt-dist"
    run(
        pyinstaller
        + [
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "dbt",
            "--collect-all",
            "dbt",
            "--collect-all",
            "dbt.adapters.duckdb",
            "--copy-metadata",
            "dbt-core",
            "--copy-metadata",
            "dbt-duckdb",
            "--distpath",
            str(dbt_dist),
            "--workpath",
            str(BUILD / "dbt-work"),
            "--specpath",
            str(BUILD),
            str(dbt_entry),
        ]
    )

    OUTPUT.mkdir(parents=True)
    shutil.copytree(main_dist / "elt_runner", OUTPUT, dirs_exist_ok=True)
    shutil.copy2(dbt_dist / "dbt.exe", OUTPUT / "dbt.exe")
    shutil.copy2(ROOT / "run_scheduled.bat", OUTPUT / "run_scheduled.bat")
    copy_runtime_assets()
    print(f"Client package created: {OUTPUT}")

    if not args.keep_build:
        shutil.rmtree(BUILD)


if __name__ == "__main__":
    build()
