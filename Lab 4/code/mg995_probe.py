"""Short unloaded channel 0 probe without assuming servo angle or rotation type.

Observe whether the shaft settles at each step or keeps rotating.
This does not measure an angle, calibrate endpoints, or test a loaded base.
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
            print("START: MG995 unloaded probe; channel 0; 50 Hz", flush=True)
            for pulse_us in (1500, 1400, 1500, 1600, 1500):
                count = round(pulse_us / 1_000_000 * 50 * 4096)
                if not hat.PCA9685.set_channel_word(0, 1, 0):
                    raise RuntimeError("Could not set channel 0 ON timing")
                if not hat.PCA9685.set_channel_word(0, 0, count):
                    raise RuntimeError("Could not set channel 0 OFF timing")
                actual = [bus.read_byte_data(0x40, reg) for reg in range(0x06, 0x0A)]
                if actual != [0, 0, count & 0xFF, count >> 8]:
                    raise RuntimeError(f"Unexpected channel 0 timing: {actual}")
                print(f"HOLD: {pulse_us} us for 2 s; PWM readback OK", flush=True)
                time.sleep(2)
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
