# Practical tests of millisecond freshness

Dave Seddon · Companion to the [explainer](explainer.md) and the [Internet-Draft](draft-seddon-httpbis-subsecond-freshness.md)

These tests run the [nginx prototype](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness) as a chain of five caches on one machine and measure how old a response is when it leaves the last cache. Anyone with Nix can repeat them in about 15 seconds each. [Test 8](#test-8-simulated-hls-players) adds simulated HLS players and takes about an hour.

## Summary

- **Updates arrive about twenty times sooner.** Through five caches with no network delay, responses under `max-age=1` were on average 999 ms behind the origin. Under `max-age=0, max-age-ms=100` they were 48 ms behind.
- **Fine age is carried across the chain.** The oldest response under the 100 ms policy was 111 ms old at the measurement point. Each cache deducts the age it received; this is not a strict 100 ms bound on delivery age.
- **The cost is origin requests.** One fetch per lifetime is ten a second at 100 ms, against one a second or fewer at `max-age=1`. Concurrent misses raised that to 36 a second with four connections.
- **A fresh reuse opportunity needs budget left after the request delay.** With 234 ms of simulated round-trip delay, a 100 ms response was stale on arrival. The last cache reused nothing.
- **Over that delayed path, 500 ms works.** Responses were on average 208 ms behind the origin, against 1011 ms under `max-age=1`.
- **Same lifetime, finer accounting: about half the staleness in nginx.** `max-age=1, max-age-ms=1000` averaged 498 ms against 1004 ms for `max-age=1`. That part of the gain comes from nginx's whole-second deadlines, not from the shorter lifetime.
- **Mismatched and malformed pairs behave as the draft says.** A companion above or below its base is used as written on a supporting path. A malformed companion yields to its base.
- **A wrong trust setting can defeat fine-age accounting.** With an older cache replaying Age-Ms inside a path configured as supporting, `max-age=1, max-age-ms=200` gave responses up to 2152 ms old, against 204 ms when configured correctly. With a base of `max-age=0` the effect did not appear in this run. Neither observation establishes a general bound on concealed age.
- **For simulated players, 200 ms found segments as soon as `max-age=0`, for a fifth of the origin requests.** Twenty players found a new segment within 968 ms at the 95th percentile under either policy, and within 2241 ms under `max-age=1`. The origin served 4 playlist requests per segment at 200 ms, against 20 at `max-age=0`.
- **Under heavy load, `max-age=0` failed in nginx and 200 ms did not.** With a load generator on the playlist, `max-age=0` took 3064 ms to discovery and players stalled. The 200 ms policy was unchanged at 936 ms.
- **Not shown.** Real players and devices, behaviour under real network conditions, and a baseline cache that applies upstream Age as RFC 9111 specifies.

| Test | Path delay | Cache-Control | Responses | Mean | p99 | Max | Origin req/s |
|---|---|---|---:|---:|---:|---:|---:|
| [1](#test-1-five-caches-no-delay) | None | `max-age=1` | 225988 | 999 | 1974 | 1999 | 1.8 |
| [1](#test-1-five-caches-no-delay) | None | `max-age=0, max-age-ms=100` | 219498 | 48 | 94 | 111 | 35.9 |
| [2](#test-2-one-connection) | None | `max-age=1` | 70467 | 1049 | 1977 | 1999 | 0.5 |
| [2](#test-2-one-connection) | None | `max-age=0, max-age-ms=100` | 65633 | 50 | 96 | 105 | 9.1 |
| [3](#test-3-a-lifetime-shorter-than-the-path) | 234 ms | `max-age=1` | 451257 | 1001 | 1861 | 1880 | 2.0 |
| [3](#test-3-a-lifetime-shorter-than-the-path) | 234 ms | `max-age=0, max-age-ms=100` | 164 | 125 | 144 | 144 | 12.3 |
| [4](#test-4-a-lifetime-longer-than-the-path) | 234 ms | `max-age=1` | 386656 | 1011 | 1862 | 1881 | 2.0 |
| [4](#test-4-a-lifetime-longer-than-the-path) | 234 ms | `max-age=0, max-age-ms=500` | 62713 | 208 | 276 | 470 | 6.4 |
| [5](#test-5-the-same-lifetime-in-both-units) | None | `max-age=1` | 243766 | 1004 | 1980 | 1999 | 2.0 |
| [5](#test-5-the-same-lifetime-in-both-units) | None | `max-age=1, max-age-ms=1000` | 243318 | 498 | 986 | 1002 | 2.4 |
| [5](#test-5-the-same-lifetime-in-both-units) | 234 ms | `max-age=1` | 307294 | 997 | 1862 | 1880 | 2.0 |
| [5](#test-5-the-same-lifetime-in-both-units) | 234 ms | `max-age=1, max-age-ms=1000` | 161846 | 443 | 770 | 967 | 3.4 |
| [6](#test-6-mismatched-and-malformed-pairs) | None | `max-age=1, max-age-ms=2000` | 88083 | 1005 | 1971 | 2001 | 1.2 |
| [6](#test-6-mismatched-and-malformed-pairs) | None | `max-age=60, max-age-ms=200` | 87343 | 99 | 195 | 233 | 13.1 |
| [6](#test-6-mismatched-and-malformed-pairs) | None | `max-age=0, max-age-ms=86400000` | 88786 | 6573 | 11817 | 11937 | 0.0 |
| [6](#test-6-mismatched-and-malformed-pairs) | None | `max-age=1, max-age-ms=0.2` | 88390 | 1027 | 1980 | 1999 | 2.0 |
| [7](#test-7-misconfigured-paths) | None | `max-age=1, max-age-ms=200`, older cache in the path | 479063 | 1023 | 2043 | 2152 | 1.9 |
| [7](#test-7-misconfigured-paths) | None | `max-age=0, max-age-ms=100`, no fine-age source | 97957 | 0 | 1 | 3 | 9796.0 |
| [7](#test-7-misconfigured-paths) | None | `max-age=0, max-age-ms=1` | 53301 | 1 | 3 | 8 | 1508.6 |

Mean, p99 and Max are staleness in milliseconds. Each row is one ten-second run.

Here "staleness" means measured time since origin generation, including
time in flight; it does not mean time past HTTP freshness expiry. A lifetime
bounds reuse decisions, not the time at which a response reaches a client.
Tests 1 to 4 change both the policy duration and the precision of age
accounting. Test 5 holds the duration at one second and changes only the
accounting. The whole-second path reflects nginx's implementation: stock
nginx stores whole-second deadlines. It forwards an Age field received from
upstream, but neither interprets nor generates one.

## Revisions and retained results

All figures here were taken with the earlier prototype revisions in the
table below. Those revisions read nginx's stored clock value and sent
Age-Ms to every client.
nginx revision `1c012f600` reads the clock for each fine decision and leaves
Age-Ms off by default. Revision `694bc608c` shortens the wait on
`proxy_cache_lock` for fine locations and updates an entry in place after a
304. The tests have not been rerun with either.

| Evidence | Revision and provenance |
|---|---|
| Tests 1–4 | The recorded prototype revision is `f7cd0dff6`; the full commit is available in the nginx history. The original notes do not identify every working-tree modification or binary build identifier. |
| Tests 5–7 | Later working-tree experiments on the same branch. Their exact per-run source and binary identities were not captured; do not attribute them to a clean commit. |
| Test 8 | nginx branch based on `9198f9a28f58b8afc8c06817f51175b4fbeea786`, with a local `workload.py` change that records failed reloads and resumes completed scenarios. The matching nginx-tests revision is `6b2428453fe42934193e7c8b04391ed30f27d768`. This is not a clean-source benchmark. |

The Test 8 summaries are published in
[results/hls-2026-11-25/](results/hls-2026-11-25/): `comparison.csv`
contains the scenario medians, and each scenario directory contains that
run's `summary.json`. The per-event records, tier configurations, access
logs, `wrk` output and invocation logs are retained locally and are not
published. The reported numbers can therefore be checked against the
summaries, but not recomputed from raw events.

The first invocation stopped at a reload timeout. The continuation reused
completed summaries and ran remaining scenarios after the harness change.
There are 50 final scenario summaries, including two mixed-version smoke
runs; they do not represent 50 independent repetitions of one comparison.
No new measurements were run for this document revision.

For a subsequent run, retain exact source commits plus any dirty diff,
binary/store identifiers, dependency lock, command, host conditions and raw
results together. Repeating the command below reproduces the method; it
cannot establish the missing provenance of an earlier run.

## Setup

The chain follows a live stream from an origin in New York to viewers in Melbourne. Every process is nginx built from the prototype branch, each on its own loopback address.

| Address | Role | Delay each way in tests 3 and 4 |
|---|---|---:|
| `127.0.0.10` | Origin, New York | |
| `127.0.0.11` | New York cache | 1 ms |
| `127.0.0.12` | Chicago cache | 10 ms |
| `127.0.0.13` | Los Angeles cache | 25 ms |
| `127.0.0.14` | Sydney cache | 75 ms |
| `127.0.0.15` | Melbourne cache | 6 ms |

- **Origin.** Returns its own clock, in milliseconds, as the response body and in an `X-Origin-Time` header. Two paths differ only in Cache-Control.

  | Path | Cache-Control |
  |---|---|
  | `/second` | `max-age=1` |
  | `/fine` | `max-age=0, max-age-ms=100` |

- **Caches.** Each proxies to the address before it. The New York cache establishes fine age from the origin. The others accept `Age-Ms` from the cache before them.
- **Client.** [wrk](https://github.com/wg/wrk) requests both paths from the Melbourne cache at the same time, as fast as it can.
- **Measurement.** The Melbourne cache logs its own time and the `X-Origin-Time` of each response it sends. The difference is that response's staleness. Both clocks are the same machine's.
- **Delay.** Loopback has none. Tests 3 and 4 put a small TCP relay on each hop, which holds traffic for the delay in the table: 117 ms one way, 234 ms for the round trip. The delays are illustrative, not measured routes.
- **Window.** Ten seconds, after a two-second warm-up.
- **Host.** x86_64 Linux, AMD Ryzen Threadripper PRO 3945WX, prototype at `f7cd0dff6`.

To repeat a test, clone the prototype branch and run this from its root. Options follow `--`.

```sh
nix run ./contrib/subsecond-cache#layers
```

The [prototype's README](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness/contrib/subsecond-cache#layered-simulation) lists every option. `--output` keeps the configurations, access logs and wrk reports.

## Test 1. Five caches, no delay

**Question.** Does a 100 ms lifetime survive five caches, and how much sooner do updates arrive?

```sh
nix run ./contrib/subsecond-cache#layers
```

| Cache-Control | Responses | Mean | p50 | p90 | p99 | Max | Origin req/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| `max-age=1` | 225988 | 999.2 | 996.0 | 1792.0 | 1974.0 | 1999.0 | 1.8 |
| `max-age=0, max-age-ms=100` | 219498 | 48.2 | 48.0 | 85.0 | 94.0 | 111.0 | 35.9 |

- **Fine age stays near the selected budget.** Measured response age on the fine path runs from 0 to about 100 ms, with a maximum of 111 ms. Five caches did not make it five times longer in this run.
- **Why it holds.** Each cache sends `Age-Ms` with the response. The next cache subtracts that age, and its own request delay, from the 100 ms before reusing the response.
- **The whole-second path runs from 0 to 2 seconds.** nginx stores whole-second deadlines, so a `max-age=1` entry lives between one and two seconds.
- **Both paths served about the same number of responses.** The shorter lifetime did not reduce what the last cache could deliver.
- **The origin saw about twenty times the requests.** Test 2 separates the part due to the lifetime from the part due to concurrency.

## Test 2. One connection

**Question.** How much of the origin load in test 1 comes from the shorter lifetime itself?

```sh
nix run ./contrib/subsecond-cache#layers -- --connections 1
```

| Cache-Control | Responses | Mean | p50 | p90 | p99 | Max | Origin req/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| `max-age=1` | 70467 | 1048.7 | 1080.0 | 1823.0 | 1977.0 | 1999.0 | 0.5 |
| `max-age=0, max-age-ms=100` | 65633 | 50.4 | 51.0 | 86.0 | 96.0 | 105.0 | 9.1 |

- **One client connection means one fetch per expiry.** The origin sees 9.1 requests a second at 100 ms and 0.5 at `max-age=1`.
- **Staleness is unchanged from test 1.** The extra origin requests in test 1 bought nothing.
- **The extra load in test 1 is concurrent misses.** With four connections, several requests find the entry expired at once and each fetches. nginx's `proxy_cache_lock` would normally collapse them, but at these revisions a request waiting on that lock checked again only every 500 ms, which is longer than the lifetime. The tests leave it off. From revision `694bc608c` a fine location checks after 5 ms, doubling to 500 ms; these tests have not been repeated with the lock on.
- **For implementers.** Collapsing concurrent misses needs a wake-up finer than the lifetimes in use.

## Test 3. A lifetime shorter than the path

**Question.** What happens when the lifetime is shorter than the round trip to the origin?

```sh
nix run ./contrib/subsecond-cache#layers -- --wan
```

| Cache-Control | Responses | Mean | p50 | p90 | p99 | Max | Origin req/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| `max-age=1` | 451257 | 1001.3 | 1008.0 | 1703.0 | 1861.0 | 1880.0 | 2.0 |
| `max-age=0, max-age-ms=100` | 164 | 124.8 | 123.0 | 135.0 | 144.0 | 144.0 | 12.3 |

- **The fine path stops caching at the far end.** A response has spent more than 100 ms in transit by the time Melbourne receives it. The Melbourne cache recorded no hits on `/fine`.
- **Every request travels the whole chain.** Four connections completed 164 requests in ten seconds, each waiting for the round trip.
- **The responses are recent but few.** They are about 125 ms old, close to the one-way delay, and already beyond the 100 ms freshness lifetime. The last cache cannot reuse them as fresh.
- **Forwarding is different from reuse.** A response obtained for the current request can arrive after its freshness budget is spent. These results illustrate the cost of a short lifetime; they do not prove a strict 100 ms delivery-age guarantee.
- **The [draft](draft-seddon-httpbis-subsecond-freshness.md) covers this** in its "Choosing a Lifetime" section: the round trip to the origin is the practical floor.

## Test 4. A lifetime longer than the path

**Question.** Over the same delayed path, does a lifetime above the round trip work?

```sh
nix run ./contrib/subsecond-cache#layers -- --wan --fine-ms 500
```

| Cache-Control | Responses | Mean | p50 | p90 | p99 | Max | Origin req/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| `max-age=1` | 386656 | 1010.7 | 1016.0 | 1716.0 | 1862.0 | 1881.0 | 2.0 |
| `max-age=0, max-age-ms=500` | 62713 | 207.9 | 210.0 | 261.0 | 276.0 | 470.0 | 6.4 |

- **Updates arrive about five times sooner** than under `max-age=1`, 208 ms against 1011 ms on average.
- **No response exceeded the lifetime.** The oldest was 470 ms.
- **Melbourne reuses each response for about 266 ms.** That is the 500 ms lifetime less the 234 ms round trip already spent.
- **The fine path served fewer responses.** Requests that arrive during a refresh wait up to 234 ms for it. Under `max-age=1` the same wait happens once every two seconds.
- **A stale-while-revalidate window would cover that wait.** The draft defines `stale-while-revalidate-ms` for this. These runs do not use it.
- **The origin saw 6.4 requests a second**, against 2.0.

## Test 5. The same lifetime in both units

**Question.** How much of the gain in test 1 comes from the shorter lifetime, and how much from finer accounting? The lifetime is one second on both paths. Only the companion differs.

```sh
nix run ./contrib/subsecond-cache#layers -- \
  --path "second=max-age=1" --path "paired=max-age=1, max-age-ms=1000"
```

| Path delay | Cache-Control | Responses | Mean | p50 | p90 | p99 | Max | Origin req/s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| None | `max-age=1` | 243766 | 1003.5 | 1003.0 | 1802.0 | 1980.0 | 1999.0 | 2.0 |
| None | `max-age=1, max-age-ms=1000` | 243318 | 497.7 | 497.0 | 895.0 | 986.0 | 1002.0 | 2.4 |
| 234 ms | `max-age=1` | 307294 | 997.2 | 996.0 | 1707.0 | 1862.0 | 1880.0 | 2.0 |
| 234 ms | `max-age=1, max-age-ms=1000` | 161846 | 443.2 | 439.0 | 709.0 | 770.0 | 967.0 | 3.4 |

The delayed rows add `--wan`.

- **With the companion, one second means one second.** Responses run from 0 to 1002 ms old. Without it they run from 0 to 1999 ms.
- **The difference is nginx's whole-second deadline.** Stock nginx stores "expires at second N+1" and treats the entry as fresh until that second has passed, so a `max-age=1` entry lives between one and two seconds. The prototype stores the deadline in milliseconds.
- **So test 1's twentyfold gain is two effects.** About twofold comes from exact deadlines and about tenfold from the shorter lifetime.
- **Over the delayed path the paired entry is never older than its lifetime.** The oldest was 967 ms. Each cache counted the 234 ms already spent.
- **This is not a test of Age truncation between conforming caches.** Stock nginx forwards a received Age but neither interprets nor generates one, so the whole-second path here has no upstream age to truncate. A baseline that applies Age as RFC 9111 specifies would sit between these two rows. We have not run one.
- **Origin requests rose slightly**, 2.4 against 2.0 a second, because the entry expires on time.

## Test 6. Mismatched and malformed pairs

**Question.** What happens when the two values of a pair disagree, by design or by accident?

```sh
nix run ./contrib/subsecond-cache#layers -- \
  --path "above=max-age=1, max-age-ms=2000" \
  --path "below=max-age=60, max-age-ms=200" \
  --path "zero-day=max-age=0, max-age-ms=86400000" \
  --path "bad=max-age=1, max-age-ms=0.2"
```

| Cache-Control | Responses | Mean | p50 | p90 | p99 | Max | Origin req/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| `max-age=1, max-age-ms=2000` | 88083 | 1005.0 | 1036.0 | 1775.0 | 1971.0 | 2001.0 | 1.2 |
| `max-age=60, max-age-ms=200` | 87343 | 99.2 | 99.0 | 174.0 | 195.0 | 233.0 | 13.1 |
| `max-age=0, max-age-ms=86400000` | 88786 | 6572.9 | 6352.0 | 10791.0 | 11817.0 | 11937.0 | 0.0 |
| `max-age=1, max-age-ms=0.2` | 88390 | 1026.7 | 1022.0 | 1833.0 | 1980.0 | 1999.0 | 2.0 |

Four paths ran at once, so each served fewer responses than in the other tests.

- **Companion above its base.** The supporting path uses 2000 ms. A cache that ignores the companion would use one second.
- **Companion below its base.** The supporting path uses 200 ms. A cache that ignores the companion would hold the response for 60 seconds. This is the mismatch most likely to be a mistake: a companion added to an existing header whose base was not lowered.
- **Base of zero with a companion of one day.** The supporting path fetched once and reused the response for the whole run, so staleness climbs to the length of the run. A cache that ignores the companion would not reuse it at all.
- **Malformed companion.** `0.2` is not an integer. The caches ignored it and applied `max-age=1`, with the same result as the whole-second path in test 5.
- **None of these is an error to a cache.** The two values are independent, so a cache cannot tell a deliberate difference from a mistake. The draft's "Mismatched Values" section says what a sender should check.
- **The prototype's header tests cover these and more**: 20 cases for mismatched pairs, digit limits, signs, suffixes, quoting, empty arguments and letter case. All pass.

## Test 7. Misconfigured paths

**Question.** What happens when an operator sets the trust configuration wrongly, or picks an absurdly short lifetime?

`--modes` sets `proxy_cache_fine_time` at each cache, origin side first. The default is `origin,trusted,trusted,trusted,trusted`. A cache set to `off` behaves as an older cache: it applies the base directive and passes Age-Ms on unchanged.

```sh
nix run ./contrib/subsecond-cache#layers -- \
  --modes origin,trusted,off,trusted,trusted \
  --path "p=max-age=1, max-age-ms=200"
```

| Configuration | Path delay | Cache-Control | Responses | Mean | p99 | Max | Origin req/s |
|---|---|---|---:|---:|---:|---:|---:|
| Correct | None | `max-age=1, max-age-ms=200` | 457820 | 98.8 | 194.0 | 204.0 | 15.2 |
| Third cache `off` | None | `max-age=1, max-age-ms=200` | 479063 | 1022.5 | 2043.0 | 2152.0 | 1.9 |
| Third cache `off` | None | `max-age=0, max-age-ms=200` | 498009 | 99.3 | 195.0 | 203.0 | 16.6 |
| Third cache `off` | 234 ms | `max-age=1, max-age-ms=500` | 288396 | 1029.8 | 2188.0 | 2256.0 | 2.0 |
| Every cache `trusted` | None | `max-age=0, max-age-ms=100` | 97957 | 0.2 | 1.0 | 3.0 | 9796.0 |
| Every cache `origin` | None | `max-age=0, max-age-ms=100` | 115236 | 51.9 | 98.0 | 100.0 | 30.0 |
| Every cache `origin` | 234 ms | `max-age=0, max-age-ms=100` | 164 | 120.9 | 123.0 | 124.0 | 16.8 |
| Correct | None | `max-age=0, max-age-ms=1` | 53301 | 1.2 | 3.0 | 8.0 | 1508.6 |

- **An older cache inside a trusted path is the one that does harm.** It held the response for one to two seconds under `max-age=1` and replayed the Age-Ms it received. The caches after it believed the response was young and reused it for up to 200 ms more. The oldest response was 2152 ms old, where the origin asked for 200 ms.
- **In this run the excess followed the base.** The older cache held the response for as long as `max-age=1` allowed. With `max-age=0` that nginx stores nothing and the result matches the correct configuration. This is one path with an honest older cache. It is not a general limit: stale permissions add to the holding time, and a faulty source can understate age by more.
- **`max-age=0` is not `no-store`.** Another older cache could store the response and validate it. A base of zero reduces the exposure on a path that is not fully known; it does not remove it.
- **A cache cannot detect this.** The replayed pair is consistent. Only configuration says which upstream maintains fine age, which is why the draft requires it.
- **No fine-age source fails towards the base.** With every cache `trusted`, the first one receives no Age-Ms from the origin and falls back to `max-age=0`. The prototype reads a missing pair as age zero only at a cache set to `origin`; the draft's receiving rule makes the same distinction, so this is the outcome the draft specifies. Nothing is reused and the origin took 9796 requests a second. Responses are never too old; the cost is load, the same as sending `max-age=0` alone.
- **Every cache set to `origin` did not show extra age in this run.** This is still incorrect sender classification. Origin mode establishes zero only without either age field; a response with a pair instead causes fine fallback in that mode. Misclassifying a cache response that lacks both fields can establish an unjustified zero. The observed figures do not establish safety, or a general per-tier bound, for this configuration.
- **One millisecond is caching in name only.** About a quarter of requests reached the origin. This is the exposure of `max-age=0` today.

## Test 8. Simulated HLS players

**Question.** Does a 200 ms playlist lifetime let players find new segments sooner, and what does it cost the origin?

```sh
nix run ./contrib/subsecond-cache#bench -- --output DIR
```

- **Path.** Origin, shield and edge, all nginx on loopback. The shield is set to `origin`, the edge to `trusted`.
- **Stream.** One-second MPEG-TS segments, with a new segment and playlist each second. Segments are sent with `max-age=60`.
- **Players.** Twenty simulated players, started at random offsets within a second. Each reloads the playlist one second after it finds a new segment and half a second after it does not, then downloads the segment. Playback starts at three buffered segments.
- **Paced.** Players either download a segment as fast as possible, or spread it over 750 ms.
- **Load.** Optionally `wrk` with 16 connections requests the playlist from the edge as fast as it can.
- **Runs.** Each combination ran three times for 60 seconds after a 10-second warm-up. The table gives the median of the three. Run on 25 November 2026.

Discovery is the time from a segment being published to a player first seeing it in a playlist.

| Playlist policy | Load | Discovery p50 (ms) | Discovery p95 (ms) | Range of p95 (ms) | Stalled player-seconds | Failed reloads | Origin playlist requests per segment |
|---|---|---:|---:|---:|---:|---:|---:|
| `max-age=0` | No | 400 | 967 | 966–974 | 0 | 0 | 20.0 |
| `max-age=1` | No | 1270 | 2241 | 2171–2259 | 0.6 | 0 | 0.5 |
| `max-age=0, max-age-ms=200` | No | 588 | 968 | 907–998 | 0 | 0 | 4.0 |
| 200 ms, plus `stale-while-revalidate-ms=200` | No | 683 | 970 | 962–1024 | 0 | 0 | 3.0 |
| `max-age=0` | Yes | 610 | 3064 | 2029–4489 | 31.4 | 4 | 768 |
| `max-age=1` | Yes | 845 | 1712 | 1684–1744 | 0 | 0 | 7.1 |
| `max-age=0, max-age-ms=200` | Yes | 557 | 936 | 872–959 | 0 | 0 | 45.2 |
| 200 ms, plus `stale-while-revalidate-ms=200` | Yes | 565 | 971 | 873–1009 | 0 | 0 | 5.0 |

These rows are the unpaced runs. Each run covers 1200 player-seconds. The paced runs gave the same ordering.

- **A 200 ms lifetime found segments as soon as `max-age=0`.** Both gave a 95th percentile near 970 ms. The player's own reload interval sets that figure, so a shorter lifetime would not improve it here.
- **It did so with a fifth of the origin requests.** Four per segment against 20, one for each player reload.
- **`max-age=1` took more than twice as long.** With no other traffic the origin was asked once every two seconds, so half the playlists were never fetched. This is nginx's whole-second deadline across two tiers, as in [Test 5](#test-5-the-same-lifetime-in-both-units). A cache that applied upstream Age would do better.
- **Under load, `max-age=0` failed.** nginx does not store a `max-age=0` response, so every request became a miss and waited its turn behind the cache lock. The load generator fell from tens of thousands of requests a second to under 3000, with timeouts in every run. Players stalled, and some reloads took more than five seconds. This is the cache lock in nginx meeting a response it cannot store. Another cache, or nginx with different settings, may behave differently.
- **Under load, 200 ms held.** Discovery was unchanged. The origin served 45 requests per segment, because several requests can refetch an expired entry at once.
- **The stale window removed that excess.** With `stale-while-revalidate-ms=200`, one request refreshes and the rest are served the stored playlist. The origin served 5 requests per segment, with the same discovery time.
- **An older cache in the path gives the fallback.** With an unmodified nginx as the shield, `max-age=0, max-age-ms=200` behaved as `max-age=0`: 962 ms and 20 requests per segment. `max-age=1, max-age-ms=200` behaved as `max-age=1`: 2234 ms. One run each.

**Limits.**

- **The machine was not idle.** A virtual machine and a software build ran alongside. The load average was 7 to 39 on 24 threads, and the load generator's rate varied between runs from about 15,000 to 42,000 requests a second. Apart from `max-age=0` under load, the 95th-percentile discovery figures in the table varied by less than 100 ms between repetitions.
- **The players are a script.** They follow one reload rule. A real player has its own schedule, bitrate switching and buffer policy.
- **The load is not an audience.** Sixteen connections requesting one URL as fast as possible is a stress, not a model of viewers.
- **One implementation, one host.** There is no network delay, loss or second cache implementation.
- **Stalls were rare except under `max-age=0` with load.** This test does not show that a finer lifetime prevents stalls in ordinary conditions.

## What these tests do not show

- **A conforming whole-second baseline.** RFC 9111 already counts upstream age and request delay, and does not grant a new lifetime at every cache. Stock nginx does not apply Age, so these runs cannot show what truncating Age to whole seconds costs between caches that do. That needs a second implementation, with the age each tier sent and received logged.
- **Caches with independent clocks and demand.** All five processes share one clock and one implementation.
- **Clock steps.** The prototype drops a fine entry when the wall clock steps by more than 10 ms, on suspend and on restart. The comparison has unit tests and the restart has an integration test. No run here steps a real clock.
- **Real players.** Tests 1 to 7 model no player. Test 8 uses scripted players on loopback. Whether sooner playlist updates reduce stalls on real devices and networks is still to be measured.
- **Real networks.** The delays are fixed and illustrative. There is no loss, jitter or congestion.
- **Other implementations.** Every cache is the same nginx prototype. Mixed deployments are covered by the prototype's [integration tests](https://github.com/randomizedcoder/nginx-tests/tree/http-cache-millisecond-freshness), not here.
- **Repeatability.** Tests 1–7 report single runs per row, not confidence intervals. Test 8 reports medians of three repetitions per scenario, with a per-run p95 range. Its two mixed-version smoke runs have one repetition each. No statistical confidence interval or production variability estimate is claimed.
