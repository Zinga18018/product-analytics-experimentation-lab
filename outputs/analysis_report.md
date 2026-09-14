# Product Analytics Experimentation Report

Synthetic data only. This is a fixed-horizon demonstration, not a measured business outcome.

## Dataset

- users: 5,000
- experiment_assignments: 5,000
- sessions: 22,287
- events: 64,908

## Declared analysis policy

These are illustrative policy settings. In a real experiment, agree on them before inspecting outcomes.

- Experiment: `onboarding_redesign`; exclusive UTC cutoff: `2026-03-02`.
- Conversion and revenue windows: first 7 and 7 days after assignment, respectively.
- Retention: any session on days 1-7 after assignment.
- Require all 8 follow-up days: 4,413 eligible users; 587 enrolled users excluded as immature.
- Denominator: all eligible assigned users, including users with no activity or purchases.
- Expected treatment allocation: 50%; SRM threshold: 0.001.
- Minimum eligible users per arm: 100; confidence level: 95%.
- Minimum conversion lift: 0.00%; allowed retention loss: 2.00 percentage points; allowed revenue loss: 1.00 currency units per assigned user.

## Experiment readout

All differences below are treatment minus control; intervals are two-sided.

| Metric | Control | Treatment | Difference | Confidence interval |
| --- | ---: | ---: | ---: | --- |
| Purchase conversion | 17.62% | 21.22% | 3.59% | [1.26%, 5.92%] |
| Retention | 61.27% | 60.65% | -0.61% | [-3.49%, 2.26%] |
| Revenue per assigned user | 20.9217 | 25.3092 | 4.3875 | [1.0814, 7.6936] |

- Eligible control/treatment users: 2,179/2,234.
- Purchase control/treatment users: 384/474.
- Two-proportion conversion p-value: 0.0026.
- Relative conversion lift: 20.3985% (undefined when control conversion is zero).
- Binary difference intervals: Newcombe method using Wilson score bounds.
- Revenue uncertainty: Welch t interval on revenue per assigned user.

## Rollout gates

- Enrolled sample-ratio check: control=2482, treatment=2518, exact binomial p=0.6206.
- Eligible sample-ratio check: control=2179, treatment=2234, exact binomial p=0.4163.

| Gate | Result |
| --- | --- |
| minimum_sample | pass |
| sample_ratio | pass |
| conversion | pass |
| retention | blocked / unestablished |
| revenue | pass |

**Decision: hold**

Hold rollout. Retention noninferiority is not established within the declared loss tolerance.

A guardrail passes only when its lower confidence bound is above the negative loss tolerance. A non-significant harm test does not establish safety. Failing a guardrail may mean harm or insufficient precision.

## Acquisition channels (descriptive, all observed time)

These channel rankings are not causal comparisons and do not use the experiment observation window.

| acquisition_channel | users | purchasers | purchase_rate | revenue | revenue_per_user |
| --- | --- | --- | --- | --- | --- |
| referral | 601 | 365 | 0.6073211314475874 | 58490.85 | 97.32 |
| email | 515 | 316 | 0.6135922330097088 | 49255.4 | 95.64 |
| social | 890 | 490 | 0.550561797752809 | 74035.71 | 83.19 |
| organic | 1732 | 927 | 0.5352193995381063 | 143780.98 | 83.01 |
| paid_search | 1262 | 687 | 0.5443740095087163 | 104653.05 | 82.93 |

## Signup-cohort retention

Activity windows are days 1-7, 8-14, and 15-30. Each includes inactive users and only users with complete follow-up for that window. Unavailable windows are labeled unavailable, not zero.

| signup_week | cohort_users | eligible_7d_users | retained_7d_users | retention_7d | eligible_14d_users | retained_14d_users | retention_14d | eligible_30d_users | retained_30d_users | retention_30d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-00 | 353 | 353 | 143 | 0.40509915014164305 | 353 | 142 | 0.40226628895184136 | 353 | 253 | 0.71671388101983 |
| 2026-01 | 549 | 549 | 226 | 0.4116575591985428 | 549 | 246 | 0.44808743169398907 | 549 | 403 | 0.7340619307832422 |
| 2026-02 | 557 | 557 | 264 | 0.473967684021544 | 557 | 272 | 0.4883303411131059 | 557 | 433 | 0.77737881508079 |
| 2026-03 | 640 | 640 | 316 | 0.49375 | 640 | 346 | 0.540625 | 640 | 535 | 0.8359375 |
| 2026-04 | 599 | 599 | 360 | 0.6010016694490818 | 599 | 391 | 0.6527545909849749 | 448 | 392 | 0.875 |
| 2026-05 | 562 | 562 | 373 | 0.6637010676156584 | 562 | 405 | 0.7206405693950177 | 0 | 0 | unavailable |
| 2026-06 | 568 | 568 | 462 | 0.8133802816901409 | 568 | 458 | 0.8063380281690141 | 0 | 0 | unavailable |
| 2026-07 | 585 | 585 | 546 | 0.9333333333333333 | 0 | 0 | unavailable | 0 | 0 | unavailable |
| 2026-08 | 587 | 0 | 0 | unavailable | 0 | 0 | unavailable | 0 | 0 | unavailable |

## Limitations

- Fixed-horizon, user-randomized, two-arm design only. No correction for repeated looks or exploratory segment testing.
- Confidence intervals are marginal, not a simultaneous joint confidence region. All prespecified gates must pass; this is a conservative review rule, not automatic deployment.
- Revenue intervals use Welch's approximation; heavy tails, refunds, incomplete event capture and novelty effects require further diagnostics in real data.
- Minimum sample size is an illustrative floor, not a power calculation. Synthetic generator effects cannot establish real customer value.
