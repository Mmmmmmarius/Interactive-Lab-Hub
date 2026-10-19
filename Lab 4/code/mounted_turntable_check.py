"""One slow, limited back-and-forth check of the assembled B1 turntable.

This is not a 360-degree command or a measurement of shaft angle.
The pulse range is narrower than the previous unloaded MG995 probe.
"""

import signal
import time

import pi_servo_hat

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


def interrupt(signum, frame):
    raise KeyboardInterrupt


def main():
    signal.signal(signal.SIGHUP, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    with SMBus(1) as bus:
        try:
            hat = pi_servo_hat.PiServoHat()
            hat.PCA9685.restart()
            if not hat.set_pwm_frequency(50):
                raise RuntimeError("Could not configure 50 Hz PWM")
            if bus.read_byte_data(0x40, 0x00) & 0x10:
                raise RuntimeError("Controller is still asleep")

            def command(pulse_us):
                if not 1450 <= pulse_us <= 1550:
                    raise ValueError("Mounted check pulse is outside its limited range")
                count = round(pulse_us / 1_000_000 * 50 * 4096)
                if not hat.PCA9685.set_channel_word(0, 1, 0):
                    raise RuntimeError("Could not set channel 0 ON timing")
                if not hat.PCA9685.set_channel_word(0, 0, count):
                    raise RuntimeError("Could not set channel 0 OFF timing")
                actual = [bus.read_byte_data(0x40, reg) for reg in range(0x06, 0x0A)]
                if actual != [0, 0, count & 0xFF, count >> 8]:
                    raise RuntimeError(f"Unexpected channel 0 timing: {actual}")

            print("START: mounted B1 check; limited back-and-forth, not 360 degrees", flush=True)
            pulse_us = 1500
            command(pulse_us)
            time.sleep(1)
            for target in (1450, 1550, 1500):
                step = 2 if target > pulse_us else -2
                while pulse_us != target:
                    pulse_us += step
                    command(pulse_us)
                    time.sleep(0.05)
                print(f"REACHED: {target} us; slow ramp and PWM readback OK", flush=True)
                time.sleep(0.3)
        except KeyboardInterrupt:
            print("Test interrupted.", flush=True)
        finally:
            bus.write_byte_data(0x40, 0x09, 0x10)
            bus.write_byte_data(0x40, 0x07, 0x00)
            bus.write_byte_data(0x40, 0x06, 0x00)
            bus.write_byte_data(0x40, 0x08, 0x00)
            stopped = [bus.read_byte_data(0x40, reg) for reg in range(0x06, 0x0A)]
            if stopped != [0, 0, 0, 0x10]:
                raise RuntimeError(f"Channel 0 stop verification failed: {stopped}")
            print("STOP: channel 0 FULL_OFF verified", flush=True)


if __name__ == "__main__":
    main()
