import re
import logging
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)

DOC_TYPE_PATTERNS = {
    "rtc": [r"record of rights", r"pahani", r"form 11", r"form 12", r"rtc", r"hissa", r"survey no", r"village accountant"],
    "ec": [r"encumbrance certificate", r"form 15", r"form 16", r"sub.?registrar", r"nil encumbrance"],
    "sale_deed": [r"sale deed", r"vendor", r"vendee", r"conveyance deed", r"absolute sale", r"pattadar"],
    "mutation": [r"mutation", r"form 9", r"pahani", r"revenue inspector", r"village accountant", r"khata transfer"],
    "khatha": [r"khatha", r"khata certificate", r"bbmp", r"property tax", r"assessment number"],
    "conversion": [r"d\.?c\. conversion", r"section 95", r"non.?agricultural", r"conversion order", r"deputy commissioner"],
    "ptcl": [r"grant land", r"government grant", r"inam", r"sarkari", r"scheduled caste", r"scheduled tribe", r"sc/st", r"ptcl"],
    "sketch": [r"survey sketch", r"village map", r"field measurement book", r"fmb", r"topo"],
    "rera": [r"rera", r"real estate", r"apartment", r"promoter", r"allottee", r"carpet area"],
}

SURVEY_NUMBER_RE = re.compile(
    r"(?:survey\s*(?:no|number|#)\.?\s*|s\.no\.?\s*|sy\.?\s*no\.?\s*)([0-9]+(?:/[0-9]+)*(?:\s*hissa\s*[0-9]+)?)",
    re.IGNORECASE
)
EXTENT_RE = re.compile(
    r"(?:extent|area|land)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(acres?|guntas?|sq\.?\s*ft|sq\.?\s*meters?|hectares?|ankanam)",
    re.IGNORECASE
)
NAME_RE = re.compile(
    r"(?:owner|vendor|vendee|seller|buyer|grantee|mortgagor|mortgagee|khata\s*holder)\s*[:=]?\s*([A-Z][a-zA-Z\s\.]{3,50}?)(?=\n|,|\.|son|wife|daughter|w/o|s/o|d/o|aged)",
    re.IGNORECASE
)
DATE_RE = re.compile(
    r"\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{4}[-/\.]\d{2}[-/\.]\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})\b",
    re.IGNORECASE
)
DOC_NUMBER_RE = re.compile(
    r"(?:document\s*(?:no|number)|reg(?:istration)?\s*no|deed\s*no)\.?\s*[:=]?\s*([A-Z0-9/-]{3,20})",
    re.IGNORECASE
)
VILLAGE_RE = re.compile(
    r"(?:village|hobli|taluk|district)\s*[:=]?\s*([A-Za-z\s]{3,40}?)(?=\n|,|\.|taluk|hobli|dist)",
    re.IGNORECASE
)
GRANT_RE = re.compile(
    r"\b(?:government\s+grant|sarkari\s+grant|grant\s+land|inam\s+land|scheduled\s+(?:caste|tribe)|sc/st\s+grant|ptcl)\b",
    re.IGNORECASE
)
ENCUMBRANCE_RE = re.compile(
    r"\b(?:mortgage|charge|lien|hypothecation|pledge|attachment|court\s+order|lis\s+pendens|injunction|stay\s+order)\b",
    re.IGNORECASE
)
MUTATION_RE = re.compile(
    r"(?:mutation\s*(?:no|number|entry))\.?\s*[:=]?\s*([A-Z0-9/-]{1,15})",
    re.IGNORECASE
)


class DocumentParser:
    def parse(self, full_text: str, doc_type_hint: str, ocr_results: List[Dict]) -> Dict:
        detected_type = self._detect_doc_type(full_text, doc_type_hint)
        property_details = self._extract_property_details(full_text)
        ownership_chain  = self._extract_ownership_chain(full_text, ocr_results)
        flags_raw        = self._extract_raw_flags(full_text, property_details)

        return {
            "doc_type":          detected_type,
            "full_text":         full_text,
            "property_details":  property_details,
            "ownership_chain":   ownership_chain,
            "raw_flags":         flags_raw,
            "has_grant_land":    bool(GRANT_RE.search(full_text)),
            "has_encumbrance":   bool(ENCUMBRANCE_RE.search(full_text)),
            "page_count":        sum(r.get("page_count", 0) for r in ocr_results),
            "ocr_engines":       list({r.get("engine", "unknown") for r in ocr_results}),
            "language":          ocr_results[0].get("language", "en") if ocr_results else "en",
            "tables":            [t for r in ocr_results for t in r.get("tables", [])],
        }

    def _detect_doc_type(self, text: str, hint: str) -> str:
        if hint and hint != "auto":
            return hint
        text_lower = text.lower()
        scores = {}
        for dtype, patterns in DOC_TYPE_PATTERNS.items():
            scores[dtype] = sum(1 for p in patterns if re.search(p, text_lower))
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def _extract_property_details(self, text: str) -> Dict:
        details = {}

        surveys = SURVEY_NUMBER_RE.findall(text)
        if surveys:
            details["survey_number"] = surveys[0].strip()
            if len(surveys) > 1:
                details["all_survey_numbers"] = [s.strip() for s in surveys[:5]]

        extents = EXTENT_RE.findall(text)
        if extents:
            val, unit = extents[0]
            details["extent"] = f"{val} {unit}"

        docs = DOC_NUMBER_RE.findall(text)
        if docs:
            details["document_number"] = docs[0]

        dates = DATE_RE.findall(text)
        if dates:
            details["dates_found"] = list(dict.fromkeys(dates))[:5]
            details["earliest_date"] = dates[0]
            details["latest_date"]   = dates[-1]

        villages = VILLAGE_RE.findall(text)
        if villages:
            details["location"] = villages[0].strip() + ", Karnataka"

        mutations = MUTATION_RE.findall(text)
        if mutations:
            details["mutation_number"] = mutations[0]

        details["is_grant_land"]  = bool(GRANT_RE.search(text))
        details["has_encumbrance"] = bool(ENCUMBRANCE_RE.search(text))

        return details

    def _extract_ownership_chain(self, text: str, ocr_results: List[Dict]) -> List[Dict]:
        chain = []
        lines = text.split("\n")

        transfer_keywords = ["sale deed", "gift deed", "settlement", "partition", "inheritance", "succession", "mutation", "grant", "allotment", "court decree", "conveyance"]

        current_entry: Dict = {}
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if not line_lower:
                continue

            is_transfer = any(kw in line_lower for kw in transfer_keywords)
            names = NAME_RE.findall(line)
            dates = DATE_RE.findall(line)

            if names or is_transfer:
                if current_entry and current_entry.get("owner_name"):
                    chain.append(current_entry)
                    current_entry = {}

                if names:
                    current_entry["owner_name"] = names[0].strip().title()
                if dates:
                    current_entry["from_date"] = dates[0]
                if is_transfer:
                    for kw in transfer_keywords:
                        if kw in line_lower:
                            current_entry["transfer_type"] = kw.title()
                            break
                doc_nums = DOC_NUMBER_RE.findall(line)
                if doc_nums:
                    current_entry["document_number"] = doc_nums[0]

                if GRANT_RE.search(line):
                    current_entry["owner_type"] = "government"
                    current_entry["flag"] = "Grant Land entry"

        if current_entry and current_entry.get("owner_name"):
            current_entry["owner_type"] = "current"
            chain.append(current_entry)

        if len(chain) > 1:
            for i in range(len(chain) - 1):
                if chain[i].get("from_date"):
                    chain[i]["to_date"] = chain[i + 1].get("from_date", "present")
                    chain[i]["period"]  = f"{chain[i]['from_date']} → {chain[i]['to_date']}"

        if chain:
            chain[-1]["owner_type"] = "current"

        return chain[:20]

    def _extract_raw_flags(self, text: str, details: Dict) -> List[str]:
        flags = []
        if details.get("is_grant_land"):
            flags.append("grant_land_detected")
        if details.get("has_encumbrance"):
            flags.append("encumbrance_detected")
        if re.search(r"\bgomal\b|\bkharab\b|\btank\s+bed\b|\bnaala\b", text, re.IGNORECASE):
            flags.append("govt_land_category")
        if re.search(r"\b79[ab]\b", text, re.IGNORECASE):
            flags.append("section_79ab_reference")
        if re.search(r"\bbenami\b", text, re.IGNORECASE):
            flags.append("benami_reference")
        if re.search(r"\bcourt\s+case\b|\bsuit\s+no\b|\bcivil\s+case\b|\bwrit\b", text, re.IGNORECASE):
            flags.append("litigation_detected")
        if re.search(r"\b(?:gpa|power\s+of\s+attorney|general\s+power)\b", text, re.IGNORECASE):
            flags.append("gpa_transaction")
        if not details.get("survey_number"):
            flags.append("no_survey_number")
        if not details.get("dates_found"):
            flags.append("no_dates_found")
        return flags
