# Practical tests of millisecond freshness

Dave Seddon · Companion to the [explainer](explainer.md) and the [Internet-Draft](draft-seddon-httpbis-subsecond-freshness.md)

These tests run the [nginx prototype](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness) as a chain of five caches on one machine and measure how old a response is when it leaves the last cache. Anyone with Nix can repeat them in about 15 seconds each.

## Summary

- **Updates arrive about twenty times sooner.** Through five caches with no network delay, responses under `max-age=1` were on average 999 ms behind the origin. Under `max-age=0, max-age-ms=100` they were 48 ms behind.
- **The lifetime holds across the whole chain.** The oldest 100 ms response seen was 111 ms old after five caches. Each cache deducts the age it received.
- **The cost is origin requests.** One fetch per lifetime is ten a second at 100 ms, against one a second or fewer at `max-age=1`. Concurrent misses raised that to 36 a second with four connections.
- **A lifetime must exceed the round trip to the origin.** With 234 ms of simulated round-trip delay, a 100 ms response was stale on arrival. The last cache reused nothing.
- **Over that delayed path, 500 ms works.** Responses were on average 208 ms behind the origin, against 1011 ms under `max-age=1`.
- **Not shown.** Whole-second lifetimes adding up across independent caches, the effect on players, and behaviour under real network conditions.

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

Mean, p99 and Max are staleness in milliseconds. Each row is one ten-second run.

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

- **The lifetime holds.** Staleness on the fine path runs evenly from 0 to about 100 ms, as it would at a single cache. Five caches did not make it five times longer.
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
- **The extra load in test 1 is concurrent misses.** With four connections, several requests find the entry expired at once and each fetches. nginx's `proxy_cache_lock` would normally collapse them, but a request waiting on that lock checks again only every 500 ms, which is longer than the lifetime. The tests leave it off.
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
- **The responses are fresh but few.** They are about 125 ms old, close to the one-way delay. The cache protects nothing.
- **This is the correct result.** The origin asked for 100 ms, and no cache served anything older than about 144 ms. The lesson is for whoever chooses the lifetime.
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

## What these tests do not show

- **Whole-second lifetimes adding up.** Operators limit cache depth today because each cache can add up to its own lifetime. That does not appear here. All five nginx processes share one clock and whole-second deadlines, so they expire and refresh together. Caches with independent clocks and independent demand would not. Showing it needs a clock offset for each cache.
- **Players.** No player, segment download or buffer is modelled. Whether sooner playlist updates reduce stalls is still to be measured.
- **Real networks.** The delays are fixed and illustrative. There is no loss, jitter or congestion.
- **Other implementations.** Every cache is the same nginx prototype. Mixed deployments are covered by the prototype's [integration tests](https://github.com/randomizedcoder/nginx-tests/tree/http-cache-millisecond-freshness), not here.
- **Repeatability.** Each row is a single run. Figures vary by a few percent between runs.
