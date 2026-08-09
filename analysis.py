from analysis_core import main
from website_publish import publish_website


if __name__ == "__main__":
    main()
    try:
        publish_website()
    except RuntimeError as exc:
        raise SystemExit(f"\nWebsite publishing stopped: {exc}") from None
