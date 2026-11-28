# Layered simulation results, 27 November 2026

Summaries behind the rerun of Tests 1, 3 and 4 in [measurements.md](../../measurements.md), and the same three with `proxy_cache_lock on`.

| Directory | Command, after `nix run ./contrib/subsecond-cache#layers --` | Test |
|---|---|---|
| `lan/` | (no options) | 1 |
| `wan/` | `--wan` | 3 |
| `wan500/` | `--wan --fine-ms 500` | 4 |
| `lan-lock/` | `--lock` | 1, with the lock |
| `wan-lock/` | `--wan --lock` | 3, with the lock |
| `wan500-lock/` | `--wan --fine-ms 500 --lock` | 4, with the lock |

Each holds one `summary.json`: the options, then for each path the response count, staleness in milliseconds and origin requests a second.

- **Source and host.** The same build and host as [hls-2026-11-27](../hls-2026-11-27/README.md#what-was-run). The load average was 19 to 47 on 24 threads.
- **One ten-second run each.** No repetitions.
- **Not published.** Access logs, `wrk` output and generated configurations.
