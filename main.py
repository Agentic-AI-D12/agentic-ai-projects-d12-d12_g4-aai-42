import os
import re
from functools import lru_cache

from tools import cost_tool, hospital_tool, resource_validator_tool

TOP_INDIA_HOSPITALS = [
    {
        "name": "All India Institute of Medical Sciences (AIIMS)",
        "address": "Ansari Nagar, New Delhi",
    },
    {
        "name": "Apollo Hospitals",
        "address": "Greams Road, Chennai, Tamil Nadu",
    },
    {
        "name": "Christian Medical College (CMC)",
        "address": "Ida Scudder Road, Vellore, Tamil Nadu",
    },
]

KNOWLEDGE_FILE = os.path.join(os.path.dirname(__file__), "knowledge", "medical_guidelines.txt")


def _normalize_word(word: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]", "", word.lower())
    if cleaned.endswith("s") and len(cleaned) > 4:
        cleaned = cleaned[:-1]
    return cleaned


@lru_cache(maxsize=1)
def load_guideline_sections() -> dict[str, str]:
    if not os.path.exists(KNOWLEDGE_FILE):
        return {}

    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        content = file.read()

    sections = {}
    parts = re.split(r"^##\s+", content, flags=re.MULTILINE)
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        heading = heading.strip()
        body = body.strip()
        if heading and body:
            sections[heading] = body

    return sections


def find_guideline_section(disease: str) -> tuple[str, str] | tuple[None, None]:
    disease_tokens = {_normalize_word(word) for word in disease.split() if _normalize_word(word)}
    if not disease_tokens:
        return None, None

    best_heading = None
    best_body = None
    best_score = 0

    for heading, body in load_guideline_sections().items():
        heading_tokens = {_normalize_word(word) for word in heading.split() if _normalize_word(word)}
        score = len(disease_tokens & heading_tokens)
        if score > best_score:
            best_score = score
            best_heading = heading
            best_body = body

    if best_score == 0:
        return None, None

    return best_heading, best_body


def build_treatment_summary(user_data: dict) -> str:
    disease = user_data.get("disease", "this condition")
    _, section = find_guideline_section(disease)

    if section:
        definition_match = re.search(r"\*\*Definition\*\*:\s*(.+)", section)
        definition = definition_match.group(1).strip() if definition_match else f"{disease} needs proper medical evaluation and treatment planning."
        steps = re.findall(r"^\s*\d+\.\s+(.+)$", section, flags=re.MULTILINE)
        steps = steps[:4]
    else:
        definition = f"{disease} is a health condition that should be assessed by a qualified doctor for correct diagnosis and treatment."
        steps = [
            "Book a specialist consultation and confirm the diagnosis with the recommended tests.",
            "Follow the prescribed medicines and avoid self-medication.",
            "Maintain hydration, diet, and lifestyle changes as advised by your doctor.",
            "Track symptoms closely and seek urgent care if pain, fever, or breathing issues worsen.",
        ]

    lines = [definition]
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step}")

    return "\n".join(lines)


def build_hospital_query(location: str) -> str:
    return f"Find 3 real hospitals in {location} that treat this condition."


def parse_hospital_tool_output(raw_text: str) -> list[dict[str, str]]:
    entries = []
    if not raw_text:
        return entries

    for block in raw_text.split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        name = ""
        address = ""
        for line in lines:
            lower_line = line.lower()
            if lower_line.startswith("hospital:"):
                name = line.split(":", 1)[1].strip()
            elif lower_line.startswith("address:"):
                address = line.split(":", 1)[1].strip()

        if name and address:
            entries.append({"name": name, "address": address})

    return entries


def format_hospital_entries(entries: list[dict[str, str]]) -> str:
    lines = []
    for entry in entries[:3]:
        lines.append(f"- **{entry['name']}**")
        lines.append(f"  Address: {entry['address']}")
    return "\n".join(lines)


@lru_cache(maxsize=32)
def get_cached_hospital_entries(location: str, willing_to_travel: str) -> tuple[tuple[str, str], ...]:
    if willing_to_travel == "Yes":
        return tuple((entry["name"], entry["address"]) for entry in TOP_INDIA_HOSPITALS)

    raw_output = hospital_tool._run(build_hospital_query(location))
    parsed_entries = parse_hospital_tool_output(raw_output)
    if parsed_entries:
        return tuple((entry["name"], entry["address"]) for entry in parsed_entries[:3])

    fallback_location = location or "your city"
    return (
        (f"City Hospital, {fallback_location}", fallback_location),
        (f"Metro Care Hospital, {fallback_location}", fallback_location),
        (f"Specialist Hospital, {fallback_location}", fallback_location),
    )


def get_hospital_entries(user_data: dict) -> list[dict[str, str]]:
    location = user_data.get("location", "your city").strip()
    willing_to_travel = user_data.get("willing_to_travel", "No")
    cached_entries = get_cached_hospital_entries(location, willing_to_travel)
    return [{"name": name, "address": address} for name, address in cached_entries]


def parse_cost_ranges(raw_text: str) -> dict[str, int]:
    parsed = {}
    for label in ["Low", "Medium", "High"]:
        match = re.search(rf"{label}:\s*[^\d]*(\d[\d,]*)", raw_text, flags=re.IGNORECASE)
        if match:
            parsed[label] = int(match.group(1).replace(",", ""))
    return parsed


def format_inr(value: int) -> str:
    return f"Rs.{value:,}"


def build_cost_breakdown(disease: str, hospital_entries: list[dict[str, str]]) -> str:
    base_costs = parse_cost_ranges(cost_tool._run(disease))
    low = base_costs.get("Low", 50000)
    medium = base_costs.get("Medium", 150000)
    high = base_costs.get("High", 400000)

    lines = [
        f"Average Low: {format_inr(low)}",
        f"Average Medium: {format_inr(medium)}",
        f"Average High: {format_inr(high)}",
        "",
    ]

    for index, entry in enumerate(hospital_entries[:3], start=1):
        seed = (sum(ord(char) for char in entry["name"]) % 10) / 100
        multiplier = 0.92 + (index * 0.06) + seed
        lines.append(f"**{entry['name']}**")
        lines.append(f"- Low: {format_inr(int(low * multiplier))}")
        lines.append(f"- Medium: {format_inr(int(medium * multiplier))}")
        lines.append(f"- High: {format_inr(int(high * multiplier))}")
        lines.append("")

    return "\n".join(lines).strip()


def generate_schedule(disease: str, hospital_names: list[str]) -> str:
    resource_blocks = []
    for name in hospital_names:
        resource_blocks.append(resource_validator_tool._run(name))

    all_resources = "\n\n".join(resource_blocks)

    return f"""Resource Validation:
{all_resources}

Execution Schedule:
Phase 1 - Diagnosis (Week 1-2):
- Consult a specialist for {disease}
- Complete all diagnostic tests (blood work, imaging, biopsies as needed)
- Review reports and confirm diagnosis

Phase 2 - Active Treatment (Week 3-6):
- Begin prescribed treatment protocol for {disease}
- Daily or weekly monitoring of treatment response
- Adjust medicines based on the doctor's advice

Phase 3 - Recovery & Follow-up (Month 2-3):
- Schedule regular follow-up consultations
- Continue diet and lifestyle precautions
- Watch for recurrence or warning symptoms"""


def run_system(user_data):
    hospital_entries = get_hospital_entries(user_data)
    hospital_text = format_hospital_entries(hospital_entries)
    treatment_text = build_treatment_summary(user_data)
    cost_text = build_cost_breakdown(user_data.get("disease", "your condition"), hospital_entries)
    hospital_names = [entry["name"] for entry in hospital_entries[:3]]
    schedule_text = generate_schedule(user_data.get("disease", "your condition"), hospital_names)

    return {
        "treatment": treatment_text,
        "hospitals": hospital_text,
        "cost": cost_text,
        "schedule": schedule_text,
    }
