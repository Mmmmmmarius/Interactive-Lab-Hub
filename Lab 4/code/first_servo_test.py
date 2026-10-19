"""First unloaded test for a positional 9g servo on channel 0.

Prepared for Lab 4.1 Part C. Physical movement needs a human observation.
Angles use the package's explicit 180-degree mapping, not a measured calibration.
"""
import time
import pi_servo_hat

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


def main():
    with SMBus(1) as bus:
        try:
            hat = pi_servo_hat.PiServoHat()
            # Wake this controller without broadcasting an I2C general-call reset.
            hat.PCA9685.restart()
            if not hat.set_pwm_frequency(50):
                raise RuntimeError("Could not configure 50 Hz PWM")
            if bus.read_byte_data(0x40, 0x00) & 0x10:
                raise RuntimeError("Controller is still asleep")
            print("START: channel 0, 50 Hz, limited unloaded movement", flush=True)
            hat.move_servo_position(0, 90, 180)
            time.sleep(0.5)
            for _ in range(2):
                for angle in (60, 90, 120, 90):
                    hat.move_servo_position(0, angle, 180)
                    registers = [bus.read_byte_data(0x40, reg) for reg in range(0x06, 0x0A)]
                    actual_off = registers[2] | (registers[3] << 8)
                    expected_off = round((1 + angle / 180) / 1000 * 50 * 4096)
                    if registers[:2] != [0, 0] or actual_off != expected_off:
                        raise RuntimeError(f"Unexpected channel 0 timing: {registers}")
                    print(f"Channel 0: {angle}; PWM readback OK", flush=True)
                    time.sleep(1)
        except KeyboardInterrupt:
            print("Test interrupted.", flush=True)
        finally:
            # In library 2.0.0, set_duty_cycle(0, 0) produces -1 and is rejected.
            # Explicitly set PCA9685 LED0_OFF_H bit 4 to disable channel 0.
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
