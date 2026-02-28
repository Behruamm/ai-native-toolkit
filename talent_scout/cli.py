import argparse
import sys
import json
import asyncio

from .pipeline import run_scout
from .pdf_report import generate_talent_pdf
from .types import TalentReport


def main():
    parser = argparse.ArgumentParser(
        description="Talent Scout — Competitor Talent Intelligence via LinkedIn"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── Command: scout ───────────────────────────────────────
    scout_parser = subparsers.add_parser(
        "scout",
        help="Run full talent scouting pipeline (scrape + AI ranking + outreach drafts)",
    )
    scout_parser.add_argument(
        "--url",
        type=str,
        help='LinkedIn company people URL (e.g. https://www.linkedin.com/company/google/people/)',
    )
    scout_parser.add_argument(
        "--title",
        type=str,
        required=False,
        default="",
        help='Target job title filter (e.g. "Senior Software Engineer")',
    )
    scout_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of candidates to retrieve (default: all)",
    )
    scout_parser.add_argument(
        "--file",
        type=str,
        help="Path to local JSON file of raw candidates (skips scraping)",
    )
    scout_parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI analysis — return only cleaned candidate list",
    )
    scout_parser.add_argument(
        "--output",
        type=str,
        help="Path to save JSON report (optional, prints to stdout if omitted)",
    )
    scout_parser.add_argument(
        "--pdf",
        type=str,
        help="Path to save PDF talent brief (optional, e.g. report.pdf)",
    )

    # ── Command: extract ─────────────────────────────────────
    ext_parser = subparsers.add_parser(
        "extract",
        help="Scrape raw candidate data only (no AI analysis)",
    )
    ext_parser.add_argument("--url", type=str, required=True, help="LinkedIn company people URL")
    ext_parser.add_argument("--title", type=str, default="", help="Target job title filter")
    ext_parser.add_argument("--limit", type=int, default=None, help="Max candidates to retrieve")
    ext_parser.add_argument("--output", type=str, help="Path to save raw JSON")

    # ── Command: pdf ─────────────────────────────────────────
    pdf_parser = subparsers.add_parser(
        "pdf",
        help="Generate PDF talent brief from an existing JSON report",
    )
    pdf_parser.add_argument(
        "--file", type=str, required=True, help="Path to a TalentReport JSON file"
    )
    pdf_parser.add_argument(
        "--output", type=str, required=True, help="Path to save the PDF report"
    )

    args = parser.parse_args()

    # ── scout ────────────────────────────────────────────────
    if args.command == "scout":
        if not args.url and not args.file:
            print("Error: Must provide either --url or --file", file=sys.stderr)
            sys.exit(1)

        try:
            report = asyncio.run(
                run_scout(
                    company_url=args.url or "",
                    target_title=args.title,
                    skip_ai=args.skip_ai,
                    local_file_json=args.file,
                    limit=args.limit,
                )
            )

            output_json = report.model_dump_json(indent=2)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"Saved report to {args.output}")
            else:
                print(output_json)

            if args.pdf:
                pdf_bytes = generate_talent_pdf(report)
                with open(args.pdf, "wb") as f:
                    f.write(pdf_bytes)
                print(f"Saved PDF to {args.pdf}")

        except Exception as e:
            print(f"Scouting failed: {e}", file=sys.stderr)
            sys.exit(1)

    # ── extract ──────────────────────────────────────────────
    elif args.command == "extract":
        from .scraper import scrape_company_people

        try:
            print(f"Scraping {args.url} via Apify (title filter: '{args.title}')...")
            raw = scrape_company_people(
                company_url=args.url,
                target_title=args.title,
                limit=args.limit,
            )
            output = json.dumps(raw, indent=2, ensure_ascii=False)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"Saved {len(raw)} candidates to {args.output}")
            else:
                print(output)

        except Exception as e:
            print(f"Extraction failed: {e}", file=sys.stderr)
            sys.exit(1)

    # ── pdf ──────────────────────────────────────────────────
    elif args.command == "pdf":
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                data = json.load(f)
            report = TalentReport.model_validate(data)
            pdf_bytes = generate_talent_pdf(report)
            with open(args.output, "wb") as f:
                f.write(pdf_bytes)
            print(f"Saved PDF to {args.output}")

        except Exception as e:
            print(f"PDF generation failed: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
