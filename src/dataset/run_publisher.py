"""
Dataset export and Hugging Face publish CLI.

Usage:
  python -m src.dataset.run_publisher                          # export JSONL locally
  python -m src.dataset.run_publisher --push --repo user/repo  # push to HF Hub
  python -m src.dataset.run_publisher --card                   # write dataset card only
"""
import argparse
import os
import sys

from .publisher import export_jsonl, export_dataset_card, push_to_hub


def main():
    parser = argparse.ArgumentParser(description="Film Craft Annotations Dataset Publisher")
    parser.add_argument("--push", action="store_true",
                        help="Push to Hugging Face Hub after exporting")
    parser.add_argument("--repo", metavar="USERNAME/REPO",
                        help="HF Hub repo ID (required with --push)")
    parser.add_argument("--card", action="store_true",
                        help="Write dataset card README only")
    parser.add_argument("--token", metavar="HF_TOKEN",
                        default=os.getenv("HF_TOKEN"),
                        help="Hugging Face API token (or set HF_TOKEN env var)")
    args = parser.parse_args()

    if args.card:
        export_dataset_card()
        return

    export_jsonl()
    export_dataset_card()

    if args.push:
        if not args.repo:
            print("--repo is required when using --push  (e.g. --repo username/film-craft-annotations)")
            sys.exit(1)
        if not args.token:
            print("Hugging Face token required. Set HF_TOKEN env var or pass --token.")
            sys.exit(1)
        push_to_hub(args.repo, token=args.token)


if __name__ == "__main__":
    main()
