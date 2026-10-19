"""MG995 experiments on I2C bus 1, address 0x40, 50 Hz.

Simulation is the default. Use --hardware explicitly to drive the Pi's pHAT.
Positions are pulse targets or normalized progress, never measured degrees.
"""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
FREQUENCY = 50
ADDRESS = 0x40
BUS = 1


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Value must be a finite positive number')
    return value


@dataclass(frozen=True)
class Config:
    channel: int = 0
    min_us: float = 1000
    center_us: float = 1500
    max_us: float = 2000
    travel_seconds: float = 2
    hold_seconds: float = 2
    demo_seconds: float = 30
    meal_seconds: float = 1200

    def __post_init__(self):
        if type(self.channel) is not int or not 0 <= self.channel < 16:
            raise ValueError('channel must be an integer from 0 to 15')
        for name in ('min_us', 'center_us', 'max_us', 'travel_seconds',
                     'hold_seconds', 'demo_seconds', 'meal_seconds'):
            positive(getattr(self, name))
        if not 0 < self.min_us < self.center_us < self.max_us < 20000:
            raise ValueError('Expected 0 < min_us < center_us < max_us < 20000')

    def pulse(self, progress, reverse=False):
        progress = float(progress)
        if not math.isfinite(progress) or not 0 <= progress <= 1:
            raise ValueError('Progress must be between 0 and 1')
        if reverse:
            progress = 1 - progress
        return self.min_us + progress * (self.max_us - self.min_us)


class Countdown:
    """Button adapters can call start(); repeats during a run are ignored."""

    def __init__(self, seconds, clock=time.monotonic):
        self.seconds = positive(seconds)
        self.clock = clock
        self.state = 'idle'
        self.started = None

    def start(self):
        if self.state == 'running':
            return False
        self.started = self.clock()
        self.state = 'running'
        return True

    def sample(self):
        if self.state == 'idle':
            return 0.0, self.seconds
        elapsed = max(0.0, self.clock() - self.started)
        progress = min(1.0, elapsed / self.seconds)
        if progress == 1.0:
            self.state = 'done'
        return progress, max(0.0, self.seconds - elapsed)


class Recorder:
    def __init__(self, directory, hardware, config):
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        self.path = directory / (stamp + '_' + uuid.uuid4().hex[:6] + '.jsonl')
        self.file = self.path.open('x', encoding='utf-8')
        self.event('session', hardware=hardware, config=config.__dict__,
                   angle_feedback=False, actual_motion_observation=None)

    def event(self, event, **fields):
        row = {'time_utc': datetime.now(timezone.utc).isoformat(),
               'event': event, **fields}
        self.file.write(json.dumps(row, ensure_ascii=False) + '\n')
        self.file.flush()
        if event != 'pulse':
            print(json.dumps(row, ensure_ascii=False), flush=True)

    def close(self):
        self.file.close()


def open_bus():
    try:
        from smbus2 import SMBus
    except ImportError:
        from smbus import SMBus
    return SMBus(BUS)


def registers(bus, channel):
    base = 6 + channel * 4
    return [bus.read_byte_data(ADDRESS, base + offset) for offset in range(4)]


def active(values):
    on_l, on_h, off_l, off_h = values
    if off_h & 0x10:
        return False
    return bool(on_h & 0x10) or ((on_h & 15) * 256 + on_l !=
                               (off_h & 15) * 256 + off_l)


class Output:
    def __init__(self, config, hardware, record):
        self.config, self.hardware, self.record = config, hardware, record
        self.bus = None
        self.hat = None
        self.lock = None
        self.owns_output = False
        self.last_count = None
        self.last_pulse = None
        self.power_checked_at = None

    def open(self):
        if not self.hardware:
            self.owns_output = True
            return
        import fcntl
        import pi_servo_hat
        self.lock = open('/tmp/info5345-servo-i2c1-40.lock', 'a+')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another experiment owns this controller')
        self.bus = open_bus()
        # Frequency is shared across the controller. Do not reconfigure it while
        # any other program is actively driving a channel.
        busy = [n for n in range(16) if active(registers(self.bus, n))]
        if busy:
            raise RuntimeError('Active PWM channels found: ' + str(busy))
        self.owns_output = True
        self.check_power()
        self.hat = pi_servo_hat.PiServoHat()
        self.hat.PCA9685.restart()
        if not self.hat.set_pwm_frequency(FREQUENCY):
            raise RuntimeError('Could not set 50 Hz PWM')
        if self.bus.read_byte_data(ADDRESS, 0) & 0x10:
            raise RuntimeError('Controller is asleep')

    def check_power(self):
        if not self.hardware:
            return
        result = subprocess.run(['vcgencmd', 'get_throttled'], text=True,
                                capture_output=True, check=True, timeout=2)
        value = result.stdout.strip()
        self.record.event('pi_power', status=value)
        if int(value.split('=')[-1], 16) & 15:
            raise RuntimeError('Pi reports an active power or thermal flag')
        self.power_checked_at = time.monotonic()

    def write(self, pulse_us):
        pulse_us = float(pulse_us)
        if not math.isfinite(pulse_us) or not (
                self.config.min_us <= pulse_us <= self.config.max_us):
            raise ValueError('Pulse is outside the configured experiment interval')
        count = round(pulse_us * FREQUENCY * 4096 / 1000000)
        if not 1 <= count <= 4095:
            raise ValueError('Pulse cannot be represented by this PWM controller')
        if self.hardware and time.monotonic() - self.power_checked_at >= 5:
            self.check_power()
        if count != self.last_count:
            if self.hardware:
                channel = self.config.channel
                if not self.hat.PCA9685.set_channel_word(channel, 1, 0):
                    raise RuntimeError('ON timing write failed')
                if not self.hat.PCA9685.set_channel_word(channel, 0, count):
                    raise RuntimeError('OFF timing write failed')
                actual = registers(self.bus, channel)
                if actual != [0, 0, count & 255, count >> 8]:
                    raise RuntimeError('PWM readback mismatch: ' + str(actual))
            self.record.event('pulse', requested_us=pulse_us, pwm_count=count)
            self.last_count = count
        self.last_pulse = pulse_us

    def close(self):
        try:
            if self.owns_output:
                if self.hardware:
                    base = 6 + self.config.channel * 4
                    # The installed library's zero-duty helper is unreliable.
                    # Assert FULL_OFF directly before clearing timing bytes.
                    for offset, value in ((3, 0x10), (1, 0), (0, 0), (2, 0)):
                        self.bus.write_byte_data(ADDRESS, base + offset, value)
                    stopped = registers(self.bus, self.config.channel)
                    if stopped != [0, 0, 0, 16]:
                        raise RuntimeError('FULL_OFF readback failed: ' + str(stopped))
                self.record.event('output_off', hardware=self.hardware,
                                  last_command_us=self.last_pulse,
                                  full_off_verified=self.hardware)
        finally:
            try:
                if self.bus is not None:
                    self.bus.close()
            finally:
                if self.lock is not None:
                    self.lock.close()


@contextmanager
def connected(output):
    try:
        output.open()
        yield output
    finally:
        output.close()


def ramp(output, start, end, seconds, clock=time.monotonic, sleep=time.sleep):
    seconds = positive(seconds)
    began = clock()
    while True:
        progress = min(1.0, max(0.0, (clock() - began) / seconds))
        output.write(start + progress * (end - start))
        if progress == 1:
            return
        sleep(min(0.02, seconds * (1 - progress)))


def run_timer(output, seconds, reverse=False, clock=time.monotonic, sleep=time.sleep):
    timer = Countdown(seconds, clock)
    timer.start()
    output.record.event('timer_started', duration_seconds=seconds)
    previous_second = None
    while True:
        progress, remaining = timer.sample()
        output.write(output.config.pulse(progress, reverse))
        rounded = math.ceil(remaining)
        if rounded != previous_second:
            output.record.event('timer_progress', state=timer.state,
                                remaining_seconds=rounded, progress=round(progress, 5))
            previous_second = rounded
        if timer.state == 'done':
            output.record.event('timer_done', final_target_us=output.last_pulse)
            return
        sleep(min(0.02, remaining))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--hardware', action='store_true', help='Drive the Pi pHAT')
    result.add_argument('--config', type=Path, default=HERE / 'servo_config.json')
    result.add_argument('--log-dir', type=Path, default=HERE / 'runs')
    commands = result.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='Read PWM registers without changing them')
    commands.add_parser('center', help='Command configured midpoint, hold, then off')
    commands.add_parser('off', help='Disable an idle controller channel without moving')
    move = commands.add_parser('move', help='One absolute target, hold, then off; no recenter')
    targets = move.add_mutually_exclusive_group(required=True)
    targets.add_argument('--pulse-us', type=float)
    targets.add_argument('--percent', type=float, help='0-100 of configured pulse interval')
    sweep = commands.add_parser('sweep', help='Center, low, high, center, then off')
    sweep.add_argument('--cycles', type=int, default=1)
    for name in ('demo', 'timer'):
        item = commands.add_parser(name, help='Countdown, stop at endpoint, then off')
        item.add_argument('--seconds', type=float)
        item.add_argument('--reverse', action='store_true')
        item.add_argument('--wait', action='store_true', help='Wait for Enter after positioning')
    return result


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        config = Config(**json.loads(args.config.read_text(encoding='utf-8')))
        target = None
        seconds = None
        if args.command == 'move':
            target = args.pulse_us if args.pulse_us is not None else config.pulse(args.percent / 100)
            if not math.isfinite(target) or not config.min_us <= target <= config.max_us:
                raise ValueError('Requested target is outside the configured interval')
        if args.command == 'sweep' and not 1 <= args.cycles <= 20:
            raise ValueError('cycles must be from 1 to 20')
        if args.command in ('demo', 'timer'):
            default = config.demo_seconds if args.command == 'demo' else config.meal_seconds
            seconds = positive(args.seconds if args.seconds is not None else default)
    except (OSError, ValueError, TypeError) as exc:
        cli.error(str(exc))

    record = Recorder(args.log_dir, args.hardware, config)
    output = Output(config, args.hardware, record)

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    for name in ('SIGINT', 'SIGTERM', 'SIGHUP'):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), interrupt)
    try:
        if args.command == 'status':
            if args.hardware:
                with open_bus() as bus:
                    values = registers(bus, config.channel)
                    record.event('status', channel=config.channel, registers=values,
                                 active=active(values), full_off=bool(values[3] & 0x10),
                                 prescale=bus.read_byte_data(ADDRESS, 0xFE))
            else:
                record.event('status', simulation=True, hardware_read=False)
            return 0
        with connected(output):
            if args.command == 'off':
                pass
            elif args.command == 'center':
                output.write(config.center_us)
                time.sleep(config.hold_seconds)
            elif args.command == 'move':
                output.write(target)
                time.sleep(config.hold_seconds)
            else:
                output.write(config.center_us)
                time.sleep(config.hold_seconds)
                if args.command == 'sweep':
                    for cycle in range(args.cycles):
                        record.event('sweep_cycle', cycle=cycle + 1)
                        for target in (config.min_us, config.max_us, config.center_us):
                            ramp(output, output.last_pulse, target, config.travel_seconds)
                            time.sleep(config.hold_seconds)
                else:
                    ramp(output, output.last_pulse, config.pulse(0, args.reverse), config.travel_seconds)
                    if args.wait:
                        record.event('waiting_for_start', input='keyboard_enter')
                        input('Press Enter to start. ')
                    run_timer(output, seconds, args.reverse)
                    time.sleep(config.hold_seconds)
        return 0
    except KeyboardInterrupt:
        record.event('interrupted')
        return 130
    except Exception as exc:
        record.event('error', message=str(exc))
        return 1
    finally:
        record.close()
        print('Run log: ' + str(record.path), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
