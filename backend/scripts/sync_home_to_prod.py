"""Retired: home-only promotion caused incomplete production pages.

Prepare a COMPLETE release with scripts/prepare_content_release.py instead.
Republish packages that snapshot; target startup creates a backup and imports
all content. No production URL, passwords or partial overwrite live in this file.
"""

if __name__ == "__main__":
    raise SystemExit("Home-only sync is retired. Run scripts/prepare_content_release.py, then republish the complete content release.")