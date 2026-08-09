import analysis_core
from website_publish import publish_website


PROJECT_SNAPSHOT = """## Project Snapshot

| Project type | Dataset | Tools | Outputs |
|---|---|---|---|
| Simulated Quantitative Case Study | 50,000-Person Synthetic UK Adult Population | Python / Pandas / NumPy / Matplotlib | Repeated-Sample Estimates; Sampling Performance Summary; Reference Samples; Figures |

**Skills demonstrated:** Sampling · Statistical Analysis
"""

_original_generate_report = analysis_core.generate_report


def generate_report_with_snapshot(*args, **kwargs) -> None:
    _original_generate_report(*args, **kwargs)
    report_path = analysis_core.REPORT_FILE
    report = report_path.read_text(encoding="utf-8")

    if "## Project Snapshot" in report:
        return

    title, remainder = report.split("\n\n", 1)
    report_path.write_text(
        f"{title}\n\n{PROJECT_SNAPSHOT.strip()}\n\n{remainder}",
        encoding="utf-8",
    )


analysis_core.generate_report = generate_report_with_snapshot


if __name__ == "__main__":
    analysis_core.main()
    try:
        publish_website()
    except RuntimeError as exc:
        raise SystemExit(f"\nWebsite publishing stopped: {exc}") from None
