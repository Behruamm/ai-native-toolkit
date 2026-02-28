import argparse
import sys
import json
import asyncio
from .scraper import extract
from .pipeline import run_full
from .pdf_report import generate_pdf, generate_post_pdf
from .types import FullAnalysis
from .deconstructor import deconstruct_post


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Profile Content Strategy Analyzer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: extract
    ext_parser = subparsers.add_parser(
        "extract", help="Extract raw data from a profile via Apify (no analysis)"
    )
    ext_parser.add_argument(
        "--url",
        type=str,
        action="append",
        help="LinkedIn profile or post URL (repeatable)",
    )
    ext_parser.add_argument(
        "--limit-per-source",
        type=int,
        help="Max posts per source URL (Apify limitPerSource)",
    )
    ext_parser.add_argument(
        "--scrape-until",
        type=str,
        help="Only scrape posts newer than this date (YYYY-MM-DD)",
    )
    ext_parser.add_argument(
        "--deep-scrape",
        action="store_true",
        default=None,
        help="Scrape additional post information",
    )
    ext_parser.add_argument(
        "--raw-data",
        action="store_true",
        help="Return raw data from the scraper",
    )

    # Command: profile (formerly analyze)
    ana_parser = subparsers.add_parser("profile", help="Perform full profile analysis")
    ana_parser.add_argument(
        "--url", type=str, help="LinkedIn profile URL to scrape first"
    )
    ana_parser.add_argument(
        "--limit-per-source",
        type=int,
        help="Max posts per source URL (Apify limitPerSource)",
    )
    ana_parser.add_argument(
        "--scrape-until",
        type=str,
        help="Only scrape posts newer than this date (YYYY-MM-DD)",
    )
    ana_parser.add_argument(
        "--deep-scrape",
        action="store_true",
        default=None,
        help="Scrape additional post information",
    )
    ana_parser.add_argument(
        "--raw-data",
        action="store_true",
        help="Return raw data from the scraper",
    )
    ana_parser.add_argument(
        "--file", type=str, help="Path to local JSON file (skips scraping)"
    )
    ana_parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI insights, generating deterministic metrics only",
    )
    ana_parser.add_argument(
        "--output", type=str, help="Path to save JSON analysis output (optional)"
    )

    # Command: post (single-post viral deconstructor)
    post_parser = subparsers.add_parser("post", help="Deconstruct a single LinkedIn post")
    post_parser.add_argument(
        "--url", type=str, required=True, help="LinkedIn post URL to deconstruct"
    )
    post_parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI insights, run deterministic analysis only",
    )
    post_parser.add_argument(
        "--output", type=str, help="Path to save JSON output (optional)"
    )
    post_parser.add_argument(
        "--pdf", type=str, help="Path to save PDF report (optional, e.g. report.pdf)"
    )
    post_parser.add_argument(
        "--no-cta",
        action="store_true",
        help="Omit the CTA page from the PDF",
    )

    # Command: pdf
    pdf_parser = subparsers.add_parser("pdf", help="Generate 8-page PDF report")
    pdf_parser.add_argument("--url", type=str, help="LinkedIn profile URL")
    pdf_parser.add_argument(
        "--limit-per-source",
        type=int,
        help="Max posts per source URL (Apify limitPerSource)",
    )
    pdf_parser.add_argument(
        "--scrape-until",
        type=str,
        help="Only scrape posts newer than this date (YYYY-MM-DD)",
    )
    pdf_parser.add_argument(
        "--deep-scrape",
        action="store_true",
        default=None,
        help="Scrape additional post information",
    )
    pdf_parser.add_argument(
        "--raw-data",
        action="store_true",
        help="Return raw data from the scraper",
    )
    pdf_parser.add_argument(
        "--file", type=str, help="Path to local JSON file (skips scraping)"
    )
    pdf_parser.add_argument(
        "--output", type=str, required=True, help="Path to save PDF report"
    )
    pdf_parser.add_argument(
        "--no-cta",
        action="store_true",
        help="Omit the CTA page from the PDF",
    )

    args = parser.parse_args()

    if args.command == "extract":
        if not args.url:
            print("Error: --url is required for extract command")
            sys.exit(1)

        try:
            urls = []
            for u in args.url or []:
                urls.extend([x.strip() for x in u.split(",") if x.strip()])
            print(f"Scraping {', '.join(urls)} via Apify...")
            deep_scrape = True if args.deep_scrape is None else args.deep_scrape
            data = extract(
                urls if len(urls) > 1 else urls[0],
                limit_per_source=args.limit_per_source,
                scrape_until=args.scrape_until,
                deep_scrape=deep_scrape,
                raw_data=args.raw_data,
            )
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Extraction failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "profile":
        if not args.url and not args.file:
            print("Error: Must provide either --url or --file")
            sys.exit(1)

        try:
            analysis = asyncio.run(
                run_full(
                    profile_url=args.url,
                    skip_ai=args.skip_ai,
                    local_file_json=args.file,
                    limit_per_source=args.limit_per_source,
                    scrape_until=args.scrape_until,
                    deep_scrape=True if args.deep_scrape is None else args.deep_scrape,
                    raw_data=args.raw_data,
                )
            )

            output_json = analysis.model_dump_json(indent=2)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"Saved analysis to {args.output}")
            else:
                print(output_json)

        except Exception as e:
            print(f"Analysis failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "post":
        try:
            result = asyncio.run(
                deconstruct_post(
                    post_url=args.url,
                    skip_ai=args.skip_ai,
                )
            )

            output_json = result.model_dump_json(indent=2)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"Saved deconstruction to {args.output}")
            else:
                print(output_json)

            if args.pdf:
                pdf_bytes = generate_post_pdf(result, include_cta=not args.no_cta)
                with open(args.pdf, "wb") as f:
                    f.write(pdf_bytes)
                print(f"Saved PDF to {args.pdf}")

        except Exception as e:
            print(f"Post deconstruction failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "pdf":
        if not args.url and not args.file:
            print("Error: Must provide either --url or --file")
            sys.exit(1)

        try:
            analysis = None
            if args.file:
                with open(args.file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "profileName" in data and "cadence" in data:
                    analysis = FullAnalysis.model_validate(data)

            if analysis is None:
                analysis = asyncio.run(
                    run_full(
                        profile_url=args.url,
                        skip_ai=False,
                        local_file_json=args.file,
                        limit_per_source=args.limit_per_source,
                        scrape_until=args.scrape_until,
                        deep_scrape=True if args.deep_scrape is None else args.deep_scrape,
                        raw_data=args.raw_data,
                    )
                )

            pdf_bytes = generate_pdf(analysis, include_cta=not args.no_cta)

            with open(args.output, "wb") as f:
                f.write(pdf_bytes)

            print(f"Successfully generated PDF report at: {args.output}")

        except Exception as e:
            print(f"PDF generation failed: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
