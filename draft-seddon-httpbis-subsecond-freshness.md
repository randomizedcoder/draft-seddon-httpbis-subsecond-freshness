---
title: "Millisecond Resolution for HTTP Cache Freshness"
abbrev: "Millisecond Cache Freshness"
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
millisecond companions for the max-age, s-maxage and stale-while-revalidate
response directives and for the Age response header field. Each companion is
sent together with its whole-second counterpart, so that caches which do not
implement this specification continue to operate as they do today.

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
request load for such a resource has to choose between no reuse and a
lifetime comparable to the interval at which the resource changes.

Whole-second age reporting has a second effect in multi-tier caches. A cache
that has held a response for 900 milliseconds reports `Age: 0`. A downstream
cache then starts counting from zero, and each tier can hold the response
for up to the full lifetime again.

This document defines a millisecond companion for each of the following:

| Whole seconds          | Milliseconds              | Defined in     |
|------------------------|---------------------------|----------------|
| delta-seconds rule     | delta-milliseconds rule   | {{delta-ms}}   |
| max-age                | max-age-ms                | {{directives}} |
| s-maxage               | s-maxage-ms               | {{directives}} |
| stale-while-revalidate | stale-while-revalidate-ms | {{directives}} |
| Age                    | Age-Ms                    | {{age-ms}}     |

For example, a cache that has held a response for 175 milliseconds of a
200 millisecond lifetime sends:

~~~ http-message
Cache-Control: max-age=0, max-age-ms=200
Age: 0
Age-Ms: 175
~~~

A downstream cache that implements this specification, and that is
configured to rely on the sender's Age-Ms value, can reuse the response for
the remaining 25 milliseconds. Any other cache applies `max-age=0`.

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

This document does not change the behaviour of caches that do not implement
it, and it does not define companions for request directives.

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
: One of the max-age, s-maxage or stale-while-revalidate response
  directives.

fine directive:
: One of the max-age-ms, s-maxage-ms or stale-while-revalidate-ms response
  directives. Each fine directive is the companion of the base directive
  whose name it extends.

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

A recipient parsing a delta-milliseconds value and converting it to binary
form needs an arithmetic type of at least 50 bits of non-negative integer
range. Note that this is wider than the 31 bits suggested for delta-seconds
in {{Section 1.2.2 of RFC9111}}. A 31-bit count of milliseconds overflows
in less than 25 days.

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

A fine directive gives a complete duration. It is not added to the value of
its base directive. For example, `max-age=1, max-age-ms=1250` describes a
freshness lifetime of 1.25 seconds for an implementing cache and of one
second for a legacy cache.

These directives are behavioural extensions in the sense of
{{Section 5.2.3 of RFC9111}}. Each modifies a base directive that is sent
alongside it. A legacy cache ignores the fine directive and applies the
base directive.

## max-age-ms

Argument syntax:

: delta-milliseconds (see {{delta-ms}})

The max-age-ms response directive indicates that the response is to be
considered stale after its age is greater than or equal to the specified
number of milliseconds. It is the companion of the max-age response
directive ({{Section 5.2.2.1 of RFC9111}}).

## s-maxage-ms

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

## stale-while-revalidate-ms

Argument syntax:

: delta-milliseconds (see {{delta-ms}})

The stale-while-revalidate-ms response directive indicates that a cache MAY
serve the response in which it appears after it becomes stale, up to the
specified number of milliseconds, under the conditions given in
{{Section 3 of RFC5861}}. It is the companion of the stale-while-revalidate
response directive.

## Pairing {#pairing}

A sender that generates a fine directive MUST also generate its base
directive in the same field. The base directive is the policy that the
sender accepts from every cache that does not use the fine directive. The
two values are otherwise independent. {{base-policy}} discusses the choice
of base value.

An implementing cache MUST ignore a fine directive when any of the
following is true:

- its base directive is absent from the same field, or is present with an
  invalid value;
- its argument does not match the delta-milliseconds rule;
- it appears more than once in the field with differing values; or
- the cache has no fine age for the response ({{fine-age}}).

A cache that ignores a fine directive applies the remaining directives as
specified in {{RFC9111}} and {{RFC5861}}. Ignoring a fine directive never
causes its base directive to be ignored.

A fine directive does not relax any other directive. The no-store, no-cache,
private, must-revalidate, proxy-revalidate and must-understand response
directives have the effects specified in {{RFC9111}} whether or not a fine
directive is present.

## Targeted Cache Control {#targeted}

The fine directives can be used in targeted cache control fields
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

When a response is received from a fine-age source, the cache determines a
fine age_value as follows:

1. If the response contains neither an Age nor an Age-Ms field, the fine
   age_value is zero.

2. If the response contains exactly one Age field line and exactly one
   Age-Ms field line, both are valid, and the Age value is equal to the
   Age-Ms value divided by 1000 and rounded down, the fine age_value is the
   Age-Ms value.

3. Otherwise, the response has no fine age_value.

When a response is received from any other sender, or has no fine
age_value, the cache has no fine age for that response. It processes the
response as specified in {{RFC9111}}, using the Age field alone.

An implementing cache MUST NOT forward, or store for later forwarding, an
Age-Ms field that it has not used as the fine age_value. This prevents an
unreliable value from reaching a downstream cache that would rely on it.

# Cache Operation {#operation}

## Establishing a Fine Age {#fine-age}

A cache has a fine age for a stored response when:

- it obtained a fine age_value for the response ({{receive}}); and
- it has measured the time since the corresponding request with a
  resolution of one millisecond or better, without interruption.

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
resident_time. If a cache can no longer account for the whole of the time
since the request, for example after a restart or a clock adjustment, it no
longer has a fine age for the response. A stored response does not gain
freshness as a result of such an event.

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

## Validation {#validation}

When a stored response is updated by a 304 (Not Modified) response
({{Section 4.3.4 of RFC9111}}), the cache establishes a new fine age from
the validation exchange as described in {{receive}} and {{fine-age}}. The
previous fine age is discarded.

The fine directives that apply afterwards are those in the updated stored
response. If the 304 response replaces a field that carried a fine
directive with one that does not, the fine directive no longer applies.

# Deployment Considerations

## Choosing the Whole-Second Policy {#base-policy}

Every cache between the origin server and the client that does not use the
fine directives applies the base directives. This includes implementing
caches that have no fine age. The base values therefore decide what happens
on any path that is not under the sender's control.

| Base value | Effect at a cache that applies the base directive |
|------------|---------------------------------------------------|
| 0          | The directive grants no time. Reuse is limited to implementing caches on configured paths. |
| 1 or more  | The cache can hold the response for that many seconds in addition to any time spent upstream, as it does today. |

A sender that requires sub-second freshness and cannot accept more sends a
base value of zero. A sender that can accept a full second at legacy caches
sends a base value of one.

Senders can scope the fine policy to the caches they have an arrangement
with by using a targeted field ({{targeted}}).

## Origin Load

A short freshness lifetime increases the rate at which caches contact the
origin server. A stale-while-revalidate-ms window allows a cache to answer
requests while one validation is in progress, but it does not help if the
validation takes longer than the window. Operators are advised to measure
the request rate at each tier when shortening a lifetime.

## Mixed Paths

When a legacy cache is deployed between two implementing caches, the
downstream cache cannot be configured to treat it as a fine-age source. The
downstream cache then applies the base directives and removes any Age-Ms
field ({{receive}}). Fine age reporting resumes at the next cache that
obtains the response from a fine-age source.

# Security Considerations

The considerations of {{Section 7 of RFC9111}} apply.

An Age-Ms value that understates the age of a response can cause a cache to
reuse the response for longer than the origin server intended, up to the
fine freshness lifetime. {{receive}} limits this by requiring configuration
before the field is used, and by requiring an implementing cache to remove
a value that it did not use. The consistency check in {{receive}} detects
some errors but is not a defence against a sender that generates a
plausible pair of values.

An Age-Ms value that overstates the age causes additional validation
requests, as an overstated Age value does today.

Short lifetimes can be used to increase load on an origin server or on an
upstream cache. This is already possible with a lifetime of zero.

Age-Ms reveals the time a response has spent in caches with finer
resolution than Age. Together with fields such as Cache-Status {{RFC9211}},
this can make it easier for an observer to infer when other clients
requested the same resource. Operators can remove the field at a trust
boundary.

# IANA Considerations

## Cache Directives

IANA is asked to register the following entries in the "Hypertext Transfer
Protocol (HTTP) Cache Directive Registry" established by
{{Section 5.2.4 of RFC9111}}:

| Cache Directive           | Reference                      |
|---------------------------|--------------------------------|
| max-age-ms                | {{directives}} of this document |
| s-maxage-ms               | {{directives}} of this document |
| stale-while-revalidate-ms | {{directives}} of this document |

## Header Field

IANA is asked to register the following entry in the "Hypertext Transfer
Protocol (HTTP) Field Name Registry" established by
{{Section 16.3.1 of RFC9110}}:

| Field Name | Status    | Structured Type | Reference                   |
|------------|-----------|-----------------|-----------------------------|
| Age-Ms     | permanent | Item            | {{age-ms}} of this document |

--- back

# Examples {#examples}

These examples assume that the cache has a fine age for the response and
that no other directive restricts reuse.

| Policy | Outcome at an implementing cache |
|---|---|
| `max-age=0, max-age-ms=200` | Fresh at 199 ms. Stale at 200 ms. |
| `max-age=1, max-age-ms=1250` | Fresh at 999 ms, 1000 ms and 1249 ms. Stale at 1250 ms. |
| `max-age=1, max-age-ms=0` | Stale immediately. |
| `max-age-ms=200` | The fine directive is ignored because max-age is absent. Freshness is determined by {{RFC9111}}. |
| `max-age=1, max-age-ms=0.2` | The fine directive is invalid and is ignored. The lifetime is one second. |
| `max-age=1, max-age-ms=200, max-age-ms=300` | The fine directive is ignored. The lifetime is one second. |
| `s-maxage=1, max-age=0, max-age-ms=200` | A shared cache uses one second. A private cache uses 200 ms. |
| `max-age=0, max-age-ms=200, no-cache` | The response is not reused without validation. |
| `max-age=0, max-age-ms=200, stale-while-revalidate=0, stale-while-revalidate-ms=200` | Fresh until 200 ms. Can be served stale while revalidating until 400 ms. |

The following table shows an implementing cache receiving a response from
a sender that it is configured to treat as a fine-age source.

| Received | Fine age_value |
|---|---|
| No Age and no Age-Ms | 0 |
| `Age: 0` and `Age-Ms: 175` | 175 ms |
| `Age: 1` and `Age-Ms: 1075` | 1075 ms |
| `Age: 1` and `Age-Ms: 175` | None. The values are inconsistent. |
| `Age: 0` only | None |
| `Age-Ms: 175` only | None |

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
  one millisecond has been identified.

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

# Other Durations in HTTP {#other}

Other HTTP fields carry time in whole seconds. They are not changed by this
document.

| Field or directive | Note |
|--------------------|------|
| stale-if-error {{RFC5861}} | Candidate for the same treatment if there is a use for it. |
| max-age, min-fresh and max-stale request directives ({{Section 5.2.1 of RFC9111}}) | Candidates, as above. |
| ttl parameter of Cache-Status {{RFC9211}} | Candidate, as above. |
| Date, Expires, Last-Modified | Timestamps with a resolution of one second. Sub-second changes to a representation can be distinguished with entity tags ({{Section 8.8.3 of RFC9110}}). |

# Implementation Status

This section is to be removed before publication.

A prototype for nginx implements the fine directives in Cache-Control and
the Age-Ms field for responses with a 200 status code. It does not yet
implement the fine directives in targeted fields.

# Acknowledgements
{:numbered="false"}

The author used Claude and OpenAI Codex to research references, to draft
and edit this text, and to explore how the extension behaves in mixed
deployments.
