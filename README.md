# Sub-second Freshness Lifetimes for HTTP Caches

HTTP caching expresses freshness in whole seconds: `max-age`, `s-maxage` and `Age` use delta-seconds, and `Expires` and `Date` use HTTP-date. For resources that change about once a second and pass through several layers of shared caches, such as live streaming manifests, one second is too coarse.

This repository holds an early proposal for new Cache-Control extension directives that let an origin server express a freshness lifetime of less than one second, without changing any existing directive.

**Read the proposal: [draft-seddon-httpbis-subsecond-freshness.md](draft-seddon-httpbis-subsecond-freshness.md)**

## The two options in brief

Both are sent alongside `max-age`, so caches that don't recognise them carry on as they do today.

| | Example | Trade-off |
|---|---|---|
| Option A | `Cache-Control: max-age=1, max-age-ms=200` | Simple integer; works in targeted fields such as `CDN-Cache-Control`. Resolution is fixed at one millisecond. |
| Option B | `Cache-Control: max-age=1, max-age-fine=200ms` | One directive with an explicit unit (`ms`, `us`, `ns`), so it should last. Needs a different spelling in Structured Fields. |

Directive names are placeholders.

## Status

This is not yet an Internet-Draft. It is here to support discussion on the [HTTP Working Group mailing list](https://lists.w3.org/Archives/Public/ietf-http-wg/) (ietf-http-wg@w3.org). If there is interest, it will be turned into an individual draft.

## Feedback

Comments are very welcome, either on the mailing list or as issues in this repository. The open questions are listed in [Section 9 of the proposal](draft-seddon-httpbis-subsecond-freshness.md#9-open-questions).

## Background

- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)
- [RFC 9213: Targeted HTTP Cache Control](https://www.rfc-editor.org/rfc/rfc9213.html)
- [RFC 5861: HTTP Cache-Control Extensions for Stale Content](https://www.rfc-editor.org/rfc/rfc5861.html)
- [2011 list discussion of one-second granularity](https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html)
