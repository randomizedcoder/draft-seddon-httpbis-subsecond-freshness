# Finer resolution for HTTP durations

Dave Seddon · Discussion proposal for the HTTP Working Group · [Internet-Draft source](draft-seddon-httpbis-subsecond-freshness.md)

## Summary

- **Problem.** HTTP expresses freshness and age in whole seconds. An origin can choose immediate staleness or a full second, with nothing in between.
- **Today.** The limit is in the wire format, not in every implementation. Of eleven browser engines and caches we read, Chromium, WebKit and Varnish already decide freshness at sub-second resolution, three more store a finer time and round it, and five use whole seconds throughout. None can be told a sub-second lifetime in a standard way. [Survey](#what-implementations-do-today)
- **Aim.** Let the wire format carry what those implementations already measure, and give the rest a defined target.
- **Proposal.** Millisecond companions for the cache directives that carry a duration and for the Age response field, so that each cache counts the time already spent upstream.
- **Scope.** Every whole-second duration in HTTP caching, plus Retry-After and Prefer `wait`. Appendix A lists each field and what we left unchanged.
- **Rollout.** The origin sends a whole-second fallback with every companion. Older caches use the fallback.
- **Browsers.** No change is required. A browser applies the whole-second fallback. [Browsers](#browsers)
- **Measured.** Through five nginx caches, responses under `max-age=1` averaged 999 ms behind the origin, and 48 ms under `max-age-ms=100`. [Practical tests](measurements.md)

HTTP already carries upstream age across cache tiers. A new lifetime at each tier is not its intended behaviour. The proposal adds a sub-second lifetime and preserves fractional age on a configured path; it does not repair arbitrary Age handling or guarantee the age of the underlying application data. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)

## Sharing a freshness lifetime

Our live HLS playlists change every second or two. Suppose the origin chooses a 200 ms freshness lifetime. A shield serving the playlist at age 175 ms can report only `Age: 0` in whole seconds. We propose that it send these fields together.

```http
Cache-Control: max-age=0, max-age-ms=200
Age: 0
Age-Ms: 175
```

- **Known supporting path.** The edge counts 175 ms upstream, 15 ms for its request and 10 ms in its own cache. At exactly 200 ms the playlist is stale. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)
- **Older cache.** It ignores the companions and applies `max-age=0`. The origin can choose `max-age=1` if a full second is acceptable at older caches.
- **Unknown path.** With that one-second fallback, an older intermediary could hold the response for another 300 ms and still forward `Age: 0` and the original `Age-Ms: 175`. An upgraded edge uses the whole-second policy and drops the unreliable fine age. [RFC 9110 §5.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.1)

### Deployment example — streaming the U.S. Super Bowl

- **Scale.** Consider an event serving 30–40 million viewers, with hundreds of millions of HTTP requests per second across all object types. These are workload estimates. For a published comparison, Tubi reported a peak of 15.5 million concurrent streaming viewers during Super Bowl LIX. [Tubi’s event report](https://corporate.tubitv.com/press/4545/)
- **Why the manifest matters.** Caches serve many players from one playlist refresh. A player that reloads just before the cache refreshes can receive a playlist that omits an already available segment. It may then wait another reload interval to discover it. [RFC 8216 §6.3.4](https://www.rfc-editor.org/rfc/rfc8216.html#section-6.3.4)
- **What to test.** A player that requests a segment 500 ms earlier has 500 ms more before the same playback deadline. On a slow or variable connection, that margin could let the download finish before the buffer runs dry. We have yet to measure how often players gain that much or how often it prevents a stall. Compare segment request and completion times, rebuffer events and origin playlist requests under both cache policies.

### Relationship to Media over QUIC

- **MoQ counts cache time in milliseconds.** Its transport draft treats relays as caches. `MAX_CACHE_DURATION` is the number of milliseconds an object can be served from a cache, and the delivery timeouts use the same unit. QUIC expresses its idle timeout and maximum acknowledgement delay in milliseconds. [draft-ietf-moq-transport-23 §§5.2, 10.3](https://datatracker.ietf.org/doc/draft-ietf-moq-transport/) · [RFC 9000 §18.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-18.2)
- **HTTP is limited by grammar.** HTTP caches can express nothing between zero and one second, though the caches themselves can serve many requests within a second.
- **HTTP remains the deployed base.** Large live events run on HLS and DASH over HTTP caches, and those services will run alongside MoQ for years. MoQ can itself run over WebTransport on HTTP/3.
- **What we expect.** Millisecond freshness would let those services use their existing caches closer to the timescales MoQ is designed for. We think this would keep HTTP a practical choice for latency-sensitive delivery where a deployment already depends on it. We have yet to measure how far it narrows the gap.

## Proposed wire format

| Existing | Proposed companion | What it controls |
|---|---|---|
| `max-age=1` | `max-age-ms=1250` | 1.25 s of freshness since generation or validation |
| `s-maxage=0` | `s-maxage-ms=200` | 200 ms for a shared cache, with the usual shared-cache revalidation requirement |
| `stale-while-revalidate=0` | `stale-while-revalidate-ms=200` | An additional 200 ms from expiry when serving stale is permitted |
| `Age: 1` | `Age-Ms: 1075` | Total estimated age of 1.075 s at this hop |

These four share a freshness lifetime between caches. The rest complete the set.

| Existing | Proposed companion | Where | What it controls |
|---|---|---|---|
| `stale-if-error=1` | `stale-if-error-ms=1500` | Response or request | 1.5 s from expiry in which a stale response can be used after an error |
| `max-age=1` | `max-age-ms=500` | Request | The client prefers a response no older than 500 ms |
| `min-fresh=0` | `min-fresh-ms=500` | Request | The client prefers a response that stays fresh for another 500 ms |
| `max-stale=0` | `max-stale-ms=250` | Request | The client accepts a response up to 250 ms past expiry |
| `ttl=0` | `ttl-ms=25` | Cache-Status parameter | Diagnostic. 25 ms of freshness remained at this cache |
| `Retry-After: 1` | `Retry-After-Ms: 250` | Response field | Retry after 250 ms. Older clients wait one second |
| `wait=1` | `wait-ms=250` | Prefer request field | The client expects processing to take at most 250 ms |

- The directives appear in Cache-Control. The response directives can also appear in a targeted field such as CDN-Cache-Control.
- Retry-After and Prefer `wait` are not caching. The draft keeps them in a separate section that the WG can split out.
- Each companion carries the complete value in unsigned decimal digits. The same spelling works as an Integer in a targeted dictionary. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9651 §3.3.1](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.1)
- The smallest positive value is 1 ms. Appendix C considers other encodings, including an explicit unit for finer resolution.
- The names are provisional. Appendix E has notes from a prototype.

### Delta milliseconds

Every whole-second duration in HTTP caching comes from one grammar rule, `delta-seconds = 1*DIGIT`. Age and the max-age, s-maxage, max-stale and min-fresh directives use it, and later extensions such as stale-while-revalidate import it. We propose a sibling rule. [RFC 9111 §1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3)

```abnf
delta-milliseconds = 1*15DIGIT
```

- **Meaning.** A non-negative integer number of milliseconds. It gives the complete duration and is never added to a delta-seconds value.
- **Range.** Fifteen digits is the Structured Fields Integer limit, about 31,700 years. The same value therefore parses in Cache-Control and in a targeted dictionary. [RFC 9651 §3.3.1](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.1)
- **Why milliseconds.** It is the finest decimal unit in which the whole delta-seconds range fits a Structured Fields Integer. The 2^31-second ceiling is 13 digits of milliseconds. Fifteen digits of microseconds cover under 32 years, and of nanoseconds under 12 days.
- **Arithmetic.** RFC 9111 suggests at least 31 bits for delta-seconds. In milliseconds, 31 bits last under 25 days. A recipient needs 41 bits for the 2^31-second ceiling and 50 bits for the whole 15-digit range. A 64-bit integer covers both.
- **Overflow.** A delta-seconds value that is too large is treated as 2^31 seconds. A companion always arrives with a whole-second base, so we propose that a recipient rejects an unrepresentable value and uses the base. The WG may prefer the saturating rule for consistency.
- **Age calculation.** RFC 9111 defines it as clock differences. Only the Age field value and the freshness lifetime are tied to seconds, so the same steps work in milliseconds. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)

## Cache behaviour

1. **Select the policy field.** [RFC 9213 §§2.1–2.3](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1)
   - A cache that supports targeted fields uses the first valid, non-empty field in its target list. That field displaces Cache-Control and Expires for the response.
   - Put the fallback, the companion and any restrictions together in each field that needs them.
   - An unrecognised dictionary member is ignored. A dictionary parse failure discards the field, and selection continues.
2. **Select the directive.** [RFC 9111 §§4.2.1, 4.2.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1)
   - In a shared cache, s-maxage takes precedence, even over a fine max-age. Otherwise use max-age, then Expires and the heuristic rules.
   - no-store, private, no-cache and the revalidation directives keep their usual effect.
   - s-maxage prohibits stale reuse by a shared cache. Use max-age in a CDN-targeted policy when a stale-while-revalidate window is wanted.
3. **Refine only the selected quantity.** The companion replaces its base. It is never added to it. [RFC 9111 §5.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.3)

   | The selected field contains | Upgraded cache with a fine age | Any other cache |
   |---|---|---|
   | Base and companion, e.g. 1 s and 1250 ms | Uses the companion, 1.25 s | Uses the base, 1 s |
   | Base only | Uses the base | Uses the base |
   | Companion only | Ignores the companion and continues with the ordinary rules | Ignores the unknown directive |

   This is the pattern RFC 9111 describes for behavioural extensions, where a new directive modifies an old one sent alongside it. Support can be partial, so send a suitable fallback for each quantity.

For example, the following gives an upgraded CDN 200 ms of freshness and a further 200 ms of stale-while-revalidate. Any other CDN gets zero freshness and no stale window. Other caches see the ordinary policy. A sender choosing a one-second fallback accepts the longer interval at older caches.

```http
Cache-Control: max-age=0
CDN-Cache-Control: max-age=0, max-age-ms=200, stale-while-revalidate=0, stale-while-revalidate-ms=200
```

## Reporting age

Use the RFC 9111 age calculation in milliseconds. Date keeps whole-second precision, so a cache that takes the greater of corrected age and Date-based apparent age may reach expiry earlier than in the example above. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)

### Recommended rollout

Send a whole-second fallback with every fine policy. No capability handshake is needed.

| Requirement | Fallback |
|---|---|
| Strict sub-second freshness budget | `max-age=0` |
| A full second is acceptable at older caches | `max-age=1` |

Make the same decision independently for the stale window.

| Response path | What the receiving cache does |
|---|---|
| Any sender → older cache | Uses the existing directives and ordinary Age processing. Fine directives confer no extra permission. |
| Origin → upgraded cache | Calculates age from the generation or validation exchange and its own elapsed time. Applies valid paired fine directives. |
| Upgraded shield → upgraded edge on a known supporting path | Uses the shield's fine age as the upstream age, adds request delay and local residence, and regenerates both Age fields on reuse. |
| Older or unknown hop → upgraded cache | Uses ordinary Age processing and the whole-second policy. Drops any fine-age field on forwarding or reuse. Resumes reporting fine age once it can establish age again, for example by validating directly with the origin. |

**Establishing a supporting path.** [RFC 9111 §5.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1)

- An operator establishes it by configuration, for example in a managed CDN.
- Knowing that the immediate peer is upgraded gives no assurance about caches earlier on the path.
- A fine-age field by itself, or an absent Age field, cannot establish the path.

**Checking the pair.**

- A sender derives both fields from one sample, with `Age = floor(Age-Ms / 1000)`.
- On a supporting path, a recipient requires one valid value of each field and checks that relation.
- If either value is missing, repeated, inconsistent or out of range, the recipient discards the fine sample and applies ordinary Age and policy processing. A direct origin exchange can establish a new estimate.
- An older cache can replay a pair that passes the check. The check supplements the configured path and cannot replace it.

## Operational and security considerations

The draft's Security Considerations section takes each of these in turn. The short version: the extension adds no authority. Every fine value rides on a whole-second base the sender must accept, and a cache uses fine age only where it has been configured to.

| Concern | What limits it | What remains |
|---|---|---|
| **A false or replayed Age-Ms** makes a response look young | Used only from a configured source, over a fully configured path. Unused values are removed. Inconsistent pairs are rejected. Off by default. | A configured source that lies, or a path that changes after configuration. The same is true of Age today. |
| **Stripping the fine fields** | The base applies, which the sender chose and legacy caches use anyway. A missing pair from a cache is never read as age zero. | The base can be longer than the fine value. A sender that cannot accept that sends a base of zero. |
| **A gateway rewrites the base only** | The draft asks rewriters to examine the companion. | An unaware gateway. Affects only caches configured for fine age. |
| **Malformed, mismatched or huge values** | Each has a defined outcome. An invalid companion never invalidates its base. Names are matched in full. | A sender's own mistakes, such as a unit slip. |
| **Clock steps, suspend, snapshots** | A cache must account for the time or stop relying on fine age. The prototype refetches after a restart, a suspend or a wall-clock step over 10 ms. | Events a cache cannot detect, such as a snapshot restore that rolls back every clock. |
| **Origin load** | No more than `max-age=0` allows today. [RFC 5861 §5](https://www.rfc-editor.org/rfc/rfc5861.html#section-5) | Short lifetimes still cost origin requests. See the [measurements](measurements.md). |
| **Tiny retry delays** | Retry-After can already be zero. Clients keep their own minimum and limits. | A client with no limits of its own. |
| **Privacy**: finer timing reveals cache activity | A cache can omit Age-Ms and `ttl-ms` at a boundary. Coarsened age rounds up. [RFC 9211 §6](https://www.rfc-editor.org/rfc/rfc9211.html#section-6) | Response timing itself, as today. |

- **Stale window.** It helps when a request arrives during the window and validation completes in time. It cannot guarantee an uninterrupted stream.
- **Tested.** The [mistakes and misconfigurations](#mistakes-and-unlikely-inputs) in Appendix B have defined outcomes, and most are measured or covered by the prototype's tests.

### Designing for another thirty years

The useful long-term property is a stable duration unit with explicit fallback, rather than a prediction about how fast future machines will run. Keep integer milliseconds, the existing 15-digit range and the distinction between timestamps, elapsed age, freshness and scheduling. Do not change the meaning of an existing field. A future finer unit would need its own demonstrated use case, range and precedence rules; no microsecond or nanosecond field is proposed now.

The range is a wire-format property, not a recommendation to retain responses for millennia. A signed 64-bit integer can store it, but blindly multiplying the maximum millisecond value by a million to produce nanoseconds overflows that integer. Timer conversions and sums need checked arithmetic. Coarse timers should reduce reuse, not silently lengthen it.

Clock resets, restarts, multi-tier trust, conditional validation, cache-key selection and private responses will still matter even if hardware becomes faster. Millisecond freshness also does not alter HLS player reload rules or create a strict end-to-end publication deadline.

### Agents and LLM applications

An agent fleet retrieving the same changing, cacheable resource could use a shared 100–500 ms budget to absorb repeated reads. That is a workload hypothesis to test, not a measured benefit or a claim that agents require polling. Event delivery, blocking requests and longer cache lifetimes can be better choices. Authorisation and `Vary` still determine who may share a response. Prompt caching, semantic similarity caches and generated POST responses are separate problems; this proposal does not make them reusable.

### Spreading the race at the live edge

Freshness precision and refresh scheduling solve different problems. Lowering a lifetime can make a synchronised burst happen more often. Stale-while-revalidate permits bounded stale responses during refresh; it does not by itself collapse concurrent requests or spread refreshes across independent caches. Request collapsing and a shield help with those bursts. [RFC 9111 §4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3)

One exploratory option is bounded probabilistic early revalidation: within the last part of an existing freshness lifetime, select a small number of requests to start a refresh, collapse competing work for that cache key, and let other clients use the still-permitted response. This needs no extra stale permission. Never randomise expiry past the freshness or stale limits, restart a stale window, or reset Age merely because a refresh has started. Published probabilistic early-expiration algorithms are useful prior art. [Vattani, Chierichetti and Lowenstein, 2015](https://cseweb.ucsd.edu/~avattani/papers/cache_stampede.pdf)

Dave's suggested 0.01% pioneer cohort amounts to 100 viewers out of one million. However, a pioneer helps other viewers only when they share the same cache key and cache. At a small edge or a personalised playlist, there may be no pioneer in a publication interval. A cache-level selection can adapt to the local request rate without exposing viewer identities or creating extra cache variants. These are experiment ideas, not proposed protocol fields.

An early refresh can also be too early: a 304 just before publication renews the old representation's freshness and can postpone discovery. Compare refresh jitter against publication-aware requests and LL-HLS blocking playlist reload. A pioneer cannot obtain an unpublished segment. [Apple's blocking playlist reload explanation](https://developer.apple.com/videos/play/wwdc2020/10231/)

For retries, any random delay belongs after the selected Retry-After minimum; subtracting jitter would invite requests before the server's requested wait. Retry scheduling should remain separate from cache expiry.

### Where curl fits

libcurl does not maintain an HTTP representation cache. An application can already send the companion request directives and read the response fields through its existing header APIs. Consequently, the cache prototype belongs in nginx and other caches; libcurl is useful for a second implementation of Retry-After-Ms and for client examples. `CURLINFO_RETRY_AFTER` currently returns seconds and should retain those units; a millisecond result needs a distinct API or an application-level adapter. [curl's cache inventory](https://everything.curl.dev/internals/caches.html) · [curl_easy_header](https://curl.se/libcurl/c/curl_easy_header.html) · [CURLINFO_RETRY_AFTER](https://curl.se/libcurl/c/CURLINFO_RETRY_AFTER.html)

## What implementations do today

We read the source of three browser engines and eight caches in November 2026 to see where the whole-second limit actually lives. The question for each: at what resolution does it measure the age of a stored response, and at what resolution can it be told a lifetime?

| Implementation | Age measured internally | Effective freshness resolution | `Age` it sends | Given `max-age=0.2` |
|---|---|---|---|---|
| Chromium | Microseconds | Sub-second | n/a | Network cache ignores the directive |
| WebKit (Safari) | Floating-point seconds | Sub-second | n/a | Uses 200 ms |
| Firefox | Whole seconds | One second | n/a | Truncates to 0 and stops reading the field |
| Varnish | Floating-point seconds | Sub-second | Whole seconds | Truncates to 0 |
| Envoy cache filter | Sub-second type | One second: age is cast to seconds | Whole seconds | Ignores the directive |
| Apache httpd `mod_cache` | Microseconds | One second: compared in seconds | Whole seconds | Ignores the directive |
| Souin (Caddy cache) | Nanoseconds | One second | Whole seconds, rounded up | Ignores the directive |
| nginx | Whole seconds | One second | None | Does not cache the response |
| Squid | Whole seconds | One second | Whole seconds | Truncates to 0 |
| Apache Traffic Server | Whole seconds | One second | Whole seconds | Truncates to 0 |
| HAProxy cache | Whole seconds | One second | Whole seconds | Truncates to 0 |

What the survey shows:

- **Three of eleven already decide freshness at sub-second resolution**: Chromium, WebKit and Varnish. In those, the wire format is the coarsest part. Three more store a finer type and round to seconds before comparing.
- **Five are whole seconds throughout.** For them the proposal is new work, not catching up. Firefox, nginx, Squid, Traffic Server and HAProxy are in this group.
- **No implementation can be told a sub-second lifetime by an origin in a standard way.** Operators who want one today use private configuration. Varnish documents millisecond durations in VCL, and Fastly documents a duration type with an `ms` suffix. Cloudflare and CloudFront document a minimum of one second.
- **Every cache sends `Age` in whole seconds**, including Varnish, which knows the fraction and discards it. This is the precision the proposal carries between tiers.
- **A fractional `max-age` has four different outcomes** across these implementations: used, truncated to zero, directive ignored, or response not cached. That is the evidence for a separate companion with a valid base, and against decimal seconds.

So the accurate statement is narrower than "implementations are already sub-second". Some widely used ones are, most are not, and none of them can agree on a sub-second lifetime because HTTP has no way to express one.

Limits of the survey: it is a source read on one date, not a test. Not confirmed: whether Fastly's cache honours a sub-second lifetime. The CDN figures come from public documentation only.

Sources: Varnish [`cache_rfc2616.c`](https://github.com/varnishcache/varnish-cache/blob/master/bin/varnishd/cache/cache_rfc2616.c), [VCL durations](https://varnish-cache.org/docs/trunk/reference/vcl.html) · Squid [`refresh.cc`](https://github.com/squid-cache/squid/blob/master/src/refresh.cc) · Traffic Server [`MIME.cc`](https://github.com/apache/trafficserver/blob/master/src/proxy/hdrs/MIME.cc) · HAProxy [`cache.c`](https://github.com/haproxy/haproxy/blob/master/src/cache.c) · Envoy [`cache_headers_utils.cc`](https://github.com/envoyproxy/envoy/blob/main/source/extensions/filters/http/cache/cache_headers_utils.cc) · httpd [`cache_util.c`](https://github.com/apache/httpd/blob/trunk/modules/cache/cache_util.c) · Souin [`pkg/rfc`](https://github.com/darkweak/souin/tree/master/pkg/rfc) · nginx [`ngx_http_upstream.c`](https://github.com/nginx/nginx/blob/master/src/http/ngx_http_upstream.c). Browser sources are listed in the next section.

## Browsers

Most HTTP is consumed by browsers, so this section states what the proposal asks of them, what it does not, and what objections to expect. It gives a summary across the three engines, then an assessment of each.

The facts were read from each engine's source tree on 24 November 2026. They are a source read, not a test. Items we could not confirm are marked.

### Summary

- **Nothing is required of browsers.** A browser has no configured fine-age source, so under the draft it has no fine age and applies the whole-second base, exactly as it does today.
- **Browser users still benefit.** The gain is at the CDN tiers. A page or player receives a fresher response from the edge without any browser change.
- **A sender can keep browsers out of it entirely.** Put the fine policy in `CDN-Cache-Control` and an ordinary policy in `Cache-Control`. The browser then never sees a companion.
- **Support is optional and can come later, or never.** Whether a private cache should use fine values at all is an [open question](#open-question-fine-values-in-a-private-cache).

| | Chromium | Firefox | Safari (WebKit) |
|---|---|---|---|
| **Impact if the browser changes nothing** | None | None | None |
| `max-age=0, max-age-ms=200` today | Stale at once; validates each use | Same | Same |
| `max-age=1, max-age-ms=200` today | Fresh for one second | Fresh for under one second | Fresh for one second |
| `Age-Ms` today | Not read | Not read | Not read |
| `max-age=0.2` today (not proposed) | Network cache ignores the directive | Truncated to 0; rest of the field unread | Used as 200 ms |
| Time arithmetic | Microseconds | Whole seconds | Floating-point seconds |
| Stored on disk | Times in microseconds; no stored expiry | Expiry in whole seconds | Timestamp in floating point |
| Clock used for age | Wall clock | Wall clock | Wall clock |
| Same-URL requests | Queue behind one fetch, up to 20 s | Wait for one revalidation, up to 20 s | No general coalescing found |
| Request directives honoured | `no-cache`, `max-age=0` only | `max-age`, `min-fresh`, `max-stale` | `max-age`, `min-fresh`, `max-stale` |
| `stale-while-revalidate` | Since Chrome 75 | Since Firefox 68 | Since Safari 14 |
| Acts on `Retry-After` | A few internal services only | Not in the network stack | No handling found |
| Cache partitioned by site | Since Chrome 86 | Since Firefox 85 | Yes |
| Script timer resolution | 100 µs; 5 µs when isolated | 1 ms; 20 µs when isolated | 1 ms; 20 µs when isolated |
| **Work to apply `max-age-ms`** | Small: parser | Large: parser, storage and every comparison | Small: parser |
| **Work to keep a fine age** | Elapsed-time accounting | The above, plus elapsed-time accounting | Elapsed-time accounting and request delay |
| **Most likely objection** | Two parsers to keep in step; little local benefit | Cost of leaving whole seconds | Already accepts a fraction; why a new name? |

"Isolated" means cross-origin isolated. "Elapsed-time accounting" is the draft's rule that a cache relying on fine age accounts for time without interruption; all three use the wall clock today.

### Chromium

Covers Chrome. Browsers built on Chromium, such as Edge, share this network stack; we did not check them individually.

**Today**

- Freshness and age are computed in microseconds. Request and response times are stored on disk in microseconds. No expiry is stored; freshness is recomputed from the headers on each use.
- The network cache matches the prefix `max-age=` and accepts digits only. `max-age-ms=200` is ignored. `max-age=0.2` is treated as absent, so the cache falls through to Expires or the heuristic.
- The renderer has a second parser that reads the value as a floating-point number, so it appears to accept a fraction that the network cache rejects.
- `Age` is parsed as an unsigned integer. `Age-Ms` is never read.

**Local caching and concurrency**

- One request per URL validates or fetches at a time. Others queue behind it, and several can share one network response. A queued request gives up after 20 seconds and goes to the network without the cache.
- The renderer's in-memory cache reuses a resource regardless of headers while the document is loading. Responses to `fetch()` and XHR are not kept there, so they reach the HTTP cache and its freshness rules.
- The back/forward cache keeps whole pages for up to ten minutes, independent of `max-age`. Speculative prefetch keeps responses for 300 seconds by default.
- `stale-while-revalidate` forces a synchronous check 60 seconds after the first stale use.
- Request `Cache-Control` is recognised only as `no-cache` or `max-age=0`. `min-fresh`, `max-stale` and other `max-age` values are ignored.
- `Retry-After` is read for speculative prefetch, captive-portal detection and reliability reporting. We found no handling for navigation or `fetch()`.

**If Chromium changes nothing**

- No impact. A paired response behaves as its base says.
- The request companions and `Retry-After-Ms` do nothing, as their bases do nothing today.

**If Chromium chose to support it**

- Applying `max-age-ms` is a parser change. The arithmetic and storage are already fine enough.
- Both parsers would need the same rule, or the renderer and network cache would disagree on freshness.
- A fine age needs more. Age is measured with the wall clock, and a backward step extends freshness. The draft's accounting rule is stricter than that.

**Privacy**

- `Cache-Control` is readable by cross-origin script, so `max-age-ms` would be visible. `Age-Ms` is not readable unless the server exposes it.
- Script timers resolve 100 µs, or 5 µs when isolated, with jitter. Both are finer than the new field.

**Assessment.** Lowest cost of the three and no risk from doing nothing. Expect "little local benefit" and "two parsers" as the objections.

Sources: [`http_response_headers.cc`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/net/http/http_response_headers.cc) · [`http_response_info.cc`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/net/http/http_response_info.cc) · [`http_cache.h`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/net/http/http_cache.h) · [`http_cache_util.cc`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/net/http/http_cache_util.cc) · [`resource_fetcher.cc`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/third_party/blink/renderer/platform/loader/fetch/resource_fetcher.cc) · [`http_parsers.cc`](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/third_party/blink/renderer/platform/network/http_parsers.cc)

Not confirmed: that the renderer parser accepts a fraction end to end; any earlier Chromium discussion of sub-second lifetimes.

### Firefox

**Today**

- All freshness arithmetic is in unsigned 32-bit whole seconds. The current time is the wall clock truncated to seconds. A source comment says the logic "can't have better resolution than seconds".
- `max-age` is read as an integer. Given `max-age=0.2`, the parser takes 0 and stops at the point, so any directives after it in that field are not read. The tokenizer treats `max-age-ms` as one unknown word and ignores it. `Age` is read with `atoi`. `Age-Ms` is never read.
- Because the clock is truncated, a `max-age=1` response is fresh for somewhere between zero and one second of real time. This is our inference from the code, not a test.
- The cache entry's expiry is stored on disk as 32-bit seconds.

**Local caching and concurrency**

- An absent entry has one writer; other requests queue until it finishes. A stale entry gets one conditional request and the others wait.
- A waiting request goes to the network after 20 seconds. A suspended writer is bypassed after 5 seconds. Navigations do not wait for a busy entry.
- The image, stylesheet and script memory caches hold expiry in whole seconds. A stylesheet or script already loaded by the page is reused regardless of expiry.
- `stale-while-revalidate` revalidation is dispatched at idle priority.
- Request `max-age`, `min-fresh` and `max-stale` are honoured.
- The network stack does not act on `Retry-After`. Application code such as Sync reads it. `Prefer` is only sent, as `Prefer: safe`.

**If Firefox changes nothing**

- No impact. A paired response behaves as its base says.
- A sender choosing `max-age=1` as the base gets less than a second of local reuse in Firefox, as today.

**If Firefox chose to support it**

- This is real work: a millisecond deadline in the entry metadata, which is a format change or a new metadata element, and a change to every comparison that uses seconds, including the memory caches.
- A sub-second stale window would often close before an idle-priority revalidation starts. This is our inference.
- The request companions would be meaningful here, because Firefox honours their bases.
- A fine age also needs elapsed-time accounting. Age uses the wall clock; a request time in the future is clamped.

**Privacy**

- Script timers resolve 1 ms by default, 20 µs when isolated, and 16.7 ms or coarser with fingerprinting resistance. At the default, the new field is no finer than the timer.

**Assessment.** No risk from doing nothing, and the highest cost to support. Expect the objection to be that cost. The proposal should not depend on Firefox support, and does not.

Sources: [`nsHttpResponseHead.cpp`](https://searchfox.org/firefox-main/source/netwerk/protocol/http/nsHttpResponseHead.cpp) · [`CacheControlParser.cpp`](https://searchfox.org/firefox-main/source/netwerk/protocol/http/CacheControlParser.cpp) · [`nsHttp.cpp`](https://searchfox.org/firefox-main/source/netwerk/protocol/http/nsHttp.cpp) · [`nsICacheEntry.idl`](https://searchfox.org/firefox-main/source/netwerk/cache2/nsICacheEntry.idl) · [`CacheEntry.cpp`](https://searchfox.org/firefox-main/source/netwerk/cache2/CacheEntry.cpp) · [`SharedSubResourceCache.h`](https://searchfox.org/firefox-main/source/layout/style/SharedSubResourceCache.h) · related test flakiness from whole-second granularity: [bug 1762147](https://bugzilla.mozilla.org/show_bug.cgi?id=1762147)

Not confirmed: back/forward cache rules; whether the cache index keeps its own copy of the expiry.

### Safari and WebKit

Safari's HTTP cache is WebKit's own network cache, which is open source. The system URL cache is switched off for web content. The transport underneath is closed source, and we cannot confirm that shipping Safari matches the public tree.

**Today**

- Freshness and age are computed in floating-point seconds. The disk cache stores its timestamp in floating point, without rounding.
- `max-age`, `max-stale`, `min-fresh` and `stale-while-revalidate` are parsed as floating-point numbers. `max-age=0.2` is accepted as 200 ms, which the HTTP grammar does not allow. A fractional `Age` is accepted too.
- `max-age-ms` matches no branch of the parser and is ignored. `Age-Ms` is never read.
- Age excludes the request delay. The source comment reads "No compensation for latency".

**Local caching and concurrency**

- A subresource that is still loading is shared between requests in the same page. `fetch()` responses are not shared this way.
- Background revalidations are de-duplicated per entry. We found no general coalescing of identical requests in the network cache.
- The back/forward cache keeps pages on its own timer. History navigation may use stale entries.
- `stale-while-revalidate` is on by default. Its tracking bug is currently reopened.
- Request `max-age`, `min-fresh` and `max-stale` are honoured.
- We found no handling of `Retry-After` or `Prefer` in the loader and network code.
- Tracking prevention caps the cache lifetime of some resources at seven days. That is unaffected.

**If WebKit changes nothing**

- No impact. A paired response behaves as its base says.
- WebKit remains the only engine we read that acts on a fractional `max-age`. Sites cannot rely on that elsewhere.

**If WebKit chose to support it**

- Applying `max-age-ms` is a parser change. Arithmetic and storage are already fine enough.
- A fine age needs more: the request delay that RFC 9111 adds to age, and elapsed-time accounting. Age uses the wall clock only; records dated in the future are discarded, and we found no other guard.
- Without request coalescing, several simultaneous `fetch()` calls for an expired entry may each go to the network. This is the one place we found where a short lifetime could multiply local requests. It is our inference from not finding coalescing, not a test.

**Privacy**

- Script timers resolve 1 ms, or 20 µs when isolated. At the default, the new field is no finer than the timer.

**Assessment.** No risk from doing nothing, and a low cost to support. Expect the objection "we already accept a fraction". The answer is that no other implementation we read does the same with it.

Sources: [`CacheValidation.cpp`](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/platform/network/CacheValidation.cpp) · [`NetworkCache.cpp`](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/NetworkProcess/cache/NetworkCache.cpp) · [`CachedResourceLoader.cpp`](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/loader/cache/CachedResourceLoader.cpp) · [`AsyncRevalidation.cpp`](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/NetworkProcess/cache/AsyncRevalidation.cpp) · [`NetworkSessionCocoa.mm`](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/NetworkProcess/cocoa/NetworkSessionCocoa.mm) · [stale-while-revalidate bug 201461](https://bugs.webkit.org/show_bug.cgi?id=201461)

Not confirmed: behaviour of shipping Safari; suspend handling; how Safari's native HLS playback caches, which is handled by the system media stack.

### What the three have in common

- **No local stampede in Chromium and Firefox.** They serialise same-URL requests behind one fetch. A short lifetime means more validations over time, not a burst. WebKit is the exception noted above.
- **Queued requests can outlive the lifetime.** A request that waited behind a slow fetch may find a 200 ms response already stale and fetch again. That is correct behaviour. A lifetime shorter than the fetch time gives no local reuse, as the [five-cache measurement](measurements.md) showed for a CDN.
- **Sub-second lifetimes do not re-fetch page resources.** An image or script already used by the page is reused from memory whatever its lifetime. The companions matter only for resources fetched repeatedly by script, such as a live playlist read with `fetch()`.
- **Retry-After-Ms asks nothing of browsers.** They barely act on Retry-After. Its audience is HTTP libraries and API clients.
- **Media.** Players built on Media Source Extensions fetch playlists through `fetch()` or XHR and so use the HTTP cache.

### Likely objections and answers

| Objection | Answer |
|---|---|
| "We have no roadmap time for this." | None is needed. Deployment starts at origins and CDNs and does not wait for any browser. |
| "A browser cache rarely reuses anything within a second. Where is the user benefit?" | Agreed for the local cache. The benefit reaches users through the CDN. We do not claim a browser-cache benefit. |
| "Age from the network cannot be trusted." | The draft agrees. A cache without a configured source ignores `Age-Ms`, which is every browser by default. |
| "Finer age is a timing side channel." | `Age-Ms` is not readable by cross-origin script unless the server exposes it. Caches are partitioned by site. Script timers already resolve 5 µs to 1 ms, and response timing reveals cache state today. |
| "`max-age-ms` is visible to cross-origin script, because Cache-Control is safelisted." | True. It reveals a policy the sender chose to publish, as `max-age` does. A sender that minds uses a targeted field. |
| "More validations cost battery and data." | The request rate is set by the page's script, not by the cache. With a base of zero, browsers already validate every use. |
| "Another parser path to keep consistent and test." | Only for an engine that opts in. The proposal would need to bring web-platform tests for the HTTP cache with it. |
| "A page could use tiny lifetimes to make users hammer a server." | A page can already do that with `no-cache` or a query string. The companion grants nothing new. |
| "Why not `max-age=0.2`?" | Eleven implementations give it four different outcomes, and a strict parser may fall back to a heuristic lifetime far longer than intended. [Survey](#what-implementations-do-today) |

### Why a browser might want it later

- **Live playback in the page.** A player polling a playlist through `fetch()` could reuse a response across frames or workers of one site for a few hundred milliseconds. This is a hypothesis; we have not measured it.
- **Developer tools.** Showing `Age-Ms` and `ttl-ms` in a network panel costs little and helps people debug CDN behaviour.
- **Interoperable fractions.** One engine already accepts a fractional `max-age`. A defined companion gives sites a portable way to say the same thing.

### Open question: fine values in a private cache

The rule that limits fine age to a configured path suits a CDN. A browser has no such configuration, so today's draft gives its cache nothing. The options:

| Option | Effect | Assessment |
|---|---|---|
| **Leave as is** (recommended for now) | Browsers apply the base. No change, no new risk. | Honest and cheap. The benefit stays in shared caches. |
| Pessimistic age | A private cache without a trusted `Age-Ms` assumes the worst the whole-second Age allows: `Age: 0` means up to 999 ms. | Safe, but most sub-second lifetimes are then stale on arrival. |
| Origin vouches for the path | Some signal that every cache on the path keeps fine age. | Most useful to browsers. Hard to make trustworthy: a secured connection and a consistent pair do not prove it. |

We recommend leaving the draft as is and asking the browser teams whether they want more.

## Questions for the working group

- **For browser implementers:** is "no change required, base applies" acceptable as the default? Would you want a private cache to use fine values, and under which of the options above?
- Where do you need to communicate a fractional-second lifetime between independently implemented caches? What resolution does the application need?
- How do you establish that every cache on a path updates age? Would the whole-second fallback work where you cannot establish that?
- Should Retry-After and Prefer `wait` stay in this document or move to their own?

Per-tier age, validation outcomes and playlist discovery times would help quantify the effect on players.

The [Internet-Draft](draft-seddon-httpbis-subsecond-freshness.md) specifies the grammar, ranges, duplicate handling and registration of the names. [RFC 9111 §5.2.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.4) · [IANA HTTP field registry](https://www.iana.org/assignments/http-fields/)

## Acknowledgements

The author used Claude and OpenAI Codex to research RFC references, draft and edit the text, and explore how the proposed extensions would behave in mixed cache deployments.

## Appendix A. Other time-related fields

We searched the current HTTP RFCs for whole-second durations and timestamps.

- **Who uses delta-seconds.** RFC 9111 defines it. RFC 5861, RFC 7240, RFC 6797, RFC 7838 and RFC 9163 import it. RFC 6265 uses the name for a value that can be negative.
- **Own rules.** Retry-After, Web Push TTL and Cache-Status ttl define whole seconds separately.
- **No durations.** HTTP/2 and HTTP/3 define no cache durations of their own. [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html) · [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)
- **Resolution.** Every field below that carries a time has a resolution of one second. None accepts a fraction.
- **Coverage.** The proposal gives a companion to every duration in RFC 9111, RFC 5861 and RFC 9211, and to Retry-After and Prefer `wait`. Each companion keeps the meaning of its base, including who measures the interval and when it starts.

The [IANA cache directive registry](https://www.iana.org/assignments/http-cache-directives/) lists the current cache directives.

| Field or directive | Current resolution | Treatment | Reason |
|---|---|---|---|
| Age, response max-age, s-maxage, stale-while-revalidate | 1 s, delta-seconds | In scope, `-ms` companions and `Age-Ms` | These determine how a freshness lifetime is shared between caches. [RFC 9111 §§5.1, 5.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) |
| stale-if-error | 1 s, delta-seconds | In scope, `stale-if-error-ms` | Bounds staleness after a qualifying error, independently of the background-validation window. It can appear in requests and responses. [RFC 5861 §§3–4](https://www.rfc-editor.org/rfc/rfc5861.html#section-4) |
| Request max-age, min-fresh, max-stale | 1 s, delta-seconds | In scope, `-ms` companions | A player can ask for a playlist no older than 500 ms. The companions preserve the distinction between a maximum age, a minimum remaining lifetime and an acceptable amount of staleness. Bare max-stale has no numerical limit. [RFC 9111 §5.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.1) |
| Cache-Status ttl | 1 s, signed Integer | In scope, `ttl-ms` | Diagnostic. It shows the remaining fine lifetime at each tier. Its value must be able to go negative once stale. [RFC 9211 §2.4](https://www.rfc-editor.org/rfc/rfc9211.html#section-2.4) |
| Retry-After, Prefer wait | 1 s, HTTP-date or delay-seconds for Retry-After, delta-seconds for wait | In scope, `Retry-After-Ms` and `wait-ms`, separable | Not caching, but the same whole-second limit, and finer `wait` was requested in 2019. Retry-After can be a date or a minimum delay. The companion carries a delay, and the sender keeps the whole-second value no earlier so that older clients do not retry early. Prefer wait expresses the client's waiting budget. [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3) · [RFC 7240 §4.3](https://www.rfc-editor.org/rfc/rfc7240.html#section-4.3) |
| Alt-Svc ma | 1 s, delta-seconds | Review separately | A related lifetime that consumes response age but governs an alternative service advertisement. [RFC 7838 §3.1](https://www.rfc-editor.org/rfc/rfc7838.html#section-3.1) |
| immutable | None, no argument | No change needed | Already applies for the calculated freshness lifetime. It takes no duration argument. [RFC 8246 §2](https://www.rfc-editor.org/rfc/rfc8246.html#section-2) |
| Date, Expires | 1 s, HTTP-date | Out of scope | A finer Expires would need a new date format, a finer Date to subtract from it, and clocks agreed to the millisecond. A fractional Expires sent today is invalid and is treated as already expired. A relative lifetime with a fine age gives every cache the same expiry instant without any of these, and max-age already overrides Expires. [RFC 9110 §5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) · [RFC 9111 §5.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3) |
| Last-Modified and date-based conditionals | 1 s, HTTP-date | Out of scope | Use distinct strong ETags for distinct manifest revisions within a second. [RFC 9110 §8.8](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8) |
| Strict-Transport-Security max-age, Expect-CT max-age, Set-Cookie Max-Age | 1 s, delta-seconds. Cookie Max-Age can be negative | Out of scope | Security policy and cookie retention have their own expiry rules. Zero can remove existing state. Each would need a separate compatibility analysis. [RFC 6797 §6.1.1](https://www.rfc-editor.org/rfc/rfc6797.html#section-6.1.1) · [RFC 9163 §2.1.3](https://www.rfc-editor.org/rfc/rfc9163.html#section-2.1.3) · [RFC 6265 §5.2.2](https://www.rfc-editor.org/rfc/rfc6265.html#section-5.2.2) |
| Web Push TTL | 1 s, `1*DIGIT` | Out of scope | It bounds how long a push service retains a message for an offline device. [RFC 8030 §5.2](https://www.rfc-editor.org/rfc/rfc8030.html#section-5.2) |
| Signature `created` and `expires`, Structured Fields Date | 1 s, Integer UNIX time and SF Date | Out of scope | These bound how long a signature is accepted. They do not affect cache freshness. RFC 9421 states that sub-second precision is not supported, and a Date with a fraction fails to parse. [RFC 9421 §2.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.3) · [RFC 9651 §3.3.7](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.7) |

## Appendix B. Boundary cases

These are suggested outcomes. They assume a trustworthy age estimate, and that stale-while-revalidate is the only applicable permission to serve stale. [RFC 9111 §4.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3)

| Input or event | Expected outcome |
|---|---|
| Lifetime 200 ms, window 200 ms | Fresh at 199 ms. Stale at 200 ms, when a request can trigger background validation. Still servable at 399 ms. Not servable at 400 ms. |
| Lifetime zero or window zero | A zero lifetime means immediately stale. A zero window grants no time to serve stale. Storage and reuse after successful validation remain separate decisions. |
| Lifetime 1250 ms | Fresh at 999, 1000 and 1249 ms. Stale at 1250 ms. Crossing a whole second has no special effect. |
| Negative value, fraction, or digits followed by junk | Reject the whole companion and use the valid base. If the enclosing dictionary failed to parse, apply RFC 9213 field selection. |
| Duplicate or conflicting values | For repeated base directives use RFC 9111 §4.2.1. In ordinary Cache-Control discard an ambiguous companion. Structured Fields decoding keeps the last value for a repeated key, so specify handling at the decoded layer and have senders emit each key once. [RFC 9651 §4.2.2](https://www.rfc-editor.org/rfc/rfc9651.html#section-4.2.2) |
| Very large value | The ceiling is 15 decimal digits, the Structured Fields Integer limit. Reject an unrepresentable companion and use the base. Apply RFC 9111's overflow rule to legacy delta-seconds. [RFC 9111 §1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2) |
| Lifetime 25 ms on a 100 ms clock | Round durations down and age up. Rounding this lifetime up to 100 ms could permit 75 ms of unintended reuse. If the cache cannot establish freshness, validate. RFC 9111 already takes the earlier time when a cache's clock is coarser than an Expires date. [RFC 9111 §4.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2) |
| 304 after validation | Update stored metadata and recalculate age from the validation exchange. Discard the previous fine-age sample. If the 304 replaces a policy field, use only pairs in the replacement. [RFC 9111 §4.3.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4) |
| Concurrent requests or a slow origin | Collapse validations for the same response where possible. Measure origin requests, validation latency and manifest age by tier. Once the stale window expires, an unfinished validation gives no permission to serve stale. [RFC 9111 §4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4) |

### Mistakes and unlikely inputs

Most of these would be accidents. Each has a defined outcome, and the prototype's tests cover the ones marked ✓. [Measured examples](measurements.md#test-6-mismatched-and-malformed-pairs)

| Input | Likely cause | Outcome | Why |
|---|---|---|---|
| `max-age=60, max-age-ms=200` ✓ | Companion added, base not lowered | 200 ms on a supporting path. 60 s everywhere else. | The base is the policy the sender accepts from every other cache. A cache cannot tell intent from error. |
| `max-age=1, max-age-ms=2000` ✓ | Deliberate, or a slip | 2 s on a supporting path. 1 s elsewhere. | The values are independent. Supporting caches reuse for longer, as asked. |
| `max-age=0, max-age-ms=86400000` ✓ | Deliberate: no reuse at older caches | One day on a supporting path. No fresh lifetime elsewhere. | Same reasoning. This is no different from a long `max-age` today. |
| `max-age=1, max-age-ms=1000` ✓ | Wanting exact accounting | One second, counted in milliseconds. | Legal, and useful: in nginx it halved the measured staleness. |
| `max-age-ms=300` meant as seconds | Unit slip | 300 ms where used. A thousand times the origin requests. | The name carries the unit. A cache cannot detect it. Typing `max-age=0` by mistake has the same exposure today. |
| `max-age-ms=200` with no `max-age` ✓ | Base forgotten | Companion ignored. RFC 9111 applies as if it were absent. | Never treated as zero or as a lifetime on its own, so older and newer caches agree. |
| Base in Cache-Control, companion in CDN-Cache-Control | Split across fields | Companion ignored. | A pair must be in the same field. |
| `s-maxage=1, max-age=0, max-age-ms=200` ✓ | Stale `s-maxage` left in place | Shared caches use one second. | `s-maxage` takes precedence at a shared cache, as in RFC 9111. Its own companion was not sent. |
| `max-age=0, max-age-ms=0200` ✓ | Zero padding | 200 ms. | The grammar is one to fifteen digits. |
| `+200`, `200ms`, `0.2`, `"200"`, empty, 16 digits ✓ | Typos, other formats | Companion ignored, base applies. | An invalid companion never invalidates its base. |
| `Age: 1` with `Age-Ms: 175` ✓ | Old cache rewrote Age only | No fine age. Whole-second policy applies. | The pair is inconsistent, so neither is trusted for fine accounting. |
| `Age-Ms` larger than the lifetime ✓ | Slow path | Stale on arrival. The cache validates. | Age is counted, not reset. |
| `Retry-After: 120` with `Retry-After-Ms: 5` | Unit slip | Supporting clients may retry after 5 ms. Others wait 120 s. | The server chose both values. A client can apply its own minimum delay. |
| Request `max-age=0, max-age-ms=0` at high rate | Abuse | Forces validation, as `max-age=0` does today. | No new capability. The prototype ignores request directives unless enabled. |

Deployment mistakes, [measured in test 7](measurements.md#test-7-misconfigured-paths):

| Mistake | Outcome | What limits it |
|---|---|---|
| An older cache inside a path configured as supporting | Responses up to the base lifetime older than intended. Measured: 2152 ms where 200 ms was asked, with `max-age=1`. | In our run, the time the base let the older cache hold the response. With `max-age=0` we measured no excess. Not a general limit: a faulty source can understate age by more. |
| A gateway rewrites `max-age` to 0 and leaves `max-age-ms=3600000` | Supporting caches read one hour. | Not contained by caches. The draft asks a rewriter to examine the companion too. Not measured. |
| An intermediary strips Age-Ms from `max-age=60, max-age-ms=200` | 60 s downstream. | Falling back restores the base, which is not always shorter. The sender must accept its base. |
| No cache configured as hearing the origin | No fine age anywhere. Every cache uses the base. | The prototype reads a missing age pair as zero only at the cache configured as hearing the origin. The cost is load, not age. |
| Every cache configured as hearing the origin | Upstream age ignored. Up to one lifetime per cache in the worst case; none in our run. | Each cache still counts its own request delay. |
| `max-age=0, max-age-ms=1` | Almost nothing is reused. A quarter of requests reached the origin. | The same exposure as `max-age=0` today. |
| Lifetime shorter than the round trip to the origin | Stale on arrival. Nothing reused at the far cache. | Age is counted. See [test 3](measurements.md#test-3-a-lifetime-shorter-than-the-path). |
| Wall clock stepped back at a cache | The prototype detects a step over 10 ms and fetches again. | A smaller step extends reuse by its size. Unit tested; no real clock was stepped. |

- **No consistency rule between the two values.** A rule such as "the base must not exceed the companion" would catch the first row, and would also forbid an origin that wants 5 seconds at older caches and 200 ms at newer ones. We left the values independent and put the check on the sender.
- **A repeated companion is ignored**, even when the values agree, and the base applies.

## Appendix C. Alternative encodings

We favour integer milliseconds in both policy fields for a first specification. The same bounded integer works in each. The alternatives are summarised here.

| Alternative | Example | Advantage | Why we did not choose it |
|---|---|---|---|
| Explicit unit | `max-age-fine="1250ms"` | Can express `"500us"` | Needs a unit grammar, conversion and a range for each unit. No use case below 1 ms has been identified. |
| Decimal seconds | `max-age=0.2` | No new names | No safe fallback at older caches |
| Inline Age fraction | `Age: 1; ms=175` | An older cache replaces both readings together | Invalid today, so a recipient may ignore the whole field |
| Targeted-field parameter | `max-age=0;ms=200` | No orphan companions | Cache-Control has no parameter syntax |

### Explicit duration unit

The companions would be `max-age-fine`, `s-maxage-fine`, `stale-while-revalidate-fine` and `Age-Fine: "1075ms"`.

- **Syntax.** A quoted string of unsigned decimal digits followed immediately by lowercase `ms`, `us` or `ns`. The quotes work in both Cache-Control and a targeted dictionary. Bare `200ms` would cause a dictionary parse error and could discard the entire targeted policy. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9651 §3.3.3](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.3)
- **Cost.** A recipient must reject a missing or unknown unit, bound the digits and check the multiplication before converting units. The Age consistency check uses the declared unit.
- **Prior art.** gRPC's `grpc-timeout` header carries at most eight digits followed by a unit letter, from hours down to nanoseconds. It shows that sub-second durations are already sent in HTTP header fields, and what a unit grammar involves. [gRPC over HTTP/2](https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md)
- **A finer unit later.** A further companion such as `max-age-us` could follow the same pattern, with the base and the millisecond companion as its fallbacks. Its range would be shorter than its base's.

### Decimal seconds

Writing `max-age=0.2` has no safe fallback. [RFC 9111 §4.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1) · [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1)

| Recipient | Outcome |
|---|---|
| Cache-Control parser | The value fails the delta-seconds grammar. RFC 9111 encourages treating a response with a non-integer max-age as stale. |
| Targeted-field parser | The value parses as a Decimal. RFC 9213 says implementations should not consume a max-age with a decimal value. |
| A recipient that truncates | Sees zero |

Deployed implementations do all of these and more. Of the eleven we read, WebKit uses the fraction, five truncate to zero, four ignore the directive and nginx declines to cache the response. [Survey](#what-implementations-do-today)

None of these lets the origin choose a one-second fallback. A separate companion leaves the base valid for every recipient.

### Encoding Age

When an older cache serves a stored response without validation, it replaces the entire Age field. An inline fraction would be removed with it. A separate companion can survive that replacement and become outdated. [RFC 9111 §4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4)

The constraint is the grammar. Age accepts one non-negative integer in seconds. For an estimated age of 1.175 seconds, consider these encodings. [RFC 9111 §§5.1–5.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1)

| Encoding | Effect during rollout |
|---|---|
| Separate fields, `Age: 1` and `Age-Ms: 1175` | Every older recipient keeps a valid reading. An upgraded recipient needs confidence that the fine reading was updated along the path. |
| Inline parameter, `Age: 1; ms=175`, or decimal, `Age: 1.175` | Keeps the readings together, but both spellings are invalid today. A cache following the recommended error handling ignores the entire field and loses the one-second reading. |
| Extra list member, `Age: 1, 1175` | A recipient following the list-recovery rule uses the first member. That rule handles malformed input. Generating a list would require changing the singleton grammar and relying on recovery across deployed caches. |

We favour the separate field for rollout. Evidence about how existing caches parse and regenerate Age would help the WG assess whether an inline encoding merits further work.

### Parameter in a targeted field

A narrower alternative for managed CDNs attaches an integer parameter to the base, e.g. `CDN-Cache-Control: max-age=0;ms=200`. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9111 §5.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2)

- **For.** An RFC 9213 recipient ignores an unfamiliar parameter and sees zero. The attachment eliminates orphan companions in that dictionary.
- **Against.** Ordinary Cache-Control has no parameter syntax, and the alternative still needs reliable age across tiers.

We would keep one spelling across both policy fields unless implementers see a deployment advantage in the narrower scope.

## Appendix D. Streaming and historical context

- **Observed staleness.** We have seen live playlists reach players four or five seconds old.
- **How to measure.** Trace one revision from publication through the shield and edge to the first player reload that discovers it. Record origin requests alongside discovery lag. HLS clients have their own playlist reload schedule. [RFC 8216 §6.3.4](https://www.rfc-editor.org/rfc/rfc8216.html#section-6.3.4)
- **HLS already has fine time.** Playlists express fractional segment durations and can timestamp the first sample to milliseconds. [RFC 8216 §§4.3.2.1](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.2.1) and [4.3.2.6](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.2.6)
- **HTTP does not.** Date and Last-Modified carry whole seconds, though an origin can use a sub-second modification time to generate an opaque ETag. A fine cache directive would let the origin set a lifetime such as 1.25 seconds independently of the media timeline. [RFC 9110 §§5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) and [8.8.3.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3.1)

### History of whole-second resolution

The whole-second unit entered HTTP caching in 1997 and has been carried forward unchanged through every revision. The tables list each specification that defines or reuses it, then the requests for finer resolution that we could find.

#### In the HTTP specifications

| Date | Document | What it says about time |
|---|---|---|
| May 1996 | RFC 1945, HTTP/1.0 | Freshness is an absolute Expires date. There is no Age field, no max-age and no delta-seconds rule. Retry-After, in an appendix of extra features, takes a date or "an integer number of seconds". [§10.7](https://www.rfc-editor.org/rfc/rfc1945.html#section-10.7) · [Appendix D.2.8](https://www.rfc-editor.org/rfc/rfc1945.html#appendix-D.2.8) |
| January 1997 | RFC 2068, HTTP/1.1 | Introduces `delta-seconds = 1*DIGIT`, the Age field and max-age. Age is "non-negative decimal integers, representing time in seconds". The 2^31 overflow value and the advice to use at least 31 bits appear here, under Age. [§3.3.2](https://www.rfc-editor.org/rfc/rfc2068.html#section-3.3.2) · [§13.2.3](https://www.rfc-editor.org/rfc/rfc2068.html#section-13.2.3) · [§14.6](https://www.rfc-editor.org/rfc/rfc2068.html#section-14.6) · [§14.9](https://www.rfc-editor.org/rfc/rfc2068.html#section-14.9) |
| February 1997 | RFC 2109, cookies | The first reuse outside caching. `Max-Age=delta-seconds`. [§4.2.2](https://www.rfc-editor.org/rfc/rfc2109.html#section-4.2.2) |
| March 1997 | WG list, Roy Fielding | Restores text omitted from RFC 2068 that defines response max-age as an age "(in seconds)". [Message](https://lists.w3.org/Archives/Public/ietf-http-wg/1997JanMar/0651.html) |
| June 1999 | RFC 2616, HTTP/1.1 | Keeps the rule and the Age text. Adds `s-maxage`, also in delta-seconds. [§3.3.2](https://www.rfc-editor.org/rfc/rfc2616.html#section-3.3.2) · [§14.6](https://www.rfc-editor.org/rfc/rfc2616.html#section-14.6) · [§14.9.3](https://www.rfc-editor.org/rfc/rfc2616.html#section-14.9.3) |
| January 2002 | RFC 3229, delta encoding | The `retain` cache directive takes an optional delta-seconds value. [§10.8.1](https://www.rfc-editor.org/rfc/rfc3229.html#section-10.8.1) |
| May 2010 | RFC 5861 | stale-while-revalidate and stale-if-error import delta-seconds from RFC 2616. [§3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) · [§4](https://www.rfc-editor.org/rfc/rfc5861.html#section-4) |
| 2011–2012 | RFC 6265, RFC 6797 | Cookie Max-Age and Strict-Transport-Security max-age use the same unit. [RFC 6265 §5.2.2](https://www.rfc-editor.org/rfc/rfc6265.html#section-5.2.2) · [RFC 6797 §6.1.1](https://www.rfc-editor.org/rfc/rfc6797.html#section-6.1.1) |
| June 2014 | RFC 7234, HTTP/1.1 caching | Moves delta-seconds into the caching document. The overflow rule now applies to every delta-seconds value. Retry-After gets its own `delay-seconds` rule in RFC 7231. Prefer `wait` adopts delta-seconds the same month. [RFC 7234 §1.2.1](https://www.rfc-editor.org/rfc/rfc7234.html#section-1.2.1) · [RFC 7231 §7.1.3](https://www.rfc-editor.org/rfc/rfc7231.html#section-7.1.3) · [RFC 7240 §4.3](https://www.rfc-editor.org/rfc/rfc7240.html#section-4.3) |
| April 2016 | RFC 7838, Alt-Svc | The `ma` parameter is delta-seconds. [§3.1](https://www.rfc-editor.org/rfc/rfc7838.html#section-3.1) |
| June 2022 | RFC 9111, HTTP caching | The current definition, unchanged in substance from 1997. [§1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2) · [§5.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1) |
| June 2022 | RFC 9211, RFC 9213 | Cache-Status `ttl` is an integer number of seconds. Targeted fields say implementations should not consume a max-age with a decimal value. [RFC 9211 §2.4](https://www.rfc-editor.org/rfc/rfc9211.html#section-2.4) · [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) |
| September 2024 | RFC 9651, Structured Fields | The Date type is an integer number of seconds. [§3.3.7](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.7) |

#### Requests for finer resolution

| Date | Where | What was asked and what happened |
|---|---|---|
| June 2011 | HTTP WG list | Poul-Henning Kamp, the author of Varnish, wrote that "some high volume sites cache content for only a couple of seconds" and that one-second granularity is "a serious limitation on caching policy". He proposed `delta-seconds = 1*DIGIT [ '.' *DIGIT]`. Mark Nottingham replied that such lifetimes had been useful in controlled deployments, that nothing prevented a Cache-Control extension with higher precision, and that Date has one-second resolution. The grammar was left as it was. [Proposal](https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0474.html) · [Reply](https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html) |
| July 2012 | nginx mailing list | A user asked for `proxy_cache_valid 200 301 302 500ms`. The reply was that it could not be done, and that millisecond granularity would limit the maximum time to about 24.8 days. That is the 31-bit limit discussed under "Delta milliseconds" above. [Question](https://mailman.nginx.org/pipermail/nginx/2012-July/034628.html) · [Reply](https://mailman.nginx.org/pipermail/nginx/2012-July/034651.html) |
| February 2017 | Unpublished draft by the author | Proposed a centisecond suffix for cache directives, alongside stale-while-revalidate for Expires, for live streaming manifests. It was an initial draft for discussion with potential co-authors and was not published. |
| March 2018 | nginx ticket 1505 | "Milliseconds and dynamic time support for *_cache_valid". `proxy_cache_valid 200 200ms` is rejected as an invalid time value. The ticket remains open. [Ticket](https://trac.nginx.org/nginx/ticket/1505) |
| May 2019 | HTTP WG issue | A request to allow fractional values for Prefer `wait`, because "sub-second values seems necessary for this header to be practically useful". It was closed as out of scope for the documents then in progress. [http-core issue 227](https://github.com/httpwg/http-core/issues/227) |
| February 2020 | Varnish | The parser for max-age and Age began to accept and ignore a decimal point. The source comment reads "to be future compatible with fractional seconds". [Commit](https://github.com/varnishcache/varnish-cache/commit/aaaf7b383339b18f368935ff3fd38a6575c15666) · [Source](https://github.com/varnishcache/varnish-cache/blob/master/bin/varnishd/cache/cache_rfc2616.c) |
| August 2025 | HLS second edition draft | Recommends that successful responses to non-blocking playlist requests be cached for half the Target Duration. Target Duration is a whole number of seconds, so a one-second target calls for a 500 ms lifetime. [draft-pantos-hls-rfc8216bis, Appendix B.1](https://datatracker.ietf.org/doc/draft-pantos-hls-rfc8216bis/) |
| November 2026 | Media over QUIC Transport | Defines `MAX_CACHE_DURATION` for relay caches in integer milliseconds. [draft-ietf-moq-transport-23 §10.3](https://datatracker.ietf.org/doc/draft-ietf-moq-transport/) |

- **Search coverage.** We searched the Squid, Apache Traffic Server, HAProxy and Envoy issue trackers and the HTTP WG repositories for terms such as "sub-second" and "milliseconds" with "max-age", and found no similar requests. We did not search mailing lists or the Squid Bugzilla, so earlier discussions may exist. Pointers are welcome.
- **Who asked.** Each request came from someone operating or building a reverse proxy cache.
- **Where each stopped.** The wire format has no place for a fraction, and decimals are unsafe to send to deployed caches.

### Hardware then and now

| Storage example | Read | Write | What the figures measure |
|---|---:|---:|---|
| Seagate Cheetah 4LP, 1997 spinning disk | 10.69 ms | 11.69 ms | Estimated time to reach data on the platter. The manual gives typical average seek plus controller overhead of 7.7 ms for reads and 8.7 ms for writes. Average rotational delay adds 2.99 ms to either. [Seagate product manual, §§4.1–4.2, note 6](https://www.seagate.com/support/disc/manuals/scsi/29120b.pdf) |
| Micron 7450 PRO, data-centre NVMe SSD | 80 µs | 15 µs | Median latency for random 4 KB operations with one request outstanding. [Micron product brief, E1.S specifications and latency footnote](https://www.micron.com/content/dam/micron/global/public/products/product-flyer/7450-nvme-ssd-product-brief.pdf) |

- Cloudflare lists the 7450 PRO in its Gen 12 edge servers alongside a 96-core processor, DDR5-4800 memory and two 25 GbE ports. [Cloudflare’s Gen 12 server specifications](https://blog.cloudflare.com/gen-12-servers/)
- The drive figures illustrate the change in local I/O timescales. A cache hit can also come from RAM, and a revalidation can incur an upstream round trip.
- Today an origin can choose immediate staleness or a full second, even when its caches can serve many requests in between. [RFC 9111 §4.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2)

### Sending a live playlist

| Link | Rate | Source |
|---|---:|---|
| Fast Ethernet, 1995 | 100 Mb/s | [IEEE 802.3u-1995](https://standards.ieee.org/ieee/802.3u/1079/) |
| PPP over SONET, 1994 | 155.52 Mb/s | [RFC 1619](https://www.rfc-editor.org/rfc/rfc1619.html) |
| One port of a Cloudflare Gen 13 server, which has two | 100 Gb/s | [Cloudflare Gen 13](https://blog.cloudflare.com/gen13-config/) |

| Published live media playlist | Body size | At 100 Mb/s | At 100 Gb/s |
|---|---:|---:|---:|
| [RFC 8216 §8.2](https://www.rfc-editor.org/rfc/rfc8216.html#section-8.2), three segment URLs | 257 B | 20.6 µs | 20.6 ns |
| [Apple’s low-latency HLS example](https://developer.apple.com/documentation/http-live-streaming/enabling-low-latency-http-live-streaming-hls), including partial segments and rendition reports | 2,466 B | 197 µs | 197 ns |

- **Method.** We counted the uncompressed playlist text with LF line endings, including the final LF, and removed document indentation. For one idle link, serialisation time is `8 × body bytes / link rate in bits per second`.
- **Caveats.** These are example sizes. Window length, URI length and the number of parts affect production playlists. A cache refresh also pays for framing, transport, queueing, propagation and upstream processing.
- **Reading.** Even on the slower link the larger body takes under 0.2 ms to serialise, so a 1,000-fold increase in bandwidth saves about 0.197 ms. A conditional request answered with 304 transfers no playlist body at all. [RFC 9110 §15.4.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4.5)

## Appendix E. Notes for implementers

A prototype for nginx implements the companions for ordinary Cache-Control. It is the `http-cache-millisecond-freshness` branch of a fork. [Branch](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness) · [Build and demo](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness/contrib/subsecond-cache) · [Integration tests, on a matching branch of an nginx-tests fork](https://github.com/randomizedcoder/nginx-tests/tree/http-cache-millisecond-freshness)

### What nginx needed

The change is about 730 added lines of C in six files. The tests are three new files in the nginx test suite, and are skipped on a binary without the change. Most of it is one new file. Everything is off unless configured.

| Area | Change | Lines added |
|---|---|---|
| [`ngx_http_cache_fine.c`](https://github.com/randomizedcoder/nginx/blob/http-cache-millisecond-freshness/src/http/ngx_http_cache_fine.c) (new) | Parse paired directives, establish fine age, emit `Age` and `Age-Ms`, merge a 304, evaluate request directives | 481 |
| [`ngx_http_file_cache.c`](https://github.com/randomizedcoder/nginx/blob/http-cache-millisecond-freshness/src/http/ngx_http_file_cache.c) | Millisecond expiry on read. Cache file version 6 keeps birth, deadline and both stale windows in milliseconds | 69 |
| [`ngx_http_upstream.c`](https://github.com/randomizedcoder/nginx/blob/http-cache-millisecond-freshness/src/http/ngx_http_upstream.c) | Call the new handler, keep the 304 headers, two ttl variables | 70 |
| [`ngx_http_cache.h`](https://github.com/randomizedcoder/nginx/blob/http-cache-millisecond-freshness/src/http/ngx_http_cache.h) | Four `int64_t` fields and two inline comparisons | 38 |
| [`ngx_http_proxy_module.c`](https://github.com/randomizedcoder/nginx/blob/http-cache-millisecond-freshness/src/http/modules/ngx_http_proxy_module.c) | Two directives | 30 |
| `ngx_http_upstream.h`, `auto/sources` | Four fields, one build line | 5 |

Operators see two directives and two variables, `$upstream_cache_ttl` and `$upstream_cache_ttl_ms`:

```nginx
proxy_cache_fine_time    origin;   # off | origin | trusted
proxy_cache_fine_request on;       # honour request max-age-ms and min-fresh-ms
```

The freshness decision is the existing one with a millisecond clock:

```c
if (now < deadline) {
    return NGX_HTTP_CACHE_HIT;
}

if (now - deadline < window) {
    return NGX_HTTP_CACHE_UPDATING;
}

return NGX_HTTP_CACHE_EXPIRED;
```

Choosing between a companion and its base is one expression. The request directives reduce to two comparisons:

```c
lifetime = v[base + 1] >= 0 ? v[base + 1] : v[base] * 1000;

return (max_age < 0 || age <= max_age)
       && (min_fresh < 0 || remaining >= min_fresh);
```

| Companion | In the prototype |
|---|---|
| `max-age-ms`, `s-maxage-ms`, `stale-while-revalidate-ms`, `stale-if-error-ms` (response) | Yes |
| `Age-Ms` | Yes, generated and consumed |
| `max-age-ms`, `min-fresh-ms` (request) | Yes, opt-in |
| Cache-Status `ttl-ms` | Variables for the operator to compose |
| `max-stale-ms`, `stale-if-error-ms` (request) | No |
| Targeted fields such as CDN-Cache-Control | No |
| `Retry-After-Ms`, Prefer `wait-ms` | Forwarded. nginx does not generate or act on either |

### Measured through five caches

A simulation runs the prototype as five caches between an origin and a client, and measures how old each response is when it leaves the last cache. [Practical tests: setup, four tests and their limits](measurements.md)

| Path delay | Cache-Control | Mean staleness, ms | Max, ms | Origin requests per second |
|---|---|---:|---:|---:|
| None | `max-age=1` | 999 | 1999 | 2 |
| None | `max-age=0, max-age-ms=100` | 48 | 111 | 36 |
| 234 ms round trip | `max-age=1` | 1011 | 1881 | 2 |
| 234 ms round trip | `max-age=0, max-age-ms=500` | 208 | 470 | 6 |

- **Updates arrive five to twenty times sooner.** Each cache deducts the age it received, so five caches did not multiply the lifetime. This is not a strict bound on delivery age.
- **The cost is origin requests.**
- **A lifetime shorter than the round trip to the origin leaves the last cache nothing to reuse.**
- These runs measure caches on one host, not players.

### What took the effort

Integer parsing and the expiry comparisons were straightforward. Most of the work concerned when a response may be reused, which age belongs to the stored representation, and how both survive validation or a restart. These cases exercise those decisions.

**Headers arrive in a different order.** [nginx cache-control tests](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_control.t)

- Collect all lines of the selected policy before deciding reuse.
- Match complete directive names and respect quoted commas.
- Test a pair split over two lines, then add unqualified `no-cache` on a third. The pair refines a lifetime, but reuse still requires validation.
- The existing nginx tests also reverse Cache-Control and Expires and exercise an overflowing max-age.

**Only the stale window needs finer resolution.** [RFC 5861 §§3–4](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) · [nginx concurrent and error cases](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_use_stale.t)

- Calculate freshness by the usual rules, including Expires. Then apply a paired stale window at that expiry, subject to the usual restrictions.
- A response can have a 200 ms stale window even if it has no max-age directive.
- A slow or failed background request does not restart the window.
- Check any stale-if-error permission independently.

**A 304 changes cache policy.** [RFC 9111 §4.3.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4) · [nginx revalidation tests](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_revalidate.t) · [nginx variant tests](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_vary.t)

- Identify the stored responses covered by the validator, merge the 304 fields, then recalculate policy and age.
- An omitted Cache-Control preserves the stored policy. A replacement containing only `max-age=0` removes the old fine lifetime.
- Use timing from the validation exchange even when the body stays on disk.
- Test two Vary variants with distinct strong ETags, so that a validation for one cannot freshen the other.

**A cache reloads a stored response.**

- Measure residence with a monotonic clock where available. Age includes downtime.
- If a restart, clock step or change of cache format makes elapsed time uncertain, validate before relying on fine freshness again. A restart at age 190 ms cannot grant a new 200 ms lifetime.
- Implementations can choose how to record this information.
