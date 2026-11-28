# Millisecond Resolution for HTTP Durations

This is the working area for the individual Internet-Draft, "Millisecond Resolution for HTTP Durations".

## Executive summary

- **The problem.** With one-second segments, a live video playlist is replaced every second, and every player reloads it. HLS recommends caching it for half the Target Duration, which is 500 ms here. HTTP cannot state that: `max-age=0` allows no fresh reuse and `max-age=1` allows twice the intended time.
- **Why.** HTTP counts cache lifetimes in whole seconds. That unit was set in January 1997 and has not changed in almost 30 years. One host in our tests answered 25,000 to 44,000 requests from cache in that second.
- **Who it affects.** Live streaming, which we measured. Busy sites whose data changes within a second, such as shopping during a sale and trading, are likely cases that we have not measured.
- **Age between caches.** A cache also has to count the time a response spent upstream. HTTP does this already, but `Age` carries whole seconds, so the fraction is lost at each hop.
- **Elsewhere.** Newer protocols count in milliseconds from the start: QUIC, and Media over QUIC Transport, which is designed for live media and gives its cache duration in milliseconds.
- **Stale-while-revalidate.** Production configurations add a stale window so that a cache keeps answering while it refreshes. Its smallest value above zero is also one second, so the same gap applies to it.
- **The proposal.** Millisecond resolution for HTTP cache lifetimes, stale windows and age, as companion fields. It is backwards compatible: older caches ignore the companions and apply the whole-second values as they do today.
- **Evidence.** In a test with twenty simulated players, a 200 ms lifetime delivered new segments as soon as `max-age=0` did, for a fifth of the origin playlist requests. Under load, adding a 200 ms stale window cut origin requests from about 42 per segment to 5. [Measurements](measurements.md)
- **Aim.** Bring HTTP caching up to date, so that HTTP stays a good choice for live and fast-changing content.

## Contents

| Document | What it is |
|---|---|
| [draft-seddon-httpbis-subsecond-freshness.md](draft-seddon-httpbis-subsecond-freshness.md) | The Internet-Draft source |
| [explainer.md](explainer.md) | Deployment examples, alternatives, the implementation survey and background |
| [measurements.md](measurements.md) | Practical tests through five nginx caches and with simulated HLS players, with results |
| [precedents.md](precedents.md) | Other systems that moved to finer time resolution, with sources |
| [results/hls-2026-11-25/README.md](results/hls-2026-11-25/README.md) | Per-run summaries behind the HLS player test |
| [results/hls-2026-11-27/README.md](results/hls-2026-11-27/README.md) | The same test rerun with the later prototype revision |
| [results/layers-2026-11-27/README.md](results/layers-2026-11-27/README.md) | Rerun of the five-cache tests, with and without the cache lock |
| [rfcs/README.md](rfcs/README.md) | Text copies of the referenced RFCs and drafts, for local searching |
| [survey-notes.md](survey-notes.md) | The lines of source each survey claim rests on, quoted at pinned commits |
| [survey-notes.py](survey-notes.py) | Script that generates the survey notes from clones of the projects |
| [survey-sources.csv](survey-sources.csv) | Source files read for the implementation survey, with hashes and links |

## Prototype

The prototype is a fork of nginx. All the changes are on one branch in each repository.

| Repository | Branch | Contents |
|---|---|---|
| [randomizedcoder/nginx](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness) | `http-cache-millisecond-freshness` | The cache changes, in `src/http` |
| [randomizedcoder/nginx, `contrib/subsecond-cache`](https://github.com/randomizedcoder/nginx/tree/http-cache-millisecond-freshness/contrib/subsecond-cache) | `http-cache-millisecond-freshness` | How to build and run it, unit tests, known problems and the benchmark scripts |
| [randomizedcoder/nginx-tests](https://github.com/randomizedcoder/nginx-tests/tree/http-cache-millisecond-freshness) | `http-cache-millisecond-freshness` | Integration tests, in the `proxy_cache_fine*.t` files |

To see only the prototype's changes: [nginx compare](https://github.com/randomizedcoder/nginx/compare/master...http-cache-millisecond-freshness) · [nginx-tests compare](https://github.com/randomizedcoder/nginx-tests/compare/master...http-cache-millisecond-freshness)

## Summary

- **Problem.** HTTP expresses freshness and age in whole seconds. An origin can choose immediate staleness or a full second, with nothing in between.
- **Cause.** One grammar rule, `delta-seconds`, set by RFC 2068 in January 1997 and unchanged in RFC 9111 (2022). The limit is in the wire format, not in every implementation.
- **Since 1997.** A disk of that year took about 11 ms to reach data; a current data-centre SSD is specified at 80 µs. NFS, syslog, HLS and TLS session tickets moved to finer units. IPv6 Neighbor Discovery, server-sent events, gRPC, QUIC and Media over QUIC Transport started with them. DNS, cookies and CoAP kept seconds. Chromium has compared age in microseconds since 2008 and WebKit in floating-point seconds since 2009. An appendix of the draft has the timeline and its sources.
- **Other uses.** Live streaming is the measured case. Stock and prices in a sale, market quotations, betting odds and live scores are examples only.
- **Today.** We read the source of eleven browser engines and caches. Chromium, WebKit, Varnish and Souin already compare age with the lifetime at sub-second resolution. Two more measure age more finely and reduce it to seconds. Five use whole seconds throughout. None can be told a sub-second lifetime in a standard way, and those that emit `Age` use whole seconds; nginx emits none. [Survey](explainer.md#what-implementations-do-today)
- **Aim.** Let the wire format carry what those implementations already measure, and give the rest a defined target.
- **Proposal.** A `delta-milliseconds` sibling, used by the companions below. Each cache counts the time already spent upstream.
- **Scope.** Every whole-second duration in HTTP caching, plus Retry-After and Prefer `wait`.
- **Browsers.** No change is required. A browser applies the whole-second policy, as it does today. [Browsers](explainer.md#browsers)
- **Rollout.** Send both resolutions. Older caches use the whole-second policy. Upgraded caches require a configured supporting path and accountable elapsed time. Losing fine metadata restores the base, which can allow longer reuse. Choose that fallback deliberately.
- **Evidence.** The nginx prototype has documented conformance gaps; the measurements are implementation-specific observations, not proof of a delivery-age bound or a gain over every conforming cache. [Conformance](explainer.md#prototype-conformance) · [Provenance](measurements.md#revisions-and-retained-results)

| Existing | Companion | Used in |
|---|---|---|
| `max-age` | `max-age-ms` | Response, request |
| `s-maxage` | `s-maxage-ms` | Response |
| `stale-while-revalidate` | `stale-while-revalidate-ms` | Response |
| `stale-if-error` | `stale-if-error-ms` | Response, request |
| `max-stale` | `max-stale-ms` | Request |
| `min-fresh` | `min-fresh-ms` | Request |
| `Age` | `Age-Ms` | Response field |
| Cache-Status `ttl` | `ttl-ms` | Response parameter |
| `Retry-After` | `Retry-After-Ms` | Response field |
| Prefer `wait` | `wait-ms` | Request preference |

A shield serving a live playlist at age 175 ms of a 200 ms lifetime sends:

```http
Cache-Control: max-age=0, max-age-ms=200
Age: 0
Age-Ms: 175
```

In production we would expect a stale-while-revalidate window as well, with its own companion:

```http
Cache-Control: max-age=0, max-age-ms=200, stale-while-revalidate=0, stale-while-revalidate-ms=200
Age: 0
Age-Ms: 175
```

### Media over QUIC

- MoQ relays already cache in integer milliseconds.
- HLS and DASH over HTTP caches remain the deployed base for large live events.
- Millisecond freshness would let those services use their existing caches closer to the same timescales. We think this would keep HTTP a practical choice for latency-sensitive delivery.
- With simulated players, a 200 ms playlist lifetime found new segments as soon as `max-age=0`, for a fifth of the origin requests. Real players are still to be measured. [Test 8](measurements.md#test-8-simulated-hls-players) · [Per-run results](results/hls-2026-11-25/)

## Building the draft

The draft is written in kramdown-rfc Markdown. With Nix:

```sh
nix shell nixpkgs#rubyPackages.kramdown-rfc2629 nixpkgs#xml2rfc -c sh -c \
  'kramdown-rfc draft-seddon-httpbis-subsecond-freshness.md > draft-seddon-httpbis-subsecond-freshness.xml \
   && xml2rfc --text --html draft-seddon-httpbis-subsecond-freshness.xml'
```

The `Makefile` uses [i-d-template](https://github.com/martinthomson/i-d-template). Running `make` clones the template into `lib/` and builds the text and HTML, given `kramdown-rfc` and `xml2rfc` on the path.

## Contributing

Discussion takes place on the HTTP Working Group mailing list, `ietf-http-wg@w3.org`. Issues and pull requests are welcome in this repository.
