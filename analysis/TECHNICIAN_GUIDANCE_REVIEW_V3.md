# Technician investigation guidance review — Phase 3

**Status:** bounded candidate prompts from the existing proposed guidance, not a universal fault classifier. Every prompt remains proposed and requires owner review before frontend activation. Telemetry and retrospective shading intervention labels do not establish a physical root cause. Show the measured trigger, data limits, evidence for and against, next evidence, primary source, safety boundary, and status together.

The cited materials provide technical context; the candidate prompts below are SolarLoss design inferences and are not diagnoses established by those sources.

## Candidate checks

### 1. Sustained signed AC residual

- **Measured trigger:** target measured AC Pg differs from calibrated healthy expected target Pg beyond the frozen one-sided threshold for the declared persistence rule. Show W, timestamps, expected-model version, validity, and gaps.
- **Candidate hypothesis:** target production changed relative to the calibrated model.
- **Evidence for:** sustained residual and adequate measurement/model support.
- **Evidence against / alternatives:** reference drift or mismatch, curtailment, clipping, inverter state, temperature, sensor error, cloud gradients, or a change in the model's operating domain.
- **Next data:** inverter event/state and curtailment logs, timestamps, calibration records, independently measured irradiance, and documented site changes.
- **Reference:** [NREL PV system operations and maintenance guidance](https://docs.nlr.gov/docs/fy19osti/73822.pdf), particularly operations monitoring and troubleshooting.
- **Safety and qualification:** a trained operator may review existing records. Electrical testing and physical inspection are for qualified personnel under the site safety program.
- **Approval:** proposed; owner approval required.

### 2. PV-side voltage Va outside a matched healthy envelope

- **Measured trigger:** timestamped Va outside the comparison-inverter envelope under explicitly matched operating conditions; include voltage unit, support count, and envelope method.
- **Candidate hypothesis:** changed operating point, mismatch, or MPPT behavior is possible.
- **Evidence for:** repeatable departure under comparable Pg and irradiance.
- **Evidence against / alternatives:** Va is an operating measurement, not open-circuit voltage; temperature, irradiance, array configuration, inverter strategy, and sensor calibration can also move it.
- **Next data:** inverter MPPT/state records, array configuration and string history; a qualified professional decides whether an I–V measurement is warranted.
- **Reference:** [Sandia PVPMC DC array I–V guide](https://pvpmc.sandia.gov/modeling-guide/3-dc-array-iv/).
- **Safety and qualification:** no disconnection, live probing, or rooftop instructions. Electrical tests require qualified personnel and applicable site procedures.
- **Approval:** proposed; owner approval required.

### 3. PV-side current Ia outside a matched envelope

- **Measured trigger:** timestamped Ia departure from the matched healthy envelope, conditional on comparable reference Pg and irradiance; show units and support.
- **Candidate hypothesis:** a changed operating point or available string/current contribution is possible.
- **Evidence for:** persistent current difference under matched conditions.
- **Evidence against / alternatives:** cloud gradients, MPPT movement, sensor calibration, temperature, or string availability; a single aggregate current does not identify a module or string fault.
- **Next data:** verify irradiance sensor exposure and calibration; obtain string-resolved current or inverter MPPT records if available.
- **Reference:** [Sandia PVPMC DC array I–V guide](https://pvpmc.sandia.gov/modeling-guide/3-dc-array-iv/).
- **Safety and qualification:** no live electrical work instruction; qualified technician required for measurements beyond stored telemetry.
- **Approval:** proposed; owner approval required.

### 4. Grid-side voltage/frequency Vg/Fg departure

- **Measured trigger:** Vg or Fg outside a documented site/OEM envelope or coincident with an inverter status record; show sample quality, units, and timing.
- **Candidate hypothesis:** grid conditions may affect inverter operation.
- **Evidence for:** a time-aligned OEM event or grid-monitoring record supports review.
- **Evidence against / alternatives:** sensor spikes, timestamp mismatch, or logger limitations. SolarLoss V2 does not validate a grid-fault classifier or applicable statutory/OEM limits.
- **Next data:** OEM status/alarm logs, applicable site grid settings, sensor accuracy, and utility or professional review when indicated.
- **Reference:** [NREL PV system operations and maintenance guidance](https://docs.nlr.gov/docs/fy19osti/73822.pdf).
- **Safety and qualification:** show no generic voltage/frequency threshold as a safety or compliance determination; do not recommend grid intervention.
- **Approval:** proposed; owner approval required.

### 5. AC residual with DC-envelope departure and visible obstruction

- **Measured trigger:** supported AC residual and contemporaneous Va/Ia departures, with a timestamped visual observation of an obstruction. Do not trigger from an imposed V2 shading label alone.
- **Candidate hypothesis:** shading is consistent with observations.
- **Evidence for:** obstruction timing aligns with departures and model support is valid.
- **Evidence against / alternatives:** soiling, mismatch, MPPT response, sensor error, or inverter operation can overlap these signals; aggregate telemetry does not locate a damaged module or establish causality.
- **Next data:** safely obtained dated photographs, obstruction/shade history, array layout, weather, inverter state, and qualified site inspection if needed.
- **Reference:** [IEA PVPS Task 13 PV failure modes report](https://iea-pvps.org/wp-content/uploads/2025/02/IEA-PVPS-T13-30-2025-PVFS-ANNEX-Degradation-and-Failure.pdf).
- **Safety and qualification:** no rooftop access directions; inspection follows the site's access and electrical-safety program.
- **Approval:** proposed; owner approval required.

### 6. Persistent reduction with reported contamination

- **Measured trigger:** persistent supported measured-versus-modelled deviation plus a separately recorded observation of contamination.
- **Candidate hypothesis:** soiling is a possible contributor.
- **Evidence for:** dated inspection and independent soiling measurement align with the period.
- **Evidence against / alternatives:** shading, equipment changes, sensor drift, aging, curtailment, and inverter state remain possible; V2 contains no validated cleaning intervention outcome.
- **Next data:** inspection/maintenance records, independent soiling measurement, rain/cleaning history, and repeat performance under comparable irradiance.
- **Reference:** [NREL PV system operations and maintenance guidance](https://docs.nlr.gov/docs/fy19osti/73822.pdf), section on soiling and cleaning decisions.
- **Safety and qualification:** no automatic cleaning prescription or savings claim; work follows the site maintenance plan and qualified access controls.
- **Approval:** proposed; owner approval required.

### 7. Missing, invalid, or unsupported aligned measurements

- **Measured trigger:** absent, invalid, stale, or non-aligned values; report missing channels, gap duration, last valid time, and quality reason. Never render missing power as zero generation.
- **Candidate hypothesis:** the production assessment cannot be completed; acquisition or logger issue is one possibility.
- **Evidence for:** direct timestamps, quality flags, missingness, and calibration/configuration records.
- **Evidence against / alternatives:** a data gap does not establish logger failure; an outage, communications loss, source-export gap, or unsupported model domain can produce similar absence.
- **Next data:** verify timestamp configuration, acquisition logs, units, channel mapping, and calibration history before rerunning the assessment.
- **Reference:** [NREL PV system operations and maintenance guidance](https://docs.nlr.gov/docs/fy19osti/73822.pdf), monitoring and troubleshooting guidance.
- **Safety and qualification:** existing-log review can be performed without physical electrical intervention. Escalate field work to qualified personnel.
- **Approval:** proposed; owner approval required.

## Display rules

- Keep the measured observation and its unit/time/support in view with the candidate hypothesis.
- Separate evidence supporting the hypothesis from counterevidence and unresolved alternatives.
- Ask for existing records or safe observations before implying invasive inspection.
- Do not infer general-fault diagnosis from the V2 imposed shading label.
- Never describe Ig as an independent confirmation of Pg; grid current and AC power are coupled operating quantities.
- Do not show OEM-specific thresholds, alarms, repair instructions, or a fault-class badge without verified equipment identity and reviewed OEM documentation.
- Keep owner approval status visible. No proposed prompt is approved by this work.

Universal root-cause classification, repair recommendations, and recovered-energy claims remain **REJECT** for the current evidence.
