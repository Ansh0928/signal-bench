# Report design

The audience is an engineering reviewer inspecting a reproducible communication fault.
The main job is to compare a broken implementation with the protected implementation
using captured messages, assertions, and controller state.

Palette: porcelain #f5f7fa, white #ffffff, graphite #192b3c, cobalt #244cc5,
eucalyptus #17705c, brick #ad3d45. Colour denotes selection, successful checks,
and violated requirements. Text accompanies every colour-coded state.

Type: system sans-serif for navigation and explanatory text; system monospace
only for protocol frames, code, and numeric evidence. No external font dependency.

Layout: a left-aligned case navigator beside a wide experiment workspace. The
workspace begins with the failure being investigated, then shows paired outcome
summaries, a step-through message sequence, and test assertions.

    Project / run provenance                         Export / Run tests
    ------------------------------------------------------------------
    Scenario navigator | Scenario title and requirement
                       | Flawed result      Protected result
                       | Trace playback and device state
                       | Assertions and expected/actual values

Review: avoid a generic metric-card dashboard. The main visual is the actual
message exchange and highlighted failing assertion. Counts and timestamps remain
secondary. On small screens, the case navigator becomes a horizontal selector and
the protocol details stack. Reduced-motion users get immediate trace completion.

The view is a captured test report. Replay reveals recorded events and never
pretends to run a physical device. Running tests invokes the local C++ suite only
when served by tools.py; a downloaded HTML report remains a portable snapshot.
