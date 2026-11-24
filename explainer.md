# Finer resolution for HTTP cache durations

Dave Seddon · Discussion proposal for the HTTP Working Group

## Abstract

An origin should be able to express a freshness lifetime in milliseconds and have each cache count the time already spent upstream. We propose millisecond companions for three cache directives and the Age response field. The origin chooses the durations and sends a whole-second fallback for older caches.

## Sharing a freshness lifetime

Our live HLS playlists change every second or two. For example, suppose the origin chooses a 200 ms freshness lifetime. A shield serving the playlist at age 175 ms can report only `Age: 0` in whole seconds. We propose that it send the following fields together.

```http
Cache-Control: max-age=0, max-age-ms=200
Age: 0
Age-Ms: 175
```

- **Known supporting path.** The edge counts 175 ms upstream, 15 ms for its request and 10 ms in its own cache. At exactly 200 ms the playlist is stale. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)
- **Older cache.** It ignores the companions and applies `max-age=0`. The origin can choose `max-age=1` if a full second is acceptable at older caches.
- **Unknown path.** With that one-second fallback, an older intermediary could hold the response for another 300 ms and still forward `Age: 0` and the original `Age-Ms: 175`. An upgraded edge uses the whole-second policy and drops the unreliable fine age. [RFC 9110 §5.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.1)

### Deployment example — streaming the U.S. Super Bowl

- **Scale.** Consider an event serving 30–40 million viewers across a wide range of connections, with hundreds of millions of HTTP requests per second across all object types. These are workload estimates. For a published comparison, Tubi reported 15.5 million concurrent streaming viewers at its peak during Super Bowl LIX. [Tubi’s event report](https://corporate.tubitv.com/press/4545/)
- **Why the manifest matters.** Caches can serve many players from one playlist refresh. If a player reloads just before the cache refreshes, it can receive a playlist that omits an already available segment. The player may then wait another reload interval to discover it. [RFC 8216 §6.3.4](https://www.rfc-editor.org/rfc/rfc8216.html#section-6.3.4)
- **What to test.** If a fresher playlist lets a player start the segment request 500 ms earlier, it has an extra 500 ms before the same playback deadline. On a slow or variable connection, that margin could let the download finish before the buffer runs dry. We have yet to measure how often players gain at least 500 ms or how often that prevents a stall. Compare segment request and completion times, rebuffer events and origin playlist requests under both cache policies.

### Relationship to Media over QUIC

Media over QUIC is attracting much of the current interest in low-latency live delivery. Its transport draft treats relays as caches and gives their timing in integer milliseconds. `MAX_CACHE_DURATION` is the number of milliseconds an object can be served from a cache, and the delivery timeouts use the same unit. QUIC itself expresses its idle timeout and maximum acknowledgement delay in milliseconds. [draft-ietf-moq-transport-23 §§5.2, 10.3](https://datatracker.ietf.org/doc/draft-ietf-moq-transport/) · [RFC 9000 §18.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-18.2)

HTTP caches can express nothing between zero and one second. That limit comes from the delta-seconds grammar. The caches themselves can already serve many requests within a second. HLS and DASH over HTTP caches remain the deployed base for large live events, and those services will run alongside MoQ for years. Millisecond freshness would let them use their existing caches closer to the timescales MoQ is designed for. We think this would keep HTTP a practical choice for latency-sensitive delivery where a deployment already depends on it. We have yet to measure how far it narrows the gap. The two also meet in deployment, since MoQ can run over WebTransport on HTTP/3.

## Proposed wire format

The first three rows are response directives in Cache-Control or a selected targeted field such as CDN-Cache-Control. The last row shows two response fields. Each companion carries the complete value. The names are provisional.

### A. Integer milliseconds

| Existing | Proposed companion | What it controls |
|---|---|---|
| `max-age=1` | `max-age-ms=1250` | 1.25 s of freshness since generation or validation |
| `s-maxage=0` | `s-maxage-ms=200` | 200 ms for a shared cache, with the usual shared-cache revalidation requirement |
| `stale-while-revalidate=0` | `stale-while-revalidate-ms=200` | An additional 200 ms from expiry when serving stale is permitted |
| `Age: 1` | `Age-Ms: 1075` | Total estimated age of 1.075 s at this hop |

Use unsigned decimal digits. The same spelling works as an Integer in a targeted dictionary. A needs one conversion factor and has a smallest positive value of 1 ms. Appendix C considers an explicit unit for deployments that need finer resolution. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9651 §3.3.1](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.1)

### Delta milliseconds

Every whole-second duration in HTTP caching comes from one grammar rule, `delta-seconds = 1*DIGIT`. Age and the max-age, s-maxage, max-stale and min-fresh directives all use it, and later extensions such as stale-while-revalidate import it. We propose a sibling rule for A to sit beside it. [RFC 9111 §1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3)

```abnf
delta-milliseconds = 1*15DIGIT
```

- **Meaning.** A non-negative integer representing time in milliseconds. It gives the complete duration and is never added to a delta-seconds value.
- **Range.** Fifteen digits is the Structured Fields Integer limit, about 31,700 years in milliseconds. The same value therefore parses in Cache-Control and in a targeted dictionary. [RFC 9651 §3.3.1](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.1)
- **Arithmetic.** RFC 9111 suggests at least 31 bits for delta-seconds. In milliseconds 31 bits last under 25 days. A recipient needs 41 bits to hold the 2^31-second ceiling in milliseconds and 50 bits for the whole 15-digit range. A 64-bit integer covers both.
- **Overflow.** A delta-seconds value that is too large is treated as 2^31 seconds. A companion always arrives with a whole-second base, so we propose that a recipient rejects an unrepresentable delta-milliseconds value and uses the base. The WG may prefer the saturating rule for consistency.

RFC 9111 defines the age calculation in terms of clock differences. Only the Age field value and the freshness lifetime are tied to seconds, so the calculation works at millisecond resolution without changing its steps. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)

## Cache behaviour

1. **Select the policy.** An RFC 9213 cache uses the first valid, non-empty field in its ordered target list. That selection displaces Cache-Control and Expires for that response. Put the fallback, companion and any restrictions together in each policy that needs them. An unrecognised member of a valid dictionary is ignored. A dictionary parse failure discards that field and selection continues. [RFC 9213 §§2.1–2.3](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1)
2. **Select the applicable directive.** In a shared cache, applicable s-maxage takes precedence even over a fine max-age. Otherwise use max-age, then the ordinary Expires and heuristic rules where applicable. An applicable no-store, private, no-cache or revalidation requirement retains its usual effect. In particular, an applicable s-maxage prohibits stale reuse by a shared cache, so use max-age in a CDN-targeted policy when a stale-while-revalidate window is wanted. [RFC 9111 §§4.2.1, 4.2.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1)
3. **Refine only the selected quantity.** When the age estimate supports fine timing (see below), an implementing cache substitutes a valid companion for its valid base in the same policy. The companion gives the complete duration. Thus 1 second paired with 1250 ms means 1.25 seconds. With just the base, both caches use seconds. With just the companion, our proposed rule ignores it and resumes ordinary policy selection within the selected field. A legacy cache ignores unknown directives. This is the pattern RFC 9111 describes for behavioural extensions, where the new directive modifies an old one sent alongside it. Support can be partial, so include a suitable fallback for each quantity. [RFC 9111 §5.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.3)

For example, the following permits a CDN implementing A to use 200 ms of freshness and a further 200 ms of stale-while-revalidate. A CDN implementing only the existing directives gets zero freshness and zero additional window. Other caches see the ordinary policy. A sender choosing a one-second fallback instead accepts the longer interval at legacy caches.

```http
Cache-Control: max-age=0
CDN-Cache-Control: max-age=0, max-age-ms=200, stale-while-revalidate=0, stale-while-revalidate-ms=200
```

## Reporting age

Use the RFC 9111 age calculation at the chosen resolution. A cache that takes the greater of corrected age and Date-based apparent age may reach expiry earlier in the example above. Date retains whole-second precision. [RFC 9111 §4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3)

### Recommended rollout

Send a whole-second fallback with every fine policy. For a strict sub-second freshness budget, choose `max-age=0`. If a full second is acceptable at older caches, choose `max-age=1`. Make the same decision independently for the permitted stale window. Either wire format can use this rule without a capability handshake.

| Response path | What the receiving cache does |
|---|---|
| Any sender → older cache | Uses the existing directives and ordinary Age processing. Fine directives confer no extra permission at this cache. |
| Origin → upgraded cache directly | On a known origin response, calculates age from the generation or validation exchange and its own elapsed time. It can apply valid paired fine directives from the first cache onwards. |
| Upgraded shield → upgraded edge on a known supporting path | Uses the shield's valid fine age as the upstream age input, accounts for request delay and local residence, and regenerates both Age fields on reuse. |
| Older or unknown caching hop → upgraded cache | Uses ordinary Age processing and the whole-second policy. On forwarding or reuse, drops any unreliable fine-age field. It resumes reporting fine age once it can establish age again, for example by validating directly with the origin. |

An operator can establish a supporting path by configuration in a managed CDN. Knowing only that the immediate peer is upgraded gives no assurance about caches earlier on the path. A fine-age field by itself, or an absent Age field, cannot establish the path. [RFC 9111 §5.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1)

For A we propose deriving both fields from one sample, with `Age = floor(Age-Ms / 1000)` when both values are representable. On a configured supporting path, require one valid value of each field and check that relation. If either value is missing, repeated, inconsistent or out of range, discard the fine sample and apply ordinary Age and policy processing. The same check for B uses the declared unit. A direct origin exchange can establish a new estimate. An older cache can replay a pair that passes the arithmetic check.

## Notes for implementers

A local nginx prototype implements A for ordinary Cache-Control. Integer parsing and the two expiry comparisons were straightforward. Most of the work concerned when a response may be reused, which age belongs to the stored representation, and how both survive validation or a restart. The following cases exercise those decisions.

| Case | Implementation guidance |
|---|---|
| Headers arrive in a different order | Collect all lines of the selected policy before deciding reuse. Match complete directive names and respect quoted commas. Try a pair split over two lines, then add unqualified `no-cache` on a third. The pair refines a lifetime but reuse still requires validation. Existing nginx tests also reverse Cache-Control and Expires and exercise overflowing max-age. [nginx cache-control tests](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_control.t) |
| Only the stale window needs finer resolution | Calculate freshness by the usual rules, including Expires when applicable. Then apply a paired stale window at that expiry, subject to the usual restrictions. A response can have a 200 ms stale window even if it has no max-age directive. A slow or failed background request does not restart the window. Check any stale-if-error permission independently. [RFC 5861 §§3–4](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) · [nginx concurrent and error cases](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_use_stale.t) |
| A 304 changes cache policy | Identify the stored responses covered by the validator, merge the 304 fields, then recalculate policy and age. An omitted Cache-Control preserves the stored policy. A replacement containing only `max-age=0` removes the old fine lifetime. Use timing from the validation exchange even when the body stays on disk. Test two Vary variants with distinct strong ETags so a validation for one cannot freshen the other. [RFC 9111 §4.3.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4) · [nginx revalidation tests](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_revalidate.t) · [nginx variant tests](https://github.com/nginx/nginx-tests/blob/master/proxy_cache_vary.t) |
| A cache reloads a stored response | Measure residence with a monotonic clock where available. Age includes downtime. If a restart, clock step or change of cache format makes elapsed time uncertain, validate before relying on fine freshness again. A restart at age 190 ms cannot grant a new 200 ms lifetime. Implementations can choose how to record this information. |

## Operational and security considerations

Short lifetimes can increase origin load. A stale-while-revalidate window helps when a request arrives during the window and validation completes in time. It cannot guarantee an uninterrupted stream. Fine age and per-tier diagnostics may also reveal cache activity at higher resolution. Operators can limit their exposure across trust boundaries. [RFC 5861 §5](https://www.rfc-editor.org/rfc/rfc5861.html#section-5) · [RFC 9211 §6](https://www.rfc-editor.org/rfc/rfc9211.html#section-6)

## Questions for the working group

- Where do you need to communicate a fractional-second lifetime between independently implemented caches? What resolution does the application need?
- How do you establish that every cache on a path updates age? Would the whole-second fallback work where you cannot establish that?

Per-tier age, validation outcomes and playlist discovery times would help quantify the effect on players.

If there is interest, an individual Internet-Draft can specify the grammar, ranges, duplicate handling and registration of the selected names. [RFC 9111 §5.2.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.4) · [IANA HTTP field registry](https://www.iana.org/assignments/http-fields/)

## Acknowledgements

The author used Claude and OpenAI Codex to research RFC references, draft and edit the text, and explore how the proposed extensions would behave in mixed cache deployments.

## Appendix A. Other time-related fields

We searched the current HTTP RFCs for whole-second durations and timestamps. The table marks each as in scope for this proposal, a candidate for later work, or out of scope. The same units could serve the candidates. Each needs a decision about who measures the interval, when it starts, and what rounding does to its guarantee. The [IANA cache directive registry](https://www.iana.org/assignments/http-cache-directives/) identifies the current cache directives.

Seven specifications use the delta-seconds grammar. RFC 9111 defines it, and RFC 5861, RFC 7240, RFC 6797, RFC 7838 and RFC 9163 import it. RFC 6265 uses the name for a value that can be negative. Retry-After, Web Push TTL and Cache-Status ttl define whole seconds with their own rules. HTTP/2 and HTTP/3 define no cache durations of their own. [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html) · [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)

| Current field or directive | Proposed treatment and reason |
|---|---|
| Age, response max-age, s-maxage, stale-while-revalidate | In scope. These determine how a freshness lifetime is shared between caches. [RFC 9111 §§5.1, 5.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) |
| stale-if-error | Candidate for either suffix. Bound staleness after a qualifying error, independently of the background-validation window. It can appear in requests and responses. [RFC 5861 §§3–4](https://www.rfc-editor.org/rfc/rfc5861.html#section-4) |
| Request max-age, min-fresh, max-stale | Candidates for either suffix. Preserve the distinction between a maximum age, a minimum remaining lifetime and an acceptable amount of staleness. Bare max-stale has no numerical limit. [RFC 9111 §5.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.1) |
| Cache-Status ttl | Optional diagnostic companion. Its value must be able to go negative once stale. [RFC 9211 §2.4](https://www.rfc-editor.org/rfc/rfc9211.html#section-2.4) |
| Date, Expires | Absolute timestamps require a clock and a timestamp encoding. For finer freshness use a relative lifetime. [RFC 9110 §5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) · [RFC 9111 §5.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3) |
| Last-Modified and date-based conditionals | Use distinct strong ETags for distinct manifest revisions within a second. [RFC 9110 §8.8](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8) |
| immutable | Already applies for the calculated freshness lifetime. It takes no duration argument. [RFC 8246 §2](https://www.rfc-editor.org/rfc/rfc8246.html#section-2) |
| Retry-After, Prefer wait | Possible later uses. Retry-After can be a date or a minimum delay. Rounding a minimum delay down can cause an early retry. Prefer wait expresses the client's waiting budget. [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3) · [RFC 7240 §4.3](https://www.rfc-editor.org/rfc/rfc7240.html#section-4.3) |
| Alt-Svc ma | A related lifetime that consumes response age but governs an alternative service advertisement. Review separately. [RFC 7838 §3.1](https://www.rfc-editor.org/rfc/rfc7838.html#section-3.1) |
| Strict-Transport-Security max-age, Expect-CT max-age, Set-Cookie Max-Age | Out of scope. Security policy and cookie retention have their own expiry rules. Zero can remove existing state. Each would need a separate compatibility analysis. [RFC 6797 §6.1.1](https://www.rfc-editor.org/rfc/rfc6797.html#section-6.1.1) · [RFC 9163 §2.1.3](https://www.rfc-editor.org/rfc/rfc9163.html#section-2.1.3) · [RFC 6265 §5.2.2](https://www.rfc-editor.org/rfc/rfc6265.html#section-5.2.2) |
| Web Push TTL | Out of scope. It bounds how long a push service retains a message for an offline device. [RFC 8030 §5.2](https://www.rfc-editor.org/rfc/rfc8030.html#section-5.2) |
| Signature `created` and `expires`, Structured Fields Date | Out of scope. These are absolute timestamps in integer seconds, and a Date with a fraction fails to parse. A relative lifetime avoids the need for a finer timestamp type. [RFC 9421 §2.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.3) · [RFC 9651 §3.3.7](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.7) |

## Appendix B. Boundary cases

These are suggested outcomes for the extensions. They assume a trustworthy age estimate. The stale-window example assumes stale-while-revalidate is the only applicable permission to serve stale. [RFC 9111 §4.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3)

| Input or event | Expected outcome |
|---|---|
| Lifetime 200 ms, window 200 ms | At age 199 ms the response is fresh. At 200 ms it is stale and a request can trigger background validation. At 399 ms that permission still applies. Use 400 ms as the exclusive end of the proposed window. |
| Lifetime zero or window zero | Zero lifetime means immediately stale. A zero window grants no time to serve stale. Storage and reuse after successful validation remain separate decisions. |
| Lifetime 1250 ms | Fresh at 999, 1000 and 1249 ms. Stale at 1250 ms. Crossing a whole second has no special effect. |
| Negative, fractional numeral, missing unit in B, unknown unit, numeric prefix followed by junk | Reject the entire companion value and use the valid base. Apply RFC 9213 field selection if the enclosing dictionary failed to parse. |
| Duplicate or conflicting values | For repeated base directives use RFC 9111 §4.2.1. In ordinary Cache-Control discard an ambiguous companion. Structured Fields dictionary decoding retains the last value for a repeated key. Specify handling at the decoded layer and have senders emit each key once. [RFC 9651 §4.2.2](https://www.rfc-editor.org/rfc/rfc9651.html#section-4.2.2) |
| Very large value | For A propose a common ceiling of 15 decimal digits, the Structured Fields Integer limit. For B bound digits and check multiplication before converting units. Reject unrepresentable companions and use the base. Apply RFC 9111's overflow rule to legacy delta-seconds. [RFC 9111 §1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2) |
| Lifetime 25 ms on a 100 ms clock | Round allowed durations down and estimated age up when reducing precision. If the cache cannot establish freshness, validate. Rounding this lifetime to 100 ms could permit 75 ms of unintended reuse. RFC 9111 already takes the earlier time when a cache's clock is coarser than an Expires date. [RFC 9111 §4.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2) |
| 304 after validation | Update stored metadata and recalculate age from the validation exchange. Discard the previous fine-age sample. If the 304 replaces a policy field, use only pairs in the replacement field. [RFC 9111 §4.3.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4) |
| Concurrent requests or a slow origin | Collapse validations for the same response where possible. Measure origin requests, validation latency and manifest age by tier. Once the stale window expires, an unfinished validation alone provides no permission to serve stale. [RFC 9111 §4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4) |

## Appendix C. Alternative encodings

### B. Explicit duration unit

| Existing | Proposed companion | What it controls |
|---|---|---|
| `max-age=1` | `max-age-fine="1250ms"` | 1.25 s of freshness since generation or validation |
| `s-maxage=0` | `s-maxage-fine="200ms"` | 200 ms for a shared cache |
| `stale-while-revalidate=0` | `stale-while-revalidate-fine="200ms"` | An additional 200 ms from expiry under the same conditions as A |
| `Age: 1` | `Age-Fine: "1075ms"` | Total estimated age of 1.075 s at this hop |

Use a quoted string containing unsigned decimal digits followed immediately by lowercase `ms`, `us` or `ns`. The quotes work in both Cache-Control and a targeted dictionary. Bare `200ms` would cause a dictionary parse error and could discard the entire targeted policy. B can express `"500us"` today, but needs unit conversion and a range for each unit. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9651 §3.3.3](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.3)

### Decimal seconds

Writing `max-age=0.2` would avoid new names, but it has no safe fallback. In Cache-Control the value fails the delta-seconds grammar, and RFC 9111 encourages a cache to treat a response with a non-integer max-age as stale. In a targeted field it parses as a Decimal, and RFC 9213 says implementations should not consume a max-age with a decimal value. A recipient that truncates it anyway sees zero. None of these outcomes lets the origin choose a one-second fallback. A separate companion leaves the base valid for every recipient. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9111 §4.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1)

### Encoding Age

Keeping both readings together has one operational advantage. When a legacy cache serves a stored response without validation, it replaces the entire Age field. That would remove an inline fraction automatically. A separate companion can survive that replacement and become outdated. [RFC 9111 §4](https://www.rfc-editor.org/rfc/rfc9111.html#section-4)

The constraint is the existing grammar. Cache-Control accepts a list of directives. Age accepts one non-negative integer in seconds. For an estimated age of 1.175 seconds, consider these encodings. [RFC 9111 §§5.1–5.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1)

| Encoding | Effect during rollout |
|---|---|
| Separate fields, `Age: 1` and `Age-Ms: 1175` | Preserves a valid reading for every legacy recipient. An upgraded recipient needs confidence that the fine reading was updated along the path. |
| Inline parameter, `Age: 1; ms=175`, or decimal, `Age: 1.175` | Keeps the readings together, but both spellings are invalid today. A cache following the recommended error handling would ignore the entire field, losing even the one-second reading. |
| Extra list member, `Age: 1, 1175` | A recipient following the list-recovery rule would use the first member. That rule handles malformed input. Generating a list would require changing the singleton grammar and relying on recovery across deployed caches. |

We favour the separate field for rollout. Evidence about how existing caches parse and regenerate Age would help the WG assess whether an inline encoding merits further work.

### Parameter in a targeted field

For a first specification we favour A across both policy fields. The same bounded integer works for both, and a use case below 1 ms could justify B. A narrower alternative for managed CDNs would attach an integer parameter to its base, e.g. `CDN-Cache-Control: max-age=0;ms=200`. An RFC 9213 recipient ignores an unfamiliar parameter and sees zero. The attachment eliminates orphan companions in that dictionary. Ordinary Cache-Control has no parameter syntax, and the alternative still needs reliable age across tiers. We would keep one spelling across both policy fields unless implementers see a deployment advantage in the narrower scope. [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1) · [RFC 9111 §5.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2)

## Appendix D. Streaming and historical context

We have seen live playlists reach players four or five seconds old. To assess how much cache timing contributes, trace one revision from publication through the shield and edge to the first player reload that discovers it. Record origin requests alongside discovery lag. HLS clients have their own playlist reload schedule. [RFC 8216 §6.3.4](https://www.rfc-editor.org/rfc/rfc8216.html#section-6.3.4)

HLS playlists already express fractional segment durations and can timestamp the first sample to milliseconds. An origin might also use a sub-second modification time when generating an opaque ETag. Date and Last-Modified carry whole seconds. A fine cache directive would let the origin set a lifetime such as 1.25 seconds independently of the media timeline. [RFC 8216 §§4.3.2.1](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.2.1) and [4.3.2.6](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.2.6) · [RFC 9110 §§5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) and [8.8.3.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3.1)

### Historical context

HTTP/1.0 specified an absolute Expires date in May 1996. HTTP/1.1 specified whole-second `max-age` and `Age` in January 1997. The WG revisited finer resolution in 2011, including the limits of Date and clock synchronisation. [RFC 1945 §10.7](https://www.rfc-editor.org/rfc/rfc1945.html#section-10.7) · [RFC 2068 §3.3.2](https://www.rfc-editor.org/rfc/rfc2068.html#section-3.3.2) · [2011 WG discussion](https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html)

| Storage example | Read | Write | What the figures measure |
|---|---:|---:|---|
| Seagate Cheetah 4LP, 1997 spinning disk | 10.69 ms | 11.69 ms | Estimated time to reach data on the platter. The manual gives typical average seek plus controller overhead of 7.7 ms for reads and 8.7 ms for writes. Average rotational delay adds 2.99 ms to either. [Seagate product manual, §§4.1–4.2, note 6](https://www.seagate.com/support/disc/manuals/scsi/29120b.pdf) |
| Micron 7450 PRO, data-centre NVMe SSD | 80 µs | 15 µs | Median latency for random 4 KB operations with one request outstanding. [Micron product brief, E1.S specifications and latency footnote](https://www.micron.com/content/dam/micron/global/public/products/product-flyer/7450-nvme-ssd-product-brief.pdf) |

Cloudflare lists the 7450 PRO in its Gen 12 edge servers alongside a 96-core processor, DDR5-4800 memory and two 25 GbE ports. The drive figures illustrate the change in local I/O timescales. A cache hit can also come from RAM, and a revalidation can incur an upstream round trip. An origin can choose a lifetime based on how often its manifest changes. Today an origin can choose immediate staleness or a full second, even when its caches can serve many requests in between. [Cloudflare’s Gen 12 server specifications](https://blog.cloudflare.com/gen-12-servers/) · [RFC 9111 §4.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2)

### Sending a live playlist

Fast Ethernet provides a historical baseline of 100 Mb/s (1995). Faster optical links also existed. The 1994 PPP-over-SONET specification described 155.52 Mb/s links. For a current CDN comparison, Cloudflare specifies two 100 GbE ports on its Gen 13 servers. The figures below use one port. [IEEE 802.3u-1995](https://standards.ieee.org/ieee/802.3u/1079/) · [RFC 1619](https://www.rfc-editor.org/rfc/rfc1619.html) · [Cloudflare Gen 13](https://blog.cloudflare.com/gen13-config/)

| Published live media playlist | Body size | At 100 Mb/s | At 100 Gb/s |
|---|---:|---:|---:|
| [RFC 8216 §8.2](https://www.rfc-editor.org/rfc/rfc8216.html#section-8.2), three segment URLs | 257 B | 20.6 µs | 20.6 ns |
| [Apple’s low-latency HLS example](https://developer.apple.com/documentation/http-live-streaming/enabling-low-latency-http-live-streaming-hls), including partial segments and rendition reports | 2,466 B | 197 µs | 197 ns |

We counted the uncompressed playlist text with LF line endings, including the final LF, and removed document indentation. These are example sizes. Window length, URI length and the number of parts affect production playlist size.

For one idle link, payload serialisation time is `8 × body bytes / link rate in bits per second`. Increasing bandwidth 1,000-fold saves about 0.197 ms on the larger example. A cache refresh also pays for framing, transport, queueing, propagation and upstream processing. A conditional request answered with 304 has no playlist body to transfer at all. Even on the slower link, the example body takes under 0.2 ms to serialise. [RFC 9110 §15.4.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.4.5)
