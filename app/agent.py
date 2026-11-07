from __future__ import annotations

import re
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import Any

from .catalog import (
    ALIAS_TO_MEDICINE,
    CLINIC_BY_NAME,
    CLINIC_KEYWORDS,
    MEDICINE_BY_NAME,
    Medicine,
    Clinic,
)
from .schemas import AgentResponse

COMMAND_ACTIONS = {
    "navigate_home",
    "navigate_clinics",
    "navigate_pharmacy",
    "navigate_contact",
    "book_appointment",
    "buy_medicine",
    "price",
    "dosage",
    "medicine_info",
    "greeting",
    "help",
    "thanks",
    "goodbye",
    "emergency",
}

CHAT_ACTIONS = {"medical_question", "unknown"}

EMERGENCY_TERMS = (
    "chest pain",
    "heart attack",
    "stroke",
    "cannot breathe",
    "can't breathe",
    "can not breathe",
    "difficulty breathing",
    "not breathing",
    "unconscious",
    "severe bleeding",
    "bleeding heavily",
    "suicide",
    "suicidal",
    "overdose",
    "seizure",
    "choking",
)

GREETING_WORDS = {"hi", "hello", "hey", "salam", "salaam", "hola", "morning", "evening"}
THANKS_WORDS = ("thank", "thanks", "thx", "appreciate")
BYE_WORDS = ("bye", "goodbye", "see you", "exit", "quit")

PRICE_TERMS = ("price", "cost", "how much", "how much is", "how much does", "how much for")
DOSAGE_TERMS = (
    "dosage", "dose", "mg", "milligram", "strength", "how many",
    "how often", "how much should i take", "how much can i take",
)
BUY_TERMS = ("buy", "order", "purchase", "add to cart", "get me", "pick up")
BOOK_TERMS = (
    "book", "appointment", "schedule", "reserve", "visit", "consult",
    "see a", "checkup", "check up",
)
INFO_TERMS = ("what is", "what are", "tell me about", "do you have", "info", "used for", "uses")
MEDICAL_TERMS = (
    "symptom", "cause", "treatment", "cure", "prevent", "side effect",
    "interact", "diagnose", "diabetes", "cancer", "flu", "cold", "covid",
    "headache", "migraine", "fever", "pain", "blood pressure", "hypertension",
    "cholesterol", "pregnancy", "depression", "anxiety", "infection", "allergy",
    "asthma", "arthritis", "obesity", "anemia", "thyroid", "kidney", "liver",
    "hepatitis", "eczema", "psoriasis", "acne", "gout", "ulcer", "gerd",
    "constipation", "diarrhea", "vomiting", "nausea", "dizziness", "fatigue",
    "insomnia", "stress", "burn", "fracture", "dehydration", "malaria",
)

NAME_STOPWORDS = {
    "i", "my", "name", "is", "the", "a", "an", "for", "and", "please",
    "tomorrow", "today", "tonight", "at", "on", "in", "to", "with", "of",
    "clinic", "doctor", "dentist", "medicine", "appointment", "book", "buy",
    "order", "get", "need", "want", "am", "pm", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday", "next",
    "this", "coming", "upcoming", "following", "morning", "afternoon",
}

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12,
}

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def normalize(text: str) -> str:
    text = text.lower().replace("\u2019", "'")
    return re.sub(r"\s+", " ", text).strip()


def _has(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def _contains_any(text: str, phrases: tuple[str, ...] | set[str]) -> bool:
    return any(_has(text, phrase) for phrase in phrases)


def find_medicine(text: str) -> Medicine | None:
    lowered = normalize(text)
    for alias, medicine in ALIAS_TO_MEDICINE:
        if _has(lowered, alias):
            return medicine

    tokens = re.findall(r"[a-z0-9]+", lowered)
    best: Medicine | None = None
    best_score = 0.0

    for alias, medicine in ALIAS_TO_MEDICINE:
        parts = alias.split()
        if len(parts) == 1:
            for token in tokens:
                if len(token) < 4:
                    continue
                score = SequenceMatcher(None, parts[0], token).ratio()
                if score > best_score:
                    best_score, best = score, medicine
        else:
            window_size = len(parts)
            for start in range(max(0, len(tokens) - window_size + 1)):
                window = " ".join(tokens[start:start + window_size])
                score = SequenceMatcher(None, alias, window).ratio()
                if score > best_score:
                    best_score, best = score, medicine

    if best is not None and best_score >= 0.82:
        return best
    return None


def find_clinic(text: str) -> Clinic | None:
    lowered = normalize(text)
    for keyword, clinic in CLINIC_KEYWORDS:
        if _has(lowered, keyword) or _has(lowered, keyword + "s"):
            return clinic
    if _has(lowered, "doctor") or _has(lowered, "doctors"):
        return CLINIC_BY_NAME["General Medicine"]
    return None


def find_name(text: str) -> str | None:
    patterns = (
        r"\bmy name is\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,2})",
        r"\bname is\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,2})",
    )
    candidate = None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1)
            break

    if candidate is None:
        match = re.search(
            r"\b(?:book|buy|order|purchase|get|reserve|schedule)\b.*?\bfor\s+"
            r"([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,2})",
            text,
            re.IGNORECASE,
        )
        if match:
            candidate = match.group(1)

    if candidate is None:
        match = re.search(r"\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", text)
        if match:
            candidate = match.group(1)

    if not candidate:
        return None

    words: list[str] = []
    for word in candidate.split():
        if word.lower() in NAME_STOPWORDS:
            break
        words.append(word)
    if not words:
        return None
    return " ".join(word.capitalize() for word in words[:3])


def _safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def find_date(text: str, today: date | None = None) -> str | None:
    today = today or date.today()
    lowered = normalize(text)

    if "day after tomorrow" in lowered:
        return (today + timedelta(days=2)).isoformat()
    if _has(lowered, "tomorrow"):
        return (today + timedelta(days=1)).isoformat()
    if _has(lowered, "today"):
        return today.isoformat()

    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", lowered)
    if match:
        return _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", lowered)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)

    month_pattern = "|".join(MONTHS)
    match = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_pattern})\b", lowered)
    if match:
        day, month = int(match.group(1)), MONTHS[match.group(2)]
        return _upcoming_date(today, month, day)

    match = re.search(rf"\b({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", lowered)
    if match:
        month, day = MONTHS[match.group(1)], int(match.group(2))
        return _upcoming_date(today, month, day)

    for name, weekday in WEEKDAYS.items():
        if _has(lowered, name):
            days_ahead = (weekday - today.weekday()) % 7 or 7
            return (today + timedelta(days=days_ahead)).isoformat()

    return None


def _upcoming_date(today: date, month: int, day: int) -> str | None:
    candidate = _safe_date(today.year, month, day)
    if candidate and candidate < today.isoformat():
        return _safe_date(today.year + 1, month, day)
    return candidate


def find_time(text: str) -> str | None:
    lowered = normalize(text)

    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lowered)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2) or 0)
        if hour < 1 or hour > 12 or minute > 59:
            return None
        if match.group(3) == "pm" and hour != 12:
            hour += 12
        if match.group(3) == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", lowered)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"

    return None


def find_quantity(text: str) -> int | None:
    lowered = normalize(text)
    match = re.search(r"\b(\d{1,2})\s*(?:x|packs?|boxes?|units?|strips?|bottles?)\b", lowered)
    if match:
        return max(1, min(int(match.group(1)), 20))

    match = re.search(r"\b(?:buy|order|get|purchase)\s+(\d{1,2})\b", lowered)
    if match:
        return max(1, min(int(match.group(1)), 20))

    for word, value in NUMBER_WORDS.items():
        if _has(lowered, word):
            return value
    return None


def _medicine_entities(medicine: Medicine) -> dict[str, Any]:
    return {
        "medicine": medicine.name,
        "price": medicine.price,
        "dosage": medicine.dosage,
        "description": medicine.description,
        "prescription": medicine.prescription,
    }


def _smalltalk(lowered: str) -> str | None:
    words = lowered.split()
    if words and words[0] in GREETING_WORDS and len(words) <= 4:
        return "greeting"
    if _contains_any(lowered, THANKS_WORDS):
        return "thanks"
    if _contains_any(lowered, BYE_WORDS):
        return "goodbye"
    return None


def handle(text: str) -> AgentResponse:
    lowered = normalize(text)

    if _contains_any(lowered, EMERGENCY_TERMS):
        return AgentResponse(
            action="emergency",
            entities={},
            reply=(
                "This may be a medical emergency. Call your local emergency number "
                "(108 in Egypt or 911) or go to the nearest emergency room now. "
                "Do not wait for an online reply."
            ),
        )

    talk = _smalltalk(lowered)
    if talk == "greeting":
        return AgentResponse(
            action="greeting",
            entities={},
            reply=(
                "Hello. I can help you find a clinic, book an appointment, "
                "check medicine prices, or answer general health questions."
            ),
        )
    if talk == "thanks":
        return AgentResponse(action="thanks", entities={}, reply="You are welcome. Anything else I can help with?")
    if talk == "goodbye":
        return AgentResponse(action="goodbye", entities={}, reply="Take care. You can come back any time.")

    if _contains_any(lowered, ("help", "what can you do", "how does this work", "rules", "capabilities", "menu")):
        return AgentResponse(
            action="help",
            entities={},
            reply=(
                "I can navigate the site, book an appointment, open the pharmacy, "
                "check prices and dosages, and answer general health questions. "
                "Try: \"book a dentist tomorrow at 5 pm\" or \"how much is Panadol Extra?\""
            ),
        )

    medicine = find_medicine(lowered)
    clinic = find_clinic(lowered)

    dosage_question = _contains_any(lowered, DOSAGE_TERMS)
    price_question = _contains_any(lowered, PRICE_TERMS)
    info_question = _contains_any(lowered, INFO_TERMS)
    buy_question = _contains_any(lowered, BUY_TERMS)
    book_question = _contains_any(lowered, BOOK_TERMS)

    if medicine and dosage_question:
        entities = _medicine_entities(medicine)
        return AgentResponse(
            action="dosage",
            entities=entities,
            reply=(
                f"The labelled strength of {medicine.name} is {medicine.dosage}. "
                "Follow the package instructions and ask a pharmacist if you are unsure."
            ),
        )

    if medicine and price_question:
        return AgentResponse(
            action="price",
            entities=_medicine_entities(medicine),
            reply=f"{medicine.name} costs {medicine.price} EGP.",
        )

    if medicine and _contains_any(lowered, ("side effect", "interact", "safe to take with")):
        return AgentResponse(
            action="medical_question",
            entities=_medicine_entities(medicine),
            reply=f"Let me look up general information about {medicine.name}.",
        )

    if medicine and info_question:
        note = " A prescription is required." if medicine.prescription else ""
        return AgentResponse(
            action="medicine_info",
            entities=_medicine_entities(medicine),
            reply=(
                f"{medicine.name}: {medicine.description} "
                f"Listed price {medicine.price} EGP, strength {medicine.dosage}.{note} "
                "Always follow the label and ask a pharmacist if unsure."
            ),
        )

    if medicine and (buy_question or _contains_any(lowered, ("need", "want"))):
        entities = _medicine_entities(medicine)
        quantity = find_quantity(lowered)
        if quantity:
            entities["quantity"] = quantity
        name = find_name(text)
        if name:
            entities["name"] = name
        return AgentResponse(
            action="buy_medicine",
            entities=entities,
            reply=(
                f"I can open the pharmacy for {medicine.name} ({medicine.price} EGP). "
                "Add a delivery name and address to place the demo order."
            ),
        )

    if clinic and (book_question or _contains_any(lowered, ("need", "want", "see", "appointment"))):
        entities: dict[str, Any] = {"clinic": clinic.name, "description": clinic.description}
        name = find_name(text)
        appointment_date = find_date(lowered)
        appointment_time = find_time(lowered)
        if name:
            entities["name"] = name
        if appointment_date:
            entities["date"] = appointment_date
        if appointment_time:
            entities["time"] = appointment_time
        return AgentResponse(
            action="book_appointment",
            entities=entities,
            reply=f"I can book an appointment at {clinic.name}. Fill in your details to confirm.",
        )

    if book_question:
        entities = {}
        name = find_name(text)
        appointment_date = find_date(lowered)
        appointment_time = find_time(lowered)
        if name:
            entities["name"] = name
        if appointment_date:
            entities["date"] = appointment_date
        if appointment_time:
            entities["time"] = appointment_time
        return AgentResponse(
            action="book_appointment",
            entities=entities,
            reply=(
                "Which clinic would you like to book? We have General Medicine, "
                "Dental Care, Pediatrics, Cardiology, Dermatology, and Orthopedics."
            ),
        )

    if buy_question:
        return AgentResponse(
            action="buy_medicine",
            entities={},
            reply="Which medicine would you like? I can open the pharmacy once you name it.",
        )

    if _has(lowered, "contact") or _contains_any(lowered, ("phone", "email", "address", "opening hours")):
        return AgentResponse(
            action="navigate_contact",
            entities={},
            reply=(
                "Call +20 100 000 0000, email hello@medicare.example, or visit "
                "12 Nile Street, Cairo. Clinics are open daily 9:00-21:00 and the "
                "pharmacy 9:00-23:00. Opening the contact section now."
            ),
        )

    if _contains_any(lowered, ("pharmacy", "medicines", "drugs", "shop")):
        return AgentResponse(
            action="navigate_pharmacy",
            entities={},
            reply=(
                "The pharmacy stocks pain relief, allergy, diabetes, and prescription "
                "medicines. Opening the pharmacy section now."
            ),
        )

    if _contains_any(lowered, ("clinic", "clinics", "doctors", "specialists", "departments")):
        return AgentResponse(
            action="navigate_clinics",
            entities={},
            reply=(
                "We have General Medicine, Dental Care, Pediatrics, Cardiology, "
                "Dermatology, and Orthopedics. Opening the clinics section now."
            ),
        )

    if _contains_any(lowered, ("home", "main page", "start page", "landing")):
        return AgentResponse(
            action="navigate_home",
            entities={},
            reply="Taking you back to the home page.",
        )

    if clinic:
        return AgentResponse(
            action="book_appointment",
            entities={"clinic": clinic.name, "description": clinic.description},
            reply=f"We have a {clinic.name} clinic. Would you like to book an appointment?",
        )

    if medicine:
        return AgentResponse(
            action="medicine_info",
            entities=_medicine_entities(medicine),
            reply=(
                f"{medicine.name}: {medicine.description} "
                f"Listed price {medicine.price} EGP, strength {medicine.dosage}."
            ),
        )

    if _contains_any(lowered, MEDICAL_TERMS):
        return AgentResponse(
            action="medical_question",
            entities={},
            reply="Let me look that up for you.",
        )

    return AgentResponse(
        action="unknown",
        entities={},
        reply=(
            "I can help with clinics, appointments, medicine prices, and general health questions. "
            "Could you rephrase that?"
        ),
    )
