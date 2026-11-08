from datetime import date, timedelta

import pytest

from app import agent


def next_weekday(today: date, weekday: int) -> str:
    days = (weekday - today.weekday()) % 7 or 7
    return (today + timedelta(days=days)).isoformat()


@pytest.mark.parametrize(
    "text,action",
    [
        ("hello", "greeting"),
        ("hi there", "greeting"),
        ("thanks", "thanks"),
        ("goodbye", "goodbye"),
        ("help", "help"),
        ("what can you do", "help"),
        ("how much is Panadol Extra", "price"),
        ("how much panadol advance", "price"),
        ("cost of cataflam", "price"),
        ("price of augmentin", "price"),
        ("what is the dosage of augmentin", "dosage"),
        ("what dose of cataflam", "dosage"),
        ("tell me about betadine", "medicine_info"),
        ("do you have claritin", "medicine_info"),
        ("buy panadol", "buy_medicine"),
        ("order two packs of betadine for Ali", "buy_medicine"),
        ("i want to buy cataflm", "buy_medicine"),
        ("i need a heart doctor", "book_appointment"),
        ("book a dentist for Ahmed tomorrow at 5 pm", "book_appointment"),
        ("schedule with a dermatologist", "book_appointment"),
        ("i want to book an appointment", "book_appointment"),
        ("go to the pharmacy", "navigate_pharmacy"),
        ("show me the clinics", "navigate_clinics"),
        ("show me the doctors", "navigate_clinics"),
        ("open home", "navigate_home"),
        ("contact us", "navigate_contact"),
        ("what is your phone number", "navigate_contact"),
        ("i have chest pain", "emergency"),
        ("my father is unconscious", "emergency"),
        ("what is diabetes", "medical_question"),
        ("symptoms of flu", "medical_question"),
        ("tell me a joke", "unknown"),
        ("what is the weather", "unknown"),
    ],
)
def test_actions(text, action):
    assert agent.handle(text).action == action


def test_price_reply():
    result = agent.handle("how much is panadol extra")
    assert result.entities["medicine"] == "Panadol Extra"
    assert result.entities["price"] == 45
    assert "45 EGP" in result.reply


def test_dosage_reply():
    result = agent.handle("what is the dosage of augmentin")
    assert result.entities["medicine"] == "Augmentin 1g"
    assert result.entities["dosage"] == "1 g"
    assert "1 g" in result.reply


def test_medicine_info_mentions_prescription():
    result = agent.handle("tell me about augmentin")
    assert result.action == "medicine_info"
    assert result.entities["prescription"] is True
    assert "prescription" in result.reply.lower()
    assert agent.handle("what are the side effects of panadol").action == "medical_question"
    assert agent.handle("symptoms of dehydration").action == "medical_question"


def test_booking_entities():
    result = agent.handle("book a dentist for Ahmed tomorrow at 5 pm")
    assert result.action == "book_appointment"
    assert result.entities["clinic"] == "Dental Care"
    assert result.entities["name"] == "Ahmed"
    assert result.entities["date"] == (date.today() + timedelta(days=1)).isoformat()
    assert result.entities["time"] == "17:00"


def test_booking_name_and_weekday():
    result = agent.handle("book a pediatrician for Sara next monday at 10:30")
    assert result.entities["clinic"] == "Pediatrics"
    assert result.entities["name"] == "Sara"
    assert result.entities["date"] == next_weekday(date.today(), 0)
    assert result.entities["time"] == "10:30"


def test_booking_iso_date():
    result = agent.handle("schedule a cardiology appointment on 2027-01-15 at 09:15")
    assert result.entities["clinic"] == "Cardiology"
    assert result.entities["date"] == "2027-01-15"
    assert result.entities["time"] == "09:15"


def test_buy_fuzzy_typo():
    result = agent.handle("buy betadin")
    assert result.action == "buy_medicine"
    assert result.entities["medicine"] == "Betadine"


def test_buy_quantity_and_name():
    result = agent.handle("buy two packs of betadine for Ali")
    assert result.action == "buy_medicine"
    assert result.entities["medicine"] == "Betadine"
    assert result.entities["quantity"] == 2
    assert result.entities["name"] == "Ali"


def test_buy_does_not_store_card_data():
    result = agent.handle("buy panadol card 4111 1111 1111 1111 cvv 123 expiry 01/30")
    assert result.action == "buy_medicine"
    flat = " ".join(f"{key}={value}" for key, value in result.entities.items()).lower()
    assert "4111" not in flat
    assert "cvv" not in flat
    assert "expiry" not in flat


def test_emergency_wording():
    result = agent.handle("i cannot breathe")
    assert result.action == "emergency"
    assert "emergency" in result.reply.lower()


def test_generic_booking_asks_for_clinic():
    result = agent.handle("i want to book an appointment")
    assert result.action == "book_appointment"
    assert "clinic" not in result.entities
    assert "which clinic" in result.reply.lower()


def test_generic_buy_asks_for_medicine():
    result = agent.handle("i want to buy something")
    assert result.action == "buy_medicine"
    assert "medicine" not in result.entities
    assert "which medicine" in result.reply.lower()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("today", "2026-11-08"),
        ("tomorrow", "2026-11-09"),
        ("day after tomorrow", "2026-11-10"),
        ("2027-01-15", "2027-01-15"),
        ("15/01/2027", "2027-01-15"),
        ("15-01-27", "2027-01-15"),
        ("15 january", "2027-01-15"),
        ("january 15", "2027-01-15"),
        ("monday", "2026-11-09"),
        ("31/02/2027", None),
        ("31 february", None),
        ("not a date", None),
    ],
)
def test_date_parsing(text, expected):
    assert agent.find_date(text, today=date(2026, 11, 8)) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("12 am", "00:00"),
        ("12 pm", "12:00"),
        ("5 pm", "17:00"),
        ("10:30 am", "10:30"),
        ("17:30", "17:30"),
        ("13 pm", None),
        ("25:00", None),
        ("10:75", None),
        ("no time", None),
    ],
)
def test_time_parsing(text, expected):
    assert agent.find_time(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("buy 25 packs of panadol", 20),
        ("buy 0 packs of panadol", 1),
        ("buy three boxes of panadol", 3),
        ("buy 2 panadol", 2),
        ("buy panadol", None),
    ],
)
def test_quantity_parsing(text, expected):
    assert agent.find_quantity(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("my name is Sara Ali", "Sara Ali"),
        ("book a dentist for John Doe tomorrow", "John Doe"),
        ("for Alice", "Alice"),
        ("my name is the", None),
        ("for the clinic", None),
    ],
)
def test_name_parsing(text, expected):
    assert agent.find_name(text) == expected


def test_generic_booking_extracts_all_entities():
    result = agent.handle("book tomorrow at 5 pm for John")
    assert result.action == "book_appointment"
    assert result.entities == {
        "name": "John",
        "date": (date.today() + timedelta(days=1)).isoformat(),
        "time": "17:00",
    }


def test_single_entity_mentions():
    clinic = agent.handle("cardiology")
    assert clinic.action == "book_appointment"
    assert clinic.entities["clinic"] == "Cardiology"

    medicine = agent.handle("panadol")
    assert medicine.action == "medicine_info"
    assert medicine.entities["medicine"] == "Panadol Extra"


def test_emergency_reply_uses_correct_local_number():
    result = agent.handle("i have chest pain")
    assert result.action == "emergency"
    assert "123" in result.reply
    assert "108" not in result.reply
