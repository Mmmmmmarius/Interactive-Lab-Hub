"""Operator-observed, bounded MG995 working-range check on channel 0.

Never infers a shaft angle or searches for a mechanical stop automatically.
An operator must confirm each range before the next run expands it.
"""

import argparse
import signal
import subprocess
import time

import pi_servo_hat

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


def interrupt(signum, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-us', type=int, required=True)
    parser.add_argument('--max-us', type=int, required=True)
    args = parser.parse_args()
    if not 1000 <= args.min_us < 1500 < args.max_us <= 2000:
        parser.error('Use 1000 <= min-us < 1500 < max-us <= 2000')
    signal.signal(signal.SIGHUP, interrupt)
    signal.signal(signal.SIGTERM, interrupt)

    with SMBus(1) as bus:
        try:
            initial = [bus.read_byte_data(0x40, reg) for reg in range(6, 10)]
            if not initial[3] & 0x10:
                raise RuntimeError('Channel 0 was active before this check')
            hat = pi_servo_hat.PiServoHat()
            hat.PCA9685.restart()
            if not hat.set_pwm_frequency(50):
                raise RuntimeError('Could not configure 50 Hz PWM')
            if bus.read_byte_data(0x40, 0x00) & 0x10:
                raise RuntimeError('Controller is still asleep')

            def command(pulse_us):
                if not args.min_us <= pulse_us <= args.max_us:
                    raise ValueError('Pulse outside this run bounds')
                count = round(pulse_us / 1_000_000 * 50 * 4096)
                if not hat.PCA9685.set_channel_word(0, 1, 0):
                    raise RuntimeError('Could not set ON timing')
                if not hat.PCA9685.set_channel_word(0, 0, count):
                    raise RuntimeError('Could not set OFF timing')
                actual = [bus.read_byte_data(0x40, reg) for reg in range(6, 10)]
                if actual != [0, 0, count & 0xFF, count >> 8]:
                    raise RuntimeError(f'Unexpected timing readback: {actual}')

            print(f'START: bounded range {args.min_us}..{args.max_us} us; no angle assumption', flush=True)
            pulse_us = 1500
            command(pulse_us)
            time.sleep(0.5)
            for target in (args.min_us, 1500, args.max_us, 1500):
                while pulse_us != target:
                    pulse_us = min(pulse_us + 5, target) if target > pulse_us else max(pulse_us - 5, target)
                    command(pulse_us)
                    time.sleep(0.03)
                status = subprocess.run(['vcgencmd', 'get_throttled'], text=True, capture_output=True, check=True).stdout.strip()
                if int(status.split('=')[-1], 16) & 0xF:
                    raise RuntimeError(f'Pi reports active power/thermal flags: {status}')
                print(f'REACHED: {target} us; PWM readback OK; {status}', flush=True)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print('Test interrupted.', flush=True)
        finally:
            bus.write_byte_data(0x40, 0x09, 0x10)
            bus.write_byte_data(0x40, 0x07, 0x00)
            bus.write_byte_data(0x40, 0x06, 0x00)
            bus.write_byte_data(0x40, 0x08, 0x00)
            stopped = [bus.read_byte_data(0x40, reg) for reg in range(6, 10)]
            if stopped != [0, 0, 0, 0x10]:
                raise RuntimeError(f'Stop verification failed: {stopped}')
            print('STOP: channel 0 FULL_OFF verified', flush=True)


if __name__ == '__main__':
    main()
