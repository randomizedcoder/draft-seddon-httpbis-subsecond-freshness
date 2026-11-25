# Practical tests of millisecond freshness

Dave Seddon · Companion to the [explainer](explainer.md) and the [Internet-Draft](draft-seddon-httpbis-subsecond-freshness.md)

These tests run the [nginx prototype](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness) as a chain of five caches on one machine and measure how old a response is when it leaves the last cache. Anyone with Nix can repeat them in about 15 seconds each.

## Summary

- **Updates arrive about twenty times sooner.** Through five caches with no network delay, responses under `max-age=1` were on average 999 ms behind the origin. Under `max-age=0, max-age-ms=100` they were 48 ms behind.
- **Fine age is carried across the chain.** The oldest response under the 100 ms policy was 111 ms old at the measurement point. Each cache deducts the age it received; this is not a strict 100 ms bound on delivery age.
- **The cost is origin requests.** One fetch per lifetime is ten a second at 100 ms, against one a second or fewer at `max-age=1`. Concurrent misses raised that to 36 a second with four connections.
- **A lifetime must exceed the round trip to the origin.** With 234 ms of simulated round-trip delay, a 100 ms response was stale on arrival. The last cache reused nothing.
- **Over that delayed path, 500 ms works.** Responses were on average 208 ms behind the origin, against 1011 ms under `max-age=1`.
- **Same lifetime, finer accounting: about half the staleness in nginx.** `max-age=1, max-age-ms=1000` averaged 498 ms against 1004 ms for `max-age=1`. That part of the gain comes from nginx's whole-second deadlines, not from the shorter lifetime.
- **Mismatched and malformed pairs behave as the draft says.** A companion above or below its base is used as written on a supporting path. A malformed companion yields to its base.
- **A wrong trust setting costs the benefit, within a limit.** With an older cache replaying Age-Ms inside a path configured as supporting, `max-age=1, max-age-ms=200` gave responses up to 2152 ms old, against 204 ms when configured correctly. With a base of `max-age=0` the effect did not appear in this run.
- **Not shown.** The effect on players, behaviour under real network conditions, and a baseline cache that applies upstream Age as RFC 9111 specifies.

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
nginx stores whole-second deadlines, and it neither reads nor sends Age.

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
- **This is not a test of Age truncation between conforming caches.** Stock nginx neither reads nor sends Age, so the whole-second path here has no upstream age to truncate. A baseline that applies Age as RFC 9111 specifies would sit between these two rows. We have not run one.
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
- **No fine-age source fails towards the base.** With every cache `trusted`, the first one receives no Age-Ms from the origin and falls back to `max-age=0`. The prototype reads a missing pair as age zero only at a cache set to `origin`; the draft's receiving rule does not make that distinction yet. Nothing is reused and the origin took 9796 requests a second. Responses are never too old; the cost is load, the same as sending `max-age=0` alone.
- **Every cache set to `origin` did no harm here.** Each cache ignores the age it receives, but still counts its own request delay. Under one stream of requests the caches refill together, so their lifetimes did not add up. With independent demand at each tier they could, up to one lifetime per cache. This run does not show that.
- **One millisecond is caching in name only.** About a quarter of requests reached the origin. This is the exposure of `max-age=0` today.

## What these tests do not show

- **A conforming whole-second baseline.** RFC 9111 already counts upstream age and request delay, and does not grant a new lifetime at every cache. Stock nginx does not apply Age, so these runs cannot show what truncating Age to whole seconds costs between caches that do. That needs a second implementation, with the age each tier sent and received logged.
- **Caches with independent clocks and demand.** All five processes share one clock and one implementation.
- **Clock steps.** The prototype drops a fine entry when the wall clock steps by more than 10 ms, on suspend and on restart. The comparison has unit tests and the restart has an integration test. No run here steps a real clock.
- **Players.** No player, segment download or buffer is modelled. Whether sooner playlist updates reduce stalls is still to be measured.
- **Real networks.** The delays are fixed and illustrative. There is no loss, jitter or congestion.
- **Other implementations.** Every cache is the same nginx prototype. Mixed deployments are covered by the prototype's [integration tests](https://github.com/randomizedcoder/nginx-tests/tree/http-cache-millisecond-freshness), not here.
- **Repeatability.** Each row is a single run. Figures vary by a few percent between runs.
