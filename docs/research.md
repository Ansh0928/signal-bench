# Research basis

Sources reviewed on 29–30 September 2026. The project is motivated by a real
failure class and documented verification work; it does not establish a current
BiVACOR defect, missing tool, or internal bottleneck.

## 1. Documented communication failure in a comparable technology

[FDA: Class 1 Device Recall, HeartMate Touch Communication System](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfres/res.cfm?id=205152)

Recall initiated 3 January 2024; posted 2 February 2024. The record describes
unexpected pump start/stop and identifies software design as the cause. Its
corrective guidance addresses interruption of communication before completion
of the stop-pump sequence.

This supports investigating interrupted command sequences. It does not disclose
the manufacturer's implementation or establish duplicate IDs as the cause.
Our two intentionally flawed guards are constructed teaching examples, not a
reproduction of the recalled software.

## 2. Direct evidence of BiVACOR's verification work

[BiVACOR: Electrical Engineer II](https://bivacor.com/careers/electrical-engineer-ii/)

The published role describes external controller/peripheral verification,
component and integration testing, specialised tooling, test coverage, and
coordination of test-software development. This establishes relevance to the
company's public engineering work, not a vacancy guarantee or proof of unmet need.

[BiVACOR: US internships](https://bivacor.com/careers/internships-2/)

The US internship page includes controller/peripheral tests, analysis, and test
records. It concerns the Huntington Beach programme and must not be confused
with the user's separate Gold Coast internship notice.

## 3. Controller development context

[AUScelerate: Advancing a Next-Generation Total Artificial Heart for Long-Term Use](https://auscelerate.org/advancing-a-next-generation-total-artificial-heart-for-long-term-use/)

Published 26 May 2026. The programme report describes long-term controller
development, reliability/interface improvements, and completed testing milestones.
It is evidence of the development context, not an unresolved issue report.

## Project hypothesis to validate with the team

Repeatable communication fault scenarios and automatically collected evidence
could reduce effort when investigating interrupted commands or extending
regression coverage. We have not measured the company's workflow or validated
this hypothesis with its engineers.

A useful question for Nils: “Would extending communication regression tests or
improving reproduction of intermittent faults be a useful intern contribution?”

No manufacturer protocols, real device connections, clinical data, names, or logos
are required by the prototype.
