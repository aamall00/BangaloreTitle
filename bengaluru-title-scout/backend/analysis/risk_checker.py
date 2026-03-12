import re
import logging
from typing import Dict, List, Any

log = logging.getLogger(__name__)


class RiskChecker:
    def __init__(self, knowledge_base=None):
        self.kb = knowledge_base

    def check(self, analysis: Dict, parsed: Dict, law_context: List[Dict]) -> Dict:
        flags = analysis.get("flags", [])
        text  = parsed.get("full_text", "").lower()

        flags = self._check_ptcl(flags, parsed, text)
        flags = self._check_land_reforms(flags, parsed, text)
        flags = self._check_chain_continuity(flags, parsed, analysis)
        flags = self._check_gpa(flags, text)
        flags = self._check_govt_land(flags, text)
        flags = self._check_dc_conversion(flags, parsed, text)
        flags = self._check_rera(flags, text)
        flags = self._check_bbmp_khatha(flags, text)
        flags = self._check_dates_and_registration(flags, parsed, text)
        flags = self._deduplicate_flags(flags)

        analysis["flags"] = flags
        analysis["risk_level"] = self._compute_risk_level(flags, analysis)
        analysis["scores"] = self._compute_scores(flags, parsed, analysis)
        return analysis

    def _check_ptcl(self, flags: List, parsed: Dict, text: str) -> List:
        if not parsed.get("has_grant_land"):
            return flags

        ptcl_flag = next((f for f in flags if "ptcl" in f.get("title", "").lower() or "grant land" in f.get("title", "").lower()), None)
        if not ptcl_flag:
            flags.append({
                "severity": "CRITICAL",
                "title": "PTCL Act — Grant Land Transfer Risk",
                "description": (
                    "This document contains references to Government Grant Land / SC/ST grant land. "
                    "Under the PTCL Act (Prevention of Transfer of Certain Lands), any transfer of "
                    "lands granted to SC/ST community members is VOID AB INITIO unless conditions "
                    "of grant are satisfied and DC permission is obtained. Third parties cannot claim "
                    "bona fide purchaser protection."
                ),
                "law_reference": "PTCL Act — Sections 4, 5, 7, 8",
                "recommendation": (
                    "STOP — Do not proceed with purchase until: (1) Original grant order obtained, "
                    "(2) Grantee's caste/community verified, (3) Grant conditions verified, "
                    "(4) DC permission for transfer obtained if within restriction period, "
                    "(5) Karnataka High Court search for PTCL restoration petitions conducted."
                ),
            })

        if re.search(r"\b(?:15|thirty|30)\s*year\b", text) or re.search(r"ptcl\s*(?:exempt|free|clear)", text):
            flags.append({
                "severity": "MEDIUM",
                "title": "PTCL Restriction Period Verification Required",
                "description": "Document may reference the 15-year restriction period under grant conditions. Verify if restriction period has expired and whether transfer permission was obtained from DC.",
                "law_reference": "PTCL Act — Section 4, Grant Conditions",
                "recommendation": "Verify original grant order date and compute restriction period. Obtain DC permission letter if within restriction period.",
            })
        return flags

    def _check_land_reforms(self, flags: List, parsed: Dict, text: str) -> List:
        if re.search(r"\b79[ab]\b", text):
            flags.append({
                "severity": "HIGH",
                "title": "Karnataka Land Reforms Act — Section 79A/79B Reference",
                "description": (
                    "Document references Section 79A or 79B of the Karnataka Land Reforms Act 1961. "
                    "Pre-2020: Prohibited non-agriculturists and institutions from holding agricultural land. "
                    "The 2020 amendment liberalised this, but transactions before the amendment may be challenged. "
                    "Verify whether the transaction predates the 2020 amendment."
                ),
                "law_reference": "Karnataka Land Reforms Act 1961 — Section 79A, 79B; 2020 Amendment",
                "recommendation": "Obtain legal opinion on whether the transaction preceded or followed the 2020 amendment. Check for pending Section 79A/79B violation proceedings in Revenue Court.",
            })

        if re.search(r"\b(?:ceiling|surplus|vested)\b", text):
            flags.append({
                "severity": "HIGH",
                "title": "Land Ceiling / Surplus Land Risk",
                "description": "References to ceiling, surplus, or vested land found. Land above the ceiling limits (10 units per family) vests in the Government and cannot be privately transferred.",
                "law_reference": "Karnataka Land Reforms Act 1961 — Ceiling Provisions, Section 82",
                "recommendation": "Obtain ceiling declaration from the Revenue Department. Verify the property is not declared surplus land.",
            })

        if re.search(r"\btenant\b|\btenancy\b|\blessee\b", text):
            flags.append({
                "severity": "MEDIUM",
                "title": "Tenancy Rights — Potential Deemed Purchase Claim",
                "description": "Tenant references found. Tenants with 2+ years continuous possession can claim deemed purchase rights under Section 45 of Karnataka Land Reforms Act.",
                "law_reference": "Karnataka Land Reforms Act 1961 — Section 45",
                "recommendation": "Verify tenancy status. Obtain NOC from any tenants before purchase. Check if tenancy vesting application is pending with Revenue Court.",
            })
        return flags

    def _check_chain_continuity(self, flags: List, parsed: Dict, analysis: Dict) -> List:
        chain = analysis.get("ownership_chain") or parsed.get("ownership_chain", [])
        dates = parsed.get("property_details", {}).get("dates_found", [])

        if not chain or len(chain) < 2:
            existing = next((f for f in flags if "chain" in f.get("title", "").lower()), None)
            if not existing:
                flags.append({
                    "severity": "MEDIUM",
                    "title": "Ownership Chain — Insufficient History",
                    "description": "The document does not show a clear 30-year ownership chain. Karnataka courts require traceable title for minimum 30 years to establish marketable title.",
                    "law_reference": "Karnataka Legal Practice — 30-Year Chain Requirement",
                    "recommendation": "Obtain all prior sale deeds, mutation entries, and RTC records to establish a 30-year ownership chain.",
                })

        for entry in chain:
            if entry.get("owner_type") == "unknown" or entry.get("flag"):
                existing = next((f for f in flags if "unknown" in f.get("title", "").lower()), None)
                if not existing:
                    flags.append({
                        "severity": "HIGH",
                        "title": "Chain Gap — Unknown Ownership Period",
                        "description": f"Owner '{entry.get('owner_name', 'Unknown')}' has unclear title or document type. This creates a gap in the ownership chain.",
                        "law_reference": "Karnataka Legal Practice — 30-Year Chain",
                        "recommendation": "Obtain registered document explaining this transfer. Any unregistered transfer is not admissible as title evidence.",
                    })
                    break
        return flags

    def _check_gpa(self, flags: List, text: str) -> List:
        if re.search(r"\b(?:general\s+power\s+of\s+attorney|gpa|power\s+of\s+attorney)\b", text):
            existing = next((f for f in flags if "gpa" in f.get("title", "").lower() or "power of attorney" in f.get("title", "").lower()), None)
            if not existing:
                flags.append({
                    "severity": "HIGH",
                    "title": "GPA Transaction — Invalid Title Risk",
                    "description": (
                        "Power of Attorney transaction detected. Per the Supreme Court ruling in "
                        "Suraj Lamp & Industries v State of Haryana (2012), sale through GPA "
                        "without a registered sale deed does NOT transfer title. Such transactions "
                        "are not valid conveyances."
                    ),
                    "law_reference": "Supreme Court — Suraj Lamp & Industries v State of Haryana (2012); Registration Act 1908 — Section 17",
                    "recommendation": "Verify whether a registered sale deed exists behind the GPA transaction. If GPA sale predates 2012, check Karnataka Government regularisation scheme.",
                })
        return flags

    def _check_govt_land(self, flags: List, text: str) -> List:
        if re.search(r"\b(?:gomal|kharab|tank\s*bed|naala|raja\s*kaluve|govt\s*land|government\s*land|forest\s*land)\b", text):
            flags.append({
                "severity": "CRITICAL",
                "title": "Government / Reserved Land Category",
                "description": "Document references Gomal (grazing), Kharab (wasteland), tank bed, naala, or other government reserved categories. These vest absolutely in the Government under the Karnataka Land Revenue Act and cannot be privately owned or transferred.",
                "law_reference": "Karnataka Land Revenue Act 1964 — Section 79",
                "recommendation": "STOP — Do not purchase. Verify land category with Revenue Department. Any purported title to government land is void.",
            })
        return flags

    def _check_dc_conversion(self, flags: List, parsed: Dict, text: str) -> List:
        is_urban = re.search(r"\b(?:bbmp|bda|layout|apartment|flat|residential|commercial|industrial)\b", text)
        has_conversion = re.search(r"\b(?:dc\s*conversion|section\s*95|non.?agricultural\s*(?:use|order)|converted\s*land)\b", text)

        if is_urban and not has_conversion:
            flags.append({
                "severity": "HIGH",
                "title": "DC Conversion Status — Unverified",
                "description": "Property appears to be used for residential/commercial purposes but no DC Conversion order (Section 95, Karnataka Land Revenue Act) is referenced in the document.",
                "law_reference": "Karnataka Land Revenue Act 1964 — Section 95",
                "recommendation": "Obtain DC Conversion order from Revenue Department. Verify conversion was for the correct extent and purpose. Check if conversion fees/betterment levy were paid.",
            })
        return flags

    def _check_rera(self, flags: List, text: str) -> List:
        if re.search(r"\b(?:apartment|flat|promoter|developer|allottee|carpet\s*area|undivided\s*share|uds)\b", text):
            if not re.search(r"\brera\b|\brera\s*(?:registered|registration|no|number)\b", text):
                flags.append({
                    "severity": "HIGH",
                    "title": "RERA Registration — Not Verified",
                    "description": "Document relates to an apartment/flat sale but RERA registration number is not mentioned. Projects above 500 sq.m or 8+ units must be RERA registered.",
                    "law_reference": "RERA Act 2016 — Section 3; RERA Karnataka",
                    "recommendation": "Verify RERA registration on rera.karnataka.gov.in. Do not book/purchase from unregistered project.",
                })
        return flags

    def _check_bbmp_khatha(self, flags: List, text: str) -> List:
        if re.search(r"\bb.?khatha\b|\bkhatha\s*b\b|\bsemi.?regularised\b", text, re.IGNORECASE):
            flags.append({
                "severity": "MEDIUM",
                "title": "B-Khatha Property — Restricted Legality",
                "description": "B-Khatha indicates a semi-regularised or disputed property in BBMP jurisdiction. B-Khatha properties cannot obtain building plan approval and have limited bank loan eligibility.",
                "law_reference": "BBMP Act 2020 — Khatha Classification",
                "recommendation": "Verify reasons for B-Khatha status. Check if property qualifies for regularisation under current BBMP scheme. Avoid purchase unless converted to A-Khatha.",
            })
        return flags

    def _check_dates_and_registration(self, flags: List, parsed: Dict, text: str) -> List:
        details = parsed.get("property_details", {})
        dates = details.get("dates_found", [])

        if not dates:
            flags.append({
                "severity": "LOW",
                "title": "No Transaction Dates Extracted",
                "description": "No dates were extracted from the document. This may indicate poor OCR quality or the document lacks transaction dates.",
                "law_reference": "General Due Diligence",
                "recommendation": "Manually verify document dates. Ensure registration date is present on the sale deed.",
            })

        if re.search(r"\bunregistered\b|\bnot\s*registered\b|\bno\s*registration\b", text):
            flags.append({
                "severity": "HIGH",
                "title": "Unregistered Document",
                "description": "Document appears to be unregistered. Unregistered sale deeds, gift deeds, and mortgage deeds are not admissible as evidence of title under Section 17 of the Registration Act.",
                "law_reference": "Registration Act 1908 — Section 17",
                "recommendation": "Registered document is mandatory for valid title. Obtain registered copy from Sub-Registrar office.",
            })
        return flags

    def _deduplicate_flags(self, flags: List) -> List:
        seen = set()
        unique = []
        for f in flags:
            key = f.get("title", "")[:40].lower()
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def _compute_risk_level(self, flags: List, analysis: Dict) -> str:
        existing = analysis.get("risk_level", "LOW")
        if any(f["severity"] == "CRITICAL" for f in flags):
            return "CRITICAL"
        if any(f["severity"] == "HIGH" for f in flags):
            if existing == "CRITICAL":
                return "CRITICAL"
            return "HIGH"
        if any(f["severity"] == "MEDIUM" for f in flags):
            if existing in ("CRITICAL", "HIGH"):
                return existing
            return "MEDIUM"
        return existing if existing in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "LOW"

    def _compute_scores(self, flags: List, parsed: Dict, analysis: Dict) -> Dict:
        existing_scores = analysis.get("scores", {})

        penalty = sum({
            "CRITICAL": 35,
            "HIGH":     20,
            "MEDIUM":   10,
            "LOW":       5,
        }.get(f["severity"], 0) for f in flags)

        base = 90
        chain = parsed.get("ownership_chain", [])
        chain_score = min(100, max(0, 60 + len(chain) * 8 - penalty))
        clarity_score = max(0, base - penalty)
        compliance_score = max(0, base - penalty - (5 if parsed.get("has_grant_land") else 0))

        return {
            "title_clarity":      existing_scores.get("title_clarity",     clarity_score),
            "chain_continuity":   existing_scores.get("chain_continuity",  chain_score),
            "legal_compliance":   existing_scores.get("legal_compliance",  compliance_score),
        }
