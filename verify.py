#!/usr/bin/env python3
"""Independent reference implementation of the intratexxxt staircase (standard library only).

    python verify.py stage <i> <state-hex> <nonce> [-d D]    check one stage, print the next state
    python verify.py transcript [progress.json]               re-check a whole transcript from stage 0
    python verify.py solve [-n N] [progress.json]             slow pure-Python solver (for reading, not racing)

It shares no code with the binary, so a transcript it accepts was not accepted on trust.
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

PUZZLE, NEXT = b"RCP|puzzle|", b"RCP|next|"


def puzzle_hash(i: int, s: bytes, x: int) -> bytes:
    return hashlib.sha256(PUZZLE + struct.pack(">Q", i) + s + struct.pack(">Q", x)).digest()


def next_state(i: int, s: bytes, x: int) -> bytes:
    return hashlib.sha256(NEXT + struct.pack(">Q", i) + s + struct.pack(">Q", x)).digest()


def valid(i: int, s: bytes, x: int, d: int) -> bool:
    # integer(H(...)) < T, with T = 2^(256-d)
    return int.from_bytes(puzzle_hash(i, s, x), "big") < (1 << (256 - d))


def load_challenge(path: str) -> dict:
    c = json.loads(Path(path).read_text())
    assert c["format"] == "rcp-challenge-v1", c["format"]
    return c


def check_transcript(p: dict, c: dict) -> int:
    if p["stage0"] != c["stage0"] or p["difficulty"] != c["difficulty"]:
        raise SystemExit("transcript belongs to a different challenge")
    d, s = p["difficulty"], bytes.fromhex(p["stage0"])
    for k, st in enumerate(p["steps"]):
        if st["i"] != k or bytes.fromhex(st["state"]) != s:
            raise SystemExit(f"step {k}: does not chain")
        if not valid(k, s, st["nonce"], d):
            raise SystemExit(f"step {k}: nonce {st['nonce']} does not meet the target")
        s = next_state(k, s, st["nonce"])
        if bytes.fromhex(st["next"]) != s:
            raise SystemExit(f"step {k}: recorded next state is wrong")
    return len(p["steps"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", default="challenge.json", help="challenge file")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("stage")
    a.add_argument("i", type=int)
    a.add_argument("state")
    a.add_argument("nonce", type=int)
    a.add_argument("-d", type=int, default=None)
    b = sub.add_parser("transcript")
    b.add_argument("path", nargs="?", default="progress.json")
    s = sub.add_parser("solve")
    s.add_argument("path", nargs="?", default="progress.json")
    s.add_argument("-n", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "stage":
        d = args.d if args.d is not None else load_challenge(args.c)["difficulty"]
        st = bytes.fromhex(args.state)
        if not valid(args.i, st, args.nonce, d):
            raise SystemExit(f"stage {args.i}: invalid")
        print(next_state(args.i, st, args.nonce).hex())
        return

    c = load_challenge(args.c)
    p = Path(args.path)
    prog = json.loads(p.read_text()) if p.exists() else {
        "format": "rcp-progress-v1", "stage0": c["stage0"], "difficulty": c["difficulty"], "steps": []}
    n = check_transcript(prog, c)
    if args.cmd == "transcript":
        print(f"ok: {n} stage(s) verified from stage 0")
        return
    d = c["difficulty"]
    for _ in range(args.n):
        i = len(prog["steps"])
        s0 = bytes.fromhex(prog["steps"][-1]["next"]) if i else bytes.fromhex(c["stage0"])
        x = 0
        while not valid(i, s0, x, d):
            x += 1
        nxt = next_state(i, s0, x)
        prog["steps"].append({"i": i, "state": s0.hex(), "nonce": x, "next": nxt.hex()})
        p.write_text(json.dumps(prog, indent=2) + "\n")
        print(f"stage {i} x={x} -> {nxt.hex()}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
