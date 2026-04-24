from crewai.tools import BaseTool
import requests
import random
import os
import re

# =========================
# 🏥 HOSPITAL TOOL
# =========================
class HospitalTool(BaseTool):
    name: str = "hospital_tool"
    description: str = "Find real hospitals in a requested Indian city or region using OpenStreetMap data"

    _headers = {
        "User-Agent": "HealthcareAgent/1.0 (hospital lookup)"
    }

    def _extract_location(self, query: str) -> str:
        cleaned = re.sub(r"\s+", " ", (query or "")).strip()
        if not cleaned:
            return "India"

        if re.search(r"\b(?:all of )?india\b", cleaned, re.IGNORECASE):
            return "India"

        patterns = [
            r"\bin\s+([A-Za-z][A-Za-z\s,.-]+?)(?:\s+(?:that|for|with|which|who|renowned|speciali[sz]ed?|treat(?:ing)?)\b|$|[?.!,])",
            r"\bnear\s+([A-Za-z][A-Za-z\s,.-]+?)(?:\s+(?:that|for|with|which|who|renowned|speciali[sz]ed?|treat(?:ing)?)\b|$|[?.!,])",
            r"\bat\s+([A-Za-z][A-Za-z\s,.-]+?)(?:\s+(?:that|for|with|which|who|renowned|speciali[sz]ed?|treat(?:ing)?)\b|$|[?.!,])",
        ]

        for pattern in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                location = match.group(1).strip(" ,.-")
                if location:
                    return location

        if re.fullmatch(r"[A-Za-z][A-Za-z\s,.-]+", cleaned):
            return cleaned

        return "India"

    def _get_search_bounds(self, location: str) -> tuple[float, float, float, float]:
        search_url = "https://nominatim.openstreetmap.org/search"
        search_query = location if location.lower() == "india" else f"{location}, India"

        response = requests.get(
            search_url,
            params={
                "q": search_query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "in",
            },
            headers=self._headers,
            timeout=20,
        )
        response.raise_for_status()

        matches = response.json()
        if not matches:
            raise ValueError(f"Could not identify location '{location}'.")

        bounding_box = matches[0].get("boundingbox")
        if bounding_box and len(bounding_box) == 4:
            south, north, west, east = map(float, bounding_box)
            return south, west, north, east

        lat = float(matches[0]["lat"])
        lon = float(matches[0]["lon"])
        delta = 0.25 if location.lower() != "india" else 4.0
        return lat - delta, lon - delta, lat + delta, lon + delta

    def _get_coordinates(self, element: dict) -> tuple[float | None, float | None]:
        if "lat" in element and "lon" in element:
            return element["lat"], element["lon"]

        center = element.get("center", {})
        if "lat" in center and "lon" in center:
            return center["lat"], center["lon"]

        return None, None

    def _build_address(self, tags: dict, lat: float | None, lon: float | None) -> str:
        parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:suburb") or tags.get("addr:neighbourhood"),
            tags.get("addr:city") or tags.get("addr:district") or tags.get("is_in:city"),
            tags.get("addr:state"),
        ]

        address_parts = []
        seen = set()
        for part in parts:
            if not part:
                continue
            normalized = part.strip().lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            address_parts.append(part.strip())

        if address_parts:
            return ", ".join(address_parts)

        if lat is not None and lon is not None:
            return f"Area near {lat:.5f}, {lon:.5f}"

        return "Location details not available"

    def _is_valid_hospital(self, name: str) -> bool:
        cleaned = (name or "").strip().lower()
        if not cleaned or cleaned == "unknown hospital":
            return False

        banned_keywords = ["ambulance", "dispensary", "dispensory"]
        return not any(keyword in cleaned for keyword in banned_keywords)

    def _run(self, query: str) -> str:
        try:
            location = self._extract_location(query)
            south, west, north, east = self._get_search_bounds(location)
            overpass_url = "https://overpass-api.de/api/interpreter"

            osm_query = f"""
            [out:json];
            (
              node["amenity"="hospital"]({south},{west},{north},{east});
              way["amenity"="hospital"]({south},{west},{north},{east});
              relation["amenity"="hospital"]({south},{west},{north},{east});
            );
            out center 50;
            """

            response = requests.get(
                overpass_url,
                params={"data": osm_query},
                headers=self._headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            results = []
            seen_entries = set()

            for el in data.get("elements", []):
                tags = el.get("tags", {})
                name = tags.get("name", "Unknown Hospital")
                if not self._is_valid_hospital(name):
                    continue
                lat, lon = self._get_coordinates(el)
                address = self._build_address(tags, lat, lon)
                key = (name.strip().lower(), address.strip().lower())

                if key in seen_entries:
                    continue
                seen_entries.add(key)

                results.append(f"Hospital: {name}\nAddress: {address}")
                if len(results) >= 3:
                    break

            if not results:
                return f"No hospitals found for {location}. Please try a nearby major city."

            return "\n\n".join(results)

        except Exception as e:
            return f"Hospital tool error: {str(e)}"
    def run(self, query: str) -> str:
        return self._run(query)

    


# =========================
# 💰 COST TOOL
# =========================
class CostTool(BaseTool):
    name: str = "cost_tool"
    description: str = "Estimate treatment cost in INR for diseases"

    #def _run(self, disease: str) -> str:
       # low = random.randint(50000, 150000)
       # mid = random.randint(150000, 400000)
       # high = random.randint(400000, 900000)

       # return f"""
#Disease: {disease}
#Low Cost: ₹{low:,}
#Medium Cost: ₹{mid:,}
#High Cost: ₹{high:,}
#""".strip()
    def _run(self, disease: str) -> str:
        low = random.randint(50000, 150000)
        mid = random.randint(150000, 400000)
        high = random.randint(400000, 900000)

        return f"Low: ₹{low}\nMedium: ₹{mid}\nHigh: ₹{high}"    
    def run(self, disease: str) -> str:
        return self._run(disease)
# =========================
# ✅ IMPORTANT: CREATE OBJECTS
# =========================
hospital_tool = HospitalTool()
cost_tool = CostTool()


# =========================
# 🩺 RESOURCE VALIDATOR TOOL (MOCK)
# =========================
class ResourceValidatorTool(BaseTool):
    name: str = "resource_validator_tool"
    description: str = "Validates mock resource availability at a hospital: doctors, beds, and estimated wait time."

    def _run(self, hospital_name: str) -> str:
        import random
        doctors_available = random.randint(2, 12)
        beds_available = random.randint(5, 80)
        wait_days = random.randint(1, 10)
        specialist = random.choice(["Oncologist", "Nephrologist", "Cardiologist", "Neurologist", "Orthopedic Surgeon"])

        return (
            f"Hospital: {hospital_name}\n"
            f"Specialist Available: {specialist} ({doctors_available} doctors)\n"
            f"Beds Available: {beds_available}\n"
            f"Estimated Wait Time: {wait_days} days"
        )

    def run(self, hospital_name: str) -> str:
        return self._run(hospital_name)


resource_validator_tool = ResourceValidatorTool()


# =========================
# 📚 RAG TOOL (LIGHTWEIGHT)
# =========================
class MedicalKnowledgeTool(BaseTool):
    name: str = "knowledge_rag_tool"
    description: str = "Search for verified medical guidelines in the internal knowledge base."

    def _run(self, query: str) -> str:
        knowledge_dir = 'knowledge'
        if not os.path.exists(knowledge_dir):
            return "Knowledge base directory not found."
        
        results = []
        for filename in os.listdir(knowledge_dir):
            if filename.endswith(".txt"):
                with open(os.path.join(knowledge_dir, filename), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple keyword match for the RAG functionality
                    if any(word.lower() in content.lower() for word in query.split()):
                        results.append(f"--- SOURCE: {filename} ---\n{content}")
        
        if not results:
            return f"No specific guidelines found for '{query}' in the local knowledge base. Use your general medical knowledge."
        
        return "\n\n".join(results)

    def run(self, query: str) -> str:
        return self._run(query)

knowledge_rag_tool = MedicalKnowledgeTool()
