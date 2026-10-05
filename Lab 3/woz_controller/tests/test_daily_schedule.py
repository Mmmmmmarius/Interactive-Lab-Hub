"""Virtual New York days and silent controller integration; no real audio."""
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from daily_schedule import DailySchedule
from controller import ScriptLibrary, TalkingBoxController
from server import dispatch_action
from console import command
from test_turn_loop import EventBackend, wait_until

ZONE = ZoneInfo("America/New_York")
SETTINGS = {"enabled": True, "timezone": "America/New_York", "morning_time": "10:30",
            "quiet_time": "20:00", "min_interval_minutes": 30, "max_interval_minutes": 90}


class Clock:
    def __init__(self, hour=10, minute=0, second=0, day=4, month=10):
        self.value = datetime(2026, month, day, hour, minute, second, tzinfo=ZONE)

    def __call__(self):
        return self.value

    def advance(self, **delta):
        self.value += timedelta(**delta)


class EndpointRandom:
    def __init__(self, upper=False):
        self.upper = upper

    def randint(self, low, high):
        return high if self.upper else low


class DailyScheduleTests(unittest.TestCase):
    def make(self, clock, upper=False):
        return DailySchedule(SETTINGS, clock, EndpointRandom(upper))

    def test_morning_at_1030_once_per_day(self):
        clock = Clock(10, 29, 59)
        schedule = self.make(clock)
        self.assertIsNone(schedule.poll())
        clock.advance(seconds=1)
        self.assertEqual(schedule.poll(), "morning")
        self.assertIsNone(schedule.poll())
        schedule.complete()
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-04T11:00:00-04:00")
        clock.advance(days=1, seconds=-1)
        schedule.poll()
        clock.advance(seconds=1)
        self.assertEqual(schedule.poll(), "morning")

    def test_starting_late_never_replays_morning(self):
        for hour, minute in [(10, 30), (10, 31), (14, 0), (21, 0)]:
            with self.subTest(hour=hour, minute=minute):
                clock = Clock(hour, minute)
                schedule = self.make(clock)
                self.assertIsNone(schedule.poll())
                self.assertNotEqual(schedule.snapshot()["next_at"], clock.value.isoformat())

    def test_random_interval_includes_30_and_90_minutes(self):
        for upper, minutes in [(False, 30), (True, 90)]:
            clock = Clock(12)
            schedule = self.make(clock, upper)
            clock.advance(minutes=minutes, seconds=-1)
            self.assertIsNone(schedule.poll())
            clock.advance(seconds=1)
            self.assertEqual(schedule.poll(), "chatter")

    def test_seeded_intervals_are_varied_and_bounded(self):
        clock = Clock(12)
        schedule = DailySchedule(SETTINGS, clock, random.Random(123))
        delays = []
        for _ in range(100):
            schedule.complete()
            target = datetime.fromisoformat(schedule.snapshot()["next_at"])
            delays.append((target - clock.value).total_seconds())
        self.assertTrue(all(1800 <= delay <= 5400 for delay in delays))
        self.assertGreater(len(set(delays)), 90)

    def test_no_chatter_at_or_after_2000(self):
        clock = Clock(19, 30)
        schedule = self.make(clock)
        self.assertEqual(schedule.snapshot()["next_kind"], "morning")
        clock.advance(minutes=30)
        self.assertIsNone(schedule.poll())
        clock.advance(hours=2)
        self.assertIsNone(schedule.poll())
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-05T10:30:00-04:00")

    def test_due_before_close_is_dropped_when_busy_through_close(self):
        clock = Clock(19, 29)
        schedule = self.make(clock)
        clock.advance(minutes=30)
        self.assertIsNone(schedule.poll(available=False))
        clock.advance(minutes=1)
        self.assertIsNone(schedule.poll())

    def test_complete_conversation_resets_wait_from_end(self):
        clock = Clock(12)
        schedule = self.make(clock)
        clock.advance(minutes=29)
        schedule.begin()
        clock.advance(minutes=20)
        self.assertIsNone(schedule.poll())
        self.assertIsNone(schedule.snapshot()["next_at"])
        schedule.complete()
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-04T13:19:00-04:00")

    def test_suspended_computer_does_not_replay_morning_or_stale_chatter(self):
        clock = Clock(10)
        schedule = self.make(clock)
        clock.advance(hours=2)
        self.assertIsNone(schedule.poll())
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-04T12:30:00-04:00")
        clock.advance(hours=2)
        self.assertIsNone(schedule.poll())
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-04T14:30:00-04:00")

    def test_morning_is_skipped_when_busy_not_queued(self):
        clock = Clock(10, 29, 59)
        schedule = self.make(clock)
        clock.advance(seconds=1)
        self.assertIsNone(schedule.poll(available=False))
        clock.advance(seconds=1)
        self.assertIsNone(schedule.poll())

    def test_pause_across_morning_does_not_catch_up_on_resume(self):
        clock = Clock(10)
        schedule = self.make(clock)
        schedule.set_paused(True)
        clock.advance(hours=1)
        self.assertIsNone(schedule.poll())
        schedule.set_paused(False)
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-04T11:30:00-04:00")

    def test_disable_persists_across_midnight_until_explicit_enable(self):
        clock = Clock(10)
        schedule = self.make(clock)
        schedule.set_enabled(False)
        clock.advance(days=1, minutes=30)
        self.assertIsNone(schedule.poll())
        self.assertIsNone(schedule.snapshot()["next_at"])
        schedule.set_enabled(True)
        self.assertIsNone(schedule.poll())
        self.assertEqual(schedule.snapshot()["next_at"], "2026-10-05T11:00:00-04:00")

    def test_backward_clock_does_not_repeat_morning(self):
        clock = Clock(10, 29, 59)
        schedule = self.make(clock)
        clock.advance(seconds=1)
        self.assertEqual(schedule.poll(), "morning")
        schedule.complete()
        clock.advance(minutes=-1)
        self.assertIsNone(schedule.poll())
        clock.advance(minutes=1)
        self.assertIsNone(schedule.poll())

    def test_new_york_time_is_independent_of_host_and_tracks_dst(self):
        value = [datetime(2026, 10, 31, 14, 29, 59, tzinfo=timezone.utc)]
        schedule = DailySchedule(SETTINGS, lambda: value[0])
        value[0] += timedelta(seconds=1)
        self.assertEqual(schedule.poll(), "morning")
        schedule.complete()
        value[0] = datetime(2026, 11, 1, 15, 29, 59, tzinfo=timezone.utc)
        schedule.poll()
        value[0] += timedelta(seconds=1)
        self.assertEqual(schedule.poll(), "morning")
        schedule.complete()
        self.assertTrue(schedule.snapshot()["next_at"].endswith('-05:00'))

    def test_invalid_settings_fail_clearly(self):
        for change in ({"min_interval_minutes": 91}, {"min_interval_minutes": True},
                       {"enabled": "yes"}, {"morning_time": "21:00"}, {"timezone": "Missing/Zone"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                DailySchedule({**SETTINGS, **change}, Clock())
        with self.assertRaises(ValueError):
            DailySchedule(SETTINGS, lambda: datetime(2026, 10, 4))


class OrnamentControllerTests(unittest.TestCase):
    def make(self, clock=None, backend=None, interval=3600):
        self.clock = clock or Clock(12)
        backend = backend or EventBackend()
        script = ScriptLibrary(ROOT/'talking-box-dialogue.json')
        script.timing['self_talk_pause_seconds'] = 0
        controller = TalkingBoxController(backend, script, clock=self.clock,
                                          rng=random.Random(19), scheduler_interval=interval)
        controller.daily.rng = EndpointRandom()
        controller.daily.complete()
        backend.controller = controller
        self.addCleanup(controller.close)
        self.addCleanup(backend.release_speak.set)
        self.addCleanup(backend.release_listen.set)
        return controller, backend

    def finish(self, controller):
        wait_until(lambda: not controller.state.snapshot()['active_action'])

    def test_background_scheduler_runs_morning_without_http_polling(self):
        controller, backend = self.make(Clock(10, 29, 59), interval=.01)
        self.clock.advance(seconds=1)
        wait_until(lambda: len(backend.spoken) == 2)
        self.finish(controller)
        self.assertEqual(backend.spoken, [controller.script.lines['panel_1'], controller.script.lines['panel_2']])
        self.assertEqual(controller.state.snapshot()['schedule']['next_at'], '2026-10-04T11:00:00-04:00')

    def test_scheduled_chatter_random_reply_and_full_turn_loop(self):
        controller, backend = self.make(backend=EventBackend(['Hello', 'Again', '']))
        self.clock.advance(minutes=30)
        controller.maybe_trigger_daily()
        self.finish(controller)
        self.assertIn(backend.spoken[0], controller.script.presets['self_talk'])
        self.assertEqual(len(backend.spoken), 3)
        for line in backend.spoken[1:]: self.assertIn(line, controller.script.presets['replies'])
        self.assertNotEqual(backend.spoken[1], backend.spoken[2])
        self.assertEqual(backend.overlaps, [])
        self.assertTrue(all(c == {'start_timeout': 2.0, 'min_silence': .8} for c in backend.listen_calls))
        self.assertEqual(controller.state.snapshot()['schedule']['next_at'], '2026-10-04T13:00:00-04:00')

    def test_manual_chatter_does_not_repeat_and_silence_has_no_reply(self):
        controller, backend = self.make()
        for _ in range(12):
            self.assertTrue(controller.start_self_talk())
            self.finish(controller)
        self.assertEqual(len(backend.spoken), 12)
        self.assertTrue(all(a != b for a,b in zip(backend.spoken, backend.spoken[1:])))
        self.assertTrue(all(line in controller.script.presets['self_talk'] for line in backend.spoken))

    def test_busy_conversation_cannot_be_interrupted_by_due_chatter(self):
        controller, backend = self.make(backend=EventBackend(block_listen=1))
        controller.speak('manual scene')
        self.assertTrue(backend.listen_entered.wait(1))
        self.clock.advance(minutes=60)
        controller.maybe_trigger_daily()
        self.assertEqual(backend.spoken, ['manual scene'])
        backend.release_listen.set()
        self.finish(controller)
        self.assertEqual(controller.state.snapshot()['schedule']['next_at'], '2026-10-04T13:30:00-04:00')

    def test_turn_can_finish_after_2000_but_no_new_spontaneous_scene(self):
        controller, backend = self.make(Clock(19, 58), EventBackend(['hi',''], block_listen=1))
        controller.start_self_talk()
        self.assertTrue(backend.listen_entered.wait(1))
        self.clock.advance(minutes=3)
        controller.maybe_trigger_daily()
        backend.release_listen.set()
        self.finish(controller)
        self.assertEqual(len(backend.spoken), 2)
        self.assertEqual(controller.state.snapshot()['schedule']['next_at'], '2026-10-05T10:30:00-04:00')

    def test_stop_cancels_and_disables_even_after_worker_finishes(self):
        controller, backend = self.make(backend=EventBackend(['late'], block_listen=1))
        controller.start_self_talk()
        self.assertTrue(backend.listen_entered.wait(1))
        controller.stop()
        backend.release_listen.set()
        self.finish(controller)
        self.clock.advance(days=1)
        controller.maybe_trigger_daily()
        self.assertEqual(len(backend.spoken),1)
        self.assertFalse(controller.state.snapshot()['schedule']['enabled'])
        self.assertIsNone(controller.state.snapshot()['schedule']['next_at'])

    def test_pause_resume_reset_schedule_controls(self):
        controller, backend = self.make()
        controller.pause()
        self.clock.advance(hours=1)
        controller.maybe_trigger_daily()
        self.assertEqual(backend.spoken, [])
        controller.resume()
        self.assertEqual(controller.state.snapshot()['schedule']['next_at'], '2026-10-04T13:30:00-04:00')
        controller.stop()
        controller.reset()
        self.assertTrue(controller.state.snapshot()['schedule']['enabled'])
        self.assertTrue(controller.state.snapshot()['automatic_reply'])
        self.assertFalse(controller.state.snapshot()['work']['running'])

    def test_api_and_console_share_controls_and_reject_invalid_toggle(self):
        controller, backend = self.make()
        for value in (None, 'true', 1, []):
            with self.assertRaises(ValueError): dispatch_action(controller,'/api/schedule',{'enabled':value})
        self.assertTrue(dispatch_action(controller,'/api/schedule',{'enabled':False}))
        self.assertFalse(controller.state.snapshot()['schedule']['enabled'])
        with patch('sys.stdout',new=io.StringIO()):
            self.assertTrue(command(controller,'schedule on'))
            self.assertTrue(command(controller,'chatter'))
        self.finish(controller)
        self.assertTrue(controller.state.snapshot()['schedule']['enabled'])
        self.assertEqual(len(backend.spoken),1)

    def test_preset_validation_rejects_missing_empty_or_invalid_lines(self):
        source = json.loads((ROOT/'talking-box-dialogue.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'dialogue.json'
            for bad in ([], ['same','same'], ['okay',{}], ['okay',''], ['okay','x'*301]):
                source['presets']['replies'] = bad
                path.write_text(json.dumps(source),encoding='utf-8')
                with self.assertRaises(ValueError): ScriptLibrary(path)


if __name__ == '__main__':
    unittest.main()
