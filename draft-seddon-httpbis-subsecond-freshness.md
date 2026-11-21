# Sub-second Time Resolution for HTTP Caching

**Status:** early proposal for discussion on the HTTP Working Group mailing list (ietf-http-wg@w3.org). This is not yet an Internet-Draft. Names, syntax and scope are all open.

**Author:** Dave Seddon

## Abstract

HTTP caching expresses time in whole seconds. For resources that change about once a second and are delivered through several layers of shared caches, such as live streaming manifests, one second is too coarse.

This document reviews the time-related fields and directives used by HTTP caches as a set, identifies which of them need a resolution finer than one second, and sets out two options for a single convention that covers all of them. The convention uses new extension directives and does not change the syntax or meaning of anything that exists today.

## 1. Introduction

### 1.1. Caching time is in whole seconds

Every time value in the caching model of [RFC 9111] has a resolution of one second:

- max-age, s-maxage and Age use delta-seconds.
- stale-while-revalidate and stale-if-error ([RFC 5861]) use delta-seconds.
- Expires and Date use HTTP-date.

The smallest non-zero freshness lifetime an origin server can ask for is therefore one second, and so is the smallest window for serving a stale response while revalidating.

### 1.2. Live streaming

In live streaming over HTTP (HLS or DASH), the encoder publishes new media segments and rewrites the manifest every one or two seconds. For live sport in particular, operators work to keep the delay between the action on the field and what the viewer sees as low as possible, so delivery becomes a race to get the latest manifest to the player.

A typical delivery path has several layers of caching:

    encoder (new manifest about once a second)
      -> origin cache (e.g., nginx or Apache Traffic Server), which
         shields the encoder and feeds several CDNs
      -> CDN first tier
      -> CDN mid tier
      -> CDN edge cache in the viewer's metro
      -> player

### 1.3. Lifetimes are effectively additive across layers

In principle the Age header field stops freshness lifetimes stacking up across hops: each cache reports how old the response already is, and the next cache counts that against the freshness lifetime.

At these timescales it does not work out that way. Age is in whole seconds, so each hop can lose up to a second of accumulated age, and what operators observe is that the lifetime is effectively additive. With max-age=1 across four or five layers, a manifest can be 4-5 seconds old when it reaches the player, even though it was replaced at the origin after one second.

Expires behaves better across layers, because every cache expires the response at the same instant relative to the origin server's clock. However, HTTP-date also has one-second resolution, and Expires is ignored whenever max-age is present.

### 1.4. The workaround, and what it costs

The usual workaround is to reduce the number of cache layers so that the additive lifetime stays low.

For example, with an origin in New York, an edge cache in Melbourne would ideally fetch from Sydney, Sydney from Los Angeles, Los Angeles from Chicago, and Chicago from New York. At up to a second per layer that is too stale, so Melbourne instead fetches more directly across the Internet, through fewer layers. That is less efficient and costs more.

With lifetimes of, say, 200 milliseconds, the cache hierarchy can be deeper and the manifest still reaches the player well within a second.

### 1.5. Other uses

Live streaming is the motivating case, but not the only one:

- Large sites want very short-lived caching of fast-changing resources.
- LLM-based agents are starting to poll HTTP resources at higher rates than people do, which makes short-lived shared caching more valuable.

### 1.6. Why standardise

An operator can always define a private header field. The reason to standardise is so that cache implementations and commercial CDNs all support the same thing. Otherwise each operator ends up with custom header fields that CDNs support unevenly or not at all, and the result is vendor lock-in.

### 1.7. Why review the time values as a set

A finer freshness lifetime is not useful on its own. The time values in the caching model work together:

- If max-age is finer but Age is not, each hop still loses up to a second of age ([Section 5](#5-age)).
- If max-age is finer but stale-while-revalidate is not, a cache can serve a response that is a full second past a 200 millisecond lifetime ([Section 6](#6-stale-while-revalidate)).

So this document looks at all of them, and proposes one convention that applies to each one that needs it.

## 2. Prior discussion

Poul-Henning Kamp raised the one-second granularity on the working group list in June 2011, noting that some high-volume sites cache content for only a couple of seconds and that the granularity is a serious limitation for them. He asked whether delta-seconds could allow real numbers.

Mark Nottingham's reply made three points:

1. Low TTLs are useful in controlled deployments (reverse proxies), but forward proxies and browser caches cannot assume clock synchronisation that tight.
2. Nothing stops a Cache-Control extension from having higher precision.
3. Date only has one-second resolution.

https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html

This proposal tries to pick up from there. It uses new extension directives, it does not rely on Date ([Section 5](#5-age)), and it is aimed at shared caches in controlled deployments ([Section 7.1](#71-which-caches)).

## 3. Time-related fields and directives

### 3.1. Inventory

| Element | Defined in | Syntax | Role in caching | Proposed here |
|---|---|---|---|---|
| max-age (response) | [RFC 9111, 5.2.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.1) | delta-seconds | Freshness lifetime | Finer form |
| s-maxage | [RFC 9111, 5.2.2.10](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.10) | delta-seconds | Freshness lifetime for shared caches | Finer form |
| Age | [RFC 9111, 5.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1) | delta-seconds | Age carried from cache to cache | Finer companion field |
| stale-while-revalidate | [RFC 5861, 3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3) | delta-seconds | Window for serving stale while revalidating | Finer form |
| stale-if-error | [RFC 5861, 4](https://www.rfc-editor.org/rfc/rfc5861.html#section-4) | delta-seconds | Window for serving stale after an error | Same convention; less pressing |
| max-age, max-stale, min-fresh (request) | [RFC 9111, 5.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.1) | delta-seconds | Client preferences | Same convention; less pressing |
| Expires | [RFC 9111, 5.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3) | HTTP-date | Absolute expiry time | No change |
| Date | [RFC 9110, 6.6.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-6.6.1) | HTTP-date | Origination time; input to apparent_age | No change; not relied on |
| Last-Modified and the conditionals that use it | [RFC 9110, 8.8.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.2) | HTTP-date | Validator | No change; use ETag |
| ttl parameter of Cache-Status | [RFC 9211, 2.4](https://www.rfc-editor.org/rfc/rfc9211.html#section-2.4) | Integer seconds | Reporting remaining freshness | Worth aligning |
| Retry-After | [RFC 9110, 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3) | HTTP-date / delay-seconds | Not a caching field | Out of scope; noted |

The first four rows are what live streaming needs. They are the core of the proposal. The remaining rows are covered in [Section 7](#7-scope).

### 3.2. Existing text

The definitions that fix the resolution at one second are quoted here for reference.

#### Delta Seconds

[RFC 9111, Section 1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2):

    The delta-seconds rule specifies a non-negative integer, representing
    time in seconds.

      delta-seconds  = 1*DIGIT

This rule has been unchanged since [RFC 2068] (January 1997).

#### max-age and s-maxage

[RFC 9111, Section 5.2.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.1):

    Argument syntax:

       delta-seconds (see Section 1.2.2)

    The max-age response directive indicates that the response is to be
    considered stale after its age is greater than the specified number
    of seconds.

[RFC 9111, Section 5.2.2.10](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.10) (s-maxage) uses the same argument syntax.

#### Age

[RFC 9111, Section 5.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1):

      Age = delta-seconds

    The Age field value is a non-negative integer, representing time in
    seconds (see Section 1.2.2).

#### Calculating Age

[RFC 9111, Section 4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3):

      apparent_age = max(0, response_time - date_value);

      response_delay = response_time - request_time;
      corrected_age_value = age_value + response_delay;

    The corrected_age_value MAY be used as the corrected_initial_age.

#### stale-while-revalidate

[RFC 5861, Section 3](https://www.rfc-editor.org/rfc/rfc5861.html#section-3):

    When present in an HTTP response, the stale-while-revalidate Cache-
    Control extension indicates that caches MAY serve the response in
    which it appears after it becomes stale, up to the indicated number
    of seconds.

      stale-while-revalidate = "stale-while-revalidate" "=" delta-seconds

#### Expires and HTTP-date

[RFC 9111, Section 5.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3):

    The Expires field value is an HTTP-date timestamp, as defined in
    Section 5.6.7 of [HTTP].

    If a response includes a Cache-Control header field with the max-age
    directive (Section 5.2.2.1), a recipient MUST ignore the Expires
    header field.

HTTP-date is defined in [RFC 9110, Section 5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) and has a resolution of one second.

#### Invalid freshness information

[RFC 9111, Section 4.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1):

    Caches are encouraged to consider responses that have invalid
    freshness information (e.g., a max-age directive with non-integer
    content) to be stale.

This is why the proposal does not change the argument syntax of any existing directive. A value such as "max-age=500ms" or "max-age=0.5" would be treated as stale by a conforming cache, and a lenient parser might read "500ms" as 500 seconds.

#### Extension directives

[RFC 9111, Section 5.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.3):

    A cache MUST ignore unrecognized cache directives.

    Behavioral extensions are designed to work by acting as modifiers to
    the existing base of cache directives.  Both the new directive and
    the old directive are supplied, such that applications that do not
    understand the new directive will default to the behavior specified
    by the old directive, and those that understand the new directive
    will recognize it as modifying the requirements associated with the
    old directive.  In this way, extensions to the existing cache
    directives can be made without breaking deployed caches.

This is the mechanism both options below use.

## 4. Proposal

### 4.1. One convention for every time value

Each existing directive that needs finer resolution gets a companion extension directive that carries the same quantity at higher precision. The companion is sent alongside the existing directive:

- A cache that recognises the companion uses it in preference to the existing directive.
- A cache that does not recognise it ignores it and behaves as it does today.

The existing directive therefore acts as the fallback, and the sender chooses its value for caches that have not been updated. In the examples below the fallback is rounded up to one second.

The same convention is applied to every time value, so that implementers and operators learn one rule, not one rule per directive.

Two options for the convention are set out for discussion. Names are placeholders.

### 4.2. Option A: a "-ms" companion, in milliseconds

    Cache-Control: max-age=1, max-age-ms=200,
                   stale-while-revalidate=1, stale-while-revalidate-ms=200

For a directive X whose argument is delta-seconds, the directive X-ms carries the same quantity as an integer number of milliseconds.

Proposed text for max-age-ms; the others follow the same pattern:

    max-age-ms

    Argument syntax:

       1*DIGIT

    The max-age-ms response directive indicates that the response is to
    be considered stale after its age is greater than the specified
    number of milliseconds.  A cache that recognizes max-age-ms uses it
    in preference to max-age.

For:

- It is simple to generate and parse.
- The value is an integer, so it works unchanged in targeted fields such as CDN-Cache-Control ([RFC 9213]), which are Structured Fields.
- Milliseconds would have been a sensible resolution for the last decade and probably will be for the next one.

Against:

- The resolution is fixed. If finer control is wanted one day, it needs a further set of directives ("-us", "-ns"), and then a rule for which one wins when several are present.

### 4.3. Option B: a companion with an explicit unit

    Cache-Control: max-age=1, max-age-fine=200ms,
                   stale-while-revalidate=1, stale-while-revalidate-fine=200ms

For a directive X whose argument is delta-seconds, the directive X-fine carries the same quantity as a delta-time.

Proposed text:

    The delta-time rule specifies a non-negative integer followed by a
    unit, representing time in milliseconds ("ms"), microseconds ("us"),
    or nanoseconds ("ns").

      delta-time  = 1*DIGIT time-unit
      time-unit   = "ms" / "us" / "ns"

    max-age-fine

    Argument syntax:

       delta-time

    The max-age-fine response directive indicates that the response is
    to be considered stale after its age is greater than the specified
    time.  A cache that recognizes max-age-fine uses it in preference
    to max-age.

For:

- It is one set of directives that should last. One second looked like a safe floor in 1997; in 30 years, microseconds or nanoseconds could well be normal.
- It is intuitive for the people who write these header fields.

Against:

- Every cache has to decide what to do with a unit finer than it can honour.
- "200ms" is not a valid Integer, Decimal or Token in Structured Fields ([RFC 9651]), so it would need a different spelling in targeted fields: a String, or a separate directive per unit in the style of Option A.

### 4.4. What gets a companion

| Existing | Option A | Option B |
|---|---|---|
| max-age (response) | max-age-ms | max-age-fine |
| s-maxage | s-maxage-ms | s-maxage-fine |
| stale-while-revalidate | stale-while-revalidate-ms | stale-while-revalidate-fine |
| Age (field) | a millisecond companion field | a companion field with a unit |

stale-if-error and the request directives could follow the same pattern if there is a use for it ([Section 7](#7-scope)).

## 5. Age

A finer freshness lifetime is of limited use if age is still carried between caches in whole seconds: each hop still loses up to a second. Age therefore needs a higher-precision companion field, in whichever style is chosen for the directives.

This also seems to address the concern about Date. Section 4.2.3 of [RFC 9111] allows the corrected_age_value (the received age plus the response delay) to be used as the corrected_initial_age, without reference to Date. The current age is then that value plus the time the response has been resident in the cache. Every term is either received from upstream or is an interval measured on the cache's own clock, so the calculation does not depend on clocks being synchronised between caches.

A cache using the new directives would calculate age this way, using the higher-precision age value where one is present.

Open points:

- The name and syntax of the companion to Age.
- What a cache does when it receives the new directives from an upstream that sent only a whole-second Age.

## 6. stale-while-revalidate

### 6.1. Why it needs the same resolution

stale-while-revalidate lets a cache answer immediately with the response it has, while it fetches a new one in the background. Without it, every request that arrives after the response becomes stale waits for the upstream fetch.

That matters more as lifetimes get shorter. A response with a 200 millisecond lifetime becomes stale five times a second. Without stale-while-revalidate, clients stall at each of those moments, at every layer of the hierarchy.

The existing directive cannot express a suitable window. Its smallest non-zero value is one second, so with a 200 millisecond lifetime a cache may serve a response for up to 1.2 seconds after storing it. That is far staler than the origin intended, and it applies at each layer. A coarse stale-while-revalidate undoes most of the benefit of a fine freshness lifetime.

### 6.2. Recommended configuration for live streaming

Setting both values at the same fine resolution is the safer configuration:

    Cache-Control: max-age=1, max-age-ms=200,
                   stale-while-revalidate=1, stale-while-revalidate-ms=200

(Shown in the style of Option A.)

For a cache that recognises the new directives, measured from when the response was generated:

| Age of the response | Cache behaviour |
|---|---|
| 0 to 200 ms | Fresh. Served from the cache. |
| 200 to 400 ms | Stale. Served immediately, while the cache revalidates in the background. Clients do not wait. |
| After 400 ms | No longer served stale. The next request waits for the upstream response. |

In normal operation the background revalidation completes well inside the second window, so clients are never stalled, and the manifest they receive is at most 400 milliseconds old at that layer.

A cache that does not recognise the new directives uses max-age=1 and stale-while-revalidate=1, exactly as it does today.

### 6.3. Semantics

The companion keeps the semantics of [RFC 5861]: the window starts when the response becomes stale, however its freshness lifetime was set. Only the resolution changes.

## 7. Scope

### 7.1. Which caches

The motivating deployments are reverse proxies and CDNs, where the operator controls or contracts every cache on the path. It may be safest for the new directives to apply to shared caches only, in the manner of s-maxage. Private caches would then continue to use max-age. In that case a single freshness directive modelled on s-maxage might be enough, without a separate companion for max-age.

### 7.2. stale-if-error

stale-if-error ([RFC 5861]) windows are usually long, because they cover origin outages. A finer form is unlikely to be needed, but it could follow the same convention for consistency.

### 7.3. Request directives

The max-age, max-stale and min-fresh request directives express client preferences. No need for a finer form has been identified. They could follow the same convention later.

### 7.4. Expires and Date

No change is proposed to HTTP-date. When a freshness directive is present, Expires is already ignored, and the age calculation in [Section 5](#5-age) does not rely on Date.

### 7.5. Last-Modified

Last-Modified also has one-second resolution, so it cannot distinguish two versions of a resource written within the same second. [RFC 9110, Section 8.8.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.1) already covers this, and [Section 8.8.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3) notes that an entity tag is more reliable "where the one-second resolution of HTTP-date values is not sufficient". Resources that use sub-second lifetimes should be validated with ETag. No change is needed.

### 7.6. Cache-Status

The ttl parameter of Cache-Status ([RFC 9211]) reports the remaining freshness lifetime as an integer number of seconds. For a response with a sub-second lifetime it will almost always read 0. It may be worth a finer companion for debugging, but nothing depends on it.

### 7.7. Retry-After

Retry-After ([RFC 9110, Section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)) is not a caching field, and is out of scope. It is listed because its delay-seconds form has the same one-second floor, and clients that poll at high rates may eventually want the same treatment.

## 8. Operational considerations

Shorter freshness lifetimes mean more requests to upstream caches and to the origin server. Setting the lifetime too low can cause a large increase in load. Operators need to be aware of this before they use these directives.

An origin server can already send max-age=0 or no-cache, so sub-second lifetimes fill a gap between "revalidate every time" and "one second"; they do not create a new extreme.

Practical guidance:

- Lifetimes in the hundreds of milliseconds (100, 200, 500ms) are likely to be about as low as anyone would want to go today.
- Short lifetimes should be paired with a stale-while-revalidate window of similar size ([Section 6](#6-stale-while-revalidate)), so that clients are not stalled at each expiry.
- Values such as 1ms or 1ns are unlikely to be meaningful in practice. Process scheduling jitter alone is larger than that, so a cache could not actually do what the field asks.
- Cache implementations and CDN operators should document the minimum resolution they support. 100ms seems a reasonable place to start in 2026.

A cache will sometimes receive a value finer than it supports. Whether it should round up to its minimum, or treat the response as stale, is an open question ([Section 10](#10-open-questions)).

## 9. Security considerations

The considerations in Section 7 of [RFC 9111] apply.

The main new consideration is load. A misconfigured or compromised origin that sends very small lifetimes can cause every cache on the path to make many more upstream requests. A minimum supported resolution in each cache, as suggested in [Section 8](#8-operational-considerations), bounds this.

## 10. Open questions

1. Option A or Option B, or something else entirely?
2. Is the set in [Section 4.4](#44-what-gets-a-companion) the right one? Should stale-if-error, the request directives or the Cache-Status ttl parameter be included from the start?
3. What should a cache do with a value finer than it supports: round up to its minimum, or treat the response as stale?
4. What should the higher-precision companion to Age look like?
5. Shared caches only, or all caches?
6. If Option A, should "-us" and "-ns" forms be defined now or left for later? If Option B, is "us" wanted between "ms" and "ns"?

## 11. References

- [RFC 2068]: Hypertext Transfer Protocol -- HTTP/1.1, January 1997
- [RFC 5861]: HTTP Cache-Control Extensions for Stale Content, May 2010
- [RFC 9110]: HTTP Semantics, June 2022
- [RFC 9111]: HTTP Caching, June 2022
- [RFC 9211]: The Cache-Status HTTP Response Header Field, June 2022
- [RFC 9213]: Targeted HTTP Cache Control, June 2022
- [RFC 9651]: Structured Field Values for HTTP, September 2024

[RFC 2068]: https://www.rfc-editor.org/rfc/rfc2068.html
[RFC 5861]: https://www.rfc-editor.org/rfc/rfc5861.html
[RFC 9110]: https://www.rfc-editor.org/rfc/rfc9110.html
[RFC 9111]: https://www.rfc-editor.org/rfc/rfc9111.html
[RFC 9211]: https://www.rfc-editor.org/rfc/rfc9211.html
[RFC 9213]: https://www.rfc-editor.org/rfc/rfc9213.html
[RFC 9651]: https://www.rfc-editor.org/rfc/rfc9651.html
