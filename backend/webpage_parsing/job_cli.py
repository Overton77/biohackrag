# webpage_parsing/job_cli.py
import asyncio
import json
import os
import sys
from argparse import ArgumentParser
from typing import List


from webpage_parsing.episode_enhacement_pipeline import (
    enhance_episodes_by_ids,
    enhance_all_episodes,
)

def parse_args():
    p = ArgumentParser(description="Episode enhancement job")
  
    p.add_argument("--mode", choices=["all", "ids"], default="all")
   
    p.add_argument("--ids", help="Comma-separated Episode ObjectIds", default="")
  
    p.add_argument("--concurrency", type=int, default=int(os.getenv("CONCURRENCY", "10")))
   
    p.add_argument("--only-missing-youtube", action="store_true")
    return p.parse_args()

def _ids_from_env_or_arg(ids_arg: str) -> List[str]:
  
    env_json = os.getenv("EPISODE_IDS_JSON")
    if env_json:
        try:
            data = json.loads(env_json)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass
   
    if ids_arg:
        return [x.strip() for x in ids_arg.split(",") if x.strip()]
  
    env_csv = os.getenv("EPISODE_IDS", "")
    if env_csv:
        return [x.strip() for x in env_csv.split(",") if x.strip()]
    return []

def main():
    args = parse_args()
    if args.mode == "ids":
        ids = _ids_from_env_or_arg(args.ids)
        if not ids:
            print("No episode IDs supplied for --mode=ids", file=sys.stderr)
            sys.exit(2)

        print(f"Enhancing {len(ids)} episode(s) with concurrency={args.concurrency} ...")
        asyncio.run(enhance_episodes_by_ids(ids, concurrency=args.concurrency))
        return

 
    print(f"Enhancing ALL eligible episodes with concurrency={args.concurrency} "
          f"only_missing_youtube={args.only_missing_youtube} ...")
    asyncio.run(
        enhance_all_episodes(
            concurrency=args.concurrency,
            filter_only_missing_youtube=args.only_missing_youtube,
        )
    )

if __name__ == "__main__":
    main()
