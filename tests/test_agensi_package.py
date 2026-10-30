"""Packaging must exclude private/runtime files and reject broken releases."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    for rel in ("skills/auto-paper-reading", "marketplace/agensi"):
        shutil.copytree(ROOT / rel, root / rel)
    (root / "src/auto_paper_reading").mkdir(parents=True)
    shutil.copyfile(ROOT / "src/auto_paper_reading/__init__.py",
                    root / "src/auto_paper_reading/__init__.py")
    shutil.copyfile(ROOT / "LICENSE", root / "LICENSE")
    return root


def build(root, out):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools/package_agensi.py"),
         "--root", str(root), "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8")


def test_package_contains_only_upload_files_and_matching_owner_material(project, tmp_path):
    skill = project / "skills/auto-paper-reading"
    (skill / "private.txt").write_text("private sentinel")
    (skill / "node_modules").mkdir()
    (skill / "node_modules/runtime.dll").write_bytes(b"not for upload")
    out = tmp_path / "delivery"
    result = build(project, out)
    assert result.returncode == 0, result.stderr
    archive = next(out.glob("*.zip"))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert sorted(z.namelist()) == [
            "LICENSE", "SKILL.md", "references/report-guide.md", "references/setup.md"]
        for name in z.namelist():
            assert z.read(name) == (skill / name).read_bytes()
    for name in ("listing.en.md", "UPLOAD.zh.md"):
        assert (out / name).read_bytes() == (project / "marketplace/agensi" / name).read_bytes()
    manifest = json.loads((out / "PACKAGE.json").read_text(encoding="utf-8"))
    assert manifest["archive"]["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    for line in (out / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest


def test_package_rejects_missing_reference_before_creating_zip(project, tmp_path):
    skill = project / "skills/auto-paper-reading/SKILL.md"
    with skill.open("a", encoding="utf-8") as f:
        f.write("\n[Required file](references/missing.md)\n")
    out = tmp_path / "delivery"
    result = build(project, out)
    assert result.returncode != 0 and "missing.md" in result.stderr
    assert not list(out.glob("*.zip"))


def test_package_rejects_license_mismatch(project, tmp_path):
    (project / "skills/auto-paper-reading/LICENSE").write_text("Different terms")
    out = tmp_path / "delivery"
    result = build(project, out)
    assert result.returncode != 0 and "LICENSE" in result.stderr
    assert not list(out.glob("*.zip"))


def test_package_rejects_version_drift(project, tmp_path):
    (project / "src/auto_paper_reading/__init__.py").write_text('__version__ = "99.0.0"')
    out = tmp_path / "delivery"
    result = build(project, out)
    assert result.returncode != 0 and "version" in result.stderr.lower()
    assert not list(out.glob("*.zip"))
