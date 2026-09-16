import json
import re
from typing import Any, Dict
import ollama
from json_repair import repair_json


class ExtractionAuditor:
    def __init__(self, source_text: str):
        self.source_text = source_text

    def _extract_root_object(self, raw_data: Any) -> Dict[str, Any]:
        """Defensively normalizes lists or unexpected wrappers into a plain dictionary."""
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict) and item:
                    return item
            return {}
        if isinstance(raw_data, dict):
            return raw_data
        return {}

    def audit(self, raw_response: str, parsed_data: Any) -> Dict[str, Any]:
        """Free Tier Diagnostic: Only analyzes and surfaces defects; does not fix them."""
        report = {
            "status": "PASS",
            "is_clean": True,
            "syntax_violations": [],
            "grounding_violations": [],
            "flagged_fields": {},
            "upgrade_callout": None,
        }

        # Catch array/list structure mismatches
        if isinstance(parsed_data, list):
            report["syntax_violations"].append(
                "Structural issue: Model returned a JSON list/array instead of a root object."
            )
            parsed_data = self._extract_root_object(parsed_data)
        elif not isinstance(parsed_data, dict):
            report["syntax_violations"].append(
                f"Structural issue: Unexpected payload type '{type(parsed_data).__name__}'."
            )
            parsed_data = {}

        # Check raw markdown formatting leaks
        if "```" in raw_response:
            report["syntax_violations"].append("Markdown code block wrapper detected in stream.")
        if not raw_response.strip().endswith("}"):
            report["syntax_violations"].append("Malformed envelope: Missing or truncated closing brace '}'.")

        # Field-level inspections
        for field, val in parsed_data.items():
            if val is None:
                continue

            # String entity grounding
            if isinstance(val, str):
                if re.search(r"[\$,]", val):
                    report["syntax_violations"].append(
                        f"Field '{field}' contains unparsed currency formatting: '{val}'"
                    )
                clean_val = re.sub(r"[^\w\s-]", "", val).strip().lower()
                if clean_val and clean_val not in self.source_text.lower():
                    report["grounding_violations"].append(
                        f"Ungrounded Entity: '{val}' not found in source document."
                    )
                    report["flagged_fields"][field] = "HALLUCINATION_DETECTED"

            # Numeric value grounding
            elif isinstance(val, (int, float)):
                val_2dec = f"{val:.2f}"
                val_int = str(int(val))
                if val_2dec not in self.source_text and val_int not in self.source_text:
                    report["grounding_violations"].append(
                        f"Ungrounded Metric: Numeric value '{val}' not found in source document."
                    )
                    report["flagged_fields"][field] = "METRIC_MISMATCH"

        # Tally final diagnostic verdict
        if report["syntax_violations"] or report["grounding_violations"]:
            report["status"] = "FLAGGED"
            report["is_clean"] = False
            total_issues = len(report["syntax_violations"]) + len(report["grounding_violations"])
            report["upgrade_callout"] = (
                f"{total_issues} defect(s) detected. "
                "Deterministic 1-click healing engine launching soon. "
                "Pre-register to get your first 2 months of automated repairs free."
            )

        return report


if __name__ == "__main__":
    source_document = """
    INVOICE #TX-4091
    Vendor: Lone Star Fleet Repairs
    Date: September 15, 2026
    Services:
      - Brake Pad Replacement: $220.00
      - Rotor Resurfacing: $180.00
    Total Due: $400.00
    """

    print("Querying local Ollama model (llama3.2)...")
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": "Extract vendor_name, invoice_number, and total_amount as JSON.",
            },
            {"role": "user", "content": f"Document:\n{source_document}"},
        ],
    )

    raw_output = response["message"]["content"]
    print("\n--- RAW MODEL OUTPUT ---")
    print(raw_output)

    # Safe preliminary parse strictly for audit consumption
    repaired_raw = repair_json(raw_output)
    preliminary_parsed = json.loads(repaired_raw)

    # Run the free diagnostic audit
    auditor = ExtractionAuditor(source_text=source_document)
    audit_report = auditor.audit(raw_response=raw_output, parsed_data=preliminary_parsed)

    print("\n=== DIAGNOSTIC AUDIT REPORT ===")
    print(f"Status: {audit_report['status']}")
    print(f"Payload Clean: {audit_report['is_clean']}")

    if audit_report["syntax_violations"]:
        print("\nSyntax Violations:")
        for err in audit_report["syntax_violations"]:
            print(f"  [!] {err}")

    if audit_report["grounding_violations"]:
        print("\nGrounding & Hallucination Flags:")
        for err in audit_report["grounding_violations"]:
            print(f"  [X] {err}")

    if audit_report["upgrade_callout"]:
        print("\n=== UPGRADE NOTICE ===")
        print(audit_report["upgrade_callout"])