"""Create the private source release. --initialize is an explicit first-time setup.

Normal saves prepare releases automatically. Run this after direct DB migrations.
Never marks a target database as source without explicit --initialize approval.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import db, new_id
from content_sync.schema import CONFIG_FILE, config
from content_sync.state import ensure_indexes, environment_id, database_binding
from content_sync.source import capture


async def main(initialize):
    await ensure_indexes(db)
    identity = await environment_id(db)
    if initialize:
        current = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {"channel": new_id()}
        current["source_id"] = identity
        current["source_binding"] = database_binding(db)
        CONFIG_FILE.write_text(json.dumps(current, indent=2) + "\n")
    result = await capture(db, force=True, archive=True)
    print(json.dumps({k: v for k, v in result.items() if k in {"state", "release_id", "counts", "captured_at"}}, indent=2))
    if result.get("state") not in {"ready", "target"}:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.initialize))