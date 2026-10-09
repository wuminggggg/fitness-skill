"""Run from project root: python -m src.cli --data PATH COMMAND."""
import argparse
import json
from .engine import FitnessEngine
from .state_manager import StateManager
from .intake import next_questions
from .trend_analysis import analyze
from .adaptation import progress_dose

def main():
    parser = argparse.ArgumentParser(description="Stateful fitness planning")
    parser.add_argument("--data", required=True, help="Private per-user data directory; never the shared skill directory")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "checkin", "record"):
        sub = commands.add_parser(name)
        sub.add_argument("--input", required=True, help="UTF-8 JSON file")
    sub = commands.add_parser("plan")
    sub.add_argument("--date", required=True, help="User-local YYYY-MM-DD")
    sub.add_argument("--indoors", action="store_true")
    commands.add_parser("status")
    sub = commands.add_parser("trends")
    sub.add_argument("--date", required=True)
    sub = commands.add_parser("progression")
    sub.add_argument("--input", required=True)
    sub.add_argument("--mode", choices=("time","reps","sets","difficulty"), required=True)
    args = parser.parse_args()
    repository = StateManager(args.data)
    engine = FitnessEngine(repository)
    try:
        if hasattr(args,"input"):
            with open(args.input,encoding="utf-8-sig") as f: value = json.load(f)
        if args.command == "init":
            profile = engine.update_profile(value)
            result = {"profile":profile,"next_questions":next_questions(profile)}
        elif args.command == "checkin": result = engine.checkin(value)
        elif args.command == "record": result = engine.record(value)
        elif args.command == "plan": result = engine.plan(args.date,args.indoors)
        elif args.command == "progression": result = progress_dose(value,args.mode)
        else:
            data = repository.load()
            result = data if args.command == "status" else analyze(data["checkins"],data["records"],data["plans"],args.date)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Input/storage error: {exc}\n")

if __name__ == "__main__": main()
