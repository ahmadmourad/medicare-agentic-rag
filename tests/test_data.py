import re
from pathlib import Path

from PIL import Image

from app.catalog import CLINICS, MEDICINES

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "Frontend"

MEDICINE_BLOCK = re.compile(
    r'\{\s*img:\s*"([^"]+)",\s*name:\s*"([^"]+)",\s*price:\s*(\d+)\s*\}'
)
CLINIC_BLOCK = re.compile(r'\{\s*name:\s*"([^"]+)",\s*description:\s*"([^"]+)"\s*\}')


def test_frontend_data_matches_catalog():
    text = (FRONTEND / "data.js").read_text(encoding="utf-8")
    medicines = {name: int(price) for _, name, price in MEDICINE_BLOCK.findall(text)}
    clinics = {name for name, _ in CLINIC_BLOCK.findall(text)}

    assert medicines == {medicine.name: medicine.price for medicine in MEDICINES}
    assert clinics == {clinic.name for clinic in CLINICS}
    assert len(medicines) == 21
    assert len(clinics) == 6


def test_images_are_local_and_valid():
    text = (FRONTEND / "data.js").read_text(encoding="utf-8")
    paths = [path for path, _, _ in MEDICINE_BLOCK.findall(text)]

    assert len(paths) == 21
    assert all(not path.startswith("http") for path in paths)
    assert not re.search(r"https?://", text)

    for relative in paths:
        image_path = FRONTEND / relative
        assert image_path.is_file(), relative
        with Image.open(image_path) as image:
            image.verify()


def test_knowledge_base_covers_catalog():
    docs = (ROOT / "app" / "knowledge" / "docs.md").read_text(encoding="utf-8")
    for medicine in MEDICINES:
        assert medicine.name in docs
        assert str(medicine.price) in docs
    for clinic in CLINICS:
        assert clinic.name in docs


def test_no_leftover_branding():
    offenders = []
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or ".git" in path.parts
            or "__pycache__" in path.parts
            or "tests" in path.parts
        ):
            continue
        if path.suffix in {".jpg", ".png", ".ico", ".mp4", ".pdf"}:
            continue
        if "Cooked Devs" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
