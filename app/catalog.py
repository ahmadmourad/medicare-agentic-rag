"""Single source of truth for clinics and medicines shown on the site."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Clinic:
    name: str
    description: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Medicine:
    name: str
    price: int
    dosage: str
    description: str
    aliases: tuple[str, ...]
    prescription: bool = False


CLINICS: tuple[Clinic, ...] = (
    Clinic("General Medicine", "Comprehensive care for all ages.", ("general", "gp", "physician")),
    Clinic("Dental Care", "Professional dental services.", ("dentist", "dentists", "dental", "tooth", "teeth")),
    Clinic("Pediatrics", "Specialized care for children.", ("pediatrician", "pediatricians", "pediatric", "pediatrics", "child", "children", "baby")),
    Clinic("Cardiology", "Heart health and cardiovascular care.", ("cardiologist", "cardiologists", "cardiology", "cardio", "cardiac", "heart")),
    Clinic("Dermatology", "Skin, hair, and nail treatments.", ("dermatologist", "dermatologists", "dermatology", "derma", "skin", "hair", "nail")),
    Clinic("Orthopedics", "Bone and joint specialists.", ("orthopedist", "orthopedists", "orthopedics", "ortho", "bone", "joint")),
)

MEDICINES: tuple[Medicine, ...] = (
    Medicine("Panadol Extra", 45, "500 mg paracetamol",
             "Pain and fever relief.", ("panadol extra", "panadol")),
    Medicine("Aspirin", 78, "as labelled on the pack",
             "Pain relief and anti-inflammatory.", ("aspirin",)),
    Medicine("Telfast", 63, "as labelled on the pack",
             "Non-drowsy allergy relief.", ("telfast", "fexofenadine")),
    Medicine("Metformin 500mg", 8, "500 mg",
             "Type 2 diabetes medication.", ("metformin 500mg", "metformin 500", "metformin")),
    Medicine("Insulin Pen", 200, "as prescribed",
             "Insulin injection pen.", ("insulin pen", "insulin"), prescription=True),
    Medicine("Tamoxifen 20mg", 70, "20 mg",
             "Hormone therapy for breast cancer.", ("tamoxifen 20mg", "tamoxifen"), prescription=True),
    Medicine("Imatinib 400mg", 2800, "400 mg",
             "Targeted therapy for certain cancers.", ("imatinib 400mg", "imatinib"), prescription=True),
    Medicine("Orlistat 120mg", 207, "120 mg",
             "Weight management aid.", ("orlistat 120mg", "orlistat")),
    Medicine("Prozac 20mg", 118, "20 mg",
             "Antidepressant.", ("prozac 20mg", "prozac", "fluoxetine"), prescription=True),
    Medicine("Zoloft 50mg", 135, "50 mg",
             "Antidepressant.", ("zoloft 50mg", "zoloft", "sertraline"), prescription=True),
    Medicine("Cataflam 50mg", 35, "50 mg",
             "Anti-inflammatory pain relief.", ("cataflam 50mg", "cataflam", "diclofenac")),
    Medicine("Augmentin 1g", 90, "1 g",
             "Antibiotic.", ("augmentin 1g", "augmentin"), prescription=True),
    Medicine("Antinal", 25, "200 mg",
             "Intestinal antiseptic.", ("antinal", "nifuroxazide")),
    Medicine("Strepsils", 110, "lozenge",
             "Sore throat relief.", ("strepsils", "sore throat")),
    Medicine("Voltaren Gel", 65, "1% gel",
             "Topical pain relief gel.", ("voltaren gel", "voltaren")),
    Medicine("Concor 5mg", 55, "5 mg",
             "Beta blocker.", ("concor 5mg", "concor", "bisoprolol"), prescription=True),
    Medicine("Glucophage 1000", 40, "1000 mg",
             "Type 2 diabetes medication.", ("glucophage 1000", "glucophage")),
    Medicine("Claritin", 75, "10 mg",
             "Allergy relief.", ("claritin", "loratadine")),
    Medicine("Betadine", 30, "10% solution",
             "Antiseptic solution.", ("betadine", "povidone iodine")),
    Medicine("Panadol Advance", 35, "500 mg paracetamol",
             "Pain and fever relief.", ("panadol advance",)),
    Medicine("Vitamin C 1000", 20, "1000 mg",
             "Vitamin C supplement.", ("vitamin c 1000", "vitamin c", "ascorbic acid")),
)

CLINIC_BY_NAME = {clinic.name: clinic for clinic in CLINICS}
MEDICINE_BY_NAME = {medicine.name: medicine for medicine in MEDICINES}

# Longest aliases first so "panadol extra" wins over "panadol".
ALIAS_TO_MEDICINE: tuple[tuple[str, Medicine], ...] = tuple(
    sorted(
        ((alias, medicine) for medicine in MEDICINES for alias in medicine.aliases),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
)

CLINIC_KEYWORDS: tuple[tuple[str, Clinic], ...] = tuple(
    sorted(
        ((keyword, clinic) for clinic in CLINICS for keyword in clinic.keywords),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
)

MEDICINE_NAMES = tuple(medicine.name for medicine in MEDICINES)
CLINIC_NAMES = tuple(clinic.name for clinic in CLINICS)
MEDICINE_PRICES = {medicine.name: medicine.price for medicine in MEDICINES}
MEDICINE_DOSAGES = {medicine.name: medicine.dosage for medicine in MEDICINES}
