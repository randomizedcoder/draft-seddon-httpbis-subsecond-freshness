# Finer time resolution in other systems

HTTP caching is not the first system to find that whole seconds are too coarse. This note records other systems that expire or validate cached state, or that exchange durations, and what each did when it needed finer time.

- **The pattern is common.** Nine systems below moved to finer time, or to a validator with no time unit. Most did so by adding a new name beside the old one, and kept the old one working.
- **It did not go smoothly.** Finer fields were filled from coarse clocks. Coarse steps dropped the fraction. Two names for one value disagreed. One kernel change was reverted and redone. Each system section below has a "What went wrong" paragraph, and [Lessons](#lessons) says what this proposal does about each problem, including the ones it does not solve.
- **It is not universal.** DNS, memcached and CoAP still use whole seconds.
- **It has costs.** Finer time on the web exposed a side channel and was later made coarser.

This is a selection, not a complete survey. Every statement below is taken from the linked source, read on 26 November 2026. Where a source did not state a date or a reason, none is given.

## Summary

| System | Before | After | How it was added | Result |
|---|---|---|---|---|
| [Redis key expiry](#redis-key-expiry) | Seconds; up to 1 s late | Milliseconds; up to 1 ms late | New commands beside the old | Both sets remain |
| [Linux neighbour cache](#linux-neighbour-cache) | Seconds and clock ticks | Milliseconds | New `_ms` settings | Old settings kept, marked obsolete |
| [Kafka log retention](#kafka-log-retention) | Hours | Minutes and milliseconds | New settings with a stated precedence | All three remain |
| [HLS segment durations](#hls-segment-durations) | Whole seconds | Decimal seconds | Gated on a declared version | Decimal is now recommended |
| [File timestamps](#file-timestamps) | Seconds, then clock ticks | Nanoseconds | Extra fields; later a change counter | One kernel change reverted; tools still guard against equal timestamps |
| [POSIX interfaces](#posix-interfaces) | Seconds, then microseconds | Nanoseconds | New functions beside the old | Two old functions removed in the 2024 edition |
| [syslog timestamps](#syslog-timestamps) | Seconds | Up to microseconds | A new message format | Fraction is optional; rsyslog still forwards in the traditional format by default |
| [HTTP validators](#http-validators) | Last-Modified, one second | ETag, no time unit | A new field beside the old | Both remain |
| [Web timers](#web-timers) | Milliseconds | Sub-millisecond | A new interface beside the old | Later coarsened for security |
| [DNS, memcached, CoAP](#systems-that-kept-whole-seconds) | Seconds | Unchanged | | |

## Redis key expiry

Redis keys can be given a time to live. `EXPIRE` takes it "in seconds". Early versions were also coarse in when they acted: "In Redis 2.4 the expire might not be pin-point accurate, and it could be between zero to one seconds out."

Redis 2.6 added "Milliseconds resolution expires, also added new commands with milliseconds precision (PEXPIRE, PTTL, ...)". `PEXPIRE` "works exactly like EXPIRE but the time to live of the key is specified in milliseconds instead of seconds". Expiry times became "absolute Unix timestamps (in milliseconds in case of Redis version 2.6 or greater)", and "Since Redis 2.6 the expire error is from 0 to 1 milliseconds." Version 2.6.12 added `EX` (seconds) and `PX` (milliseconds) options to `SET`.

The seconds commands were kept, so existing clients were unaffected. The migration notes say the change "is very unlikely to break code". Redis added a second name with the unit in it, which is the approach this proposal takes.

**What went wrong.** One reply had two meanings: "In Redis 2.6 or older the command returns -1 if the key does not exist or if the key exist but has no associated expire." Redis 2.8 changed the reply, so that -2 means no key and -1 means no expiry. The command names multiplied, and options on `SET` were then added to cover them: "Since the SET command options can replace SETNX, SETEX, PSETEX, GETSET, it is possible that in future versions of Redis these commands will be deprecated and finally removed." Expiry is stored as an absolute time, so it depends on the clock: "For expires to work well, the computer time must be taken stable." A data file moved between machines whose clocks differ can have "all the keys loaded to be expired at loading time".

Sources: [EXPIRE](https://redis.io/docs/latest/commands/expire/) · [PEXPIRE](https://redis.io/docs/latest/commands/pexpire/) · [PTTL](https://redis.io/docs/latest/commands/pttl/) · [SET](https://redis.io/docs/latest/commands/set/) · [2.6 release notes](https://raw.githubusercontent.com/redis/redis/2.6/00-RELEASENOTES)

## Linux neighbour cache

The Linux kernel caches the link-layer address of each neighbour, for ARP and for IPv6 Neighbor Discovery. The original ARP specification left expiry open: "It may be desirable to have table aging and/or timeouts. The implementation of these is outside the scope of this protocol." Linux exposed its timers as settings. `base_reachable_time` was in seconds, and `retrans_time` was "The number of jiffies to delay before retransmitting a request". A jiffy is a kernel clock tick, and the manual lists this as a defect: "Some timer settings are specified in jiffies, which is architecture- and kernel version-dependent".

Linux 2.6.12 added `base_reachable_time_ms`, "As for base_reachable_time, but measures time in milliseconds", and `retrans_time_ms`. IPv6 Neighbor Discovery carries both timers in milliseconds in Router Advertisements.

Both old settings still exist. Each is documented as "now obsolete in favor of" its `_ms` replacement.

**What went wrong.** The first unit depended on the machine, as the manual's bug list above says. The fix did not remove anything: each of these timers now has two settings, and one of them is obsolete.

Sources: [arp(7)](https://man7.org/linux/man-pages/man7/arp.7.html) · [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html) · [RFC 4861 §4.2](https://www.rfc-editor.org/rfc/rfc4861.html#section-4.2)

## Kafka log retention

Apache Kafka deletes stored messages after a retention time, first set by `log.retention.hours`. In 2013 a user asked for minutes: "It would be tremendously valuable for us to be able to define the log.retention in minutes, not hours." The reason was cost: "The storage required to process that much data over an hour is beyond what we wanted to pay for". That was fixed in version 0.8.1.

The per-topic setting, `retention.ms`, was already in milliseconds, and the two did not match. A 2014 issue noted that "The log property for retention.ms is in millis but the server default it maps to is in minutes"; it was fixed in 0.8.2.0. The broker now has `log.retention.ms` as well.

All three settings remain, and the documentation states which applies. For `log.retention.ms`: "If not set, the value in log.retention.minutes is used." For `log.retention.minutes`: "If not set, the value in log.retention.hours is used". This is the closest match to this proposal: a fine value that takes precedence when present, and a coarse value that applies otherwise.

**What went wrong.** Two names for one value used different units. The 2014 report says: "Our documentation is a little confusing on the log configs." The fix kept every name, so the broker has three settings for one retention time, and an operator has to know the order in which they apply.

Sources: [Kafka 3.9 broker configuration](https://kafka.apache.org/39/generated/kafka_config.html) · [KAFKA-918](https://issues.apache.org/jira/browse/KAFKA-918) · [KAFKA-1325](https://issues.apache.org/jira/browse/KAFKA-1325)

## HLS segment durations

An HLS playlist gives the duration of each media segment in an `EXTINF` tag. In the draft of June 2010, "duration" was "an integer that specifies the duration of the media file in seconds".

Decimal durations came later, tied to a protocol version that the playlist declares. RFC 8216 says: "if the compatibility version number is less than 3, durations MUST be integers", and a playlist must declare version 3 or higher if it contains "Floating-point EXTINF duration values". The reason given is accumulated error: "Durations SHOULD be decimal-floating-point, with enough accuracy to avoid perceptible error when segment durations are accumulated."

The older form is still allowed for old clients, with a rounding rule. The current draft of the second edition goes further for low latency: the Part Target Duration is "a decimal-floating-point number of seconds". The same draft says: "Successful responses to non-blocking Playlist requests should be cached for half the Target Duration." The Target Duration is still a whole number of seconds, so a one-second target asks for a 500 ms cache lifetime, which HTTP cannot express.

**What went wrong.** Two resolutions now meet in one playlist. The Target Duration stayed "a decimal-integer indicating the target duration in seconds", so a decimal duration is checked against it after rounding: "The EXTINF duration of each Media Segment in the Playlist file, when rounded to the nearest integer, MUST be less than or equal to the target duration; longer segments can trigger playback stalls or other errors." Integer durations for old clients need a rule of their own: "Durations that are reported as integers SHOULD be rounded to the nearest integer."

Sources: [RFC 8216 §4.3.2.1](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.2.1) · [RFC 8216 §4.3.3.1](https://www.rfc-editor.org/rfc/rfc8216.html#section-4.3.3.1) · [RFC 8216 §7](https://www.rfc-editor.org/rfc/rfc8216.html#section-7) · [draft-pantos-http-live-streaming-04](https://datatracker.ietf.org/doc/html/draft-pantos-http-live-streaming-04) · [draft-pantos-hls-rfc8216bis-22](https://datatracker.ietf.org/doc/html/draft-pantos-hls-rfc8216bis-22)

## File timestamps

A file's modification time is the validator for many caches: build tools, Git's index and network file system clients all use it to decide whether a cached copy is current. Coarse timestamps let a change go unnoticed.

Formats moved to finer units in steps. NFS version 2 carried "seconds and microseconds"; NFS version 3 carries "seconds and nanoseconds", and warns that "The use of mtime by clients to detect changes to file system objects residing on a server is dependent on the granularity of the time base on the server." On disk, ext4 timestamps began as "32-bit signed integers that represent seconds since the Unix epoch". In larger inodes the fields are widened, and "the upper 30 bits are used to provide nanosecond timestamp accuracy". The original fields stay where they were. FAT is the coarse extreme: "write time has a resolution of 2 seconds".

A finer format was not enough by itself. "Historically, the kernel has always used coarse time values to stamp inodes. This value is updated every jiffy", so two changes in one tick looked the same; with NFS version 3, "unchanging timestamps can make it difficult to tell whether to invalidate caches". Linux 6.13, released in January 2025, added multigrain timestamps, which use fine-grained time only "when a file has had its timestamps queried recently". Always using it was rejected on cost: "higher resolution timestamps on all files can increase the rate at which metadata needs to be written to the disk".

Tools still defend against equal timestamps. NFS version 4 added a `change` attribute, "A value created by the server that the client can use to determine if file data, directory contents, or attributes" have been modified. Git compares file content when a timestamp is not older than its index, because such entries may be "racily clean". GNU make has a special target, `.LOW_RESOLUTION_TIME`, for files whose commands "generate low resolution time stamps". rsync has `--modify-window`, which treats timestamps as equal when they differ by no more than a set amount, "because FAT represents times with a 2-second resolution". Finer time made the window smaller, and a validator that does not depend on time closed it.

**What went wrong.** Three separate things.

- **A coarse step dropped the fraction.** "Unfortunately, some hosts do not provide a way to set a high resolution file time stamp, so commands like ‘cp -p’ that explicitly set a file’s time stamp must discard its sub-second part." The copy then looks out of date: "dst is typically slightly older than src even when it is up to date."
- **Memory and disk disagreed.** Git can compare nanoseconds, but "On Linux, this is not enabled by default because in-core timestamps can have finer granularity than on-disk timestamps, resulting in meaningless changes when an inode is evicted from the inode cache."
- **The first kernel change was reverted.** An earlier version of multigrain timestamps was reverted in 2023, "from the mainline for the 6.6-rc3 release": "Users reported regressions due to enabling multi-grained timestamps unconditionally." Mixing fine and coarse stamps lost the order of changes: "That can cause file2 to appear to have been changed after file1, contrary to what actually happened." The current kernel documentation answers this with a floor: "maintain a global floor value that ensures that this can’t happen."

Sources: [RFC 1094 §2.3.4](https://www.rfc-editor.org/rfc/rfc1094.html#section-2.3.4) · [RFC 1813 §2.6](https://www.rfc-editor.org/rfc/rfc1813.html#section-2.6), under `nfstime3` and `wcc_attr` · [RFC 7530 §5.8.1.4](https://www.rfc-editor.org/rfc/rfc7530.html#section-5.8.1.4) · [ext4 inode timestamps](https://docs.kernel.org/filesystems/ext4/inodes.html#inode-timestamps) · [Multigrain timestamps](https://docs.kernel.org/filesystems/multigrain-ts.html) · [Linux 6.13](https://kernelnewbies.org/Linux_6.13) · [Windows file times](https://learn.microsoft.com/en-us/windows/win32/sysinfo/file-times) · [Racy Git](https://git-scm.com/docs/racy-git) · [GNU make special targets](https://www.gnu.org/software/make/manual/html_node/Special-Targets.html) · [rsync(1)](https://download.samba.org/pub/rsync/rsync.1) · [Revert of the multigrain infrastructure](https://github.com/torvalds/linux/commit/647aa768281f38cb1002edb3a1f673c3d66a8d81) · [LWN: Rethinking multi-grain timestamps](https://lwn.net/Articles/946394/)

## POSIX interfaces

The POSIX programming interfaces show the same steps. `utime()` sets file times "measured in seconds since the Epoch". `utimes()` is accurate "only to the microsecond". `futimens()` and `utimensat()` "allow time specifications accurate to the nanosecond". Timeouts followed: `select()` takes "seconds and microseconds", and `pselect()` takes "seconds and nanoseconds". For reading the clock, `gettimeofday()` returns "seconds and microseconds", and `clock_gettime()` uses seconds and nanoseconds.

Each finer interface was a new function, and the old ones kept their meaning. Issue 7 of the standard records that "Changes are made related to support for finegrained timestamps". File status gained `st_mtim`, a seconds-and-nanoseconds value, and kept the old name: "For compatibility with earlier versions of this standard, the st_atime macro shall be defined with the value st_atim.tv_sec."

The old functions were retired slowly. In Issue 7 of the standard, the edition cited here, `utime()` and `gettimeofday()` are "marked obsolescent", and applications are told to use the newer functions. A finer unit does not promise a finer clock: "Clock resolutions are implementation-defined".

**What went wrong.** The unit changed twice, and each change added functions. Retiring the old ones took until the 2024 edition, Issue 8, which names `gettimeofday()` and `utime()` among "The functions removed in Issue 8". The microsecond `utimes()` is still in it. The unit also ran ahead of the clock. The Linux manual says: "Before Linux 2.6.21, the accuracy of timer and sleep system calls (see below) was also limited by the size of the jiffy."

Sources: [utime](https://pubs.opengroup.org/onlinepubs/9699919799/functions/utime.html) · [futimens, utimensat, utimes](https://pubs.opengroup.org/onlinepubs/9699919799/functions/futimens.html) · [pselect, select](https://pubs.opengroup.org/onlinepubs/9699919799/functions/pselect.html) · [gettimeofday](https://pubs.opengroup.org/onlinepubs/9699919799/functions/gettimeofday.html) · [clock_getres](https://pubs.opengroup.org/onlinepubs/9699919799/functions/clock_getres.html) · [sys/stat.h](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/sys_stat.h.html). These pages are the 2018 edition of Issue 7. For Issue 8: [rationale, with the list of removed functions](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xsh_chap01.html) · [function index](https://pubs.opengroup.org/onlinepubs/9799919799/idx/functions.html). For Linux: [time(7)](https://man7.org/linux/man-pages/man7/time.7.html).

## syslog timestamps

The syslog format described in RFC 3164, in August 2001, has a timestamp "in the format of "Mmm dd hh:mm:ss"". It has no field for a fraction of a second.

RFC 5424, in March 2009, replaced it with a timestamp derived from RFC 3339 and added an optional fraction: `TIME-SECFRAC = "." 1*6DIGIT`. "The originator SHOULD include TIME-SECFRAC if its clock accuracy and performance permit."

This change came with a new message format; RFC 5424 obsoletes RFC 3164. The fraction is optional and limited to six digits. The RFC's own example of a nanosecond value is invalid because it is "longer than the allowed 6 digits".

**What went wrong.** The six-digit limit cannot carry a nanosecond value, as that example shows. The fraction is optional, so a reader cannot count on it. The old style is also still a default in one implementation. The rsyslog documentation describes `RSYSLOG_TraditionalForwardFormat` as the "traditional forwarding format with low-precision timestamps. Useful when sending to older syslogd instances", and gives it as the default template of the forwarding module.

Sources: [RFC 3164 §4.1.2](https://www.rfc-editor.org/rfc/rfc3164.html#section-4.1.2) · [RFC 5424 §6.2.3](https://www.rfc-editor.org/rfc/rfc5424.html#section-6.2.3) · [rsyslog reserved template names](https://docs.rsyslog.com/doc/reference/templates/templates-reserved-names.html) · [rsyslog forwarding module parameters](https://docs.rsyslog.com/doc/configuration/modules/omfwd/parameters/module.html)

## HTTP validators

HTTP has met this limit before. HTTP/1.0, in May 1996, validated a cached response by its Last-Modified date. That date has one-second resolution, so a validator "defined with only one-second resolution, might be a weak validator". The failure case is "if two different responses were sent by the origin server during the same second, but both had the same Last-Modified time".

HTTP/1.1, in January 1997, added the ETag field: "The ETag entity-header field defines the entity tag for the associated entity." The date format was left alone. The current specification explains the choice: "An entity tag can be more reliable for validation than a modification date", including "where the one-second resolution of HTTP-date values is not sufficient".

Both fields remain in use. HTTP solved one-second validation with a new field beside the old one. Freshness lifetimes and Age still have the one-second unit, and this proposal treats them the same way.

**What went wrong.** Nothing was retired. Both validators are still in use, and a Last-Modified date alone is still weak when a response can change twice in one second.

Sources: [RFC 1945 §10.10](https://www.rfc-editor.org/rfc/rfc1945.html#section-10.10) · [RFC 2068 §14.20](https://www.rfc-editor.org/rfc/rfc2068.html#section-14.20) · [RFC 9110 §8.8.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.1) · [§8.8.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.2.2) · [§8.8.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3)

## Web timers

This example is here for its result. A web page's original clock counts "time in milliseconds since 01 January, 1970 UTC". The High Resolution Time specification lists its limits: it is "subject to both clock skew and adjustment of the system clock", and it "Does not provide sub-millisecond time resolution." The specification added `performance.now()` beside it, "providing monotonically increasing time values with sub-millisecond resolution".

**What went wrong.** Fine timers then became a tool for attacks. In January 2018, in response to Spectre and Meltdown, Mozilla wrote that "The resolution of performance.now() will be reduced to 20µs", as "a partial, short-term, mitigation". The specification now says that "cache attacks, statistical fingerprinting and micro-architectural attacks are a privacy and security concern", and sets the resolution at "100 microseconds, or a higher implementation-defined value", or 5 microseconds for a cross-origin isolated page, again with a higher value allowed.

Web timers are still finer than a millisecond, but the resolution is now chosen with the observer in mind. The draft applies this from the start: by default a cache does not generate `Age-Ms` or `ttl-ms`. An operator configures which recipients are sent them.

Sources: [High Resolution Time](https://www.w3.org/TR/hr-time-3/) (a W3C Working Draft) · [MDN: Performance.now()](https://developer.mozilla.org/en-US/docs/Web/API/Performance/now#security_requirements) · [Mozilla Security Blog, 3 January 2018](https://blog.mozilla.org/security/2018/01/03/mitigations-landing-new-class-timing-attack/)

## Systems that kept whole seconds

Not every cache moved.

- **DNS.** The time to live is "a 32 bit unsigned integer that specifies the time interval (in seconds) that the resource record may be cached before it should be discarded". Staying coarse did not avoid corrections: RFC 2181 found the definition "not as clear as it could be, with respect to how many significant bits exist, and whether the value is signed or unsigned", and fixed its range, not its unit. [RFC 1035 §4.1.3](https://www.rfc-editor.org/rfc/rfc1035.html#section-4.1.3) · [RFC 2181 §8](https://www.rfc-editor.org/rfc/rfc2181.html#section-8)
- **memcached.** Expiry is a number of seconds, and "Time is internally updated on second boundaries, which makes expiration time roughly +/- 1s." So "a TTL of 1 will sometimes immediately expire". One field also has two meanings: above 30 days, "the server will consider it to be real Unix time value rather than an offset from current time". [Protocol](https://raw.githubusercontent.com/memcached/memcached/master/doc/protocol.txt)
- **CoAP.** A protocol from 2014 also chose seconds for Max-Age: "an integer number of seconds between 0 and 2**32-1 inclusive". [RFC 7252 §5.10.5](https://www.rfc-editor.org/rfc/rfc7252.html#section-5.10.5)

Newer transport and media protocols chose milliseconds from the start.

- **QUIC.** "The maximum idle timeout is a value in milliseconds that is encoded as an integer". [RFC 9000 §18.2](https://www.rfc-editor.org/rfc/rfc9000.html#section-18.2)
- **Media over QUIC Transport.** The cache duration for a relay "is an integer expressing the number of milliseconds an Object can be served from a cache." This is an Internet-Draft and can change. [draft-ietf-moq-transport-23 §10.3](https://datatracker.ietf.org/doc/html/draft-ietf-moq-transport-23)

A whole-second unit is not a defect in itself. It depends on what the system is used for.

## What worked

| Observation | Examples | In this proposal |
|---|---|---|
| The fine value got a new name; the old value kept its unit | Redis, Linux, Kafka, POSIX, ETag, `performance.now()` | `max-age-ms` beside `max-age`; `Age-Ms` beside `Age` |
| A stated rule says which value applies | Kafka's precedence; HLS's version number | The companion applies on a configured path; otherwise the base applies |
| The old form kept working | Redis, Linux, Kafka, HLS, ETag. POSIX kept two old functions until 2024 | A cache that does not know the companions follows RFC 9111 unchanged |

## Lessons

Each row is a problem recorded above; its sources are in the section for each system named under "Where". The last two columns say what the draft does and whether that settles it. Four rows are addressed. The rest are partly addressed, open, or accepted as costs.

| What went wrong | Where | What this proposal does | Status |
|---|---|---|---|
| A finer format carried values from a coarse clock | Linux file timestamps; POSIX clock resolution | An age is rounded up to the resolution of the clock readings used, and is not reported more finely | Addressed in the draft. The nginx prototype had this fault; see below |
| A coarse step in the path dropped the fraction | `cp -p` and make; Git on Linux | Fine age is used only on a path configured end to end; anything else uses the whole-second base | Partly: depends on configuration. A recipient cannot detect a wrong path |
| Fine and coarse values were mixed and their order was lost | Multigrain timestamps, reverted in 2023 | `Age` and `Age-Ms` come from one estimate; a pair that disagrees is rejected | Addressed |
| Two names for one value disagreed on the unit | Kafka | The unit is in each new name, and the two values are independent | Partly. A sender can still write seconds where milliseconds are meant |
| Absent and unusual values were ambiguous | Redis `PTTL`; DNS TTL; memcached's 30-day rule | Missing, empty, duplicate, over-long and mismatched values each have a defined result | Addressed |
| Finer timing exposed information and was made coarser | `performance.now()` | `Age-Ms` and `ttl-ms` are off by default, and sent only to configured recipients | Partly. Response timing can still be observed |
| Finer time cost more | Multigrain timestamps | The cost here is origin requests. The sender chooses the lifetime | Open: the operator's decision, to be measured |
| Names multiplied | Redis, where `SET` options can now replace four commands; Kafka's three settings | Ten names are added. One general mechanism was considered and not chosen | Open: a question for the working group |
| The finer unit was not fine enough | POSIX microseconds, replaced by nanoseconds; syslog's six digits cannot carry nanoseconds | Milliseconds are chosen for range and for existing use. A later, finer companion would repeat this work | Open |
| The old form never went away | Linux keeps its obsolete settings; POSIX kept two old functions until 2024; rsyslog's forwarding default | The whole-second base is permanent and is not deprecated. Every sender still chooses it deliberately | Accepted |
| Coarse islands remained | HLS Target Duration | Date, Expires, Last-Modified and heuristic freshness stay in whole seconds | Accepted |
| Absolute times depended on clocks agreeing | Redis | The new values are durations and ages, not clock times. Each cache measures elapsed time on its own clock | Addressed for the new fields. A local clock step or suspend must be accounted for, or fine age dropped |

### The prototype made the first mistake

By default nginx reads the clock when an event arrives: "By default, gettimeofday() is called each time a kernel event is received." With `timer_resolution` set, "gettimeofday() is only called once per specified interval." The first version of the nginx prototype printed `Age-Ms` to the millisecond from that stored reading, and sent `Age-Ms` to every client. It now reads the clock for each fine decision, treats a negative age as a clock fault, and sends `Age-Ms` only where a directive turns it on. A test with `timer_resolution 100ms` fails against the old behaviour. These changes are in nginx revision `1c012f600` and are newer than the published measurements. The draft lists this and the prototype's other mistakes for implementers, under "Implementation Pitfalls".

Source: [nginx `timer_resolution`](https://nginx.org/en/docs/ngx_core_module.html#timer_resolution)
