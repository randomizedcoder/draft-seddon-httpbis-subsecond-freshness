# Millisecond Resolution for HTTP Cache Freshness

This is the working area for the individual Internet-Draft, "Millisecond Resolution for HTTP Cache Freshness".

- [Internet-Draft source](draft-seddon-httpbis-subsecond-freshness.md)
- [Explainer with deployment examples, alternatives and background](explainer.md)

## Summary

- **Problem.** HTTP caches measure freshness in whole seconds. An origin can choose immediate staleness or a full second, with nothing in between.
- **Cause.** One grammar rule, `delta-seconds` in RFC 9111.
- **Proposal.** A `delta-milliseconds` sibling, used by the companions below. Each cache counts the time already spent upstream.
- **Rollout.** Send both resolutions. Older caches use the whole-second policy. Upgraded caches use the finer values when they can account for age since the origin or the last validation, and otherwise fall back to whole seconds.

| Existing | Companion |
|---|---|
| `max-age` | `max-age-ms` |
| `s-maxage` | `s-maxage-ms` |
| `stale-while-revalidate` | `stale-while-revalidate-ms` |
| `Age` | `Age-Ms` |

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
- The effect on players is still to be measured.

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
