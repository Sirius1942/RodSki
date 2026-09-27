"""Allow ``python -m rodski.rodski_cli`` to use the RodSki CLI entry point."""

from . import main


if __name__ == "__main__":
    raise SystemExit(main())
