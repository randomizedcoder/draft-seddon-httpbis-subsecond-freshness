# Sub-second Freshness Lifetimes for HTTP Caches

**Status:** early proposal for discussion on the HTTP Working Group mailing list (ietf-http-wg@w3.org). This is not yet an Internet-Draft. Names, syntax and scope are all open.

**Author:** Dave Seddon

## Abstract

HTTP caching expresses freshness in whole seconds. For resources that change about once a second and are delivered through several layers of shared caches, such as live streaming manifests, one second is too coarse. This document describes the problem and sets out two options for new Cache-Control extension directives that let an origin server express a freshness lifetime of less than one second, without changing the syntax or meaning of any existing directive.

## 1. Introduction

### 1.1. Freshness is in whole seconds

Every input to the freshness model in [RFC 9111] has a resolution of one second:

- max-age, s-maxage and Age use delta-seconds.
- Expires and Date use HTTP-date.

The smallest non-zero freshness lifetime an origin server can ask for is therefore one second.

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

## 2. Prior discussion

Poul-Henning Kamp raised the one-second granularity on the working group list in June 2011, noting that some high-volume sites cache content for only a couple of seconds and that the granularity is a serious limitation for them. He asked whether delta-seconds could allow real numbers.

Mark Nottingham's reply made three points:

1. Low TTLs are useful in controlled deployments (reverse proxies), but forward proxies and browser caches cannot assume clock synchronisation that tight.
2. Nothing stops a Cache-Control extension from having higher precision.
3. Date only has one-second resolution.

https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html

This proposal tries to pick up from there. It uses new extension directives, it does not rely on Date ([Section 5](#5-age)), and it is aimed at shared caches in controlled deployments ([Section 6.1](#61-which-caches)).

## 3. Existing text

The definitions that fix the resolution at one second are quoted here for reference.

### 3.1. Delta Seconds

[RFC 9111, Section 1.2.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-1.2.2):

    The delta-seconds rule specifies a non-negative integer, representing
    time in seconds.

      delta-seconds  = 1*DIGIT

This rule has been unchanged since [RFC 2068] (January 1997).

### 3.2. max-age and s-maxage

[RFC 9111, Section 5.2.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.1):

    Argument syntax:

       delta-seconds (see Section 1.2.2)

    The max-age response directive indicates that the response is to be
    considered stale after its age is greater than the specified number
    of seconds.

[RFC 9111, Section 5.2.2.10](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.10) (s-maxage) uses the same argument syntax.

### 3.3. Age

[RFC 9111, Section 5.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.1):

      Age = delta-seconds

    The Age field value is a non-negative integer, representing time in
    seconds (see Section 1.2.2).

### 3.4. Calculating Age

[RFC 9111, Section 4.2.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.3):

      apparent_age = max(0, response_time - date_value);

      response_delay = response_time - request_time;
      corrected_age_value = age_value + response_delay;

    The corrected_age_value MAY be used as the corrected_initial_age.

### 3.5. Expires and HTTP-date

[RFC 9111, Section 5.3](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3):

    The Expires field value is an HTTP-date timestamp, as defined in
    Section 5.6.7 of [HTTP].

    If a response includes a Cache-Control header field with the max-age
    directive (Section 5.2.2.1), a recipient MUST ignore the Expires
    header field.

HTTP-date is defined in [RFC 9110, Section 5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7) and has a resolution of one second.

### 3.6. Invalid freshness information

[RFC 9111, Section 4.2.1](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.2.1):

    Caches are encouraged to consider responses that have invalid
    freshness information (e.g., a max-age directive with non-integer
    content) to be stale.

This is why the proposal does not change the argument syntax of max-age. A value such as "max-age=500ms" or "max-age=0.5" would be treated as stale by a conforming cache, and a lenient parser might read "500ms" as 500 seconds.

### 3.7. Extension directives

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

A new extension response directive carries the finer-grained freshness lifetime. It is sent alongside max-age (or s-maxage). A cache that recognises the new directive uses it; a cache that does not recognise it ignores it and uses max-age as it does today.

Two options are set out for discussion. Directive names are placeholders.

### 4.1. Option A: milliseconds

    Cache-Control: max-age=1, max-age-ms=200

Proposed text:

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

- The resolution is fixed. If finer control is wanted one day, it needs another directive (max-age-us, max-age-ns), and then a rule for which one wins when several are present.

### 4.2. Option B: an explicit unit

    Cache-Control: max-age=1, max-age-fine=200ms

Proposed text:

    max-age-fine

    Argument syntax:

       delta-time

      delta-time  = 1*DIGIT time-unit
      time-unit   = "ms" / "us" / "ns"

    The delta-time rule specifies a non-negative integer followed by a
    unit, representing time in milliseconds ("ms"), microseconds ("us"),
    or nanoseconds ("ns").

    The max-age-fine response directive indicates that the response is
    to be considered stale after its age is greater than the specified
    time.  A cache that recognizes max-age-fine uses it in preference
    to max-age.

For:

- It is one directive that should last. One second looked like a safe floor in 1997; in 30 years, microseconds or nanoseconds could well be normal.
- It is intuitive for the people who write these header fields.

Against:

- Every cache has to decide what to do with a unit finer than it can honour.
- "200ms" is not a valid Integer, Decimal or Token in Structured Fields ([RFC 9651]), so it would need a different spelling in targeted fields: a String, or a separate directive per unit in the style of Option A.

### 4.3. Shared caches

Whichever option is chosen, s-maxage presumably wants an equivalent (s-maxage-ms, or s-maxage-fine). If the new directives apply to shared caches only ([Section 6.1](#61-which-caches)), a single directive modelled on s-maxage might be enough.

## 5. Age

A finer freshness lifetime is of limited use if age is still carried between caches in whole seconds: each hop still loses up to a second. Age therefore needs a higher-precision companion, in whichever style is chosen for the directive (for example, an integer number of milliseconds).

This also seems to address the concern about Date. Section 4.2.3 of [RFC 9111] allows the corrected_age_value (the received age plus the response delay) to be used as the corrected_initial_age, without reference to Date. The current age is then that value plus the time the response has been resident in the cache. Every term is either received from upstream or is an interval measured on the cache's own clock, so the calculation does not depend on clocks being synchronised between caches.

A cache using the new directive would calculate age this way, using the higher-precision age value where one is present.

Open points:

- What the companion to Age looks like: a new field, and its name and syntax.
- What a cache does when it receives the new directive from an upstream that sent only a whole-second Age.

## 6. Scope

### 6.1. Which caches

The motivating deployments are reverse proxies and CDNs, where the operator controls or contracts every cache on the path. It may be safest for the new directives to apply to shared caches only, in the manner of s-maxage. Private caches would then continue to use max-age.

### 6.2. stale-while-revalidate

stale-while-revalidate ([RFC 5861]) is defined relative to the point at which a response becomes stale, however the freshness lifetime was set. It is expected to work unchanged with the new directives, and it remains the recommended way to let each layer keep serving the previous response while it refreshes in the background.

Its own argument is in delta-seconds. Whether that needs a finer-grained form is an open question.

### 6.3. Request directives

The max-age, max-stale and min-fresh request directives are out of scope for now.

## 7. Operational considerations

Shorter freshness lifetimes mean more requests to upstream caches and to the origin server. Setting the lifetime too low can cause a large increase in load. Operators need to be aware of this before they use these directives.

An origin server can already send max-age=0 or no-cache, so sub-second lifetimes fill a gap between "revalidate every time" and "one second"; they do not create a new extreme.

Practical guidance:

- Lifetimes in the hundreds of milliseconds (100, 200, 500ms) are likely to be about as low as anyone would want to go today.
- Values such as 1ms or 1ns are unlikely to be meaningful in practice. Process scheduling jitter alone is larger than that, so a cache could not actually do what the field asks.
- Cache implementations and CDN operators should document the minimum resolution they support. 100ms seems a reasonable place to start in 2026.

A cache will sometimes receive a lifetime finer than it supports. Whether it should round up to its minimum, or treat the response as stale, is an open question ([Section 9](#9-open-questions)).

## 8. Security considerations

The considerations in Section 7 of [RFC 9111] apply.

The main new consideration is load. A misconfigured or compromised origin that sends very small lifetimes can cause every cache on the path to make many more upstream requests. A minimum supported resolution in each cache, as suggested in [Section 7](#7-operational-considerations), bounds this.

## 9. Open questions

1. Option A or Option B, or something else entirely?
2. What should a cache do with a lifetime finer than it supports: round up to its minimum, or treat the response as stale?
3. What should the higher-precision companion to Age look like?
4. Shared caches only, or all caches?
5. Does stale-while-revalidate need a finer-grained form as well?
6. If Option A, should "us" and "ns" directives be defined now or left for later? If Option B, is "us" wanted between "ms" and "ns"?

## 10. References

- [RFC 2068]: Hypertext Transfer Protocol -- HTTP/1.1, January 1997
- [RFC 5861]: HTTP Cache-Control Extensions for Stale Content, May 2010
- [RFC 9110]: HTTP Semantics, June 2022
- [RFC 9111]: HTTP Caching, June 2022
- [RFC 9213]: Targeted HTTP Cache Control, June 2022
- [RFC 9651]: Structured Field Values for HTTP, September 2024

[RFC 2068]: https://www.rfc-editor.org/rfc/rfc2068.html
[RFC 5861]: https://www.rfc-editor.org/rfc/rfc5861.html
[RFC 9110]: https://www.rfc-editor.org/rfc/rfc9110.html
[RFC 9111]: https://www.rfc-editor.org/rfc/rfc9111.html
[RFC 9213]: https://www.rfc-editor.org/rfc/rfc9213.html
[RFC 9651]: https://www.rfc-editor.org/rfc/rfc9651.html
