\# Prespecified analysis plan — development v6



\## Data



\- Primary data: `evaluation\_records\_v6.jsonl`, frozen in `development\_manifest\_v6.json`.

\- Primary analysis set: evaluation cases in which a given method and the full-composite method both succeeded.

\- Expected primary paired set: 94 cases.

\- The three cases with `no\_path` for every method—evaluation F2/02, evaluation F2/04, and pilot F6/11—are reported separately as admissibility outcomes. They are not excluded from the outcome table.

\- No additional cases, metrics, subgroup analyses, or outcome transformations will be added after analysis begins.



\## Research questions



1\. Do the single-objective and two-objective routing methods differ from the full-composite method on simulation route outcomes?

2\. Are observed differences consistent across the pilot and evaluation splits?



This study assesses a synthetic grid-world planning model. It does not estimate real-world field performance.



\## Outcomes



Primary outcome:



\- Scalarized cost under each method’s declared objective.



Secondary outcomes:



\- Distance (m).

\- Energy (Wh).

\- Mission time (s).

\- Mean row error (m).

\- Minimum swept-body clearance (m).



For clearance, higher values indicate more clearance. For all other outcomes, lower values are better.



\## Comparisons



Within each evaluation case, compare each method with the full-composite method:



1\. Distance versus full composite.

2\. Energy versus full composite.

3\. Soil versus full composite.

4\. Distance-clearance versus full composite.



The full-composite method is the reference because it combines all five declared cost components.



\## Statistical analysis



For each method comparison and each outcome:



\- Estimate the median within-case difference (method minus full composite).

\- Use paired bootstrap resampling of cases with 10,000 resamples.

\- Report a two-sided 95% percentile bootstrap confidence interval.

\- Use a two-sided paired Wilcoxon signed-rank test on the within-case differences.

\- Adjust Wilcoxon p-values across the 24 method-by-outcome tests using the Holm–Bonferroni procedure.

\- Treat adjusted p < 0.05 as statistically significant.



No subgroup analyses, covariate adjustments, or alternative significance thresholds are planned.



\## Missing and inadmissible outcomes



\- A method-case is missing from a paired comparison only when that method or the full-composite method did not produce a successful, verified route.

\- The number of paired cases is reported for every comparison.

\- `no\_path` outcomes are counted and reported, but not imputed.

\- No sensitivity analysis that changes the primary analysis set is planned.



\## Robustness analyses



Run the following after the primary analysis:



1\. Repeat paired median estimates and bootstrap intervals separately for pilot and evaluation splits.

2\. Report the percentage of paired cases in which each method has a lower value than full composite for each non-clearance outcome.

3\. For clearance, report the percentage of paired cases in which each method has a higher value than full composite.



These are descriptive robustness checks, not additional confirmatory tests.



\## Verification requirement



Before inferential results are interpreted, an independent route-and-cost verifier must:



\- Recompute route length, energy, time, row integral, and swept clearance from route states.

\- Use separately written geometry and cost implementations, not imports from the planner’s cost functions.

\- Confirm every successful evaluation route against the planner-reported scalarized cost within numerical tolerance.

\- Report the number of routes checked, number passed, and maximum absolute cost discrepancy.



\## Interpretation boundary



Results apply only to the implemented synthetic grid-world model, its declared parameters, and its generated cases. They do not establish field performance, physical-robot validity, calibrated energy consumption, agronomic benefit, or real-world routing superiority.

