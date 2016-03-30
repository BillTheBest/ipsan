# -*-coding: utf-8 -*-


import os
import argparse


change_log_file = "Changes"


def list_latest():
    if not os.path.exists(change_log_file):
        return

    with open(change_log_file, "r") as f:

        for line in f:
            if line.strip().startswith("-"):
                print(line)
            if not line.strip():
                break


def extract_latest():
    if not os.path.exists(change_log_file):
        return

    lines = []
    with open(change_log_file, "r") as f:
        for line in f:
            if line.strip().startswith("-"):
                lines.append(line.strip())
            if not line.strip():
                break
    print("\\n".join(lines))


def list_all():
    if not os.path.exists(change_log_file):
        return

    with open(change_log_file, "r") as f:
        for line in f:
            print(line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", help="List all change log", action="store_true")
    parser.add_argument("--latest", help="List latest change log", action="store_true")
    parser.add_argument("--extract", help="Extract change log", action="store_true")
    args = parser.parse_args()

    if args.all:
        list_all()
    elif args.latest:
        list_latest()
    elif args.extract:
        extract_latest()
    else:
        parser.print_help()
