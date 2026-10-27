\# Agricultural Scouting Route Planning



Reproducible code and evaluation artifacts for multi-objective,

heading-aware route planning for prescribed-waypoint agricultural scouting.



\## Scope



This repository supports offline route planning on known static maps.

It does not implement perception, localization, actuator commands,

closed-loop control, or physical-robot execution.



\## Repository structure



\- `scripts/` — case generation, planning, evaluation, verification, analysis, and figure scripts

\- `configs/` — dependency, environment, and release configuration records

\- `data/synthetic/` — synthetic case inputs, to be generated or added

\- `data/real\_dem/` — real-DEM demonstration inputs, to be added

\- `results/v6\_frozen/` — locked v6 pilot and evaluation records and analyses

\- `results/real\_dem/` — real-DEM demonstration results, to be added

\- `results/baseline/` — position-only A\* baseline results, to be added

\- `figures/` — generated manuscript figures

\- `tests/` — validation tests, to be added



\## Locked v6 benchmark



The `results/v6\_frozen/` folder contains the locked v6 pilot and evaluation

records, independent verification summary, statistical analysis outputs,

and release manifests.



The v6 evaluation compares five objective configurations:



\- Distance-focused

\- Energy-focused

\- Soil-focused

\- Distance-clearance

\- Full five-objective formulation



All configurations use the same maps, missions, motion abstraction,

hard constraints, and evaluation metrics.



\## Reproduce the locked v6 evaluation



```bash

python scripts/agri\_generator\_v3.py

python scripts/agri\_pilot\_v6.py

python scripts/agri\_evaluation\_v6.py

python scripts/independent\_verifier\_v6.py

python scripts/analysis\_v6.py

python scripts/make\_figures\_v6.py

```



The exact command-line arguments may depend on the original release workflow.

Consult the script headers and `results/v6\_frozen/release\_manifest\_v6.json`

for the archived run configuration.



\## Scope of claims



This repository characterizes objective-dependent scouting-route trade-offs

within a shared computational planning framework. It does not establish

field deployment, physical energy savings, soil-compaction reduction,

or superiority over external planning systems.

