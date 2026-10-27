# Results

## Verification and analysis set

The independent verifier checked 945 successful routes; 945 passed and 0 failed. The maximum absolute scalarized-cost discrepancy was 2.13e-14.

The primary analysis used the evaluation split. Each of the four reference configurations was compared with the full five-objective formulation on the same 94 jointly successful cases.

## Primary comparisons

Differences are method minus full composite. For minimum clearance, positive differences indicate greater clearance; for all other outcomes, negative differences indicate lower values. Bootstrap intervals are 95% percentile intervals from 10,000 paired case resamples. Wilcoxon p-values were Holm-adjusted across all 24 prespecified tests.

| Comparison | Outcome | Paired n | Median difference | 95% bootstrap CI | Wilcoxon p | Holm-adjusted p |
|---|---|---:|---:|---:|---:|---:|
| Distance-focused vs. full | Scalarized cost | 94 | 27.54 | [26.9, 28] | 3.81e-17 | 9.143e-16 |
| Distance-focused vs. full | Distance (m) | 94 | -0.01562 | [-0.4142, -0.001137] | 2.602e-12 | 2.769e-11 |
| Distance-focused vs. full | Energy (Wh) | 94 | -0.002575 | [-0.005192, 0.001963] | 0.0002209 | 0.0008838 |
| Distance-focused vs. full | Mission time (s) | 94 | -0.03123 | [-0.8284, -0.002361] | 2.602e-12 | 2.769e-11 |
| Distance-focused vs. full | Mean row error (m) | 94 | 0.3015 | [0.2821, 0.3129] | 3.81e-17 | 9.143e-16 |
| Distance-focused vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] | 1 | 1 |
| Energy-focused vs. full | Scalarized cost | 94 | 16.21 | [15.98, 16.68] | 3.81e-17 | 9.143e-16 |
| Energy-focused vs. full | Distance (m) | 94 | -0.005647 | [-0.4142, 0] | 8.285e-07 | 5.8e-06 |
| Energy-focused vs. full | Energy (Wh) | 94 | -0.006829 | [-0.01106, -0.002648] | 2.518e-12 | 2.769e-11 |
| Energy-focused vs. full | Mission time (s) | 94 | -0.01129 | [-0.8284, 0] | 8.285e-07 | 5.8e-06 |
| Energy-focused vs. full | Mean row error (m) | 94 | 0.1072 | [0.01936, 0.1499] | 1.641e-12 | 1.969e-11 |
| Energy-focused vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] | 1 | 1 |
| Soil-focused vs. full | Scalarized cost | 94 | -20.44 | [-20.93, -19.9] | 3.81e-17 | 9.143e-16 |
| Soil-focused vs. full | Distance (m) | 94 | 2.339 | [2.071, 2.899] | 2.79e-16 | 4.865e-15 |
| Soil-focused vs. full | Energy (Wh) | 94 | 0.03835 | [0.03217, 0.04787] | 3.499e-16 | 4.899e-15 |
| Soil-focused vs. full | Mission time (s) | 94 | 4.678 | [4.142, 5.799] | 2.79e-16 | 4.865e-15 |
| Soil-focused vs. full | Mean row error (m) | 94 | 0.4697 | [0.4392, 0.5116] | 3.81e-17 | 9.143e-16 |
| Soil-focused vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] | 1 | 1 |
| Distance-clearance vs. full | Scalarized cost | 94 | 8.441 | [7.774, 8.848] | 3.81e-17 | 9.143e-16 |
| Distance-clearance vs. full | Distance (m) | 94 | 1 | [1, 1.293] | 2.703e-16 | 4.865e-15 |
| Distance-clearance vs. full | Energy (Wh) | 94 | 0.01384 | [0.01286, 0.01621] | 4.107e-16 | 5.339e-15 |
| Distance-clearance vs. full | Mission time (s) | 94 | 2 | [2, 2.586] | 2.703e-16 | 4.865e-15 |
| Distance-clearance vs. full | Mean row error (m) | 94 | 0.001429 | [0, 0.009211] | 1.239e-05 | 6.195e-05 |
| Distance-clearance vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] | 5.798e-08 | 4.638e-07 |

## Robustness across splits

The following descriptive checks repeat the paired median estimates separately for the pilot and evaluation splits.

| Split | Comparison | Outcome | Paired n | Median difference | 95% bootstrap CI |
|---|---|---|---:|---:|---:|
| pilot | Distance-focused vs. full | Scalarized cost | 95 | 27.61 | [26.76, 28.02] |
| pilot | Distance-focused vs. full | Distance (m) | 95 | -0.00388 | [-0.01923, 0] |
| pilot | Distance-focused vs. full | Energy (Wh) | 95 | 0.0009098 | [-0.005404, 0.001963] |
| pilot | Distance-focused vs. full | Mission time (s) | 95 | -0.007759 | [-0.03845, 0] |
| pilot | Distance-focused vs. full | Mean row error (m) | 95 | 0.3 | [0.2752, 0.3103] |
| pilot | Distance-focused vs. full | Minimum clearance (m) | 95 | 0 | [0, 0] |
| evaluation | Distance-focused vs. full | Scalarized cost | 94 | 27.54 | [26.92, 28] |
| evaluation | Distance-focused vs. full | Distance (m) | 94 | -0.01562 | [-0.4142, -0.0008586] |
| evaluation | Distance-focused vs. full | Energy (Wh) | 94 | -0.002575 | [-0.005191, 0.001963] |
| evaluation | Distance-focused vs. full | Mission time (s) | 94 | -0.03123 | [-0.8284, -0.002273] |
| evaluation | Distance-focused vs. full | Mean row error (m) | 94 | 0.3015 | [0.2821, 0.3129] |
| evaluation | Distance-focused vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] |
| pilot | Energy-focused vs. full | Scalarized cost | 95 | 16.22 | [15.85, 16.75] |
| pilot | Energy-focused vs. full | Distance (m) | 95 | 0 | [-0.01105, 0] |
| pilot | Energy-focused vs. full | Energy (Wh) | 95 | -0.001963 | [-0.007811, -5.81e-05] |
| pilot | Energy-focused vs. full | Mission time (s) | 95 | 0 | [-0.02346, 0] |
| pilot | Energy-focused vs. full | Mean row error (m) | 95 | 0.11 | [0.01881, 0.1518] |
| pilot | Energy-focused vs. full | Minimum clearance (m) | 95 | 0 | [0, 0] |
| evaluation | Energy-focused vs. full | Scalarized cost | 94 | 16.21 | [15.97, 16.7] |
| evaluation | Energy-focused vs. full | Distance (m) | 94 | -0.005647 | [-0.4142, 0] |
| evaluation | Energy-focused vs. full | Energy (Wh) | 94 | -0.006829 | [-0.01105, -0.002648] |
| evaluation | Energy-focused vs. full | Mission time (s) | 94 | -0.01129 | [-0.8284, 0] |
| evaluation | Energy-focused vs. full | Mean row error (m) | 94 | 0.1072 | [0.01936, 0.1529] |
| evaluation | Energy-focused vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] |
| pilot | Soil-focused vs. full | Scalarized cost | 95 | -20.31 | [-21.11, -19.77] |
| pilot | Soil-focused vs. full | Distance (m) | 95 | 2.485 | [2.071, 3.607] |
| pilot | Soil-focused vs. full | Energy (Wh) | 95 | 0.04224 | [0.03316, 0.05912] |
| pilot | Soil-focused vs. full | Mission time (s) | 95 | 4.971 | [4.142, 7.213] |
| pilot | Soil-focused vs. full | Mean row error (m) | 95 | 0.4879 | [0.4439, 0.5533] |
| pilot | Soil-focused vs. full | Minimum clearance (m) | 95 | 0 | [0, 0] |
| evaluation | Soil-focused vs. full | Scalarized cost | 94 | -20.44 | [-20.93, -19.9] |
| evaluation | Soil-focused vs. full | Distance (m) | 94 | 2.339 | [2.071, 2.899] |
| evaluation | Soil-focused vs. full | Energy (Wh) | 94 | 0.03835 | [0.03185, 0.04777] |
| evaluation | Soil-focused vs. full | Mission time (s) | 94 | 4.678 | [4.142, 5.799] |
| evaluation | Soil-focused vs. full | Mean row error (m) | 94 | 0.4697 | [0.4425, 0.5175] |
| evaluation | Soil-focused vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] |
| pilot | Distance-clearance vs. full | Scalarized cost | 95 | 8.621 | [8.144, 9.004] |
| pilot | Distance-clearance vs. full | Distance (m) | 95 | 1 | [1, 1.294] |
| pilot | Distance-clearance vs. full | Energy (Wh) | 95 | 0.01384 | [0.01319, 0.01726] |
| pilot | Distance-clearance vs. full | Mission time (s) | 95 | 2 | [2, 2.588] |
| pilot | Distance-clearance vs. full | Mean row error (m) | 95 | 0.01201 | [0.002977, 0.02924] |
| pilot | Distance-clearance vs. full | Minimum clearance (m) | 95 | 0 | [0, 0] |
| evaluation | Distance-clearance vs. full | Scalarized cost | 94 | 8.441 | [7.789, 8.848] |
| evaluation | Distance-clearance vs. full | Distance (m) | 94 | 1 | [1, 1.293] |
| evaluation | Distance-clearance vs. full | Energy (Wh) | 94 | 0.01384 | [0.01254, 0.01621] |
| evaluation | Distance-clearance vs. full | Mission time (s) | 94 | 2 | [2, 2.586] |
| evaluation | Distance-clearance vs. full | Mean row error (m) | 94 | 0.001429 | [0, 0.008885] |
| evaluation | Distance-clearance vs. full | Minimum clearance (m) | 94 | 0 | [0, 0] |

## Completion outcomes

| Split | Method | Status counts |
|---|---|---|
| evaluation | Distance-focused | no_path: 2, success: 94 |
| evaluation | Energy-focused | no_path: 2, success: 94 |
| evaluation | Soil-focused | no_path: 2, success: 94 |
| evaluation | Distance-clearance | no_path: 2, success: 94 |
| evaluation | full | no_path: 2, success: 94 |
| pilot | Distance-focused | no_path: 1, success: 95 |
| pilot | Energy-focused | no_path: 1, success: 95 |
| pilot | Soil-focused | no_path: 1, success: 95 |
| pilot | Distance-clearance | no_path: 1, success: 95 |
| pilot | full | no_path: 1, success: 95 |

## Interpretation boundary

Scalarized-cost comparisons reflect each configuration’s declared objective and do not establish cross-method superiority. Results apply only to the implemented synthetic grid-world model, its declared parameters, and its generated cases; they do not establish field performance, physical-robot validity, calibrated energy consumption, agronomic benefit, or real-world routing superiority.
