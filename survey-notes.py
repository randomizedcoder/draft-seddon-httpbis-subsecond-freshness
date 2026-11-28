#!/usr/bin/env python3
"""Generate survey-notes.md from clones of the surveyed projects.

Each finding names a file and a line range.  The quoted lines are copied
from the file at the pinned commit, so a quote cannot drift from the
source.  The statements about what the lines mean are ours.

Usage:  python3 -I survey-notes.py CLONES_DIR > survey-notes.md

CLONES_DIR holds one clone per project, in the directory named below,
checked out at the commit below.  The script reads files only.  It stops
if a clone is at another commit or a line range is missing.
"""

import subprocess
import sys
import textwrap

GH = "https://github.com/{repo}/blob/{commit}/{path}#L{a}-L{b}"
GITILES = "https://chromium.googlesource.com/chromium/src/+/{commit}/{path}#{a}"

# name: (directory, commit, link template, repository, fence language)
PROJECTS = {
    "Chromium": ("chromium", "acd38aea114059ede9cbae99084b9b80c59c4ad7",
                 GITILES, "", "cpp"),
    "WebKit": ("webkit", "6d74a822d0bfbf573a552c00fddfae56fa63481e",
               GH, "WebKit/WebKit", "cpp"),
    "Firefox": ("firefox", "ac1fc4756876469bc1ea6f7e610c3c240cb14a26",
                GH, "mozilla-firefox/firefox", "cpp"),
    "Varnish Cache": ("varnish", "0038dd19804fd92cd8bd4bfe92e5a515a57d5e8e",
                      GH, "varnishcache/varnish-cache", "c"),
    "Vinyl Cache": ("vinyl", "b91c1d5df04d290b6b317365eab71f936f8467b4",
                    None, "", "c"),
    "Souin": ("souin", "2acc79712a434fdc9efea54f8b36221fac0b7957",
              GH, "darkweak/souin", "go"),
    "pquerna/cachecontrol": ("pquerna-cachecontrol",
                             "baaf0ee615291de0a8c93d784b77e9b59fdf3a84",
                             GH, "pquerna/cachecontrol", "go"),
    "Apache httpd": ("httpd", "352229d736c444313a9f84a20cce66c3e8679f59",
                     GH, "apache/httpd", "c"),
    "Envoy": ("envoy", "4bc24ca62bd084472b2a9b120a474a9816e4a25e",
              GH, "envoyproxy/envoy", "cpp"),
    "nginx": ("nginx", "e76b6746c92d8b1167f361977032d123f8f92393",
              GH, "nginx/nginx", "c"),
    "Squid": ("squid", "76d813169215a82dea60b8a0820d0b100120263e",
              GH, "squid-cache/squid", "cpp"),
    "Apache Traffic Server": ("trafficserver",
                              "b23bcc2fb20fc014a44c8973eec03226ec5a79e4",
                              GH, "apache/trafficserver", "cpp"),
    "HAProxy": ("haproxy", "c2852d5b7c27fb93abc1cfb3246e6e172481ca17",
                GH, "haproxy/haproxy", "c"),
}

NET = "net/http/http_response_headers.cc"
BLINK = "third_party/blink/renderer/platform/"
FX = "netwerk/protocol/http/"
WK = "Source/WebCore/platform/network/"
ENVOY = "source/extensions/filters/http/"

# Section: (heading, summary bullets, findings, not determined)
# Finding: (project, path, first line, last line, statement)
SECTIONS = [
    ("Chromium", [
        "Two caches. Both keep age in microseconds. They parse `max-age` "
        "differently.",
        "`max-age=0.2`: the network cache ignores the directive; the "
        "renderer's memory cache uses 0.2 s.",
    ], [
        ("Chromium", "base/time/time.h", 358, 359,
         "`base::TimeDelta` is a 64-bit count of microseconds."),
        ("Chromium", NET, 1497, 1504,
         "Network cache: age is a `TimeDelta` and includes the response "
         "delay."),
        ("Chromium", NET, 1266, 1270,
         "Network cache: the freshness test compares two `TimeDelta` "
         "values, with no rounding."),
        ("Chromium", NET, 1519, 1533,
         "Network cache: a received `Age` is whole seconds. `Age: 0.5` "
         "does not parse and is treated as absent."),
        ("Chromium", NET, 926, 938,
         "Network cache: `max-age` must be digits only, so `max-age=0.2` "
         "gives no value and the directive is ignored."),
        ("Chromium", BLINK + "loader/fetch/resource.cc", 548, 560,
         "Memory cache: age is a `TimeDelta`, with no response delay term."),
        ("Chromium", BLINK + "loader/fetch/resource.cc", 629, 633,
         "Memory cache: the freshness test."),
        ("Chromium", BLINK + "loader/fetch/resource_response.cc", 406, 410,
         "Memory cache: a received `Age` is parsed as a floating-point "
         "number, so `Age: 0.5` is used as 0.5 s."),
        ("Chromium", BLINK + "network/http_parsers.cc", 911, 920,
         "Memory cache: `max-age` is parsed as a floating-point number, "
         "so `max-age=0.2` is used as 0.2 s."),
    ], [
        "Timestamps for HTTP/2 and HTTP/3.",
        "`Age` handling outside the directories read. No code generating "
        "`Age` was found in `net/http`.",
        "After the network cache ignores `max-age`, the reading was that "
        "it falls back to `Expires` and then to a heuristic. Those lines "
        "are not quoted here.",
    ]),
    ("WebKit", [
        "Age and lifetime are `Seconds`, a double. Nothing is truncated.",
        "`max-age=0.2` is used as 0.2 s.",
        "WebKit's own cache code only.",
    ], [
        ("WebKit", "Source/WTF/wtf/Seconds.h", 217, 218,
         "`Seconds` holds a double."),
        ("WebKit", WK + "CacheValidation.cpp", 115, 126,
         "Age is computed in `Seconds` from `WallTime`, with no response "
         "delay term."),
        ("WebKit", "Source/WebCore/loader/cache/CachedResource.cpp",
         416, 416, "Memory cache: the freshness test."),
        ("WebKit", "Source/WebKit/NetworkProcess/cache/NetworkCache.cpp",
         208, 215, "Disk cache: the freshness test."),
        ("WebKit", WK + "ResourceResponseBase.cpp", 797, 801,
         "A received `Age` is parsed as a double, so `Age: 0.5` is used."),
        ("WebKit", WK + "CacheValidation.cpp", 320, 323,
         "`max-age` is parsed as a double."),
    ], [
        "The platform network libraries (CFNetwork, libsoup, curl), which "
        "have caches and `Age` handling of their own.",
        "Negative values.",
        "Timer resolution.",
        "No code generating `Age` was found in the directories read.",
    ]),
    ("Firefox", [
        "Whole seconds throughout, in `uint32_t`.",
        "`max-age=0.2`: read as 0, and every later directive in the field "
        "is dropped.",
    ], [
        ("Firefox", FX + "nsHttp.h", 411, 415,
         "The clock used is whole seconds."),
        ("Firefox", FX + "nsHttpResponseHead.cpp", 577, 579,
         "Age is computed from whole-second inputs into a `uint32_t`."),
        ("Firefox", FX + "nsHttpResponseHead.cpp", 601, 611,
         "The age arithmetic."),
        ("Firefox", FX + "nsHttp.cpp", 379, 394,
         "The freshness test is `now < expiration`. The comment above it "
         "states the resolution."),
        ("Firefox", FX + "nsHttpResponseHead.cpp", 922, 928,
         "A received `Age` goes through `atoi`, so `Age: 0.5` is 0."),
        ("Firefox", FX + "CacheControlParser.cpp", 45, 46,
         "`max-age` takes a seconds value."),
        ("Firefox", FX + "CacheControlParser.cpp", 62, 70,
         "After a directive the parser expects the end or a comma. For "
         "`max-age=0.2` the integer read stops at the point, the next "
         "character is not a comma, and the loop ends. Later directives "
         "in the field are not read."),
        ("Firefox", "xpcom/ds/Tokenizer.cpp", 504, 508,
         "The integer token ends at the first character that is not a "
         "digit."),
        ("Firefox", FX + "nsHttpResponseHead.cpp", 787, 796,
         "`stale-while-revalidate` is added to the expiration in whole "
         "seconds."),
    ], [
        "Image and script memory caches.",
        "`Age` handling elsewhere in the tree. No code generating `Age` "
        "was found in `netwerk/protocol/http`, `netwerk/base` or "
        "`netwerk/cache2`.",
        "Preferences that change the behaviour.",
    ]),
    ("Varnish Cache and Vinyl Cache", [
        "Times are doubles, the lifetime a float. The freshness test is "
        "in floating point.",
        "The `Age` sent is rounded down to whole seconds.",
        "`max-age=0.2` is read as 0, `max-age=1.5` as 1. The parser "
        "accepts the point on purpose.",
        "The GitHub repository is frozen and points to Vinyl Cache. The "
        "same lines are in both, quoted from each below. Vinyl Cache has "
        "no links here because its host did not serve a stable link to a "
        "line.",
    ], [
        ("Varnish Cache", "include/vdef.h", 272, 274,
         "The time types are doubles."),
        ("Varnish Cache", "bin/varnishd/cache/cache.h", 356, 357,
         "An object's origin time and lifetime."),
        ("Varnish Cache", "bin/varnishd/cache/cache_hash.c", 572, 572,
         "The freshness test."),
        ("Varnish Cache", "bin/varnishd/cache/cache_req_fsm.c", 169, 170,
         "The `Age` sent."),
        ("Varnish Cache", "bin/varnishd/cache/cache_rfc2616.c", 68, 85,
         "The `max-age` parser."),
        ("Vinyl Cache", "bin/vinyld/cache/cache.h", 363, 364,
         "Vinyl Cache: origin time and lifetime."),
        ("Vinyl Cache", "bin/vinyld/cache/cache_hash.c", 571, 571,
         "Vinyl Cache: the freshness test."),
        ("Vinyl Cache", "bin/vinyld/cache/cache_req_fsm.c", 169, 170,
         "Vinyl Cache: the `Age` sent."),
        ("Vinyl Cache", "bin/vinyld/cache/cache_rfc2616.c", 74, 83,
         "Vinyl Cache: the `max-age` parser."),
    ], [
        "That VCL durations take milliseconds comes from the VCL "
        "reference, `doc/sphinx/reference/vcl.rst`. It is not quoted here.",
    ]),
    ("Souin", [
        "The expiry is a stored instant with nanoseconds. The test is "
        "against that instant.",
        "The current time is the request's `Date` field when it parses, "
        "which is whole seconds.",
        "The `Age` sent is rounded up.",
        "`max-age=0.2`: the whole field fails to parse and the response "
        "is not stored.",
    ], [
        ("Souin", "pkg/rfc/cache_status.go", 25, 27,
         "The expiry is stored with nanoseconds."),
        ("Souin", "pkg/rfc/cache_status.go", 40, 44,
         "The freshness test."),
        ("Souin", "context/now.go", 25, 30,
         "Where the current time comes from."),
        ("Souin", "pkg/rfc/cache_status.go", 155, 157,
         "The `Age` sent."),
        ("pquerna/cachecontrol", "cacheobject/directive.go", 139, 140,
         "The parser, in `pquerna/cachecontrol` v0.2.0, takes an unsigned "
         "integer."),
        ("pquerna/cachecontrol", "cacheobject/directive.go", 536, 537,
         "It is used for the response `max-age`."),
        ("Souin", "pkg/middleware/middleware.go", 498, 503,
         "A field that fails to parse: the response is not stored."),
    ], [
        "The storage back ends.",
    ]),
    ("Apache httpd mod_cache", [
        "Age is measured in microseconds and returned in whole seconds.",
        "The test is \"age less than lifetime\" in integer seconds. With a "
        "whole-second lifetime N, floor(age) < N is the same as age < N, "
        "so the outcome for `max-age` is exact.",
        "`max-age=0.2`: the directive is ignored.",
    ], [
        ("Apache httpd", "modules/cache/cache_util.c", 246, 257,
         "Age, in `apr_time_t` microseconds, returned through "
         "`apr_time_sec`."),
        ("Apache httpd", "modules/cache/cache_util.c", 697, 698,
         "The freshness test."),
        ("Apache httpd", "modules/cache/cache_util.c", 1091, 1096,
         "The parser requires the number to end the argument (`!*endp`)."),
    ], []),
    ("Envoy cache filters", [
        "Age is computed in the system clock's duration, then cast to "
        "seconds.",
        "A response is stale once the cast age exceeds the lifetime, so "
        "it is fresh for up to one second longer than the lifetime.",
        "`max-age=0.2`: the directive is ignored.",
        "The `cache` and `cache_v2` filters have the same lines.",
    ], [
        ("Envoy", ENVOY + "cache/cache_headers_utils.cc", 233, 245,
         "`cache`: age."),
        ("Envoy", ENVOY + "cache/http_cache.cc", 112, 112,
         "`cache`: the freshness test."),
        ("Envoy", ENVOY + "cache/cache_headers_utils.cc", 35, 39,
         "`cache`: the parser. `SimpleAtoi` fails on `0.2`."),
        ("Envoy", ENVOY + "cache_v2/cache_headers_utils.cc", 283, 283,
         "`cache_v2`: age."),
        ("Envoy", ENVOY + "cache_v2/cache_sessions.cc", 91, 91,
         "`cache_v2`: the freshness test."),
        ("Envoy", ENVOY + "cache_v2/cache_headers_utils.cc", 56, 56,
         "`cache_v2`: the parser."),
    ], [
        "The storage back ends.",
        "The reading was that the `Age` sent is the truncated age, and "
        "that a response whose `max-age` was ignored is cacheable only "
        "with `no-cache` or with `Date` and `Expires`. Those lines are "
        "not quoted here.",
    ]),
    ("nginx", [
        "Whole seconds, in `time_t`.",
        "No `Age` is generated or read.",
        "`max-age=0.2`: the response is not cacheable.",
    ], [
        ("nginx", "src/http/ngx_http_file_cache.c", 656, 658,
         "The freshness test."),
        ("nginx", "src/http/ngx_http_upstream.c", 5152, 5158,
         "A value that fails to parse makes the response uncacheable."),
        ("nginx", "src/http/ngx_http_upstream.c", 5218, 5225,
         "The parser fails on any character other than a digit or a "
         "separator."),
    ], []),
    ("Squid", [
        "Whole seconds, in `time_t`.",
        "The `Age` sent is whole seconds.",
        "`max-age=0.2` is read as 0.",
        "No `stale-while-revalidate` was found.",
    ], [
        ("Squid", "src/time/gadgets.cc", 28, 33,
         "The clock used for cache decisions, `squid_curtime`, is whole "
         "seconds."),
        ("Squid", "src/refresh.cc", 143, 148,
         "The freshness test for an explicit expiry."),
        ("Squid", "src/client_side_reply.cc", 1286, 1288,
         "The `Age` sent."),
        ("Squid", "src/HttpHeaderTools.cc", 84, 94,
         "The integer parser is `atoi`, which stops at the point."),
        ("Squid", "src/HttpHdrCc.cc", 152, 153,
         "It is used for `max-age`."),
    ], []),
    ("Apache Traffic Server", [
        "Whole seconds, in `time_t`.",
        "`max-age=0.2`: the text left over after the number makes the "
        "parser clear the directive, so it is ignored, not truncated.",
    ], [
        ("Apache Traffic Server", "src/proxy/http/HttpTransact.cc",
         8898, 8902, "The clock used is whole seconds."),
        ("Apache Traffic Server", "src/proxy/http/HttpTransact.cc",
         8067, 8071, "The freshness test."),
        ("Apache Traffic Server", "src/proxy/hdrs/MIME.cc", 4049, 4070,
         "Content left after a directive clears that directive."),
    ], [
        "The reading was that the `Age` sent is whole seconds. Those "
        "lines are not quoted here.",
    ]),
    ("HAProxy cache", [
        "Whole seconds.",
        "`max-age=0.2` is read as 0 by `strtol`, and a response with a "
        "lifetime of zero is not stored.",
    ], [
        ("HAProxy", "src/cache.c", 1109, 1111, "The parser."),
        ("HAProxy", "src/cache.c", 1866, 1868,
         "A lifetime of zero or less is not stored."),
        ("HAProxy", "src/cache.c", 1946, 1947,
         "The expiry is a whole second."),
        ("HAProxy", "src/cache.c", 2779, 2779, "The freshness test."),
        ("HAProxy", "src/cache.c", 2258, 2258, "The `Age` sent."),
    ], [
        "The reading was that a response received with `Age: 0.5` is not "
        "stored. Those lines are not quoted here.",
    ]),
]

INTRO = """\
# Implementation survey: reading notes

These notes back the survey table in the draft and in
[explainer.md](explainer.md#what-implementations-do-today). They show,
for each implementation, the lines the claims rest on.

## How the reading was done

- **Pinned.** Each project was cloned on 27 November 2026 and read at
  the commit in the table below.
- **Read, not run.** Nothing was built or executed. Outcomes such as
  "`max-age=0.2` is read as 0" were traced through the parser by hand.
  Where the last step is a library function, such as `strtol`, `atoi` or
  `strconv.ParseUint`, its documented behaviour is assumed.
- **Assisted.** The reading was done with an AI coding assistant, then
  each cited line was compared with the file.
- **Quotes are exact.** This page is generated by
  [survey-notes.py](survey-notes.py), which copies each quoted range
  from the file at the pinned commit. The sentence above each quote is
  our reading of it, and that is the part that can be wrong.
- **One revision each.** Released versions may differ.

Three questions were asked of each implementation:

1. In what unit is the age of a stored response measured?
2. In what unit is the age compared with the freshness lifetime?
3. What happens to `Cache-Control: max-age=0.2`, and to a received
   `Age: 0.5`?

Corrections are welcome, as an issue or a pull request, most of all from
people who work on these projects.

## To check a quote

Follow the link, or with a clone:

```sh
git -C <clone> checkout <commit>
sed -n '<first>,<last>p' <clone>/<path>
```

To regenerate this page: `python3 -I survey-notes.py <clones directory>
> survey-notes.md`. The SHA-256 of each file read is in
[survey-sources.csv](survey-sources.csv).

## Commits
"""


def fail(message):
    sys.exit("survey-notes.py: " + message)


def head(directory):
    out = subprocess.run(
        ["git", "-C", directory, "log", "-1", "--format=%H %cs"],
        capture_output=True, text=True, check=True)
    return out.stdout.split()


def quote(root, finding):
    project, path, first, last, statement = finding
    directory, commit, template, repo, language = PROJECTS[project]
    with open(f"{root}/{directory}/{path}", encoding="utf-8") as f:
        lines = f.read().split("\n")
    if last > len(lines) or first < 1 or first > last:
        fail(f"{project} {path}:{first}-{last} is outside the file")
    text = textwrap.dedent(
        "\n".join(lines[first - 1:last]).expandtabs(8)).rstrip()
    if not text.strip():
        fail(f"{project} {path}:{first}-{last} is empty")
    name = path.rsplit("/", 1)[-1]
    where = f"{name}:{first}" if first == last else f"{name}:{first}-{last}"
    if template:
        url = template.format(repo=repo, commit=commit, path=path,
                              a=first, b=last)
        where = f"[`{where}`]({url})"
    else:
        where = f"`{path}:{first}-{last}`"
    return f"{statement} {where}\n\n```{language}\n{text}\n```\n"


def main():
    if len(sys.argv) != 2:
        fail("usage: survey-notes.py CLONES_DIR")
    root = sys.argv[1].rstrip("/")
    out = [INTRO]
    out.append("| Project | Commit | Commit date |")
    out.append("|---|---|---|")
    for project, (directory, commit, *_rest) in PROJECTS.items():
        found, date = head(f"{root}/{directory}")
        if found != commit:
            fail(f"{project}: clone is at {found}, expected {commit}")
        out.append(f"| {project} | `{commit}` | {date} |")
    out.append("")
    for heading, summary, findings, open_items in SECTIONS:
        out.append(f"## {heading}\n")
        out.extend(f"- {line}" for line in summary)
        out.append("")
        out.extend(quote(root, finding) for finding in findings)
        if open_items:
            out.append("Not determined, or not quoted:\n")
            out.extend(f"- {line}" for line in open_items)
            out.append("")
    print("\n".join(out).rstrip())


if __name__ == "__main__":
    main()
