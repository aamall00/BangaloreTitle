import os
import json
import logging
from typing import Dict, List, Any

log = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are a senior Karnataka land title attorney and due diligence expert with 20+ years of experience in Bengaluru real estate law. You have deep expertise in:
- Karnataka Land Revenue Act, 1964
- Karnataka Land Reforms Act, 1961 (including 2020 amendments)
- Prevention of Transfer of Certain Lands (PTCL) Act — SC/ST grant land protections
- RERA Karnataka regulations
- BBMP/BDA regulations for Bengaluru urban properties
- Indian Registration Act, 1908
- Transfer of Property Act, 1882

Your task: Analyse the provided land document text and relevant Karnataka law context to produce a comprehensive title due diligence report.

CRITICAL RULES:
1. Always flag Grant Land / PTCL issues as HIGH or CRITICAL risk — these void transactions
2. Always check 30-year chain continuity — any gap is at minimum MEDIUM risk
3. Section 79A/79B violations (pre-2020) are HIGH risk; check if transaction predates the 2020 amendment
4. Encumbrances without discharge NOC = HIGH risk
5. GPA transactions post-2012 = HIGH risk per Suraj Lamp Supreme Court ruling
6. Missing DC conversion for urban use = HIGH risk
7. B-Khatha properties in BBMP = MEDIUM risk minimum
8. Be precise with law citations (Act name + Section number)

Respond ONLY with valid JSON matching the exact schema provided."""

ANALYSIS_USER_PROMPT = """DOCUMENT TEXT:
{document_text}

RELEVANT KARNATAKA LAW CONTEXT:
{law_context}

ADDITIONAL CONTEXT: {additional_context}

PARSED DOCUMENT DETAILS:
- Document Type: {doc_type}
- Survey Number: {survey_number}
- Extent: {extent}
- Is Grant Land: {is_grant_land}
- Has Encumbrance: {has_encumbrance}
- Raw Flags: {raw_flags}
- Ownership Chain Entries: {chain_count}

Produce a comprehensive title due diligence analysis as JSON with this EXACT schema:
{{
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "summary": "2-3 sentence plain English summary of title status",
  "document_type_detected": "string",
  "property_details": {{
    "survey_number": "string or null",
    "extent": "string or null",
    "location": "string or null",
    "document_number": "string or null",
    "earliest_date": "string or null",
    "latest_date": "string or null",
    "is_grant_land": true/false,
    "has_encumbrance": true/false
  }},
  "scores": {{
    "title_clarity": 0-100,
    "chain_continuity": 0-100,
    "legal_compliance": 0-100
  }},
  "ownership_chain": [
    {{
      "owner_name": "string",
      "owner_type": "individual|company|government|current|unknown",
      "period": "string",
      "from_date": "string or null",
      "to_date": "string or null",
      "document_type": "string",
      "document_number": "string or null",
      "transfer_type": "string",
      "flag": "string or null (any legal issue with this link)"
    }}
  ],
  "flags": [
    {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "short flag title",
      "description": "detailed description of the issue",
      "law_reference": "Act Name, Section X",
      "recommendation": "specific action to resolve"
    }}
  ],
  "legal_analysis": {{
    "ptcl_analysis": "string — analysis of PTCL/SC/ST grant land issues (null if not applicable)",
    "land_reforms_analysis": "string — analysis of 79A/79B, ceiling, tenant issues",
    "land_revenue_analysis": "string — RTC, mutation, survey number, conversion analysis",
    "rera_analysis": "string — RERA compliance if apartment/developer (null if not applicable)",
    "dc_conversion_analysis": "string — DC conversion status and validity",
    "encumbrance_analysis": "string — mortgage, lien, court orders analysis"
  }},
  "recommendations": [
    "specific actionable recommendation 1",
    "specific actionable recommendation 2"
  ],
  "extracted_data": {{
    "all_names_found": [],
    "all_dates_found": [],
    "all_survey_numbers": [],
    "encumbrances_listed": [],
    "court_cases_found": []
  }}
}}"""


class TitleAnalyzer:
    def __init__(self, preferred_llm: str = "claude"):
        self.preferred_llm = preferred_llm

    def analyze(self, parsed: Dict, law_context: List[Dict], additional_context: str = "") -> Dict:
        law_text = self._format_law_context(law_context)
        document_text = parsed.get("full_text", "")[:8000]

        prompt = ANALYSIS_USER_PROMPT.format(
            document_text=document_text,
            law_context=law_text,
            additional_context=additional_context or "None provided",
            doc_type=parsed.get("doc_type", "unknown"),
            survey_number=parsed.get("property_details", {}).get("survey_number", "Not found"),
            extent=parsed.get("property_details", {}).get("extent", "Not found"),
            is_grant_land=parsed.get("has_grant_land", False),
            has_encumbrance=parsed.get("has_encumbrance", False),
            raw_flags=", ".join(parsed.get("raw_flags", [])) or "None",
            chain_count=len(parsed.get("ownership_chain", [])),
        )

        try:
            if self.preferred_llm in ("claude", "auto"):
                result = self._call_claude(prompt)
            else:
                result = self._call_openai(prompt)

            if not result:
                result = self._call_openai(prompt)

        except Exception as e:
            log.error(f"LLM analysis failed: {e}")
            result = self._fallback_analysis(parsed)

        if result.get("ownership_chain") is None or len(result.get("ownership_chain", [])) == 0:
            result["ownership_chain"] = parsed.get("ownership_chain", [])

        if not result.get("property_details"):
            result["property_details"] = parsed.get("property_details", {})

        return result

    def _call_claude(self, user_prompt: str) -> Dict:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
            message = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=ANALYSIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = message.content[0].text
            return self._parse_json_response(content)
        except Exception as e:
            log.error(f"Claude API error: {e}")
            raise

    def _call_openai(self, user_prompt: str) -> Dict:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=4096,
                temperature=0.1,
            )
            content = response.choices[0].message.content
            return self._parse_json_response(content)
        except Exception as e:
            log.error(f"OpenAI API error: {e}")
            raise

    def _parse_json_response(self, content: str) -> Dict:
        import re
        content = content.strip()

        # strip markdown code fences
        if "```" in content:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1).strip()

        # find the outermost { ... }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]

        # attempt direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # truncated JSON — strip trailing incomplete key/value and close open braces/brackets
        try:
            depth_brace = 0
            depth_bracket = 0
            in_string = False
            escape = False
            last_safe = 0
            for i, ch in enumerate(content):
                if escape:
                    escape = False
                    continue
                if ch == "\\" and in_string:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth_brace += 1
                elif ch == "}":
                    depth_brace -= 1
                elif ch == "[":
                    depth_bracket += 1
                elif ch == "]":
                    depth_bracket -= 1
                if depth_brace == 1 and depth_bracket == 0 and ch in (",", "{"):
                    last_safe = i

            truncated = content[:last_safe] + ("}" * depth_brace)
            return json.loads(truncated)
        except Exception:
            pass

        raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")

    def _format_law_context(self, law_context: List[Dict]) -> str:
        if not law_context:
            return "No specific law context retrieved."
        parts = []
        for item in law_context[:10]:
            parts.append(f"[{item.get('act','')} — {item.get('section','')}]\n{item.get('text','')}")
        return "\n\n".join(parts)

    def _fallback_analysis(self, parsed: Dict) -> Dict:
        details = parsed.get("property_details", {})
        flags = []
        risk = "MEDIUM"

        if parsed.get("has_grant_land"):
            flags.append({
                "severity": "CRITICAL",
                "title": "Grant Land Detected",
                "description": "Document contains references to Government Grant / SC/ST grant land. Transfer may be prohibited under PTCL Act.",
                "law_reference": "PTCL Act, Sections 4, 5, 7, 8",
                "recommendation": "Obtain original grant order and verify PTCL compliance with a Karnataka land law specialist before proceeding.",
            })
            risk = "CRITICAL"

        if parsed.get("has_encumbrance"):
            flags.append({
                "severity": "HIGH",
                "title": "Encumbrance Detected",
                "description": "Document mentions encumbrance, mortgage, or charge. Verify discharge status.",
                "law_reference": "Registration Act 1908 — Encumbrance Certificate",
                "recommendation": "Obtain 30-year EC from Sub-Registrar office and verify all encumbrances are discharged.",
            })
            if risk == "MEDIUM":
                risk = "HIGH"

        for flag in parsed.get("raw_flags", []):
            if flag == "litigation_detected":
                flags.append({
                    "severity": "HIGH",
                    "title": "Potential Litigation",
                    "description": "Document references court cases or legal proceedings.",
                    "law_reference": "Transfer of Property Act, Section 52 (Lis Pendens)",
                    "recommendation": "Conduct litigation search in City Civil Court and Karnataka High Court.",
                })
                if risk == "MEDIUM":
                    risk = "HIGH"
            elif flag == "gpa_transaction":
                flags.append({
                    "severity": "HIGH",
                    "title": "GPA Transaction",
                    "description": "Power of Attorney transaction detected. May not create valid title post-2012.",
                    "law_reference": "Supreme Court — Suraj Lamp & Industries v State of Haryana (2012)",
                    "recommendation": "Verify underlying registered sale deed. GPA alone does not transfer title.",
                })

        if not flags:
            flags.append({
                "severity": "MEDIUM",
                "title": "Manual Review Required",
                "description": "AI analysis unavailable (no API key configured). Document requires manual legal review.",
                "law_reference": "General Due Diligence",
                "recommendation": "Configure Claude or OpenAI API key in Settings for AI-powered analysis.",
            })

        return {
            "risk_level": risk,
            "summary": f"Document analysis completed with fallback mode. {'Grant land detected — PTCL Act compliance required.' if parsed.get('has_grant_land') else 'Configure API keys for full AI analysis.'} {len(flags)} issue(s) flagged.",
            "document_type_detected": parsed.get("doc_type", "unknown"),
            "property_details": details,
            "scores": {"title_clarity": 40, "chain_continuity": 40, "legal_compliance": 40},
            "ownership_chain": parsed.get("ownership_chain", []),
            "flags": flags,
            "legal_analysis": {
                "ptcl_analysis": "PTCL check requires AI analysis or manual review. Grant land references found." if parsed.get("has_grant_land") else None,
                "land_reforms_analysis": "Please configure API key for automated Karnataka Land Reforms Act analysis.",
                "land_revenue_analysis": f"Survey No: {details.get('survey_number', 'Not extracted')}. Extent: {details.get('extent', 'Not extracted')}.",
                "rera_analysis": None,
                "dc_conversion_analysis": "DC conversion status requires manual verification with Revenue Department.",
                "encumbrance_analysis": "Encumbrance found — verify discharge with Sub-Registrar EC." if parsed.get("has_encumbrance") else "No encumbrance keywords detected in document.",
            },
            "recommendations": [
                "Configure Claude or OpenAI API key in Settings for full AI-powered analysis.",
                "Obtain 30-year Encumbrance Certificate from Sub-Registrar office.",
                "Verify RTC (Form 11/12) and Mutation Register from Karnataka land records portal.",
                "Engage a Karnataka-based property lawyer for final title opinion.",
            ],
            "extracted_data": {
                "all_names_found": [],
                "all_dates_found": details.get("dates_found", []),
                "all_survey_numbers": details.get("all_survey_numbers", [details.get("survey_number")] if details.get("survey_number") else []),
                "encumbrances_listed": [],
                "court_cases_found": [],
            },
        }
