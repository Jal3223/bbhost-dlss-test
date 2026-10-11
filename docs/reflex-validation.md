# Reflex and generated-frame pacing validation — 2026-10-11

The Vulkan integration sleeps before input and simulation, carries immutable
simulation IDs through asynchronous rendering, and attributes real and generated
presentation separately. Setup and F10 expose Off, On and On + Boost as restart
choices. Driver sleep and its CPU semaphore wait do not hold the marker mutex;
holding that mutex reproduced periodic long pauses and was corrected before the
measurements below.

The generated-pair scheduler starts earlier than the former one-subframe delay.
A bounded, slowly decaying budget for late GPU completions preserves space
between generated and real images under varying load. Its deterministic checks
cover variable completions, discontinuities and expired-position selection.

## Method

RTX 5080, driver 617.14, NGX 310.9.1, PresentMon 2.6.0, otherwise idle GPU,
driver FPS limits removed. The output request is approximately seven megapixels;
the presentation surface is 1920×1080 on a 119.88 Hz display. Tests retain the
application's `bbhost.exe` filename and layered DXGI driver profile. Copied saves
and camera sweeps in the Hunter's Dream are used for paired measurements;
Central Yharnam is checked separately. Animated-object motion vectors are on.

Runs last 110 seconds. PresentMon's measured window is 70–109 seconds; startup,
capture and shutdown are excluded. GPU tracking is disabled in these PresentMon
runs; no lost-ETW-event warning occurs in either alternating Reflex A/B round.
Source cadence and evaluation cost come from the renderer's GPU timestamps.
Driver latency reports use the last 39 seconds of completed reports with valid
input timestamps. Their window is consequently distinct from PresentMon's.

**Input-to-present means input sampling to the CPU present call. It excludes
monitor scanout and photon latency.** Display-change counts above refresh do not
establish that many complete scanouts. The measurements are local evidence on
one NVIDIA card and driver, not latency certification across hardware.

## GPU-bound Reflex comparison

Native DLAA plus DLSS 2x, game cap 60; actual real cadence is below that cap.
Both modes retain markers, the adaptive scheduler and the ordinary simulation
limiter. The only A/B choice is Reflex Off versus On.

| Run | Real FPS | Display changes/s | p99 display interval | Median input-to-present | p99 input-to-present |
| --- | ---: | ---: | ---: | ---: | ---: |
| Off / A | 52.00 | 103.38 | 13.89 ms | 79.16 ms | 87.62 ms |
| On / A | 52.90 | 105.94 | 13.50 ms | 41.70 ms | 49.16 ms |
| Off / B | 52.63 | 104.30 | 13.73 ms | 78.68 ms | 88.03 ms |
| On / B | 52.93 | 105.60 | 13.20 ms | 41.50 ms | 47.31 ms |

All four measured display windows have zero missing timing rows. Each On run
skips one expired generated position in its sampled source window; Off skips
none. No sampled resets suppress interpolation. The median driver-reported
input-to-GPU-end interval changes from 80–81 ms to approximately 43 ms. Shared
queue attribution has weaker precision than the tested dedicated compositor
queue, so these GPU reports must not be generalized to that fallback.

An earlier fixed 2 ms launch budget produced a 19.02 ms p99 display interval
under this workload. Adapting the budget brought the exploratory repeat to
13.57 ms and the two final On runs to 13.50/13.20 ms. This exploratory comparison
is separate from the clean alternating A/B measurements above.

## Source-rate and changing-load checks

DLSS Quality plus 2x uses the same adaptive scheduler and Reflex On. The 40/50
cases select 60 FPS simulation and add a diagnostic source throttle; these are
not new supported game-speed presets. The changing-load case cycles source
targets 60, 40, 30 and 50 every ten seconds. Its aggregate FPS mixes those rates
and must not be interpreted as a fixed-rate target.

| Source target | Measured real FPS | Display changes/s | p99 display interval | Missing timing rows | Expired positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| 30 | 30.00 | 60.00 | 18.45 ms | 0 | 0 |
| 40 | 40.00 | 80.00 | 14.47 ms | 0 | 0 |
| 50 | 50.00 | 100.00 | 12.96 ms | 0 | 0 |
| 60 | 59.52 | 119.13 | 11.56 ms | 0 | 2 |
| Changing targets | 44.46 | 90.31 | 18.06 ms | 0 | 0 |

The expired-position counts use the final sampled GPU-source window; they are
not a claim that startup and every transition throughout the run never skip a
position. The source and PresentMon windows differ slightly. No sampled reset
suppression occurs. Cadence remains approximately twice real FPS below the
selected cap rather than collapsing when input falls below 60.

A separate native-DLAA workload requests approximately eleven megapixels with
the selected game cap still at 60 and no diagnostic source throttle. The real
GPU-bound cadence is 38.06 FPS; 2x reaches 76.37 display changes/s, with a
16.62 ms p99 display interval and zero missing timing rows. One sampled generated
position expires, with no sampled reset suppression. This run includes the
subsequent narrow WSI guard; the earlier A/B table predates that guard.

At fixed 30 real FPS, experimental 3x reaches 90.01 display changes/s with
14.62 ms p99 intervals; 4x reaches 120.00 with 10.82 ms p99 intervals. Both have
zero missing timing rows and sampled expired/suppressed positions. These are
cadence checks on a 120 Hz display, not certification of interpolation quality
or a reason to expose higher factors as ordinary supported settings.

[Aggregate measurements](data/reflex-validation-2026-10-11.csv) retain both A/B
rounds, submission/display percentiles, driver intervals and failure counters.

## FSR pixel investigation

The GPU fixture now uses textured foreground/background planes, perspective
depth, per-pixel camera motion and an analytic midpoint. It requires centroid
error ≤2 output pixels, foreground silhouette IoU ≥0.93, area error ≤7%, and
mean normalized background error ≤0.0125. Motion-vector scale is one for
pixel-valued vectors, matching the host adapter.

Camera motion at 16, 32 and 64 render pixels per source frame passes with
synchronization validation: midpoint error rounds to 0.00 pixels, IoU is 1.0000,
area error is 0.0000, and background error is 0.0006/0.0004/0.0004. Outputs are
finite and the resize/resource-retirement fixture passes at all three speeds.
The 64-pixel fixture uses fewer history frames to keep its endpoints in view;
this is a controlled planar test, not a gameplay quality score.

An owned-output gameplay readback captures HUD-free input, the real endpoint,
the generated image, HUD color and its alpha mask after compositor retirement.
The inspected fast-pan mask is confined to HUD pixels. The generated world image
still shows breakup around fine branches and disoccluded detail. Those artifacts
remain a limitation of the current analytical provider/integration; the passing
fixture and mask do not prove every gameplay guide or occlusion case correct.
No speculative vector sign/scale or HUD threshold adjustment is shipped.

## Synchronization limits

NGX runtime 310.9.1 emits internal `nv.ngx.dlssg.resource` synchronization
diagnostics. The first transition/clear hazard occurs inside the vendor's
evaluation, despite host barriers before and after that call. The standalone
NGX GPU probe reproduces it without the game renderer. A host barrier cannot
repair ordering between private SDK operations inside the call. The diagnostics
remain visible; this is **not** a clean NGX synchronization-validation pass.
The related vendor report is [NVIDIA Streamline issue 84](https://github.com/NVIDIA-RTX/Streamline/issues/84).

FSR's standalone fast-pan fixture is synchronization-clean. Existing gameplay
renderer diagnostics remain visible and are compared against a paired run.
The first paired run also exposed swapchain host-thread warnings that a summary
of VUID strings alone missed. Sleep calls and timing queries now serialize with
acquire/present through a separate WSI guard; the CPU sleep wait remains outside
that guard. Marker overlap warnings are retained and investigated against the
explicit [marker concurrency exception](https://docs.vulkan.org/refpages/latest/refpages/source/vkSetLatencyMarkerNV.html),
which permits concurrent swapchain use except destruction. A clean GPU hazard
check must not be described as a wholly warning-free validation run.
The repeated DLSS 2x run with the WSI guard has no sleep/query threading
conflicts and no `SYNC-HAZARD` reports. Eleven marker-overlap reports remain;
they are retained rather than filtered. The standalone NGX probe still reports
ten write-after-write and ten read-after-write hazards inside its evaluations.

## Build and menu checks

All eight locally registered checks pass, including the FSR GPU fixture. The
fixture also passes with the validation DLL/manifest explicitly selected at
16/32/64-pixel camera speeds. Hosted fixture skips are not treated as GPU proof.

Setup changes Off to On + Boost and saves both the options choice and
`[dlss] reflex = "boost"`. A restart reports successful driver mode/boost values
of one. F10 renders in output space, identifies Reflex as restart-required,
cycles Boost to Off and saves the options choice; the active driver's Boost
mode remains unchanged until restart, as intended.
The next Central Yharnam restart reads that saved Off choice and reports
`lowLatencyMode=0`, `boost=0`, with generation active and a normal gameplay
picture. Both test areas use separate copied saves.

The new build's Hunter's Dream F12 check reports no clipped target-size
problems, lost clears, stale uploads or stale copy-back data, and 46 float
targets with no infinite or NaN texels. Diagnostic captures are excluded from
the performance tables.
The Central Yharnam F12 check also passes the same resource/finite-value checks.

On the final WSI-guard build, FSR 3 Quality plus FSR 2x at 30 real FPS measures
60.00 display changes/s and 18.48 ms p99 intervals. FSR 4 source-v07 Quality plus
the same generation backend measures 60.00 and 18.40 ms. Both have zero missing
timing rows and no sampled expired positions/reset suppression. One malformed
FSR 4 driver timing report is rejected by the latency analyzer and retained in
the aggregate's invalid-report count.

## Scope

2x remains the ordinary menu choice. Higher DLSS factors remain opt-in while
the 120 Hz display, backpressure and artifact limits are assessed. FSR supports
2x only; its optional source-v07 FSR 4 model is reconstruction, not ML frame
generation. Multiplayer should retain 60 FPS simulation.

See [Reflex configuration and diagnostics](reflex.md),
[DLSS development](dlss-development.md) and [FSR validation](fsr-validation.md).
