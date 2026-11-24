# Finer resolution for HTTP cache durations

Dave Seddon · Discussion proposal for the HTTP Working Group · [Internet-Draft source](draft-seddon-httpbis-subsecond-freshness.md)

## Summary

- **Problem.** HTTP caches count freshness and age in whole seconds. An origin can choose immediate staleness or a full second, with nothing in between.
- **Proposal.** Millisecond companions for max-age, s-maxage, stale-while-revalidate and the Age response field, so that each cache counts the time already spent upstream.
- **Rollout.** The origin sends a whole-second fallback with every companion. Older caches use the fallback.

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

- The first three rows are response directives in Cache-Control or a targeted field such as CDN-Cache-Control. The last row shows two response fields.
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

- **Origin load.** Short lifetimes can increase it. [RFC 5861 §5](https://www.rfc-editor.org/rfc/rfc5861.html#section-5)
- **Stale window.** It helps when a request arrives during the window and validation completes in time. It cannot guarantee an uninterrupted stream.
- **Privacy.** Fine age and per-tier diagnostics reveal cache activity at higher resolution. Operators can limit their exposure across trust boundaries. [RFC 9211 §6](https://www.rfc-editor.org/rfc/rfc9211.html#section-6)

## Questions for the working group

- Where do you need to communicate a fractional-second lifetime between independently implemented caches? What resolution does the application need?
- How do you establish that every cache on a path updates age? Would the whole-second fallback work where you cannot establish that?

Per-tier age, validation outcomes and playlist discovery times would help quantify the effect on players.

The [Internet-Draft](draft-seddon-httpbis-subsecond-freshness.md) specifies the grammar, ranges, duplicate handling and registration of the names. [RFC 9111 §5.2.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.4) · [IANA HTTP field registry](https://www.iana.org/assignments/http-fields/)

## Acknowledgements

The author used Claude and OpenAI Codex to research RFC references, draft and edit the text, and explore how the proposed extensions would behave in mixed cache deployments.

## Appendix A. Other time-related fields

We searched the current HTTP RFCs for whole-second durations and timestamps.

- **Who uses delta-seconds.** RFC 9111 defines it. RFC 5861, RFC 7240, RFC 6797, RFC 7838 and RFC 9163 import it. RFC 6265 uses the name for a value that can be negative.
- **Own rules.** Retry-After, Web Push TTL and Cache-Status ttl define whole seconds separately.
- **No durations.** HTTP/2 and HTTP/3 define no cache durations of their own. [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html) · [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)
- **Candidates.** The same unit could serve them. Each needs a decision about who measures the interval, when it starts, and what rounding does to its guarantee.

The [IANA cache directive registry](https://www.iana.org/assignments/http-cache-directives/) lists the current cache directives.

| Field or directive | Treatment | Reason |
|---|---|---|
| Age, response max-age, s-maxage, stale-while-revalidate | In scope | These determine how a freshness lifetime is shared between caches. [RFC 9111 §§5.1, 5.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1) · [RFC 5861 §3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) |
| stale-if-error | Candidate | Bounds staleness after a qualifying error, independently of the background-validation window. It can appear in requests and responses. [RFC 5861 §§3–4](https://www.rfc-editor.org/rfc/rfc5861.html#section-4) |
| Request max-age, min-fresh, max-stale | Candidate | Preserve the distinction between a maximum age, a minimum remaining lifetime and an acceptable amount of staleness. Bare max-stale has no numerical limit. [RFC 9111 §5.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.1) |
| Cache-Status ttl | Candidate, diagnostic | Its value must be able to go negative once stale. [RFC 9211 §2.4](https://www.rfc-editor.org/rfc/rfc9211.html#section-2.4) |
| Retry-After, Prefer wait | Possible later use | Retry-After can be a date or a minimum delay. Rounding a minimum delay down can cause an early retry. Prefer wait expresses the client's waiting budget. [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3) · [RFC 7240 §4.3](https://www.rfc-editor.org/rfc/rfc7240.html#section-4.3) |
| Alt-Svc ma | Review separately | A related lifetime that consumes response age but governs an alternative service advertisement. [RFC 7838 §3.1](https://www.rfc-editor.org/rfc/rfc7838.html#section-3.1) |
| immutable | No change needed | Already applies for the calculated freshness lifetime. It takes no duration argument. [RFC 8246 §2](https://www.rfc-editor.org/rfc/rfc8246.html#section-2) |
| Date, Expires | Out of scope | Absolute timestamps require a clock and a timestamp encoding. For finer freshness use a relative lifetime. [RFC 9110 §5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) · [RFC 9111 §5.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3) |
| Last-Modified and date-based conditionals | Out of scope | Use distinct strong ETags for distinct manifest revisions within a second. [RFC 9110 §8.8](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8) |
| Strict-Transport-Security max-age, Expect-CT max-age, Set-Cookie Max-Age | Out of scope | Security policy and cookie retention have their own expiry rules. Zero can remove existing state. Each would need a separate compatibility analysis. [RFC 6797 §6.1.1](https://www.rfc-editor.org/rfc/rfc6797.html#section-6.1.1) · [RFC 9163 §2.1.3](https://www.rfc-editor.org/rfc/rfc9163.html#section-2.1.3) · [RFC 6265 §5.2.2](https://www.rfc-editor.org/rfc/rfc6265.html#section-5.2.2) |
| Web Push TTL | Out of scope | It bounds how long a push service retains a message for an offline device. [RFC 8030 §5.2](https://www.rfc-editor.org/rfc/rfc8030.html#section-5.2) |
| Signature `created` and `expires`, Structured Fields Date | Out of scope | These are absolute timestamps in integer seconds, and a Date with a fraction fails to parse. A relative lifetime avoids the need for a finer timestamp type. [RFC 9421 §2.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.3) · [RFC 9651 §3.3.7](https://www.rfc-editor.org/rfc/rfc9651.html#section-3.3.7) |

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

### Decimal seconds

Writing `max-age=0.2` has no safe fallback. [RFC 9111 §4.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1) · [RFC 9213 §2.1](https://www.rfc-editor.org/rfc/rfc9213.html#section-2.1)

| Recipient | Outcome |
|---|---|
| Cache-Control parser | The value fails the delta-seconds grammar. RFC 9111 encourages treating a response with a non-integer max-age as stale. |
| Targeted-field parser | The value parses as a Decimal. RFC 9213 says implementations should not consume a max-age with a decimal value. |
| A recipient that truncates | Sees zero |

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

A local nginx prototype implements the companions for ordinary Cache-Control. Integer parsing and the two expiry comparisons were straightforward. Most of the work concerned when a response may be reused, which age belongs to the stored representation, and how both survive validation or a restart. These cases exercise those decisions.

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
