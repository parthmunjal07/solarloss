# Solar ageing and performance-loss research plan

**Disposition:** do not estimate an ageing rate from the present La Réunion shading study. Its observation and design address short shading interventions at one installation; they do not identify long-term module degradation or fleet performance loss. Adding an unverified age multiplier to V2 is **REJECT**.

## Define the quantity before collecting data

Keep two estimands separate:

1. **Module degradation:** change in module maximum power or other explicitly measured module property under stable, controlled reference conditions, usually supported by repeated laboratory I–V characterization at standard test conditions. This is closer to a physical module property, but does not by itself describe the plant's operational energy loss.
2. **Plant performance loss:** long-term trend in normalized system energy or performance after accounting for expected solar resource and temperature, filtering downtime and other known operational effects under a declared method. This is a system outcome and may combine modules, inverter, wiring, availability, soiling, configuration, and measurement effects depending on exclusions. Do not call it module ageing unless those components are identified.

The [NREL PV Lifetime project report](https://www.nrel.gov/docs/fy24osti/90651.pdf) illustrates why the measures should stay distinct: module maximum-power degradation is characterized with accurate indoor I–V measurements under constant conditions and compared with field-performance analysis. [RdTools documentation](https://rdtools.readthedocs.io/en/stable/) similarly distinguishes its year-on-year degradation-rate workflow from performance-loss-rate accounting and describes sensor drift as a bias risk.

## Minimum site record

For a defensible plant-level trend, collect and preserve:

- Commissioning date, system and module make/model/serial or cohort, nameplate ratings and layout, inverter and firmware, string topology, orientation/tilt/tracking, DC/AC ratio, export-meter definition, and every replacement, repower, reconfiguration, and capacity change.
- Time-stamped AC energy or power with units, interval semantics, clock synchronization, missingness and quality flags; DC string or inverter data where available; and a source-of-record lineage.
- Plane-of-array irradiance and module temperature where possible, plus ambient temperature and weather; sensor make, location, cleaning, calibration certificates, calibration dates, sensor replacement and drift checks. Cross-check irradiance against an independent satellite/reanalysis or redundant calibrated sensor when feasible.
- Inverter availability and state, outages, curtailment, clipping, grid constraints, alarms, firmware/control changes, shading changes, vegetation, soiling and cleaning dates, snow or storm events, and technician work records.
- At least several full seasonal cycles, with sufficient valid observations in comparable conditions. A practical plan should target five or more years where data access allows, but there is no universal duration that cures bad sensor quality or system changes. Predeclare the observation span and completeness threshold after the site's cadence and climate are known.
- For module-level degradation claims, periodic independent I–V measurements, controlled-condition Pmax/STC corrections, module identity and chain of custody, measurement uncertainty, degradation/repair history, and reference/control modules or a comparable cohort.

These requirements align with the intent of [IEC 61724-1:2021](https://webstore.iec.ch/en/publication/65561), which defines PV performance-monitoring terminology, equipment, methods and system classes and updates irradiance and soiling monitoring guidance. Consult the licensed standard and choose a monitoring class appropriate to the intended claim; this plan does not reproduce normative requirements.

## Analysis plan and uncertainty

1. **Freeze data provenance and estimand.** Hash immutable raw files; record site, system, sensor, units, timestamp convention, cadence, time zone, calibration periods, metadata sources, transformations, exclusions, and protocol/software versions.
2. **Build an auditable quality screen.** Check timestamp continuity, power/energy consistency, daylight support, irradiance and temperature range, meter/sensor outages, clipping, curtailment, inverter downtime, and system changes. Keep both original and filtered data with reason codes.
3. **Construct normalized daily performance series.** Choose a transparent normalization approach suitable for the design, with clear irradiance, temperature, capacity, and availability treatment. Prevent unstable low-irradiance denominators; quantify effects of filtering and aggregation. Do not use a single weather model as unquestioned truth.
4. **Estimate plant trend with RdTools year-on-year (YoY) as a candidate.** The RdTools YoY method decomposes a normalized time series into year-to-year comparisons and returns a distribution and an uncertainty interval. Record the software version, filters, daily aggregation, recentering choice, interval level, exceedance statistic, all YoY slopes, and points' reuse. Treat the interval as conditional on method and input data, not as a catch-all sensor/system uncertainty.
5. **Run sensitivity and checks.** Compare sensor-based results with an independent resource source or clear-sky analysis as a sensor-drift check; vary justified filtering and seasonal coverage; inspect residual time trends, seasonal cycles, and step changes. PVPMC's [validation procedure](https://pvpmc.sandia.gov/model-validation/model-validation-procedure/) recommends error and residual analyses plus baseline comparison, and its [overview](https://pvpmc.sandia.gov/model-validation/) stresses timestamp-consistent, scrubbed data.
6. **Separate competing loss mechanisms.** Attribute known outages, curtailment, clipping, soiling/cleaning, inverter replacement, sensor replacement/drift, shading and configuration changes in separate event logs and sensitivity models. A step change after maintenance should not be forced into a gradual degradation slope. Report the primary method with and without disputed periods.
7. **Report uncertainty by source.** Provide a method-based interval for the YoY slope, temporal/site-block resampling where justified, sensor calibration uncertainty, sensitivity across filters/resource sources, valid coverage, and missing-data periods. Avoid treating adjacent daily observations as independent replicates.
8. **Validate physical module degradation separately.** Compare operational trends against repeated controlled I–V/STC measurements and reference/control modules. Agreement can strengthen the physical interpretation; disagreement is evidence that plant-level loss includes other system or measurement factors.

Report signed trend convention explicitly, for example percent change per year where a negative rate denotes decline. Do not translate that rate into lifetime, economic savings, cause, or recoverable energy without separate assumptions and evidence.

## Candidate public data

- [PVDAQ public datasets, OEDI/NREL](https://data.openei.org/submissions/4568): system performance and metadata for varied experimental and commercial sites; some sites include irradiance, temperature, wind and precipitation. This is a useful discovery source for plant-level performance methods, but each candidate system still needs metadata, sensor, operational-event and data-gap screening. A documented dataset does not imply independently adjudicated degradation labels.
- [NREL PV Lifetime project](https://www.nlr.gov/pv/lifetime) and its [2024 project report](https://www.nrel.gov/docs/fy24osti/90651.pdf): useful module-level context and repeated indoor I–V characterization. Confirm access terms and download-level provenance for any module time series before analysis.
- [NREL PV Fleet Performance Data Initiative](https://www.nrel.gov/pv/fleet-performance-data-initiative.html): relevant fleet-scale performance-loss methodology and published data products. Fleet summaries can benchmark trends but may not have unit-level intervention and sensor detail needed to attribute mechanism.

No public dataset is automatically interchangeable with SolarLoss. Before combining any dataset, audit units, AC/DC boundary, timestamps, aggregation, sensor accuracy, system changes, availability flags, label meaning, and permission/license.

## Decision and next step

- **GO:** design a separate data-collection and provenance plan for ageing/performance-loss research.
- **LIMIT:** use PVDAQ or fleet data for method development only after system-specific checks; use RdTools as a candidate method, not a truth oracle.
- **REJECT:** computing or inserting an age-based adjustment from the present V2 data.

No degradation code was executed and no degradation rate is reported. Begin with one well-documented multi-year system plus sensor and intervention history; freeze the estimand and quality gates before producing a slope.
