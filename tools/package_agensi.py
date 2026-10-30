"""Build the text-only Agensi upload ZIP and creator materials (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile


ROOT = Path(__file__).resolve().parents[1]
UPLOAD_FILES = ("LICENSE", "SKILL.md", "references/report-guide.md", "references/setup.md")
CREATOR_FILES = ("listing.en.md", "UPLOAD.zh.md")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_version(root: Path) -> str:
    source = (root / "src/auto_paper_reading/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"(\d+\.\d+\.\d+)"', source, re.M)
    if not match:
        raise ValueError("Cannot read project version")
    return match.group(1)


def build_package(root: Path, out: Path) -> Path:
    version = project_version(root)
    skill = root / "skills/auto-paper-reading"
    files = {name: (skill / name).read_bytes() for name in UPLOAD_FILES}
    if files["LICENSE"] != (root / "LICENSE").read_bytes():
        raise ValueError("Package LICENSE does not match the repository LICENSE")
    texts = {name: data.decode("utf-8").replace("\r\n", "\n") for name, data in files.items()}
    entry = texts["SKILL.md"]
    if not entry.startswith("---\n"):
        raise ValueError("SKILL.md requires YAML frontmatter")
    header = entry.split("---", 2)[1]
    for key, expected in (("version", version), ("toolkit-version", version),
                          ("toolkit-ref", "v" + version)):
        match = re.search(rf'^  {key}:\s*"([^"]+)"\s*$', header, re.M)
        if not match or match.group(1) != expected:
            raise ValueError(f"Package version mismatch: {key} must be {expected}")
    if not re.search(r"^name: auto-paper-reading$", header, re.M):
        raise ValueError("Unexpected skill name")
    # Check package-local links against the actual upload list, not the repo tree.
    for name, text in texts.items():
        if "\x00" in text:
            raise ValueError(f"Binary content is not allowed: {name}")
        if not name.endswith(".md"):
            continue
        for link in re.findall(r"\]\(([^)]+)\)", text):
            url = urlsplit(link)
            if url.scheme or not url.path:
                continue
            target = PurePosixPath(name).parent / unquote(url.path)
            if target.is_absolute() or ".." in target.parts or target.as_posix() not in files:
                raise ValueError(f"Missing or unsafe package reference: {name} -> {link}")
    creator = {name: (root / "marketplace/agensi" / name).read_bytes()
               for name in CREATOR_FILES}
    listing = creator["listing.en.md"].decode("utf-8").replace("\r\n", "\n")
    fields = {m.group(1): m.group(2).strip() for m in re.finditer(
        r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", listing, re.M | re.S)}
    for name, limit in (("Name", 60), ("Summary", 300)):
        if not 0 < len(fields.get(name, "")) <= limit:
            raise ValueError(f"Listing {name} must contain 1–{limit} characters")
    if sum(len(text) for text in texts.values()) > 6_000_000:
        raise ValueError("Package exceeds the text delivery limit")

    # Validation finishes before creating a deliverable. Fixed ZIP metadata makes
    # repeated builds from the same source byte-for-byte reproducible.
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"auto-paper-reading-agensi-v{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or set(z.namelist()) != set(files):
            raise ValueError("ZIP verification failed")
        if any(z.read(name) != data for name, data in files.items()):
            raise ValueError("ZIP content verification failed")
    for name, data in creator.items():
        (out / name).write_bytes(data)
    manifest = {
        "version": version,
        "archive": {"name": archive.name, "bytes": archive.stat().st_size,
                    "sha256": digest(archive.read_bytes())},
        "files": [{"path": name, "bytes": len(data), "sha256": digest(data)}
                  for name, data in files.items()],
        "checks": {"zip_crc": "passed", "source_bytes": "passed",
                   "single_skill_entry": True, "package_references": "passed",
                   "license_matches_repository": True, "version_consistency": "passed"},
        "scope": "Package validation only; runtime/review evidence is recorded separately.",
    }
    (out / "PACKAGE.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    deliverables = [archive, *(out / name for name in CREATOR_FILES), out / "PACKAGE.json"]
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(p.read_bytes())}  {p.name}\n" for p in deliverables),
        encoding="utf-8")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    parser.add_argument("--out", type=Path, help="Delivery directory")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        out = args.out.resolve() if args.out else root / "output" / f"agensi-v{project_version(root)}"
        print(build_package(root, out))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
