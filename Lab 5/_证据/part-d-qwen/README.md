# Part D: Qwen trial record

The four trials ran on the Raspberry Pi on November 1, 2026, from 19:29 to 19:31 New York time. Codex selected the two additional test questions, executed the course script through SSH, saved the output and organized the comparison.

The course `ask_qwen.py` matched its Git HEAD before execution. Its system instruction was: `You are a small bedside device. Answer in at most three short sentences.` Thinking was disabled, temperature was 0.3, and `num_predict` was 120. No prompt or answer was replaced after seeing a result.

All four requests completed successfully, with empty standard-error files and no output-limit warning. The Part C hand demo and its audio loop were stopped before the model trials.

## Original output

| Trial | Model | Request time | Output |
| --- | --- | --- | --- |
| 1 | qwen3.5:0.8b | 35.9 s | [Unedited output](1-history.txt) |
| 2 | qwen3.5:0.8b | 6.9 s | [Unedited output](2-timer.txt) |
| 3 | qwen3.5:0.8b | 13.0 s | [Unedited output](3-example-log.txt) |
| 4 | qwen3:0.6b | 15.7 s | [Unedited output](4-history-comparison.txt) |

The timings above are printed by the course script. They include the HTTP request and any model loading, but not Python process startup. The [manifest](trials.json) also records separate process durations, exact commands, model state before each request and the script hash. Neither history model was loaded immediately before its own history request. The 0.8B model remained loaded for the timer and example-log trials. Different answer lengths and loading conditions limit speed comparisons.

## Reproduction

The working directory was `/home/pi/Interactive-Lab-Hub-Lab5/Lab 5`. Each command used its `.venv/bin/python` interpreter.

```bash
python ask_qwen.py --model qwen3.5:0.8b "Tell me a bit about the history of Roosevelt Island."
```

```bash
python ask_qwen.py --model qwen3.5:0.8b "A timer starts at 20 minutes. After 7 minutes and 30 seconds, how much time remains? Answer in minutes and seconds."
```

```bash
python ask_qwen.py --model qwen3.5:0.8b "Use only this example log: 22:00 no person detected; 22:05 one person detected; 22:06 no person detected. When was a person detected, and can this log tell us why they were there?"
```

```bash
python ask_qwen.py --model qwen3:0.6b "Tell me a bit about the history of Roosevelt Island."
```

## Interpretation

Both history answers contained substantial errors. The timer calculation was correct. The example-log response identified the detection time, but did not clearly distinguish absence of detection from a person leaving and did not explain that motivation was unknowable from the log. Trial 3 is a supplied example, not an overnight observation.

External fact checks: [National Park Service](https://home.nps.gov/places/blackwell-s-island-new-york-city.htm) and [Cornell Tech](https://tech.cornell.edu/news/cornell-tech-campus-opens-on-roosevelt-island-marking-transformational-mile/). The complete answers and comparison are in the [assignment README](../../README.md#part-d).
