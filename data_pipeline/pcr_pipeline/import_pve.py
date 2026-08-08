from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .pve_fixture import import_fire_8_10


def main() -> int:
    configured_database_url = os.getenv("PCR_DATABASE_URL", "").strip() or None
    parser = argparse.ArgumentParser(description="Import the verified Fire 8-10 fixture closure")
    parser.add_argument(
        "--research-core",
        type=Path,
        default=Path("research_core/pcr_tw_project"),
    )
    parser.add_argument(
        "--database-url",
        default=configured_database_url,
        required=configured_database_url is None,
    )
    args = parser.parse_args()

    engine = create_engine(args.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        result = import_fire_8_10(session, args.research_core)
    print(json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True, default=list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
