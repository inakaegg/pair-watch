import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/pair-watch/skills/pair-watch/scripts/codex-seat.py'


class NativeSeatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pair test '$ ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'fake codex'
        self.bin.write_text('#!' + sys.executable + '\nimport json,sys,time\nfrom pathlib import Path\np=Path(__file__).with_name("calls.jsonl")\nwith p.open("a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\nif sys.argv[1] != "queue":time.sleep(300)\n')
        self.bin.chmod(0o755)
        self.records = []
        self.run_id = "run-" + uuid.uuid4().hex
        self.addCleanup(self.retire)

    def retire(self):
        for record in self.records:
            if record.exists():
                r = json.loads(record.read_text())
                subprocess.run([r['tmux'], '-L', r['tmux_socket'], 'kill-server'], capture_output=True)

    def call(self, action, record, *args, watcher='watcher', ok=True):
        r = subprocess.run([sys.executable, str(SCRIPT), action, '--record', str(record),
                            '--watcher', watcher, '--run', record.parent.name, '--seat', record.stem, *map(str, args)], text=True, capture_output=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        return r.stderr

    def message(self, n, text='task'):
        return f'PAIR_MSG_BEGIN seq={n}\n{text}\nPAIR_MSG_END seq={n}\n'

    def start(self, seat='A'):
        inbox, outbox = self.root / f'in-{seat}', self.root / f'out-{seat}'
        inbox.write_text('pw-watcher: watcher\n' + self.message(1))
        outbox.write_text('')
        record = self.root / 'watcher' / self.run_id / f'{seat}.json'
        record.parent.mkdir(parents=True, exist_ok=True)
        self.records.append(record)
        r = self.call('start', record, '--run', self.run_id, '--seat', seat,
                      '--cwd', self.root, '--worktree', self.root, '--inbox', inbox,
                      '--outbox', outbox, '--codex', self.bin, '--model', 'fixture-model', '--effort', 'high')
        return record, r

    def bind(self, record, r):
        thread = str(uuid.uuid4())
        rollout = self.root / (thread + '.jsonl')
        data = [{'type':'session_meta','payload':{'id':thread}},
                {'type':'response_item','payload':{'role':'user','content':[{'text':f"pw-watcher: watcher\npw-seat-token: {r['token']}\nlaunch"}]}}]
        rollout.write_text(''.join(json.dumps(i)+'\n' for i in data))
        return self.call('bind', record, '--thread', thread, '--rollout', rollout)

    def test_owner_handshake_framing_ack_dedupe_and_stop(self):
        record, r = self.start()
        self.call('start', record, '--run', 'x', '--seat', 'A', '--cwd', self.root,
                  '--worktree', self.root, '--inbox', r['inbox'], '--outbox', r['outbox'],
                  '--model', 'fixture', '--effort', 'high', ok=False)
        self.call('notify', record, '--seq', 1, ok=False)
        r = self.bind(record, r)
        self.call('notify', record, '--seq', 1, watcher='foreign', ok=False)
        inbox, outbox = Path(r['inbox']), Path(r['outbox'])
        initial = inbox.read_text()
        inbox.write_text(self.message(2) + initial)
        self.call('notify', record, '--seq', 2, ok=False)
        outbox.write_text(self.message(1, 'ready'))
        inbox.write_text('PAIR_MSG_BEGIN seq=3\nunfinished\n' + self.message(2) + initial)
        self.call('notify', record, '--seq', 2, ok=False)
        inbox.write_text(self.message(2) + initial)
        self.call('notify', record, '--seq', 2)
        self.call('notify', record, '--seq', 2)
        calls = [json.loads(l) for l in (self.root/'calls.jsonl').read_text().splitlines()]
        queued = [c for c in calls if c[0] == 'queue']
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0][2], r['session_id'])
        self.call('stop', record, ok=False)
        self.assertEqual(self.call('stop', record, '--final-report-verified')['status'], 'retired')
        self.call('notify', record, '--seq', 2, ok=False)

    def test_two_seats_are_disjoint_and_bad_rollout_is_rejected(self):
        records = [self.start(s) for s in ('A', 'B')]
        first = self.bind(*records[0])
        self.call('bind', records[1][0], '--thread', first['session_id'], '--rollout', first['rollout'], ok=False)
        bound = [first, self.bind(*records[1])]
        self.assertNotEqual(bound[0]['token'], bound[1]['token'])
        self.assertNotEqual(bound[0]['session_id'], bound[1]['session_id'])
        for (record, _), r in zip(records, bound):
            self.call('bind', record, '--thread', bound[1]['session_id'], '--rollout', bound[1]['rollout'], ok=False)
            Path(r['outbox']).write_text(self.message(1))
            inbox = Path(r['inbox']); inbox.write_text(self.message(2) + inbox.read_text())
            self.call('notify', record, '--seq', 2)
        queued = [json.loads(l) for l in (self.root/'calls.jsonl').read_text().splitlines() if json.loads(l)[0]=='queue']
        self.assertEqual({c[2] for c in queued}, {r['session_id'] for r in bound})

    def test_dead_pane_is_not_replaced_or_notified(self):
        record, r = self.start()
        self.bind(record, r)
        subprocess.run([r['tmux'], '-L', r['tmux_socket'], 'kill-session', '-t', r['tmux_session']], check=True)
        self.call('notify', record, '--seq', 1, ok=False)


    def test_wrong_run_and_seat_are_rejected_for_notify_and_stop(self):
        record, r = self.start()
        self.bind(record, r)
        for action, flags in [('notify', ['--seq', 1]), ('stop', ['--final-report-verified'])]:
            for key in ('run', 'seat'):
                with self.subTest(action=action, key=key):
                    self.call(action, record, *flags, '--'+key, 'other', ok=False)

    def test_relative_edit_targets_real_linked_worktree_only(self):
        main = self.root/'main'; worktree = self.root/'linked'
        subprocess.run(['git', 'init', '-q', str(main)], check=True)
        subprocess.run(['git', '-C', str(main), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-m', 'fixture'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-b', 'fixture', str(worktree)], check=True, capture_output=True)
        self.bin.write_text('#!' + sys.executable + '\nimport os,sys,time\nfrom pathlib import Path\nos.chdir(sys.argv[sys.argv.index("-C")+1])\nPath("relative.txt").write_text("seat only")\ntime.sleep(300)\n')
        record = self.root/'watcher'/self.run_id/'C.json';record.parent.mkdir(parents=True)
        inbox=self.root/'in-C';outbox=self.root/'out-C';inbox.write_text('pw-watcher: watcher\n'+self.message(1));outbox.write_text('')
        self.records.append(record)
        self.call('start', record, '--cwd', main, '--worktree', worktree, '--inbox', inbox, '--outbox', outbox, '--codex', self.bin, '--model', 'fixture', '--effort', 'high')
        import time
        # Wait for the tmux shell to start the fake CLI, not a fixed startup delay.
        for _ in range(250):
            if (worktree/'relative.txt').exists() or (main/'relative.txt').exists():break
            time.sleep(0.02)
        self.assertTrue((worktree/'relative.txt').exists())
        self.assertFalse((main/'relative.txt').exists())


if __name__ == '__main__':
    unittest.main()
