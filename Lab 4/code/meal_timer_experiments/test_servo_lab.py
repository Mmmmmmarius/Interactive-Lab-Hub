"""Offline behavior checks. None of these tests moves a physical servo."""

from contextlib import redirect_stderr
import io
import math
import unittest
from unittest.mock import Mock, patch

import servo_lab as lab


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class Bus:
    def __init__(self):
        self.data = {9: 16}
        self.closed = False
        self.bad_read = False

    def read_byte_data(self, address, register):
        value = self.data.get(register, 0)
        if self.bad_read and register == 8 and not self.data.get(9, 0) & 16:
            return value ^ 1
        return value

    def write_byte_data(self, address, register, value):
        self.data[register] = value

    def close(self):
        self.closed = True


def fake_output():
    output = lab.Output(lab.Config(), True, Mock())
    output.bus = Bus()
    output.owns_output = True
    output.lock = Mock()
    output.power_checked_at = lab.time.monotonic()
    output.hat = Mock()

    def set_word(channel, is_on, value):
        base = 6 + 4 * channel + (0 if is_on else 2)
        output.bus.data[base] = value & 255
        output.bus.data[base + 1] = value >> 8
        return True

    output.hat.PCA9685.set_channel_word.side_effect = set_word
    output.open = Mock()
    return output


class TimerTests(unittest.TestCase):
    def test_repeated_start_is_ignored_then_restart_works(self):
        clock = Clock()
        timer = lab.Countdown(2, clock)
        self.assertEqual(timer.sample(), (0, 2))
        self.assertTrue(timer.start())
        clock.sleep(1)
        self.assertFalse(timer.start())
        self.assertEqual(timer.sample(), (0.5, 1))
        clock.sleep(10)
        self.assertEqual(timer.sample(), (1, 0))
        self.assertEqual(timer.state, 'done')
        self.assertTrue(timer.start())
        self.assertEqual(timer.sample(), (0, 2))

    def test_clock_adjustments_do_not_change_countdown(self):
        clock = Clock()
        timer = lab.Countdown(10, clock)
        timer.start()
        with patch('time.time', return_value=-100000000):
            clock.sleep(3)
            self.assertEqual(timer.sample(), (0.3, 7))

    def test_forward_and_reverse_finish_at_endpoint_without_recenter(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                clock = Clock()
                output = lab.Output(lab.Config(), False, Mock())
                targets = []
                original = output.write

                def record(pulse):
                    original(pulse)
                    targets.append(pulse)

                output.write = record
                lab.run_timer(output, 0.15, reverse, clock, clock.sleep)
                self.assertEqual(targets[-1], 1000 if reverse else 2000)
                self.assertTrue(all(1000 <= value <= 2000 for value in targets))
                self.assertEqual(targets, sorted(targets, reverse=reverse))
                self.assertEqual(clock.now, 0.15)

    def test_invalid_durations_rejected(self):
        for duration in (0, -1, float('nan'), float('inf')):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                lab.Countdown(duration)


class HardwareBoundaryTests(unittest.TestCase):
    def test_bad_input_never_opens_hardware(self):
        inputs = [
            ['--hardware', 'timer', '--seconds', '0'],
            ['--hardware', 'move', '--percent', '101'],
            ['--hardware', 'move', '--pulse-us', 'nan'],
            ['--hardware', 'move', '--pulse-us', '100'],
        ]
        for argv in inputs:
            with self.subTest(argv=argv), patch.object(lab.Output, 'open') as opened:
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                    lab.main(argv)
                self.assertEqual(exc.exception.code, 2)
                opened.assert_not_called()

    def test_ctrl_c_disables_pwm_and_closes_handles(self):
        output = fake_output()
        with self.assertRaises(KeyboardInterrupt):
            with lab.connected(output):
                output.write(1500)
                raise KeyboardInterrupt
        self.assertEqual(lab.registers(output.bus, 0), [0, 0, 0, 16])
        self.assertTrue(output.bus.closed)
        output.lock.close.assert_called_once()

    def test_readback_failure_also_disables_pwm(self):
        output = fake_output()
        output.bus.bad_read = True
        with self.assertRaisesRegex(RuntimeError, 'PWM readback mismatch'):
            with lab.connected(output):
                output.write(1600)
        self.assertEqual(lab.registers(output.bus, 0), [0, 0, 0, 16])

    def test_setup_failure_after_ownership_still_disables_output(self):
        output = fake_output()
        output.bus.data[9] = 1
        output.open.side_effect = RuntimeError('setup failed')
        with self.assertRaisesRegex(RuntimeError, 'setup failed'):
            with lab.connected(output):
                self.fail('An unsuccessful setup must not reach the experiment')
        self.assertEqual(lab.registers(output.bus, 0), [0, 0, 0, 16])

    def test_unowned_controller_is_not_disabled(self):
        output = fake_output()
        output.owns_output = False
        output.bus.data[8] = 88
        output.bus.data[9] = 1
        output.open.side_effect = RuntimeError('busy')
        with self.assertRaisesRegex(RuntimeError, 'busy'):
            with lab.connected(output):
                pass
        self.assertEqual(lab.registers(output.bus, 0), [0, 0, 88, 1])

    def test_simulation_never_loads_hardware(self):
        output = lab.Output(lab.Config(), False, Mock())
        with patch.object(lab, 'open_bus', side_effect=AssertionError('hardware touched')):
            with lab.connected(output):
                output.write(1500)


if __name__ == '__main__':
    unittest.main()
