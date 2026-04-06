from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.eval.real_pdf_validation import validate_real_pdfs


DEFAULT_OLLAMA_EXE = Path.home() / "AppData/Local/Programs/Ollama/ollama.exe"


def _write_markdown(report: dict, target: Path, model: str) -> None:
    lines = [
        "# Real PDF Final Validation",
        "",
        f"- Model: `{model}`",
        f"- Overall pass: `{report['overall_pass']}`",
        "",
        "## Documents",
    ]

    for document in report["documents"]:
        lines.extend(
            [
                (
                    f"- `{document['document_id']}` | authority=`{document['authority_level']}` "
                    f"| title=`{document['title']}` | version=`{document['version']}` "
                    f"| pages=`{document['pages']}`"
                ),
                f"  source: `{document['source_uri']}`",
            ]
        )

    lines.extend(["", "## Retrieval Checks"])
    for check in report["retrieval_checks"]:
        top_result = check["top_results"][0] if check["top_results"] else None
        lines.append(f"- `{check['query_id']}` pass=`{check['pass']}` query=`{check['query']}`")
        if top_result:
            lines.append(
                (
                    f"  top result: `{top_result['document_id']}` page=`{top_result['page']}` "
                    f"authority=`{top_result['authority_level']}` "
                    f"title=`{top_result['title']}`"
                )
            )
            lines.append(
                (
                    f"  citation: document=`{top_result['citation']['document']}` "
                    f"title=`{top_result['citation']['title']}` "
                    f"page=`{top_result['citation']['page']}`"
                )
            )

    lines.extend(
        [
            "",
            "## LLM Judgement",
            f"- normative lead: `{report['llm_judgement'].get('normative_lead_document_id')}`",
            f"- contextual document: `{report['llm_judgement'].get('contextual_document_id')}`",
            f"- authority policy passed: `{report['llm_judgement'].get('authority_policy_passed')}`",
            f"- summary: {report['llm_judgement'].get('summary', '')}",
        ]
    )

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run real-document validation with offline PDF preprocessing and a local Ollama model.")
    parser.add_argument("--spec-pdf", required=True)
    parser.add_argument("--context-pdf", required=True)
    parser.add_argument("--model", default="qwen2.5:0.5b")
    parser.add_argument("--ollama-exe", default=str(DEFAULT_OLLAMA_EXE))
    parser.add_argument("--output-json", default=".sisyphus/evidence/real-pdf-validation.json")
    parser.add_argument("--output-md", default=".sisyphus/evidence/real-pdf-validation.md")
    args = parser.parse_args()

    report = validate_real_pdfs(
        spec_pdf=args.spec_pdf,
        contextual_pdf=args.context_pdf,
        model=args.model,
        ollama_executable=args.ollama_exe,
    )

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(report, output_md, args.model)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
