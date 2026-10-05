#!/usr/bin/env python3
"""Manual entry point that needs no HTTP socket. Defaults to silent simulation."""
from __future__ import annotations

import argparse
import json

from server import build_controller, dispatch_action


HELP = """morning | chatter | listen | say TEXT | simulate TEXT (empty = silence)
schedule on/off | auto on/off
pause | resume | stop | reset | status | help | quit
Legacy manual work demo: work MINUTES | remind | accept | defer
Daily ornament: 10:30 morning, random 30-90 minute chatter before 20:00 New York.
Stop disables the daily schedule; 'schedule on' enables it. Reset restores defaults.
Commands use the same controller as the web view. Status lists busy/cancelling
actions; retry after they finish. 'simulate' queues input only in dry-run mode.
"""


def command(controller, line: str) -> bool:
    """Execute a manual command. False means quit; errors stay in the console."""
    line = line.strip()
    if not line:
        return True
    name, _, tail = line.partition(" ")
    if name in {"quit", "exit"}:
        return False
    if name == "help":
        print(HELP)
        return True
    if name == "status":
        print(json.dumps(controller.state.snapshot(), indent=2))
        return True
    routes = {"morning": "/api/morning", "chatter": "/api/self-talk", "listen": "/api/listen",
              "remind": "/api/work/expire", "accept": "/api/work/accept",
              "defer": "/api/work/defer", "pause": "/api/pause",
              "resume": "/api/resume", "stop": "/api/stop", "reset": "/api/reset"}
    body = {}
    if name in routes:
        path = routes[name]
    elif name == "say":
        path, body = "/api/speak", {"text": tail}
    elif name == "simulate":
        path, body = "/api/simulate", {"text": tail}
    elif name == "work":
        path, body = "/api/work/start", {"minutes": float(tail)}
    elif name == "auto":
        if tail not in {"on", "off"}:
            raise ValueError("Use auto on or auto off")
        path, body = "/api/replies", {"automatic": tail == "on"}
    elif name == "schedule":
        if tail not in {"on", "off"}:
            raise ValueError("Use schedule on or schedule off")
        path, body = "/api/schedule", {"enabled": tail == "on"}
    else:
        raise ValueError("Unknown command; type help")
    accepted = dispatch_action(controller, path, body)
    print("Accepted" if accepted else "Busy or unavailable; inspect status and retry")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("dry-run", "pi"), default="dry-run")
    parser.add_argument("--model", choices=("tiny.en", "base.en"), default="tiny.en")
    args = parser.parse_args()
    controller = build_controller(args.backend, args.model)
    print(f"Talking Box console; backend={args.backend}")
    print(HELP)
    try:
        while True:
            try:
                if not command(controller, input("flower> ")):
                    break
            except (ValueError, TypeError) as error:
                print(f"Input error: {error}")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        controller.close()


if __name__ == "__main__":
    main()
