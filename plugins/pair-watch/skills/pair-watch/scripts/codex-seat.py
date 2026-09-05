#!/usr/bin/env python3
"""Start, identify, notify and retire a watcher-owned Codex TUI under tmux."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

MARKER = re.compile(r"^PAIR_MSG_END seq=([1-9][0-9]*)$", re.MULTILINE)


class SeatError(ValueError):
    pass


def run(argv, timeout=20):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise SeatError(f"{Path(argv[0]).name} failed ({result.returncode}): {result.stderr.strip()[:800]}")
    return result.stdout.strip()


def tmux(record, *args):
    return run([record["tmux"], "-L", record["tmux_socket"], *args])


def completed(path):
    text = Path(path).read_text(encoding="utf-8")
    matches = list(MARKER.finditer(text))
    if not matches:
        return text, 0
    begins = re.findall(r"^PAIR_MSG_BEGIN seq=([1-9][0-9]*)$", text, re.MULTILINE)
    sequences = [int(match.group(1)) for match in matches]
    if begins != [str(n) for n in sequences]:
        raise SeatError("Every native message needs matching begin/end markers")
    cursor = 0
    for match in matches:
        begin = text.find(f"PAIR_MSG_BEGIN seq={match.group(1)}\n", cursor)
        prefix = text[cursor:begin].strip()
        if begin < cursor or (prefix and not (match.group(1) == "1" and prefix.startswith("pw-watcher: ") and "\n" not in prefix)):
            raise SeatError("Unfinished or unframed content in channel")
        cursor = match.end()
    if text[cursor:].strip():
        raise SeatError("Unfinished content after completed message")
    if len(set(sequences)) != len(sequences) or set(sequences) != set(range(1, len(sequences) + 1)):
        raise SeatError("Message sequences must be unique and contiguous from 1")
    return text, max(sequences)


def save(path, record):
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def locked(path):
    with path.with_name(path.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def live(record):
    if record["status"] not in {"started", "bound"}:
        raise SeatError("Seat is not active")
    fields = tmux(record, "display-message", "-p", "-t", record["pane_id"],
                  "#{pane_id}|#{pane_pid}|#{pane_dead}|#{@pair_watch_owner}").split("|")
    if fields != [record["pane_id"], record["pane_pid"], "0", record["token"]]:
        raise SeatError("Live pane does not match the recorded owner and process")


def start(args, path):
    if path.exists():
        raise SeatError("Registry entry already exists; do not overwrite or adopt it")
    cwd, worktree = args.cwd.resolve(strict=True), args.worktree.resolve(strict=True)
    inbox, outbox = args.inbox.resolve(strict=True), args.outbox.resolve(strict=True)
    if not cwd.is_dir() or not worktree.is_dir() or inbox == outbox:
        raise SeatError("Invalid workspace or channel paths")
    text, sequence = completed(inbox)
    if sequence != 1 or not text.startswith(f"pw-watcher: {args.watcher}\n") or not text.rstrip().endswith("PAIR_MSG_END seq=1"):
        raise SeatError("Initial inbox must start with the watcher binding and end with sequence 1")
    if outbox.read_text().strip():
        raise SeatError("New seat needs an empty outbox")
    executable, tmux_bin = shutil.which(args.codex), shutil.which("tmux")
    if not executable or not tmux_bin:
        raise SeatError("Codex and tmux executables are required")
    token = uuid.uuid4().hex
    record = dict(watcher=args.watcher, run=args.run, seat=args.seat, token=token,
                  cwd=str(cwd), worktree=str(worktree), inbox=str(inbox), outbox=str(outbox),
                  codex=executable, tmux=tmux_bin, status="starting", notified=1,
                  tmux_socket="pw-" + hashlib.sha256((args.watcher + args.run).encode()).hexdigest()[:20],
                  tmux_session="pw-" + token[:16], model=args.model, effort=args.effort,
                  started=datetime.now(timezone.utc).isoformat(), session_id=None, rollout=None)
    # Claims also prevent two otherwise distinct registry entries from sharing a channel.
    claims = []
    created_session = False
    created_registry = False
    try:
        for channel in (inbox, outbox):
            claim = channel.with_name(channel.name + ".owner")
            with claim.open("x") as file:
                file.write(token)
            claims.append(claim)
        with path.open("x") as file:
            json.dump(record, file)
        created_registry = True
        prompt = (f"pw-watcher: {args.watcher}\npw-seat-token: {token}\n"
                  f"Read the completed initial instruction in {inbox}. Your assigned worktree is {worktree}; "
                  "it already exists. Follow the brief, publish the start declaration to the outbox, "
                  "then end your turn. Future instructions arrive through the same inbox.")
        argv = [executable, "-C", str(worktree), "--add-dir", str(inbox.parent),
                "--add-dir", str(outbox.parent), "-a", "never", "-s", "workspace-write"]
        if args.model:
            argv += ["-m", args.model]
        if args.effort:
            argv += ["-c", "model_reasoning_effort=" + json.dumps(args.effort)]
        argv.append(prompt)
        command = shlex.join(["env", "-u", "CODEX_THREAD_ID", *argv])
        pane = tmux(record, "new-session", "-d", "-P", "-F", "#{pane_id}|#{pane_pid}",
                    "-s", record["tmux_session"], "-x", "160", "-y", "45", command)
        created_session = True
        record["pane_id"], record["pane_pid"] = pane.split("|")
        tmux(record, "set-option", "-p", "-t", record["pane_id"], "@pair_watch_owner", token)
        record["status"] = "started"
        save(path, record)
    except (OSError, ValueError, subprocess.SubprocessError):
        if created_session:
            try:
                tmux(record, "kill-session", "-t", record["tmux_session"])
            except (SeatError, subprocess.SubprocessError):
                pass
        for claim in claims:
            if claim.read_text() == token:
                claim.unlink()
        if created_registry:
            record["status"] = "failed"
            save(path, record)
        raise
    return record


def bind(args, record):
    if record["session_id"] is not None:
        raise SeatError("Thread already bound; do not rebind")
    session_id = str(uuid.UUID(args.thread))
    rollout = args.rollout.resolve(strict=True)
    identity, matched = None, False
    with rollout.open() as file:
        for line in file:
            item = json.loads(line)
            payload = item.get("payload", {})
            if item.get("type") == "session_meta":
                identity = payload.get("id")
            if item.get("type") == "response_item" and payload.get("role") == "user":
                content = "\n".join(part.get("text", "") for part in payload.get("content", []) if isinstance(part, dict))
                if f"pw-watcher: {record['watcher']}\npw-seat-token: {record['token']}\n" in content:
                    matched = True
    if identity != session_id or not matched:
        raise SeatError("Rollout is not the thread launched for this watcher and seat")
    record.update(session_id=session_id, rollout=str(rollout), status="bound")


def notify(args, record):
    if record["status"] != "bound":
        raise SeatError("Complete the handshake and bind before notifying")
    text, sequence = completed(record["inbox"])
    if args.seq != sequence:
        raise SeatError("Notify only the latest completed inbox sequence")
    # An unfinished newest inbox entry is prepended; its body must not be treated as the old entry.
    first = MARKER.search(text)
    if not first or int(first.group(1)) != sequence:
        raise SeatError("Inbox must keep newest completed message first")
    if sequence <= record["notified"]:
        return
    if sequence != record["notified"] + 1:
        raise SeatError("Do not skip a notification sequence")
    _, response = completed(record["outbox"])
    if response != record["notified"]:
        raise SeatError("Wait for the previous instruction's outbox response")
    run([record["codex"], "queue", "--thread", record["session_id"], "--message",
         f"Read completed inbox sequence {sequence} in {record['inbox']}. "
         "Process it only if not already processed; do not act on unfinished content."], timeout=20)
    record["notified"] = sequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "bind", "notify", "stop"))
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--watcher", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--seat", required=True)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--worktree", type=Path)
    parser.add_argument("--inbox", type=Path)
    parser.add_argument("--outbox", type=Path)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--thread")
    parser.add_argument("--rollout", type=Path)
    parser.add_argument("--seq", type=int)
    parser.add_argument("--final-report-verified", action="store_true")
    args = parser.parse_args()
    required = {"start": ("run", "seat", "cwd", "worktree", "inbox", "outbox", "model", "effort"),
                "bind": ("thread", "rollout"), "notify": ("seq",), "stop": ()}[args.action]
    if any(getattr(args, key) is None for key in required):
        parser.error("Missing action arguments: " + ", ".join(required))
    path = args.record.resolve()
    try:
        if any(not re.fullmatch(r"[A-Za-z0-9_.:-]+", value) or value in {".", ".."} for value in (args.watcher, args.run, args.seat)):
            raise SeatError("Invalid watcher, run or seat identifier")
        if (path.parent.parent.name, path.parent.name, path.name) != (args.watcher, args.run, args.seat + ".json"):
            raise SeatError("Record path must end in watcher/run/seat.json")
        with locked(path):
            if args.action == "start":
                record = start(args, path)
            else:
                record = json.loads(path.read_text())
                if (record["watcher"], record["run"], record["seat"]) != (args.watcher, args.run, args.seat):
                    raise SeatError("Registry belongs to another watcher, run or seat")
                live(record)
                if args.action == "bind":
                    bind(args, record)
                elif args.action == "notify":
                    notify(args, record)
                else:
                    if not args.final_report_verified:
                        raise SeatError("Verify final report or handoff before retiring the seat")
                    tmux(record, "kill-session", "-t", record["tmux_session"])
                    record.update(status="retired", retired=datetime.now(timezone.utc).isoformat())
                save(path, record)
        print(json.dumps(record))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"codex-seat: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
