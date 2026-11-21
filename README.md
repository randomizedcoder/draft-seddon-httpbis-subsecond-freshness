# Sub-second Time Resolution for HTTP Caching

HTTP caching expresses time in whole seconds: `max-age`, `s-maxage`, `Age` and `stale-while-revalidate` use delta-seconds, and `Expires` and `Date` use HTTP-date. For resources that change about once a second and pass through several layers of shared caches, such as live streaming manifests, one second is too coarse.

This repository holds an early proposal that reviews the time-related caching fields and directives as a set, and proposes one convention for giving the ones that need it a resolution finer than one second, without changing anything that exists today.

**Read the proposal: [draft-seddon-httpbis-subsecond-freshness.md](draft-seddon-httpbis-subsecond-freshness.md)**

## The two options in brief

In both, each existing directive gets a higher-precision companion that is sent alongside it. Caches that don't recognise the companion carry on as they do today.

**Option A: a `-ms` companion, in milliseconds**

    Cache-Control: max-age=1, max-age-ms=200,
                   stale-while-revalidate=1, stale-while-revalidate-ms=200

Simple integers, which work unchanged in targeted fields such as `CDN-Cache-Control`. The resolution is fixed at one millisecond.

**Option B: a companion with an explicit unit (`ms`, `us`, `ns`)**

    Cache-Control: max-age=1, max-age-fine=200ms,
                   stale-while-revalidate=1, stale-while-revalidate-fine=200ms

One set of directives that should last. Needs a different spelling in Structured Fields.

Directive names are placeholders. Either way, `Age` needs a higher-precision companion as well.

## Why stale-while-revalidate is included

A 200 millisecond lifetime expires five times a second. Pairing it with a 200 millisecond `stale-while-revalidate` window lets each cache keep serving while it refreshes in the background, so clients are not stalled. The existing directive cannot express a window shorter than one second.

## Status

This is not yet an Internet-Draft. It is here to support discussion on the [HTTP Working Group mailing list](https://lists.w3.org/Archives/Public/ietf-http-wg/) (ietf-http-wg@w3.org). If there is interest, it will be turned into an individual draft.

## Feedback

Comments are very welcome, either on the mailing list or as issues in this repository. The open questions are listed in [Section 10 of the proposal](draft-seddon-httpbis-subsecond-freshness.md#10-open-questions).

## Background

- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)
- [RFC 5861: HTTP Cache-Control Extensions for Stale Content](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9213: Targeted HTTP Cache Control](https://www.rfc-editor.org/rfc/rfc9213.html)
- [2011 list discussion of one-second granularity](https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html)
