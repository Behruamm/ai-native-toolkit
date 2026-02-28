import asyncio
from linkedin_analyzer.pipeline import run_full
from linkedin_analyzer.pdf_report import generate_pdf


async def main():
    # Example local run bypassing AI via the local test fixture
    # This demonstrates the core libraries being used programmatically

    print("Running deterministic analysis on local fixture...")
    analysis = await run_full(
        skip_ai=True, local_file_json="../tests/fixtures/sample_posts.json"
    )

    # Generate the PDF
    pdf_bytes = generate_pdf(analysis)

    # Save
    with open("example_output.pdf", "wb") as f:
        f.write(pdf_bytes)

    print("Saved example_output.pdf")


if __name__ == "__main__":
    asyncio.run(main())
