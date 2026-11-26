# Test 8 results: simulated HLS players, 25 November 2026

Per-run summaries behind [Test 8](../../measurements.md#test-8-simulated-hls-players).

| File | Contents |
|---|---|
| `comparison.csv` | One row per policy, pacing and load combination: the median across repetitions of each metric |
| `<policy>-<paced>-<load>-<rep>/summary.json` | One run: discovery and completion percentiles, buffer, stalls, failed reloads, origin playlist requests per segment, and one sample event |
| `mixed-fine/`, `mixed-second/` | One run each with an unmodified nginx shield |

- **Policies.** `zero` is `max-age=0`; `second` is `max-age=1`; `fine` is `max-age=0, max-age-ms=200`; `background` adds a 200 ms stale-while-revalidate window.
- **Harness.** `contrib/subsecond-cache/workload.py` in the [nginx branch](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness), `nix run .#bench`. It generates each tier's nginx configuration.
- **Not published.** Per-event CSVs, access logs, generated configurations and media, about 1.7 GB.

## Limits

- One host, loopback, nginx only, twenty scripted players.
- The host was busy: load average 7 to 39 on 24 threads.
- The first invocation stopped at a reload timeout. The harness was changed to count failed reloads, and the remaining runs were made with that change. Runs made before it have no `failed_playlist_requests` field.
- Exact per-run source and binary identities were not recorded.
