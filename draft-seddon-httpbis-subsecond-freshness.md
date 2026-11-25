---
title: "Millisecond Resolution for HTTP Durations"
abbrev: "Millisecond HTTP Durations"
category: std

docname: draft-seddon-httpbis-subsecond-freshness-latest
submissiontype: IETF
number:
date:
consensus: true
v: 3
area: "Web and Internet Transport"
workgroup: "HTTP"
keyword:
 - caching
 - freshness
 - max-age
 - Age
 - milliseconds
venue:
  group: "HTTP"
  type: "Working Group"
  mail: "ietf-http-wg@w3.org"
  arch: "https://lists.w3.org/Archives/Public/ietf-http-wg/"
  github: "randomizedcoder/draft-seddon-httpbis-subsecond-freshness"

author:
 -
    fullname: Dave Seddon
    email: dave.seddon.ca@gmail.com

normative:
  RFC5861:
  RFC7240:
  RFC9110:
  RFC9111:
  RFC9213:
  RFC9651:

informative:
  RFC8216:
  RFC9000:
  RFC9211:
  I-D.ietf-moq-transport:
  WG2011:
    title: "Re: #282: Recommend minimum sizes for protocol elements"
    author:
      - name: Mark Nottingham
    target: https://lists.w3.org/Archives/Public/ietf-http-wg/2011AprJun/0480.html
    date: 2011-06-27
    refcontent: "Message to the ietf-http-wg mailing list"

--- abstract

HTTP caches express freshness lifetimes and response age in whole seconds.
An origin server can therefore ask for a response to be reused for zero
seconds or for one second, with nothing in between. This document defines
millisecond companions for the cache directives that carry a duration, for
the Age response header field and for the ttl parameter of Cache-Status. It
also defines companions for the Retry-After header field and the wait
preference. Each companion is sent together with its whole-second
counterpart, so that implementations which do not support this
specification continue to operate as they do today.

--- middle

# Introduction

HTTP caching {{RFC9111}} measures time in whole seconds. Freshness lifetimes,
the Age header field and the stale-while-revalidate window {{RFC5861}} all
use the delta-seconds rule ({{Section 1.2.2 of RFC9111}}). The smallest
non-zero freshness lifetime is one second.

Some resources change more often than that. A live HTTP Live Streaming media
playlist {{RFC8216}} can change every second or two, and a player that
receives an outdated playlist waits another reload interval before it
discovers a new segment. An origin server that wants its caches to absorb
request load for such a resource has to choose between immediate staleness and a
lifetime comparable to the interval at which the resource changes.

HTTP already accounts for upstream age and request delay across cache tiers
({{Section 4.2.3 of RFC9111}}); it does not grant a new lifetime at each
tier. However, a whole-second Age value can lose the fractional part of an
age estimate. A cache reporting an estimated age of 900 milliseconds as
`Age: 0` cannot communicate those 900 milliseconds to the next cache.
Repeated loss of precision can understate age along a path, depending on
the clocks and age calculations in use. This document provides a way to
carry that precision between independently implemented caches.

Machine-driven clients, including agents that retrieve changing resources
for language-model applications, can have the same need when many requests
share a cacheable representation. This is a possible additional use case,
not evidence of a measured benefit. Finer freshness does not make a response
cacheable, change its cache key or authorise sharing private responses.

This document defines a millisecond companion for each of the following:

| Whole seconds          | Milliseconds              | Used in             | Defined in     |
|------------------------|---------------------------|---------------------|----------------|
| delta-seconds rule     | delta-milliseconds rule   | grammar             | {{delta-ms}}   |
| max-age                | max-age-ms                | response, request   | {{directives}} |
| s-maxage               | s-maxage-ms               | response            | {{directives}} |
| stale-while-revalidate | stale-while-revalidate-ms | response            | {{directives}} |
| stale-if-error         | stale-if-error-ms         | response, request   | {{directives}} |
| max-stale              | max-stale-ms              | request             | {{directives}} |
| min-fresh              | min-fresh-ms              | request             | {{directives}} |
| Age                    | Age-Ms                    | response            | {{age-ms}}     |
| Cache-Status ttl       | ttl-ms                    | response            | {{ttl-ms}}     |
| Retry-After            | Retry-After-Ms            | response            | {{retry}}      |
| Prefer wait            | wait-ms                   | request             | {{wait}}       |

For example, a cache that has held a response for 175 milliseconds of a
200 millisecond lifetime sends:

~~~ http-message
Cache-Control: max-age=0, max-age-ms=200
Age: 0
Age-Ms: 175
~~~

A downstream cache that implements this specification, and that is
configured to rely on the sender's Age-Ms value, has at most 25 milliseconds
of freshness remaining before accounting for its request delay and local
residence. Any other cache applies `max-age=0`.

Finer resolution was raised in the HTTP Working Group in 2011, for sites
that cache content for a couple of seconds. The response observed that a
Cache-Control extension could provide higher precision, that such short
lifetimes had been useful mainly in controlled deployments, and that the
Date header field has a resolution of one second {{WG2011}}. This document
takes the extension approach.

Protocols used for live media have since adopted millisecond units. Media
over QUIC Transport expresses the time an object can be served from a
relay's cache in milliseconds {{I-D.ietf-moq-transport}}, and QUIC
expresses its idle timeout in milliseconds ({{Section 18.2 of RFC9000}}).

This document does not change the behaviour of implementations that do not
support it. It covers every duration defined by {{RFC9111}}, {{RFC5861}} and
{{RFC9211}}. Retry-After and the wait preference are not part of caching.
They are included in {{non-cache}} so that the whole-second durations of
HTTP can be considered together, and that section can be separated if the
Working Group prefers. {{other}} lists the time-related fields that this
document leaves unchanged.

## Requirements Language

{::boilerplate bcp14-tagged}

## Notational Conventions

This document uses ABNF as defined in {{!RFC5234}}. It uses the following
terms from other specifications: "cache", "shared cache", "fresh", "stale",
"freshness lifetime" and "validation" from {{RFC9111}}, and "origin server"
from {{RFC9110}}.

The following terms are defined by this document:

implementing cache:
: A cache that implements this specification.

legacy cache:
: A cache that does not implement this specification.

base directive:
: One of the max-age, s-maxage, stale-while-revalidate or stale-if-error
  response directives, or the max-age, max-stale, min-fresh or
  stale-if-error request directives.

fine directive:
: A directive whose name is that of a base directive followed by "-ms".
  Each fine directive is the companion of the base directive whose name it
  extends, in the same kind of message.

fine age:
: An estimate of a response's age with millisecond resolution, established
  as described in {{fine-age}}.

# Delta Milliseconds {#delta-ms}

The delta-milliseconds rule specifies a non-negative integer, representing
time in milliseconds.

~~~ abnf
delta-milliseconds = 1*15DIGIT
~~~

The limit of fifteen digits matches the range of a Structured Fields
Integer ({{Section 3.3.1 of RFC9651}}), so that the same value can be
carried in a Cache-Control directive, in a targeted cache control field
{{RFC9213}} and in the Age-Ms field. The largest value is a little over
31,000 years.

One millisecond is the finest decimal unit in which the whole delta-seconds
range fits within that limit. The 2^31 seconds at which
{{Section 1.2.2 of RFC9111}} saturates is 2,147,483,648,000 milliseconds,
which has thirteen digits. Fifteen digits of microseconds cover less than
32 years, and fifteen digits of nanoseconds less than 12 days. A companion
in a finer unit could therefore not express every value of its base as a
Structured Fields Integer.

A recipient parsing a delta-milliseconds value and converting it to binary
form needs an arithmetic type of at least 50 bits of non-negative integer
range. Note that this is wider than the 31 bits suggested for delta-seconds
in {{Section 1.2.2 of RFC9111}}. A 31-bit count of milliseconds overflows
in less than 25 days.

Parsing a value successfully does not imply that it can be converted to a
platform's timer unit without overflow. Implementations need checked
arithmetic when adding durations or converting them to finer units. A
timer's range must not cause an age to wrap to a smaller value, a freshness
lifetime or stale window to increase, or a retry delay to become shorter.
The wire range is independent of an implementation's timer resolution.

A value that does not match the delta-milliseconds rule is invalid. This
includes a value with:

- a sign;
- a fraction;
- a unit suffix; or
- more than fifteen digits.

The consequences of an invalid value are specified where the rule is used.
This differs from delta-seconds, where a value that is too large is treated
as 2^31 seconds. A delta-milliseconds value is always accompanied by a
whole-second value that the recipient can use instead.

# Fine Cache Directives {#directives}

Each fine directive takes an argument that uses the token form of the
delta-milliseconds rule. A sender MUST NOT generate the quoted-string form.
A recipient treats an argument in the quoted-string form as not matching
the rule. This differs from the advice for existing directives in
{{Section 5.2 of RFC9111}}. The base directive is always available, so a
recipient needs only one form.

A recipient MUST compare the complete directive name. Directive names in
Cache-Control are case-insensitive ({{Section 5.2 of RFC9111}}), so
`MAX-AGE-MS=200` is the max-age-ms directive. A name that only begins with,
or contains, a name defined here is a different directive: `max-age-msx`
is not max-age-ms, and max-age-ms is never read as max-age. The names of
the Age-Ms and Retry-After-Ms fields are case-insensitive, as are all field
names ({{Section 5.1 of RFC9110}}), and so is the wait-ms preference
({{Section 2 of RFC7240}}). Structured Fields keys are lower case only
{{RFC9651}}. That applies to a fine directive in a targeted field
({{targeted}}) and to the ttl-ms parameter: a key in another case causes
the field to fail to parse, and a recipient then ignores the whole field.

A fine directive gives a complete duration. It is not added to the value of
its base directive. For example, `max-age=1, max-age-ms=1250` describes a
freshness lifetime of 1.25 seconds for an implementing cache and of one
second for a legacy cache.

These directives are behavioural extensions in the sense of
{{Section 5.2.3 of RFC9111}}. Each modifies a base directive that is sent
alongside it. A legacy cache ignores the fine directive and applies the
base directive.

{{response-directives}} defines the response directives and
{{request-directives}} the request directives. The requirements of
{{pairing}} apply to both.

## Response Directives {#response-directives}

### max-age-ms

Argument syntax:

: delta-milliseconds (see {{delta-ms}})

The max-age-ms response directive indicates that the response is to be
considered stale after its age is greater than or equal to the specified
number of milliseconds. It is the companion of the max-age response
directive ({{Section 5.2.2.1 of RFC9111}}).

### s-maxage-ms

Argument syntax:

: delta-milliseconds (see {{delta-ms}})

The s-maxage-ms response directive indicates that, for a shared cache, the
specified number of milliseconds overrides the freshness lifetime given by
max-age, max-age-ms or the Expires header field. It is the companion of the
s-maxage response directive ({{Section 5.2.2.10 of RFC9111}}).

The s-maxage-ms directive does not alter the other effects of s-maxage. In
particular, a response containing s-maxage is still subject to the
requirements of the proxy-revalidate response directive, so a shared cache
cannot serve it stale.

### stale-while-revalidate-ms

Argument syntax:

: delta-milliseconds (see {{delta-ms}})

The stale-while-revalidate-ms response directive indicates that a cache MAY
serve the response in which it appears after it becomes stale, up to the
specified number of milliseconds, under the conditions given in
{{Section 3 of RFC5861}}. It is the companion of the stale-while-revalidate
response directive.

### stale-if-error-ms {#sie}

Argument syntax:

: delta-milliseconds (see {{delta-ms}})

The stale-if-error-ms response directive indicates that, when an error is
encountered, a cache MAY use the stale response in which it appears to
satisfy a request, until the response has been stale for the specified
number of milliseconds, under the conditions given in
{{Section 4 of RFC5861}}. It is the companion of the stale-if-error
response directive.

## Request Directives {#request-directives}

Each of the following request directives takes a delta-milliseconds
argument ({{delta-ms}}). Each has the meaning of its base directive, with
the duration in milliseconds.

max-age-ms:
: The client prefers a response whose age is less than or equal to the
  specified number of milliseconds. Companion of max-age
  ({{Section 5.2.1.1 of RFC9111}}).

max-stale-ms:
: The client will accept a response that has exceeded its freshness
  lifetime by no more than the specified number of milliseconds. Companion
  of max-stale ({{Section 5.2.1.2 of RFC9111}}).

min-fresh-ms:
: The client prefers a response that will still be fresh for at least the
  specified number of milliseconds. Companion of min-fresh
  ({{Section 5.2.1.3 of RFC9111}}).

stale-if-error-ms:
: The client will accept a stale response when an error is encountered,
  until the response has been stale for the specified number of
  milliseconds. Companion of stale-if-error ({{Section 4 of RFC5861}}).

A max-stale directive without an argument accepts a stale response of any
age. A max-stale-ms directive that accompanies it has no effect.

An implementing cache applies a fine request directive to a stored response
for which it has a fine age ({{fine-age}}). For any other stored response
it applies the base directive.

A cache that forwards a request forwards its fine directives together with
their base directives.

## Pairing {#pairing}

A sender that generates a fine directive MUST also generate its base
directive, with an argument, in the same field. The base directive is the
policy that the sender accepts from every cache that does not use the fine
directive. The
two values are otherwise independent. {{base-policy}} discusses the choice
of base value.

An implementing cache MUST ignore a fine directive when any of the
following is true:

- its base directive is absent from the same field, or is present with an
  invalid value;
- its argument does not match the delta-milliseconds rule;
- it appears more than once in the field; or
- the cache has no fine age for the response, or for the stored response
  being considered for a request ({{fine-age}}).

A cache that ignores a fine directive applies the remaining directives as
specified in {{RFC9111}} and {{RFC5861}}. Ignoring a fine directive never
causes its base directive to be ignored.

Ignoring a fine directive restores the base policy. It does not necessarily
reduce the permitted duration: `max-age=60, max-age-ms=200` permits 60
seconds wherever the fine directive is not used. A sender MUST select base
directives that it accepts whenever the fine directive or a fine age is
unavailable. This includes the loss or rejection of the fields defined in
this document at an intermediary.

A fine directive does not relax any other directive. The no-store, no-cache,
private, must-revalidate, proxy-revalidate and must-understand response
directives have the effects specified in {{RFC9111}} whether or not a fine
directive is present.

## Targeted Cache Control {#targeted}

The fine response directives can be used in targeted cache control fields
{{RFC9213}}, such as CDN-Cache-Control. In such a field a fine directive is
a Dictionary member whose value is an Integer. A member with any other
type, or with a negative value, is invalid and is ignored as described in
{{pairing}}. Parameters on the member are ignored.

When a cache selects a targeted field as described in
{{Section 2.2 of RFC9213}}, the pairing requirements apply within that
field. A fine directive in a targeted field is not paired with a base
directive in Cache-Control, or the reverse.

The following response gives a CDN that implements this specification 200
milliseconds of freshness followed by a further 200 milliseconds in which
it can serve the stale response while it revalidates. A CDN that does not
implement this specification gets no freshness and no stale window. Other
caches apply the Cache-Control field.

~~~ http-message
Cache-Control: max-age=0
CDN-Cache-Control: max-age=0, max-age-ms=200,
    stale-while-revalidate=0, stale-while-revalidate-ms=200
~~~

Note that max-age is used in the targeted field in this example. An
s-maxage directive would prohibit the CDN from serving the stale response.

# The Age-Ms Response Header Field {#age-ms}

The Age-Ms response header field conveys the sender's estimate of the time
since the response was generated or successfully validated at the origin
server, in milliseconds. It is the companion of the Age header field
({{Section 5.1 of RFC9111}}).

Age-Ms is an Item Structured Header Field {{RFC9651}}. Its value MUST be an
Integer, and the value MUST be non-negative. Such a value matches the
delta-milliseconds rule ({{delta-ms}}).

~~~ http-message
Age: 1
Age-Ms: 1075
~~~

Age-Ms carries the whole of the estimated age. It is not a fraction to be
added to the Age field value.

## Generating Age-Ms {#generate}

An implementing cache that generates an Age header field, as required by
{{Section 4 of RFC9111}}, SHOULD also generate an Age-Ms header field when
it has a fine age for the response. It MUST NOT generate Age-Ms when it has
no fine age.

When a cache generates both fields, it MUST derive them from the same age
estimate, so that the Age field value is equal to the Age-Ms field value
divided by 1000 and rounded down. A cache MUST NOT generate Age-Ms without
also generating Age.

These requirements apply to every response in which the cache generates an
Age header field. That includes a 304 (Not Modified) response that the
cache generates from a stored response.

An implementing cache that forwards a response without serving it from
storage, and has a fine age for it, SHOULD likewise generate both fields.
A downstream cache obtains no fine age from a cache's response that lacks
them ({{receive}}).

A cache MAY omit Age-Ms, for example where downstream recipients do not
need fine age ({{security}}). A downstream cache then applies the base
directives. A cache that reports a coarser age than it holds MUST round the
age up, and MUST derive Age and Age-Ms from the same rounded estimate. For
example, an age of 999 milliseconds rounded up to a 10 millisecond step is
sent as `Age-Ms: 1000` with `Age: 1`.

An origin server does not generate Age-Ms.

## Receiving Age-Ms {#receive}

A legacy cache that serves a stored response replaces the Age field with
its own estimate, but it forwards an Age-Ms field that it stored along with
the response unchanged. The Age-Ms value then understates the age of the
response. A recipient cannot detect this from the message, because such a
pair of values can be consistent.

For that reason, an implementing cache MUST NOT use a received Age-Ms field
unless it has been configured to treat the sender of the response as a
fine-age source. A fine-age source is an origin server, or an implementing
cache whose own responses come only from fine-age sources. This is a
property of the path between the cache and the origin server. It is
established by configuration, for example between the tiers of a content
delivery network under common administration. This document defines no
mechanism to discover it.

The configuration MUST cover the complete path that serves the response
back to the origin server. That includes every cache or intermediary that
can retain or rewrite age metadata, and any alternative path used after a
failover. The consistency of Age and Age-Ms does not establish that this
condition holds, and neither does a secured connection to the sender. An
implementing cache MUST NOT rely on fine age for a path whose accounting
properties are unknown.

The configuration also identifies whether the sender is an origin server
or an implementing cache. When a response is received from a fine-age
source, the cache determines a fine age_value as follows:

1. If the sender is an origin server and the response contains neither an
   Age nor an Age-Ms field, the fine age_value is zero.

2. If the sender is an implementing cache, the response contains exactly
   one Age field line and exactly one Age-Ms field line, both are valid,
   and the Age value is equal to the Age-Ms value divided by 1000 and
   rounded down, the fine age_value is the Age-Ms value.

3. Otherwise, the response has no fine age_value.

The zero value in the first case relies on the configuration: the response
was generated or successfully validated at the origin server for this
exchange. The absence of the fields does not establish that by itself, so
a response without them from an implementing cache has no fine age_value.
This document does not authenticate the time of generation or validation.

A recipient applies the second case to the complete field values as
received, before any recovery that discards additional Age members
({{Section 5.1 of RFC9111}}). When the response has no fine age_value,
that recovery remains available for the Age field.

When a response is received from any other sender, or has no fine
age_value, the cache has no fine age for that response. It processes the
response as specified in {{RFC9111}}, using the Age field alone.

An implementing cache MUST NOT forward, or store for later forwarding, an
Age-Ms field that it has not used as the fine age_value. This prevents an
unreliable value from reaching a downstream cache that would rely on it.

# The ttl-ms Cache-Status Parameter {#ttl-ms}

The ttl-ms parameter of the Cache-Status header field {{RFC9211}} conveys
the response's remaining freshness lifetime as calculated by the cache, in
milliseconds. It is the companion of the ttl parameter
({{Section 2.4 of RFC9211}}). Its value is an Integer. It can be negative,
to indicate staleness.

~~~ http-message
Cache-Status: ExampleCache; hit; ttl=0; ttl-ms=25
~~~

A cache MAY generate ttl-ms when it has a fine age for the response
({{fine-age}}). It MUST NOT generate ttl-ms otherwise. A cache that
generates ttl-ms MUST also generate ttl in the same list member, and
derives both from the same calculation.

The ttl value MUST equal the ttl-ms value divided by 1000 and rounded
towards negative infinity. For example, `ttl-ms=-1` is accompanied by
`ttl=-1`, and `ttl-ms=25` is accompanied by `ttl=0`.

Like the other Cache-Status parameters, ttl-ms describes how a cache
handled a request. A recipient does not use it to calculate freshness.

# Cache Operation {#operation}

## Establishing a Fine Age {#fine-age}

A cache has a fine age for a stored response when:

- it obtained a fine age_value for the response ({{receive}}); and
- it can account for the elapsed time since the corresponding request
  without interruption, using the rounding rule below when its clock has
  a resolution coarser than one millisecond.

The fine age is calculated as described in {{Section 4.2.3 of RFC9111}},
with all quantities in milliseconds:

~~~
response_delay      = response_time - request_time
corrected_age_value = age_value + response_delay
resident_time       = now - response_time
current_age         = corrected_age_value + resident_time
~~~

The apparent_age calculation of {{Section 4.2.3 of RFC9111}} relies on the
Date header field, which has a resolution of one second. A cache MAY omit
it when calculating a fine age for a response from a fine-age source.

A cache SHOULD use a monotonic clock to measure response_delay and
resident_time. The accounting MUST include time during which the cache was
not running or the system was suspended; a clock being monotonic does not
establish that it counts that time. If an event makes the accounting
uncertain, the cache MUST cease to rely on the affected fine age. A stored
response does not gain freshness as a result of such an event. In
particular:

- A gradual adjustment to the rate of a clock (a slew) preserves elapsed
  time and does not affect the fine age.
- A discontinuous change to a clock (a step) loses the fine age of every
  response whose elapsed time was measured with that clock.
- A restart loses the fine age unless the cache has recorded enough to
  account for the time it was not running.
- A restore of older clock or cache state, such as a virtual machine
  snapshot, loses the fine age of the affected responses.

A cache whose clock has a coarser resolution than one millisecond MUST
round each age up, and each lifetime and stale window down, to that
resolution. This is consistent with the treatment of Expires in
{{Section 4.2 of RFC9111}}.

## Calculating Freshness {#freshness}

An implementing cache that has a fine age for a response determines the
freshness lifetime by using the first match of:

1. If the cache is shared and the s-maxage response directive is present,
   the value of a paired s-maxage-ms directive if there is one, and
   otherwise the value of s-maxage.

2. If the max-age response directive is present, the value of a paired
   max-age-ms directive if there is one, and otherwise the value of
   max-age.

3. The remaining rules of {{Section 4.2.1 of RFC9111}}.

"Paired" here means that the fine directive is not ignored under
{{pairing}}. A lifetime that is expressed in seconds is converted to
milliseconds for the comparison.

The response is fresh when the freshness lifetime is greater than the fine
age. A response with a lifetime of 200 milliseconds is fresh at an age of
199 milliseconds and stale at 200 milliseconds.

A cache that has no fine age for a response uses {{RFC9111}} unchanged.

## Serving Stale Responses {#stale}

An implementing cache that has a fine age for a response, and that finds a
paired stale-while-revalidate-ms directive, uses its value in place of the
value of stale-while-revalidate. The window begins when the response
becomes stale, however its freshness lifetime was determined. A response
with a lifetime of 200 milliseconds and a window of 200 milliseconds can be
served stale at an age of 399 milliseconds and cannot at 400 milliseconds.

A validation that is still in progress when the window ends does not extend
it.

A paired stale-if-error-ms directive, in the response or in the request, is
used in the same way in place of the value of stale-if-error. Its window
also begins when the response becomes stale, and is independent of the
stale-while-revalidate window.

## Applying Request Directives {#apply-request}

An implementing cache that has a fine age for a stored response evaluates
the request directives of {{Section 5.2.1 of RFC9111}} in milliseconds. It
uses the value of each paired fine request directive in place of the value
of its base directive. A value expressed in seconds, whether from a request
directive or from the response, is converted to milliseconds.

For example, a stored response with a freshness lifetime of 2000
milliseconds and a fine age of 1600 milliseconds satisfies
`max-age=1, max-age-ms=1750`. It does not satisfy
`min-fresh=0, min-fresh-ms=500`, because it will be fresh for only another
400 milliseconds.

## Validation {#validation}

When a stored response is updated by a 304 (Not Modified) response
({{Section 4.3.4 of RFC9111}}), the cache establishes a new fine age from
the validation exchange as described in {{receive}} and {{fine-age}}. The
previous fine age is discarded.

The fine directives that apply afterwards are those in the updated stored
response. If the 304 response replaces a field that carried a fine
directive with one that does not, the fine directive no longer applies.

# Durations Outside Caching {#non-cache}

The companions in this section do not depend on the rest of this document,
apart from the delta-milliseconds rule.

## The Retry-After-Ms Response Header Field {#retry}

The Retry-After-Ms response header field indicates how long the user agent
ought to wait before making a follow-up request, in milliseconds, measured
from when the response is received. It is the companion of the Retry-After
header field ({{Section 10.2.3 of RFC9110}}).

Retry-After-Ms is an Item Structured Header Field {{RFC9651}}. Its value
MUST be an Integer, and the value MUST be non-negative.

~~~ http-message
Retry-After: 1
Retry-After-Ms: 250
~~~

A server that generates Retry-After-Ms MUST also generate Retry-After. A
recipient that does not implement this specification uses Retry-After
alone. A server SHOULD therefore choose a Retry-After value that is not
earlier than the time indicated by Retry-After-Ms, so that no recipient
retries sooner than the server intends.

A recipient that implements this specification uses a valid Retry-After-Ms
value in place of the Retry-After value. It MUST ignore Retry-After-Ms when
the Retry-After field is absent or invalid.

A recipient MUST also ignore Retry-After-Ms if either field occurs on more
than one field line, or its combined value is not a valid non-negative Integer
Item. Unrecognised Item parameters are ignored. Header field order does
not affect the selection; the recipient evaluates the pair after receiving
the header section for that response. A pair from an informational response,
a redirect or a previous request is not a pair for a later response.

Retry-After-Ms does not require a follow-up request or authorise the
automatic replay of a request. It does not replace a recipient's own limits
on attempts, concurrency or total elapsed time. A recipient can wait for
longer, or abandon the retry. Any delay that a recipient adds, including
random delay, MUST NOT cause a retry earlier than the selected delay.

Retry-After-Ms carries a delay and has no form that carries a date. This
document defines no means of accounting for time that the response spent
in transit or in a cache.

## The wait-ms Preference {#wait}

The wait-ms preference establishes an upper bound, in milliseconds, on the
length of time the client expects the server to take to process the request
once it has been received. It is the companion of the wait preference
({{Section 4.3 of RFC7240}}).

~~~ abnf
wait-ms = "wait-ms" BWS "=" BWS delta-milliseconds
~~~

BWS is defined in {{Section 5.6.3 of RFC9110}}.

~~~ http-message
Prefer: respond-async, wait=1, wait-ms=250
~~~

A client that sends wait-ms MUST also send wait. A server that does not
recognise wait-ms ignores it ({{Section 2 of RFC7240}}) and can apply wait.
A server that implements this specification uses a valid wait-ms value in
place of the wait value, and ignores wait-ms when wait is absent.

A server MUST ignore wait-ms if wait has an invalid value or wait-ms does
not match its grammar. Duplicate preferences are processed as specified in
{{Section 2 of RFC7240}}. The preference does not establish an end-to-end
request deadline or change the client's transport timeouts. It does not
oblige a server to hold resources for the requested duration.

# Deployment Considerations

## Choosing the Whole-Second Policy {#base-policy}

Every cache between the origin server and the client that does not use the
fine directives applies the base directives. This includes implementing
caches that have no fine age. The base values therefore decide what happens
on any path that is not under the sender's control.

For the max-age and s-maxage response directives, the choice is:

| Base value | Effect at a cache that applies the base directive |
|------------|---------------------------------------------------|
| 0          | No fresh lifetime. The response can be stored and validated; stale reuse requires separate permission. |
| 1 or more  | The cache applies the whole-second duration, accounting for upstream age as specified in RFC 9111. |

A sender that requires sub-second freshness and cannot accept more sends a
base value of zero. A sender that can accept a full second at legacy caches
sends a base value of one.

Senders can scope the fine policy to the caches they have an arrangement
with by using a targeted field ({{targeted}}).

The same choice applies to a client that sends a fine request directive.
For example, `max-age=0, max-age-ms=500` causes a legacy cache to validate
its stored response, and `max-age=1, max-age-ms=500` allows a legacy cache
to use a response that is up to one second old.

## Mismatched Values {#mismatch}

The two values of a pair are independent ({{pairing}}). A recipient
therefore cannot distinguish a deliberate difference from a mistake, and
applies whichever value it uses as written. The following table shows what
a sender obtains.

| Pair | Caches that use the fine directive | All other caches |
|------|-----------------------------------|------------------|
| `max-age=0, max-age-ms=200` | 200 milliseconds | No fresh lifetime |
| `max-age=1, max-age-ms=200` | 200 milliseconds | One second |
| `max-age=1, max-age-ms=2000` | Two seconds | One second |
| `max-age=60, max-age-ms=200` | 200 milliseconds | 60 seconds |
| `max-age=0, max-age-ms=86400000` | One day | No fresh lifetime |

A base value much larger than its companion is the case most likely to be
a mistake, for example when a companion is added to an existing field
without lowering the base. Most caches then hold the response for the
longer time. Before deploying a pair, a sender is advised to confirm that
it accepts the base value from every cache.

A mistake of unit has a similar effect. Sending `max-age-ms=300` where 300
seconds was intended reduces the lifetime a thousandfold at the caches that
use it, and increases the request rate at the origin server to match. A
cache cannot detect this. The same exposure exists today when a sender
generates `max-age=0` in error.

This document does not require the two values to be consistent. Such a
rule would prevent a sender from choosing a fallback that differs from the
fine policy, which is the purpose of the base value.

## Rewriting Policy at an Intermediary {#rewriting}

An intermediary that changes a duration to enforce a local policy might
not recognise its companion. For example, a gateway that rewrites
`max-age=3600, max-age-ms=3600000` to `max-age=0, max-age-ms=3600000`
leaves a policy that an implementing cache reads as one hour.

An intermediary that intentionally changes a duration to enforce a local
policy SHOULD also examine its companion in the same field, and remove or
replace the companion if retaining it would defeat that policy. The same
applies to targeted fields ({{targeted}}) and to the pairs in {{non-cache}}.
This does not require an intermediary to alter fields that it otherwise
forwards.

## Choosing a Lifetime {#choosing}

One millisecond is the resolution of the companions. It is not a
recommended lifetime. The time a validation takes sets a practical lower
limit:

- A cache spends a freshness lifetime that is shorter than its validation
  round trip mostly waiting for the origin server. A lifetime of several
  round trips is needed before most requests are answered from the cache.
- A stale-while-revalidate-ms window allows a cache to answer requests
  during validation when stale reuse is permitted. A window shorter than
  the validation can help requests that arrive within it, but requests
  after it ends might block. Operators should size it for the validation
  latency distribution, including queueing and failures.
- Timer granularity and scheduling delay on a loaded host can amount to
  several milliseconds. The rounding rule in {{fine-age}} ensures that such
  delay shortens reuse and never extends it.

A sender is advised to choose values that remain acceptable if a cache
honours them only approximately, and that are no shorter than the
application needs.

## Origin Load

A short freshness lifetime increases the rate at which caches contact the
origin server. Shortening a lifetime from one second to 200 milliseconds
allows up to five times as many validations from each cache. Operators are
advised to measure the request rate at each tier when shortening a
lifetime.

## Synchronised Refreshes {#synchronised}

A shorter lifetime does not spread requests over time. Clients following
the same publication schedule, or caches expiring a popular response at
the same instant, can produce bursts of validation requests. A
stale-while-revalidate window can hide validation latency from clients but
does not itself ensure that requests are collapsed within a cache or
coordinate refreshes at independent caches.

Implementations can collapse concurrent requests for the same eligible
stored response ({{Section 4 of RFC9111}}) and can start a validation before
freshness expires. A cache can vary when it starts that validation, without
extending the permitted freshness lifetime or stale window. Any such
scheduling needs to preserve cache-key and authorisation boundaries and
avoid unbounded speculative requests. This document defines no scheduling
algorithm, client cohort or jitter field.

Early validation does not guarantee a newer representation. If it reaches
the origin before the next publication, a 304 can renew the freshness of
the old representation and delay discovery of that publication.

## Application Timeliness {#timeliness}

A freshness lifetime bounds reuse without validation; it is not a guarantee
about when the origin publishes new information or when a client receives
it. A successfully validated representation can have an old application
timestamp. Transport, response-body transfer, player reload rules and
processing add further delay. A fine stale window permits further reuse
and therefore contributes to the application's tolerated delay.

Applications that require a particular publication or sequence number need
an application mechanism for expressing that requirement. Sub-second
changes to a representation can be distinguished with entity tags; they do
not require a finer Last-Modified field. Event-driven delivery or a blocking
request can also avoid repeated polling. This extension does not replace
those mechanisms.

## Mixed Paths

When a legacy cache is deployed between two implementing caches, the
downstream cache cannot be configured to treat it as a fine-age source. The
downstream cache then applies the base directives and removes any Age-Ms
field ({{receive}}). Fine age reporting resumes at the next cache that
obtains the response from a fine-age source.

If the downstream cache is wrongly configured to treat that path as a
fine-age source, the legacy cache can reuse the response under the base
directives while forwarding the Age-Ms value it received. The downstream
cache then underestimates the age by up to the time the legacy cache held
the response. For a legacy cache that follows the base directives, they
and any stale permissions determine that time, which is a reason to
choose a base lifetime of zero when the path is not fully known
({{base-policy}}).

# Security Considerations {#security}

The considerations of {{Section 7 of RFC9111}} apply.

This document adds finer durations and a finer age. It adds no authority:
a fine directive does not relax a restriction on storing or sharing a
response ({{pairing}}), and each fine value has a whole-second base that
its sender has to accept. What it does add is age metadata that a cache
acts on and that is not authenticated. The subsections below state what
can go wrong, what limits it, and what remains.

## Understated Age {#sec-age}

An Age-Ms value that understates the age of a response can cause a cache to
reuse the response for longer than the origin server intended. This can
result from a legacy cache that forwards a stored Age-Ms unchanged, from a
path that changes after configuration, or from a sender that lies.

The exposure is limited as follows:

- A cache uses Age-Ms only from a sender that it has been configured to
  treat as a fine-age source, and the configuration has to cover the
  complete path ({{receive}}). The default is the behaviour of {{RFC9111}}.
- A cache removes an Age-Ms value that it did not use, so that an
  unreliable value does not travel further ({{receive}}).
- An inconsistent pair of age values is not used. This detects some
  errors, including a legacy cache that has updated Age past a second
  boundary.
- For each receipt, the remaining fresh reuse at that cache is at most the
  selected fine freshness lifetime, less the accounted request delay.

What remains: the last item is not a bound on the response's actual age or
on its total time across a path. Successive false age samples can
repeatedly conceal upstream time, and any permitted stale reuse adds its
own window. A consistent pair, a secured connection to the sender, an
entity tag or a Last-Modified value does not show that the path accounted
for age correctly. A cache can impose local limits on reuse; they reduce
the exposure but do not authenticate an upstream age. A fine-age source
that lies is not defended against, as a cache that sends a false Age is not
defended against today.

An Age-Ms value that overstates the age causes additional validation
requests, as an overstated Age value does today.

## Loss of Fine Metadata {#sec-fallback}

An attacker or a fault that removes Age-Ms, or invalidates a fine
directive, causes the base policy to apply. This is not always the more
restrictive outcome: `max-age=60, max-age-ms=200` then permits 60 seconds.

This grants nothing that the sender did not send. The sender is required to
choose a base that it accepts on every path ({{pairing}}), and a legacy
cache applies that base in any case. A sender that cannot accept more than
its fine lifetime sends a base of zero ({{base-policy}}). A base of zero
still permits storage and validation; a sender that needs neither uses
no-store or no-cache as it does today.

Removing both age fields does not make a response appear new to a cache
that receives it from another cache: a missing pair from a cache gives no
fine age ({{receive}}).

## Rewritten Policy {#sec-rewrite}

An intermediary that lowers a duration to enforce a local policy, and does
not recognise the companion, leaves a fine value that an implementing cache
downstream will use ({{rewriting}}). The caches cannot detect this. It is
contained only by updating the enforcement point, or by that point removing
directives it does not recognise. It affects only downstream caches that
have been configured to use fine age.

## Unusual Values {#sec-values}

Mismatched, malformed and extreme values have defined outcomes
({{pairing}}, {{mismatch}}, {{examples}}). An invalid fine value never
invalidates its base, and a fine directive without its base is never used.
Names are compared in full ({{directives}}), so a fine directive is not
mistaken for its base or the reverse.

The largest value is fifteen digits, about 31,700 years in milliseconds.
A long lifetime chosen by an origin server for its own response is an
existing capability. Implementations need checked arithmetic when
converting or adding values ({{delta-ms}}); a result that would overflow
is not a reason to lengthen reuse.

## Clocks {#sec-clocks}

A fine age depends on elapsed time measured at each cache. A clock step, a
suspend, a restart or a restored snapshot can make a stored response appear
younger than it is. {{fine-age}} requires a cache to account for that time
or to stop relying on the affected fine age, after which the base policy
applies.

What remains: an implementation cannot detect every such event. A restore
that also rolls back the state used for detection is an example. The same
events affect whole-second ages today; with sub-second lifetimes a given
error is a larger multiple of the lifetime.

## Load {#sec-load}

Short lifetimes can be used to increase load on an origin server or on an
upstream cache, and synchronised expiry can sharpen bursts
({{synchronised}}). This is already possible with a lifetime of zero, so a
fine lifetime does not add to what a sender can cause. In the same way, a
fine request directive does not let a client cause more validation than
`max-age=0` does, and a cache can ignore request directives under local
policy as it can today.

## Retry and Wait Hints {#sec-retry}

A small Retry-After-Ms value invites frequent retries. A server chooses the
value, as it does for Retry-After, which can already be zero. The hint does
not require or authorise a retry, and a recipient keeps its own minimum
delay and its limits on attempts, concurrency and total time ({{retry}}).
The wait-ms preference does not oblige a server to hold resources
({{wait}}).

## Privacy {#sec-privacy}

Age-Ms reveals the time a response has spent in caches with finer
resolution than Age. Together with fields such as Cache-Status {{RFC9211}},
this can make it easier for an observer to infer when other clients
requested the same resource, which adds to the timing attacks described in
{{Section 7.2 of RFC9111}}. The ttl-ms parameter exposes the same timing.

The observer has to receive the fields, or be able to obtain comparable
responses from the same shared cache. A cache can omit Age-Ms
({{generate}}) and withhold ttl-ms where downstream recipients do not need
them; a cache that coarsens age rounds it up, so that privacy handling
never understates age. Omitting Age-Ms while still sending ttl-ms leaves
the finer timing visible.

What remains: neither the finer fields nor their omission guarantees
privacy. Response timing itself can reveal cache state, as it does today.

# IANA Considerations

## Cache Directives

IANA is asked to register the following entries in the "Hypertext Transfer
Protocol (HTTP) Cache Directive Registry" established by
{{Section 5.2.4 of RFC9111}}:

| Cache Directive           | Reference                      |
|---------------------------|--------------------------------|
| max-age-ms                | {{directives}} of this document |
| max-stale-ms              | {{directives}} of this document |
| min-fresh-ms              | {{directives}} of this document |
| s-maxage-ms               | {{directives}} of this document |
| stale-if-error-ms         | {{directives}} of this document |
| stale-while-revalidate-ms | {{directives}} of this document |

## Header Fields

IANA is asked to register the following entries in the "Hypertext Transfer
Protocol (HTTP) Field Name Registry" established by
{{Section 16.3.1 of RFC9110}}:

| Field Name     | Status    | Structured Type | Reference                   |
|----------------|-----------|-----------------|-----------------------------|
| Age-Ms         | permanent | Item            | {{age-ms}} of this document |
| Retry-After-Ms | permanent | Item            | {{retry}} of this document  |

## Cache-Status Parameter

IANA is asked to register the following entry in the "HTTP Cache-Status"
registry established by {{RFC9211}}:

Name:
: ttl-ms

Type:
: Integer

Description:
: The response's remaining freshness lifetime, in milliseconds

Reference:
: {{ttl-ms}} of this document

## Preference

IANA is asked to register the following entry in the "HTTP Preferences"
registry established by {{RFC7240}}:

Preference:
: wait-ms

Value:
: A non-negative integer number of milliseconds

Description:
: An upper bound, in milliseconds, on the time the client expects the
  server to take to process the request

Reference:
: {{wait}} of this document

--- back

# Examples {#examples}

These examples assume that the cache has a fine age for the response and
that no other directive restricts reuse.

| Policy | Outcome at an implementing cache |
|---|---|
| `max-age=0, max-age-ms=200` | Fresh at 199 ms. Stale at 200 ms. |
| `max-age=1, max-age-ms=1250` | Fresh at 999 ms, 1000 ms and 1249 ms. Stale at 1250 ms. |
| `max-age=1, max-age-ms=0` | Stale immediately. |
| `max-age=60, max-age-ms=200` | Fresh at 199 ms. Stale at 200 ms. The values are independent. |
| `max-age=1, max-age-ms=2000` | Fresh at 1999 ms. Stale at 2000 ms. |
| `max-age=0, max-age-ms=0200` | Leading zeros are permitted. The lifetime is 200 ms. |
| `max-age=0, max-age-ms="200"` | The fine directive is ignored. The response is stale immediately. |
| `max-age-ms=200` | The fine directive is ignored because max-age is absent. Freshness is determined by {{RFC9111}}. |
| `max-age=1, max-age-ms=0.2` | The fine directive is invalid and is ignored. The lifetime is one second. |
| `max-age=1, max-age-ms=200, max-age-ms=300` | The fine directive is ignored. The lifetime is one second. |
| `s-maxage=1, max-age=0, max-age-ms=200` | A shared cache uses one second. A private cache uses 200 ms. |
| `max-age=0, max-age-ms=200, no-cache` | The response is not reused without validation. |
| `max-age=0, max-age-ms=200, stale-while-revalidate=0, stale-while-revalidate-ms=200` | Fresh until 200 ms. Can be served stale while revalidating until 400 ms. |
| `max-age=0, max-age-ms=200, stale-if-error=1, stale-if-error-ms=1500` | Fresh until 200 ms. Can be used when an error is encountered until 1700 ms. |

The following table shows request directives applied to a stored response
that has a freshness lifetime of 2000 milliseconds.

| Request | Fine age | Outcome at an implementing cache |
|---|---|---|
| `max-age=1, max-age-ms=1750` | 1600 ms | Satisfied. |
| `max-age=1, max-age-ms=1750` | 1800 ms | Not satisfied. The cache validates the response. |
| `min-fresh=0, min-fresh-ms=500` | 1600 ms | Not satisfied. The response is fresh for only another 400 ms. |
| `max-stale=0, max-stale-ms=250` | 2200 ms | Satisfied. The response has been stale for 200 ms. |
| `max-stale, max-stale-ms=250` | 2500 ms | Satisfied. max-stale without an argument accepts any staleness. |
| `max-age-ms=1750` | 1600 ms | The fine directive is ignored because max-age is absent. |

The following table shows an implementing cache receiving a response from
a sender that it is configured to treat as a fine-age source.

| Sender | Received | Fine age_value |
|---|---|---|
| Origin server | No Age and no Age-Ms | 0 |
| Origin server | `Age: 0` and `Age-Ms: 175` | None. An origin server does not generate these. |
| Cache | No Age and no Age-Ms | None. Absence does not show an exchange with the origin server. |
| Cache | `Age: 0` and `Age-Ms: 175` | 175 ms |
| Cache | `Age: 1` and `Age-Ms: 1075` | 1075 ms |
| Cache | `Age: 1` and `Age-Ms: 175` | None. The values are inconsistent. |
| Cache | `Age: 0` only | None |
| Cache | `Age-Ms: 175` only | None |
| Cache | `Age: 1, 5` and `Age-Ms: 1075` | None. Age recovery under RFC 9111 still applies. |
| Cache | `Age: 0` and `Age-Ms: 175;tag="a,b"` | 175 ms. The comma is inside a parameter, which is ignored. |
| Cache | `Age: 0` and `AGE-MS: 175` | 175 ms. Field names are case-insensitive. |

# Alternatives Considered {#alternatives}

This appendix records designs that were considered. It is intended to help
discussion and can be removed before publication.

Decimal seconds:
: A value such as `max-age=0.2` needs no new names. It does not match the
  delta-seconds rule, and {{Section 4.2.1 of RFC9111}} encourages a cache
  to treat a response with such a value as stale. In a targeted field it
  parses as a Decimal, which {{Section 2.1 of RFC9213}} says
  implementations should not consume. Neither case lets the sender choose
  what a legacy cache does.

Explicit units:
: Companions such as `max-age-fine="1250ms"` could also express
  microseconds. They need a unit grammar, a range for each unit and
  conversion between units. No use case that needs a resolution finer than
  one millisecond has been identified. If one is, a further companion in
  that unit could follow the pattern of this document, with the base and
  the millisecond companion as its fallbacks. Its range would be shorter
  than that of its base ({{delta-ms}}).

A parameter in targeted fields:
: `CDN-Cache-Control: max-age=0;ms=200` attaches the fine value to its base,
  and a legacy recipient ignores the parameter. Cache-Control has no
  parameter syntax, so this would limit the extension to targeted fields.

A fraction within Age:
: `Age: 1.175` or `Age: 1; ms=175` would be replaced as a unit when a
  legacy cache regenerates the field, which would remove the problem
  described in {{receive}}. Both are invalid according to
  {{Section 5.1 of RFC9111}}, and a cache that receives an invalid Age
  field is advised to ignore it, losing the whole-second value as well.

# Time-Related Fields Left Unchanged {#other}

The following fields and parameters carry time in whole seconds and are not
changed by this document.

| Field or parameter | Reason |
|--------------------|--------|
| Date, Expires, Last-Modified | Timestamps. A finer Expires would need a new date format, a finer Date and clocks that agree to the millisecond. A fine lifetime with a fine age gives each cache the same expiry time without them. Sub-second changes to a representation can be distinguished with entity tags ({{Section 8.8.3 of RFC9110}}). |
| Alt-Svc ma | Governs an alternative service advertisement, not a response. |
| immutable | Takes no duration. It applies for the freshness lifetime, however that is expressed. |
| Strict-Transport-Security max-age, Expect-CT max-age, Set-Cookie Max-Age | Security policy and cookie retention, with their own expiry rules. |
| Web Push TTL | Bounds how long a push service retains a message for a device that is offline. |
| Signature created and expires parameters | Bound the acceptance of a signature. Their specification states that sub-second precision is not supported. |

# Implementation Status

This section is to be removed before publication.

A prototype for nginx implements fine directives in Cache-Control and the
Age-Ms field for responses with a 200 status code. It implements:

- the max-age-ms, s-maxage-ms, stale-while-revalidate-ms and
  stale-if-error-ms response directives;
- the max-age-ms and min-fresh-ms request directives, when enabled by
  configuration; and
- variables from which an operator can compose the ttl and ttl-ms
  Cache-Status parameters.

It does not yet implement the fine directives in targeted fields, or the
max-stale-ms and stale-if-error-ms request directives. It forwards
Retry-After-Ms and wait-ms without acting on them.

The prototype differs from this document in three ways. It records the time
a response was stored using a wall clock, and discards the fine age when
the difference between that clock and a monotonic clock moves by more than
10 milliseconds, or after a restart. It does not detect a smaller step, or
a restored snapshot that rolls both clocks back together ({{fine-age}}).
It applies a fine stale window only to a response whose
freshness lifetime comes from max-age or s-maxage, and not to one whose
lifetime comes from Expires. It rejects an Age-Ms value that carries
parameters, where this document ignores the parameters.

# Acknowledgements
{:numbered="false"}

The author used Claude and OpenAI Codex to research references, to draft
and edit this text, and to explore how the extension behaves in mixed
deployments.
