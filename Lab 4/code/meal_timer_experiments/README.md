# MG995 experiment scripts

Prepared on October 19, 2026 for the B1 rotating cardboard meal timer.

> **Hardware status, October 19:** The current Servo pHAT emitted smoke after a wiring error. Do not run any `--hardware` command on that board. Local simulation can continue. The controller must be replaced or inspected, and the Pi and connections checked, before powered experiments resume. All successful hardware results below predate this incident. See the [project incident record](../../README.md#wiring-incident-and-current-hardware-status).

## Current setup

- Raspberry Pi with the red SparkFun Servo pHAT, I2C bus 1, address 0x40.
- MG995 on channel 0. PWM frequency: 50 Hz.
- The supplied configuration uses the previously exercised 1000–2000 microsecond interval and a 1500 microsecond midpoint.
- The earlier 100–3500 microsecond exploration remains in the historical test records. It is not the default operating interval here.
- The script has no shaft-angle feedback. Percentages describe the configured pulse interval, not measured degrees or relative turns. The physical left/right direction depends on mounting.

On October 19, a midpoint command was sent for two seconds, then the channel was disabled. The PWM readback and FULL_OFF check passed. This confirms the signal, not a new visual observation of the mechanism. See [the recenter record](recenter_verification.json).

## Run on the Pi

These commands are retained for use with checked, functional hardware. They are not a troubleshooting procedure for the damaged board. The script cannot detect a damaged controller, overheating or a short circuit.

The files are deployed to `/home/pi/Interactive-Lab-Hub/Lab 4/meal_timer_experiments`. Use the existing Lab 4 Python environment. No additional package installation is required for these commands.

```bash
cd '/home/pi/Interactive-Lab-Hub/Lab 4/meal_timer_experiments'
PYTHON='/home/pi/Interactive-Lab-Hub/Lab 4/.venv/bin/python'
```

| Task | Command | Behavior |
| --- | --- | --- |
| Inspect output | `"$PYTHON" servo_lab.py --hardware status` | Reads the selected channel without changing PWM. |
| Return to midpoint | `"$PYTHON" servo_lab.py --hardware center` | Sends the configured midpoint for two seconds, then disables output. |
| One position | `"$PYTHON" servo_lab.py --hardware move --percent 25` | Sends one absolute target, holds for two seconds, then disables output. No automatic recenter. |
| Exact pulse target | `"$PYTHON" servo_lab.py --hardware move --pulse-us 1600` | Uses an absolute target within the configured interval. |
| One complete sweep | `"$PYTHON" servo_lab.py --hardware sweep` | Center, low endpoint, high endpoint, center. About 14 seconds with this configuration. |
| Two sweeps | `"$PYTHON" servo_lab.py --hardware sweep --cycles 2` | Repeats the same interval twice. It does not accumulate turns. |
| Short countdown | `"$PYTHON" servo_lab.py --hardware demo --wait` | Positions at the start, waits for Enter, then moves across the interval over 30 seconds. |
| Reverse countdown | `"$PYTHON" servo_lab.py --hardware demo --wait --reverse` | Same interaction with the two endpoints exchanged. |
| Normal countdown | `"$PYTHON" servo_lab.py --hardware timer --seconds 1200 --wait` | A provisional 20-minute experiment. The final meal duration is still undecided. |

Put global options such as `--hardware` and `--config` before the command. Press **Ctrl+C** in the running terminal to stop; the program disables output without recentering. Normal completion, Python exceptions, SIGTERM and SSH hangup also use the shutdown routine. A killed process or disconnected I2C bus cannot guarantee software cleanup.

The timer first visits the midpoint and then moves to its start target. With `--wait`, it holds that target until Enter. Timing begins after Enter. At the end, it holds the endpoint for two seconds, disables output, and exits. Disabling output releases active holding torque, so the final resting position depends on the mechanism. Run the command again to start another trial.

`move` and `center` send their first target directly. `sweep` and the timer use timed ramps after their initial midpoint command. These ramps control the target trajectory; they do not measure the servo's speed. The `off` command is only for an idle controller. If another experiment owns the controller, stop that experiment with Ctrl+C first.

## Simulate without moving hardware

Omit `--hardware`. This mode uses only Python's standard library and works on Windows as well as the Pi.

```bash
python servo_lab.py demo --seconds 3
python servo_lab.py timer --seconds 10 --reverse
python -m unittest -v test_servo_lab
```

The command prints remaining time and progress. Every run creates a JSONL record in `runs/`, containing the configuration, simulation/hardware flag, target pulses, completion or failure, and output-off result. Simulated shutdown records do not claim a physical FULL_OFF check.

## Adjust the experiment

Edit [servo_config.json](servo_config.json). `min_us`, `center_us` and `max_us` are signal targets. `travel_seconds` controls each ramp, and `hold_seconds` controls pauses. `demo_seconds` and `meal_seconds` are editable experiment durations. The code rejects non-finite values, invalid intervals, and targets outside the configured interval before moving hardware.

The operating interval is a starting point from previous tests, not an established absolute mechanical range. Use the actual dial clearance and observed travel to choose the final configuration. The program does not detect rubbing, stalls, current draw or servo-rail voltage. Pi power flags only describe the Pi.

## What is ready and what remains

- Ready: midpoint, position, sweep, monotonic countdown, reversed countdown, local simulation, run logs and output shutdown.
- The countdown core has idle, running and done states. Repeated `start()` calls during a run are ignored; a new call after completion restarts the timer. The terminal commands run one experiment at a time.
- Physical button wiring, GPIO choice, debouncing and long-press behavior remain to be integrated. Enter is a temporary controller input and does not establish a physical button test.
- The colored dial's direction, actual angle, final duration and endpoint retention still need checking on the assembled clock.
- Codex prepared this code and its checks. Operator observations are recorded separately from register checks and simulation results.
