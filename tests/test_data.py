import re
from pathlib import Path

from PIL import Image

from app.catalog import CLINIC_BY_NAME, CLINICS, MEDICINE_BY_NAME, MEDICINES

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


def _table_rows(section: str):
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ":", " "}:
            continue
        if cells[0] in {"Medicine", "Clinic"}:
            continue
        rows.append(cells)
    return rows


def test_knowledge_base_covers_catalog():
    docs = (ROOT / "app" / "knowledge" / "docs.md").read_text(encoding="utf-8")
    for medicine in MEDICINES:
        assert medicine.name in docs
        assert f"{medicine.price} EGP" in docs
    for clinic in CLINICS:
        assert clinic.name in docs


def test_knowledge_base_medicine_table_matches_catalog():
    docs = (ROOT / "app" / "knowledge" / "docs.md").read_text(encoding="utf-8")
    pharmacy = docs.split("## Pharmacy", 1)[1].split("### How to order", 1)[0]
    rows = _table_rows(pharmacy)

    assert len(rows) == len(MEDICINES)
    for name, strength, price, use, prescription in rows:
        medicine = MEDICINE_BY_NAME[name]
        assert strength == medicine.dosage
        assert price == f"{medicine.price} EGP"
        assert use == medicine.description
        assert prescription == ("Yes" if medicine.prescription else "No")


def test_knowledge_base_clinic_table_matches_catalog():
    docs = (ROOT / "app" / "knowledge" / "docs.md").read_text(encoding="utf-8")
    clinics = docs.split("## Clinics", 1)[1].split("### How to book", 1)[0]
    rows = _table_rows(clinics)

    assert len(rows) == len(CLINICS)
    for name, _, description in rows:
        assert description == CLINIC_BY_NAME[name].description


def test_catalog_invariants():
    medicine_names = [medicine.name for medicine in MEDICINES]
    aliases = [alias for medicine in MEDICINES for alias in medicine.aliases]
    clinic_names = [clinic.name for clinic in CLINICS]

    assert len(medicine_names) == len(set(medicine_names))
    assert len(clinic_names) == len(set(clinic_names))
    assert len(aliases) == len(set(aliases))
    assert all(alias == alias.lower() for alias in aliases)
    assert all(medicine.price > 0 for medicine in MEDICINES)
    assert all(medicine.dosage and medicine.description for medicine in MEDICINES)
    assert all(clinic.description for clinic in CLINICS)


def test_frontend_local_assets_exist():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    for value in re.findall(r'(?:src|href)="([^"]+)"', html):
        if value.startswith(("http://", "https://", "#", "mailto:", "tel:")):
            continue
        local_path = value.split("?", 1)[0]
        assert (FRONTEND / local_path).is_file(), value

    script = (FRONTEND / "index.js").read_text(encoding="utf-8")
    imports = re.findall(r'from\s+"([^"]+)"', script)
    assert imports
    for value in imports:
        assert (FRONTEND / value.split("?", 1)[0]).is_file(), value


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
        if path.suffix in {".jpg", ".png", ".ico", ".mp4", ".gif", ".pdf"}:
            continue
        if "Cooked Devs" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
