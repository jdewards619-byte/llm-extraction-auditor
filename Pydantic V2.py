import re
from typing import Dict, Any, List


class ExtractionAuditor:
    def __init__(self, source_text: str):
        self.source_text = source_text

    def audit_raw_payload(self, raw_text: str, target_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Free Tier: Audits the raw LLM output and logs every infraction
        without performing the auto-repair export.
        """
        report = {
            "is_clean": True,
            "lazy_tax_eligible": False,
            "syntax_violations": [],
            "grounding_violations": [],
            "flagged_fields": {}
        }

        # 1. Audit Markdown & Syntax Hygiene
        if "```" in raw_text:
            report["syntax_violations"].append("Payload contaminated with Markdown code fences.")
        if not raw_text.strip().endswith("}"):
            report["syntax_violations"].append("Truncated payload: Missing closing bracket '}'.")

        # 2. Audit Grounding (Did the model fabricate facts?)
        for field, value in target_data.items():
            if value is None:
                continue

            # Text grounding check
            if isinstance(value, str):
                # Check for dirty currency/symbols in raw values
                if re.search(r"[\$,]", value):
                    report["syntax_violations"].append(
                        f"Field '{field}' contains unparsed formatting symbols: '{value}'"
                    )

                clean_val = re.sub(r"[^\w\s-]", "", value).strip().lower()
                if clean_val and clean_val not in self.source_text.lower():
                    report["grounding_violations"].append(
                        f"Ungrounded Hallucination: Field '{field}' ('{value}') absent from source text."
                    )
                    report["flagged_fields"][field] = "FABRICATED"

            # Numeric grounding check
            elif isinstance(value, (int, float)):
                val_str = f"{value:.2f}"
                val_int = str(int(value))
                if val_str not in self.source_text and val_int not in self.source_text:
                    report["grounding_violations"].append(
                        f"Ungrounded Metric: Value '{value}' in field '{field}' not found in source text."
                    )
                    report["flagged_fields"][field] = "UNVERIFIED_NUMBER"

        # Tally results
        if report["syntax_violations"] or report["grounding_violations"]:
            report["is_clean"] = False
            report["lazy_tax_eligible"] = True

        return report

    def apply_lazy_tax(self, repaired_data: Dict[str, Any], is_subscribed: bool) -> Dict[str, Any]:
        """
        Paid Tier: Unlocks clean, production-ready export.
        """
        if not is_subscribed:
            return {
                "status": "LOCKED",
                "message": "Pay subscription to unlock 1-click schema healing and clean JSON export."
            }
        
        return {
            "status": "SUCCESS",
            "clean_payload": repaired_data
        }


# --- Demonstration ---
if __name__ == "__main__":
    source_doc = "INVOICE #99A | Apex Supplies LLC | Total Due: $1,450.00"

    # Dirty LLM output with both syntax issues and a hallucinated vendor
    raw_llm_stream = '```json {"vendor": "Acme Global", "total": "$1,450.00"'
    parsed_sample = {"vendor": "Acme Global", "total": "$1,450.00"}

    auditor = ExtractionAuditor(source_text=source_doc)
    audit_report = auditor.audit_raw_payload(raw_llm_stream, parsed_sample)

    print("=== FREE TIER AUDIT REPORT ===")
    print(f"Clean: {audit_report['is_clean']}")
    print("Syntax Errors Found:")
    for err in audit_report["syntax_violations"]:
        print(f"  [x] {err}")
    print("Hallucinations Caught:")
    for err in audit_report["grounding_violations"]:
        print(f"  [!] {err}")

    print("\n=== PAYWALL GATE ===")
    # Attempting to export without paying the lazy tax
    print(auditor.apply_lazy_tax(repaired_data={"vendor": "Apex Supplies LLC", "total": 1450.0}, is_subscribed=False))