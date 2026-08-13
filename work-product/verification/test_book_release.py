import re
import unittest
import zipfile
from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
BOOK_ROOTS = (ROOT / "en" / "src", ROOT / "zh" / "src")
TEXT_SUFFIXES = {".md", ".txt", ".toml", ".yml", ".yaml", ".py", ".sh", ".ps1"}
IGNORED_PARTS = {".venv", ".pytest_cache", "__pycache__", ".tools", "book"}
NON_EXAMPLE_CHAPTERS = {"preparation-llms-agents-coding-assistants.md"}
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "data:")


def text_files(root: Path):
    for path in root.rglob("*"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def visible_markdown(text: str) -> str:
    text = re.sub(r"\{\{#include\s+[^}]+}}", "", text)
    text = re.sub(r"\]\([^)]+\)", "]", text)
    text = re.sub(r'\b(?:href|src)="[^"]+"', "", text)
    return text


class BookReleaseTests(unittest.TestCase):
    def test_local_markdown_and_html_references_resolve(self):
        markdown_link = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        html_reference = re.compile(r'\b(?:href|src)="([^"]+)"')
        include = re.compile(r"\{\{#include\s+([^}\s]+)")
        failures = []

        for root in BOOK_ROOTS:
            for path in root.rglob("*.md"):
                if any(part in IGNORED_PARTS for part in path.parts):
                    continue
                text = path.read_text(encoding="utf-8")
                targets = [match.group(1) for match in markdown_link.finditer(text)]
                targets.extend(match.group(1) for match in html_reference.finditer(text))
                targets.extend(match.group(1) for match in include.finditer(text))

                for target in targets:
                    target = target.strip().strip("<>").split()[0]
                    if not target or target.startswith(("#", *EXTERNAL_SCHEMES)):
                        continue
                    target = unquote(target.split("#", 1)[0])
                    target = re.sub(r":\d+(?::\d+)?$", "", target)
                    resolved = (path.parent / target).resolve()
                    if resolved.suffix == ".html" and not resolved.is_file():
                        resolved = resolved.with_suffix(".md")
                    if not resolved.is_file():
                        failures.append(
                            f"{path.relative_to(ROOT).as_posix()} -> {target}"
                        )

        self.assertEqual(failures, [])

    def test_every_chapter_has_both_prompt_routes(self):
        failures = []
        for root in BOOK_ROOTS:
            for path in sorted((root / "weeks").glob("*.md")):
                if path.name in NON_EXAMPLE_CHAPTERS:
                    continue
                text = path.read_text(encoding="utf-8")
                counts = (
                    text.count('class="prompt-route prompt-route--create"'),
                    text.count('class="prompt-route prompt-route--reproduce"'),
                )
                if counts != (1, 1):
                    failures.append(
                        f"{path.relative_to(ROOT).as_posix()}: create={counts[0]}, reproduce={counts[1]}"
                    )
        self.assertEqual(failures, [])

    def test_reproduce_prompts_enforce_the_asset_contract(self):
        prompt = re.compile(
            r'<div class="prompt-route prompt-route--reproduce">.*?</div>\s*'
            r"```text\s*(.*?)```",
            re.DOTALL,
        )
        required = {
            "ASSET_GUIDE.md",
            "READER_PROMPT.md",
            "TUTORIAL_CONTRACT.md",
            "VERSIONS.md",
        }
        failures = []
        for root in BOOK_ROOTS:
            for path in sorted((root / "weeks").glob("*.md")):
                if path.name in NON_EXAMPLE_CHAPTERS:
                    continue
                match = prompt.search(path.read_text(encoding="utf-8"))
                if not match:
                    failures.append(f"{path.relative_to(ROOT)}: prompt missing")
                    continue
                missing = sorted(name for name in required if name not in match.group(1))
                if missing:
                    failures.append(
                        f"{path.relative_to(ROOT)}: missing {', '.join(missing)}"
                    )

        self.assertEqual(failures, [])

    def test_download_archives_include_asset_contracts(self):
        required = {
            "ASSET_GUIDE.md",
            "READER_PROMPT.md",
            "TUTORIAL_CONTRACT.md",
            "VERSIONS.md",
        }
        archive_names = {
            "dora-hello-world-reference.zip",
            "rerun-scene-reference.zip",
            "habitat-camera-sensors-reference.zip",
            "multimodal-pick-and-place-reference.zip",
            "lidar-slam-navigation-reference.zip",
            "llm-action-planning-reference.zip",
            "agent-sdk-task-planning-reference.zip",
            "octos-multi-agent-supervision-reference.zip",
        }
        failures = []
        for root in BOOK_ROOTS:
            archives = {path.name: path for path in (root / "assets").rglob("*.zip")}
            self.assertTrue(archive_names.issubset(archives), root)
            for name in sorted(archive_names):
                with zipfile.ZipFile(archives[name]) as archive:
                    members = {member.removeprefix("./") for member in archive.namelist()}
                missing = sorted(required - members)
                if missing:
                    failures.append(f"{root.parent.name}/{name}: {', '.join(missing)}")
        self.assertEqual(failures, [])

    def test_bilingual_download_archives_have_identical_content(self):
        def archive_content(path: Path):
            with zipfile.ZipFile(path) as archive:
                return {
                    member.filename.removeprefix("./"): sha256(
                        archive.read(member)
                    ).hexdigest()
                    for member in archive.infolist()
                    if not member.is_dir()
                }

        en_assets = BOOK_ROOTS[0] / "assets"
        zh_assets = BOOK_ROOTS[1] / "assets"
        failures = []
        for en_archive in sorted(en_assets.rglob("*.zip")):
            relative = en_archive.relative_to(en_assets)
            zh_archive = zh_assets / relative
            if not zh_archive.is_file():
                failures.append(f"missing zh/{relative.as_posix()}")
                continue
            if archive_content(en_archive) != archive_content(zh_archive):
                failures.append(relative.as_posix())

        self.assertEqual(failures, [])

    def test_download_archives_match_their_source_directories(self):
        def source_content(path: Path):
            return {
                member.relative_to(path).as_posix(): sha256(member.read_bytes()).hexdigest()
                for member in path.rglob("*")
                if member.is_file()
                and not any(part in IGNORED_PARTS for part in member.parts)
            }

        def archive_content(path: Path):
            with zipfile.ZipFile(path) as archive:
                return {
                    member.filename.removeprefix("./"): sha256(
                        archive.read(member)
                    ).hexdigest()
                    for member in archive.infolist()
                    if not member.is_dir()
                }

        failures = []
        for root in BOOK_ROOTS:
            for archive in sorted((root / "assets").rglob("*.zip")):
                source = archive.parent / "source"
                if not source.is_dir():
                    failures.append(f"missing source for {archive.relative_to(ROOT)}")
                    continue
                if archive_content(archive) != source_content(source):
                    failures.append(archive.relative_to(ROOT).as_posix())

        self.assertEqual(failures, [])

    def test_complex_asset_entries_build_missing_images(self):
        packages = {
            "lidar-slam-navigation": "lidar-slam-navigation-reference.zip",
            "llm-action-planning": "llm-action-planning-reference.zip",
            "agent-sdk-task-planning": "agent-sdk-task-planning-reference.zip",
            "octos-multi-agent-supervision": "octos-multi-agent-supervision-reference.zip",
        }
        for root in BOOK_ROOTS:
            for package in packages:
                entry = root / "assets" / package / "source" / "tutorial.sh"
                with self.subTest(root=root, package=package):
                    text = entry.read_text(encoding="utf-8")
                    self.assertIn('docker build --tag "$IMAGE" "$ROOT"', text)

                    archive_path = root / "assets" / package / packages[package]
                    with zipfile.ZipFile(archive_path) as archive:
                        member = next(
                            name
                            for name in archive.namelist()
                            if name.removeprefix("./") == "tutorial.sh"
                        )
                        archived_entry = archive.read(member).decode("utf-8")
                    self.assertIn(
                        'docker build --tag "$IMAGE" "$ROOT"', archived_entry
                    )

    def test_no_obsolete_dora_packages_or_versions(self):
        obsolete = re.compile(r"\b0\.5\.0\b|dora-rs-cli")
        failures = []
        for root in (*BOOK_ROOTS, ROOT / "verification"):
            for path in text_files(root):
                if path.resolve() == Path(__file__).resolve():
                    continue
                if path.name == "uv.lock" or "logs" in path.parts:
                    continue
                if obsolete.search(path.read_text(encoding="utf-8")):
                    failures.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(failures, [])

    def test_user_facing_markdown_has_no_week_labels(self):
        label = re.compile(r"\bweek[\s_-]*\d+\b|第\s*\d+\s*周", re.IGNORECASE)
        failures = []
        for root in BOOK_ROOTS:
            for path in root.rglob("*.md"):
                if any(part in IGNORED_PARTS for part in path.parts):
                    continue
                text = visible_markdown(path.read_text(encoding="utf-8"))
                if label.search(text):
                    failures.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(failures, [])

    def test_rc4_is_pinned_in_dora_examples(self):
        requirement_files = [
            ROOT / "verification" / "dora-hello-world" / "requirements.txt",
            ROOT / "zh" / "src" / "assets" / "week2-rerun-scene" / "source" / "requirements.txt",
            ROOT / "zh" / "src" / "assets" / "multimodal-pick-and-place" / "source" / "environment-dora.yml",
        ]
        for path in requirement_files:
            with self.subTest(path=path):
                self.assertIn("dora-rs==1.0.0rc4", path.read_text(encoding="utf-8"))

    def test_mixed_python_examples_include_runtime_bridges(self):
        sources = ROOT / "zh" / "src" / "assets"
        required = [
            sources / "multimodal-pick-and-place" / "source" / "simulation_bridge_node.py",
            sources / "multimodal-pick-and-place" / "source" / "simulation_worker.py",
            sources / "lidar-slam-navigation" / "source" / "dora" / "bridge_protocol.py",
            sources / "lidar-slam-navigation" / "source" / "dora" / "sensor_ros_worker.py",
            sources / "lidar-slam-navigation" / "source" / "dora" / "navigation_ros_worker.py",
        ]
        for package in (
            "llm-action-planning",
            "agent-sdk-task-planning",
            "octos-multi-agent-supervision",
        ):
            bridge = sources / package / "source" / "dora" / "runtime_bridge"
            required.extend(
                [
                    bridge / "sidecar_bridge.py",
                    bridge / "sidecar_node.py",
                    bridge / "worker_shim" / "dora.py",
                ]
            )
        missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
