from __future__ import annotations

from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent

CASE_STUDY_TITLE = "Sampling Strategy Comparison"
CASE_STUDY_SLUG = "sampling-strategy-comparison"
CASE_STUDY_DATE = "2026"
CASE_STUDY_LEDE = (
    "A simulated sampling study using a known 50,000-person population to compare "
    "bias, precision, and representativeness across four sampling strategies."
)

WEBSITE_REPOSITORY = "ag-prudenzano/ag-prudenzano.github.io"
WEBSITE_REMOTE = f"https://github.com/{WEBSITE_REPOSITORY}.git"
WEBSITE_BRANCH = "main"
TEMPLATE_PAGE = "survey-response-quality-audit.html"
SCRIPT_FILE = "script.js"
INDEX_FILE = "index.html"
PUBLISH_TOKEN_ENV = "PORTFOLIO_PUBLISH_TOKEN"

SURVEY_TEMPLATE_TITLE = "Survey Response Quality Audit"
SURVEY_TEMPLATE_SLUG = "survey-response-quality-audit"
SURVEY_TEMPLATE_LEDE = (
    "A simulated audit of 1,250 UK online survey responses using eight "
    "respondent-level quality checks to identify records for review or exclusion."
)


def run_command(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
        env=env,
    )


def source_repository_is_clean() -> bool:
    result = run_command(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "report.md",
            "data/sampling_strategy_population.csv",
            "outputs",
            "figures",
        ],
        cwd=ROOT,
    )
    return not result.stdout.strip()


def current_source_commit() -> str:
    result = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT)
    return result.stdout.strip()


def get_publish_environment() -> dict[str, str]:
    token = os.environ.get(PUBLISH_TOKEN_ENV, "").strip()
    if not token:
        raise RuntimeError(
            "Automatic website publishing needs a one-time Codespaces secret named "
            f"{PUBLISH_TOKEN_ENV}. The secret must contain a GitHub token that can "
            f"write repository contents in {WEBSITE_REPOSITORY}."
        )

    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env.pop("GITHUB_TOKEN", None)
    return env


def configure_git_credentials(env: dict[str, str]) -> None:
    if not shutil.which("gh"):
        raise RuntimeError(
            "GitHub CLI is required for automatic website publishing in this Codespace."
        )

    setup = subprocess.run(
        ["gh", "auth", "setup-git"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if setup.returncode != 0:
        detail = (setup.stderr or setup.stdout).strip()
        raise RuntimeError(f"Could not configure GitHub credentials: {detail}")


def configure_commit_identity(website_root: Path) -> None:
    name = run_command(
        ["git", "config", "user.name"], cwd=ROOT, check=False
    ).stdout.strip()
    email = run_command(
        ["git", "config", "user.email"], cwd=ROOT, check=False
    ).stdout.strip()

    run_command(
        ["git", "config", "user.name", name or "AG Prudenzano"],
        cwd=website_root,
    )
    run_command(
        [
            "git",
            "config",
            "user.email",
            email or "309410350+ag-prudenzano@users.noreply.github.com",
        ],
        cwd=website_root,
    )


def update_publication_map(script_text: str) -> str:
    entry = (
        f'  "{CASE_STUDY_TITLE}": {{\n'
        f'    href: "{CASE_STUDY_SLUG}.html",\n'
        f'    date: "{CASE_STUDY_DATE}",\n'
        "  },"
    )

    pattern = re.compile(
        rf'  "{re.escape(CASE_STUDY_TITLE)}": \{{\n'
        r'    href: "[^"]+",\n'
        r'    date: "[^"]+",\n'
        r'  \},'
    )

    if pattern.search(script_text):
        return pattern.sub(entry, script_text, count=1)

    marker = "const publishedPortfolioStudies = {\n"
    if marker not in script_text:
        raise RuntimeError("Could not find the website publication map in script.js.")

    return script_text.replace(marker, marker + entry + "\n", 1)


def build_report_page(template_text: str) -> str:
    page = template_text.replace(SURVEY_TEMPLATE_TITLE, CASE_STUDY_TITLE)
    page = page.replace(SURVEY_TEMPLATE_SLUG, CASE_STUDY_SLUG)
    page = page.replace(SURVEY_TEMPLATE_LEDE, CASE_STUDY_LEDE)
    return page


def update_script_cache_key(index_text: str, source_commit: str) -> str:
    cache_key = f"published-{CASE_STUDY_SLUG}-{source_commit}"
    return re.sub(
        r'script\.js\?v=[^"]+',
        f"script.js?v={cache_key}",
        index_text,
        count=1,
    )


def publish_website() -> None:
    if not (ROOT / "report.md").exists():
        print("Website publishing skipped: report.md does not exist yet.")
        return

    if not source_repository_is_clean():
        print(
            "Website publishing skipped because generated case-study files have "
            "uncommitted changes."
        )
        return

    publish_env = get_publish_environment()
    configure_git_credentials(publish_env)
    source_commit = current_source_commit()

    with tempfile.TemporaryDirectory(prefix="portfolio-website-") as temp_dir:
        website_root = Path(temp_dir) / "website"

        clone = run_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                WEBSITE_BRANCH,
                WEBSITE_REMOTE,
                str(website_root),
            ],
            cwd=Path(temp_dir),
            check=False,
            env=publish_env,
        )
        if clone.returncode != 0:
            detail = (clone.stderr or clone.stdout).strip()
            raise RuntimeError(f"Could not clone website repository: {detail}")

        configure_commit_identity(website_root)

        script_path = website_root / SCRIPT_FILE
        index_path = website_root / INDEX_FILE
        template_path = website_root / TEMPLATE_PAGE
        report_page_path = website_root / f"{CASE_STUDY_SLUG}.html"

        script_text = script_path.read_text(encoding="utf-8")
        script_path.write_text(
            update_publication_map(script_text),
            encoding="utf-8",
        )

        template_text = template_path.read_text(encoding="utf-8")
        report_page_path.write_text(
            build_report_page(template_text),
            encoding="utf-8",
        )

        index_text = index_path.read_text(encoding="utf-8")
        index_path.write_text(
            update_script_cache_key(index_text, source_commit),
            encoding="utf-8",
        )

        changed = run_command(
            ["git", "status", "--porcelain"],
            cwd=website_root,
        ).stdout.strip()
        if not changed:
            print("Website is already up to date.")
            return

        run_command(
            [
                "git",
                "add",
                "--",
                SCRIPT_FILE,
                INDEX_FILE,
                f"{CASE_STUDY_SLUG}.html",
            ],
            cwd=website_root,
        )
        run_command(
            ["git", "commit", "-m", f"Publish {CASE_STUDY_TITLE}"],
            cwd=website_root,
        )

        push = run_command(
            ["git", "push", "origin", WEBSITE_BRANCH],
            cwd=website_root,
            check=False,
            env=publish_env,
        )
        if push.returncode != 0:
            detail = (push.stderr or push.stdout).strip()
            raise RuntimeError(
                f"Could not push the website update to {WEBSITE_REPOSITORY}. "
                f"Check that {PUBLISH_TOKEN_ENV} has write access to that repository. "
                f"Details: {detail}"
            )

        print(f"Website updated and pushed to {WEBSITE_REPOSITORY}.")
