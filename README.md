# LLM Extraction Auditor

A lightweight diagnostic linter that audits raw LLM outputs before they hit production databases. Detects syntax truncation, markdown block leaks, dirty formatting, and ungrounded hallucinations in sub-millisecond execution time.

## The Problem
LLMs frequently return invalid JSON:
- Wrapping payloads in conversational text or markdown code fences (` ```json `).
- Dropping closing braces `}` or quotes.
- Injecting formatting like `$400.00` instead of a float `400.0`.
- Hallucinating entities and metrics that never existed in the source document.

Re-prompting the LLM costs tokens and adds seconds of latency. This auditor catches defects instantly on the CPU.

## Installation

```bash
git clone https://github.com/jdewards619-byte/llm-extraction-auditor.git
cd llm-extraction-auditor
pip install ollama json-repair pydantic
