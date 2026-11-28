# Millisecond Resolution for HTTP Durations

This is the working area for the individual Internet-Draft, "Millisecond Resolution for HTTP Durations".

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
- **Cause.** One grammar rule, `delta-seconds` in RFC 9111. The limit is in the wire format, not in every implementation.
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
