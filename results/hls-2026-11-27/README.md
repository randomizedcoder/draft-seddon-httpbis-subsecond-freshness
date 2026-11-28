# Test 8 results: simulated HLS players, 27 November 2026

Per-run summaries behind the rerun of [Test 8](../../measurements.md#test-8-simulated-hls-players). The first run is in [hls-2026-11-25](../hls-2026-11-25/).

| File | Contents |
|---|---|
| `comparison.csv` | One row per policy, pacing and load combination: the median across repetitions of each metric |
| `<policy>-<rep>-<paced>-<load>/summary.json` | One run: discovery and completion percentiles, buffer, stalls, failed reloads, origin playlist requests per segment, and one sample event |
| `mixed-fine/`, `mixed-second/` | One run each with an unmodified nginx shield |

- **Policies.** `zero` is `max-age=0`; `second` is `max-age=1`; `fine` is `max-age=0, max-age-ms=200`; `background` adds a 200 ms stale-while-revalidate window.
- **Harness.** `contrib/subsecond-cache/workload.py` in the [nginx branch](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness), `nix run .#bench -- --output DIR`. One invocation, exit status 0, 50 scenarios.
- **Not published.** Per-event CSVs, access logs, `wrk` output, generated configurations and media.

## What was run

| Item | Value |
|---|---|
| nginx source | Commit `277ed19670afe4084a3ddaabdf4858c19b1bd767` plus the later prototype fixes, which were not yet committed. The source changes were then committed as `092c1979bbfc425a80cc7c0be60e33aa1b629722` |
| SHA-256 of that uncommitted diff | `c630d415a229fc27116b02053e11e7aa60a2c073976cb275f33fce55a4bdda96` |
| SHA-256 of `flake.lock` | `d23042a588db8b13df76db9e3fa3c6db1871e7a69a994b9d6ae71fb4d084b661` |
| Host | x86_64 Linux 7.3.3, 24 threads |
| Started | 2026-11-27 14:59 -08:00, about an hour |

## Limits

- One host, loopback, nginx only, twenty scripted players.
- The host was busy: load average 6 to 48 on 24 threads, sampled each minute.
- Built from a working tree with uncommitted changes, so this is not a clean-commit benchmark. The diff hash above identifies it.
