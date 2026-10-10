"""One report, straight from the terminal. No web server needed.

    python -m complaints.cli "aaj lunch mein dal mein keeda tha"
    python -m complaints.cli "AC se paani tapak raha hai" --photo demo/photos/ac.jpg
    python -m complaints.cli "AC se paani aa raha hai" --answer "BH2 E207"
"""

import argparse
import sys

from api import db
from complaints.agent import handle_answer, handle_report

STATUS_LINE = {
    "filed": "FILED",
    "merged": "MERGED",
    "needs_input": "GEMMA ASKS",
    "rejected": "REJECTED",
    "error": "ERROR",
}


def show(result):
    for step in result["steps"]:
        print(f"  ... {step['label']}")
    print(f"\n[{STATUS_LINE.get(result['status'], result['status'].upper())}] ", end="")
    if result["status"] == "needs_input":
        print(result["question"])
    else:
        print(result["message"])
    complaint = result.get("complaint")
    if complaint:
        where = " / ".join(x for x in (complaint["building"], complaint["spot"], complaint["meal"]) if x)
        print(f"       #{complaint['id']}  {complaint['domain']} / {complaint['category']}"
              f"{'  (' + where + ')' if where else ''}")
        print(f"       {complaint['summary']}")
        print(f"       severity {complaint['severity']} | {complaint['report_count']} report(s) | "
              f"priority {complaint['priority']} | escalated {complaint['escalated']} | "
              f"to {complaint['authority']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Triage one complaint with Gemma 4.")
    parser.add_argument("text", help="what the student wrote")
    parser.add_argument("--photo", default=None, help="path to a photo")
    parser.add_argument("--answer", action="append", default=[],
                        help="answer Gemma's question without being prompted (repeatable)")
    args = parser.parse_args()

    db.init_db()
    print(f"\n> {args.text}" + (f"   [photo: {args.photo}]" if args.photo else "") + "\n")

    result = handle_report(args.text, photo_path=args.photo)
    show(result)

    queued = list(args.answer)
    while result["status"] == "needs_input":
        if queued:
            answer = queued.pop(0)
            print(f"> {answer}\n")
        elif sys.stdin.isatty():
            try:
                answer = input("your answer > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nStopped.")
                return 1
            print()
        else:
            print("(no answer given, stopping)")
            return 0
        if not answer:
            print("Stopped.")
            return 1
        result = handle_answer(result["thread_id"], answer)
        show(result)

    return 0 if result["status"] in ("filed", "merged", "rejected") else 1


if __name__ == "__main__":
    sys.exit(main())
