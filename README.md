# Millisecond Resolution for HTTP Cache Freshness

This is the working area for the individual Internet-Draft, "Millisecond Resolution for HTTP Cache Freshness".

- [Internet-Draft source](draft-seddon-httpbis-subsecond-freshness.md)
- [Explainer with deployment examples, alternatives and background](explainer.md)

## Summary

HTTP caches measure freshness in whole seconds. An origin can choose immediate staleness or a full second, with nothing in between. We propose letting an origin set a freshness lifetime in milliseconds and having each cache count the time already spent upstream. For example, a shield serving a live playlist at age 175 ms could report how much of a 200 ms lifetime has elapsed. The same format can express a lifetime of 1.25 seconds.

The whole-second limit comes from one grammar rule, `delta-seconds` in RFC 9111. We propose a `delta-milliseconds` sibling and use it for companions to `max-age`, `s-maxage` and `stale-while-revalidate` in `Cache-Control` or `CDN-Cache-Control`, plus an `Age-Ms` response field.

During rollout, send both resolutions. Older caches use the whole-second policy. Upgraded caches use the finer values when they can account for age from the origin or last validation. An older cache can replay an outdated fine age, so an upgraded cache on an unknown path uses the whole-second fallback.

Media over QUIC is attracting much of the current interest in low-latency live delivery, and its relays already cache in integer milliseconds. HLS and DASH over HTTP caches remain the deployed base for large live events. Millisecond freshness would let those services use their existing caches closer to the same timescales, which we think would keep HTTP a practical choice for latency-sensitive delivery. The effect on players is still to be measured.

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
