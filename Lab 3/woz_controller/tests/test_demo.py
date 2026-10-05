"""The demo advances the real daily scheduler without touching system time or audio."""
from datetime import timedelta
import time
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audio_backend import DryRunBackend
from demo import DemoSession


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.demo = DemoSession()
        self.addCleanup(self.demo.close)
        self.demo.backend = DryRunBackend(delay=.002, transcripts=[])
        self.demo.controller.backend = self.demo.backend
        self.demo.controller.script.timing['self_talk_pause_seconds'] = 0

    def finish(self):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            state = self.demo.snapshot()['state']
            if not state['active_action'] and not state['schedule']['busy']:
                return state
            time.sleep(.005)
        self.fail('Demo exchange did not finish')

    def test_morning_and_random_reply_use_production_script(self):
        self.demo.step('next', 'Hello box')
        state = self.finish()
        self.assertEqual(self.demo.now.hour, 10)
        self.assertEqual(self.demo.now.minute, 30)
        self.assertEqual(state['transcript'], 'Hello box')
        self.assertIn(state['last_spoken'], self.demo.controller.script.presets['replies'])
        self.assertEqual(state['status'], 'quiet')

    def test_silent_morning_then_random_wait_and_chatter(self):
        self.demo.step('next')
        state = self.finish()
        self.assertEqual(state['last_spoken'], self.demo.controller.script.lines['panel_2'])
        before = self.demo.now
        self.demo.step('next')
        state = self.finish()
        self.assertLessEqual(timedelta(minutes=30), self.demo.now - before)
        self.assertLessEqual(self.demo.now - before, timedelta(minutes=90))
        self.assertIn(state['last_spoken'], self.demo.controller.script.presets['self_talk'])

    def test_evening_waits_for_next_morning(self):
        self.demo.step('quiet')
        state = self.demo.snapshot()['state']
        self.assertEqual(state['status'], 'quiet')
        self.assertEqual(state['last_spoken'], '')
        self.assertEqual(state['schedule']['next_at'], '2026-10-05T10:30:00-04:00')
        self.demo.step('next')
        self.finish()
        self.assertEqual(self.demo.now.day, 5)

    def test_busy_jump_rejected_and_reset_cancels(self):
        self.demo.backend.delay = .3
        self.demo.step('next', 'Hello')
        with self.assertRaisesRegex(ValueError, 'finished'):
            self.demo.step('quiet')
        self.demo.step('reset')
        self.assertEqual(self.demo.snapshot()['now'], '2026-10-04T10:29:59-04:00')
        self.assertEqual(self.demo.snapshot()['state']['last_spoken'], '')

    def test_invalid_input_does_not_advance_time(self):
        original = self.demo.now
        for action, text in [('invalid', ''), ('next', 'x' * 301), ('next', 123)]:
            with self.assertRaises(ValueError):
                self.demo.step(action, text)
        self.assertEqual(original, self.demo.now)


if __name__ == '__main__':
    unittest.main()
