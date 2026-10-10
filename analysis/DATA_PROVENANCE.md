# Dataset provenance and source audit

## Pinned source

- Record: [Zenodo 7291380](https://zenodo.org/records/7291380)
- DOI: [10.5281/zenodo.7291380](https://doi.org/10.5281/zenodo.7291380)
- Pinned record version: v2, published 2022-10-07; the Zenodo concept page now indicates a newer version exists, but this analysis deliberately uses the requested immutable record DOI.
- Access: open. License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). Cite Graillet et al. and retain attribution when reusing or adapting the data.
- Metadata retrieval: Zenodo record page and public record API. File sizes and MD5 values below are checked against the record and verified against the downloaded bytes before analysis.

## Files

| File | Role | Bytes | Record MD5 |
|---|---|---:|---|
| `dt1_solar_and_meteorological_measurement.csv` | CSV header: GTI, DTI, ambient temperature, module back-surface temperature (metadata image calls DTI `DHI`) | 1,541,026,563 | `5b1e14695adbae4918bff49840916616` |
| `dt2_electrical_production_inverter_1_with_faults.csv` | Experimental inverter line and `Fault` label | 135,034,852 | `b97d75f39d9545578f5ee85733a514be` |
| `dt3_electrical_production_inverter_2.csv` | Potential comparison/reference line | 126,216,618 | `c03a8016450adb65a260be7be2fff2ca` |
| `00_metadata_variable.jpg` | Variable units and fault-label descriptions | 209,622 | `e0f3296375eb4af0d38add7027f33261` |

No raw dataset bytes are included in Git. The notebook downloads the two electrical files first and requests the weather file only for its overlap audit and an optional weather-assisted candidate. All downloads are streamed and checksum verified.

## Published system and measured fields

The Zenodo description identifies a 4 kW domestic grid-connected rooftop PV system at the University of La Réunion, coordinates approximately -20.90126, 55.48422. The Data in Brief article reports electrical sampling at 0.2 Hz and meteorological sampling at 1 Hz. Its metadata image defines electrical fields `Eg` (energy injected, kWh), `Pg` (power injected, W), `Ia` (plant current, A), `Ig` (grid current, A), `Va` (PV voltage, V), `Vg` (grid voltage, V), and `Fg` (grid frequency, Hz). The metadata image names diffuse tilted irradiance `DHI`; the actual downloaded weather CSV header is `DTI`. The weather pipeline uses the actual CSV field `DTI` and records this metadata/header discrepancy. Both irradiance columns are in W/m²; `TA` and `TPV` are in °C.

The scientific setup paper describes two lines of 12 modules, two parallel strings of six modules per line, north orientation, and 26° tilt. The target file is the line where shading was introduced. It reports TE1500/TE1700 modules with maximum powers 175 W/170 W. It also states calculated line capacities of 2.04/2.09 kWp in prose, while the table's line mapping and arithmetic imply 2.10/2.04 kWp. The capacity-ratio baseline is therefore reported under both documented interpretations; the discrepancy is not silently resolved.

## Timestamp handling

Electrical CSV timestamps are parsed as ISO timestamps with a numeric `+04:00` source offset and converted to UTC for joins and JSON. The source offset is retained in the audit report. The time series is not assumed to be exactly 5 seconds merely because the publication reports 0.2 Hz: actual interval distributions, duplicates, missing rows, and exact inverter alignment are computed from the pinned bytes. The report distinguishes publication cadence from observed cadence.

## Fault and intervention labels

`Fault` occurs only in the target electrical file. The Zenodo metadata image documents `0` as no fault, `1` as uniform shading, `2.1`–`2.3` as constant full-module partial shading, `3.1`–`3.2` as constant partial-module shading, and `4` as intermittent partial shading. The label column is excluded from model predictors. It is used only for healthy-period restrictions, grouping/evaluation, and reporting documented experimental conditions.

## Publications consulted

1. Graillet, A. et al. “Electrical production data of a domestic grid-connected rooftop PV plant in normal and shading faults conditions associated with solar and meteorological data in a tropical climate.” *Data in Brief* 46 (2023), 108723. [DOI 10.1016/j.dib.2022.108723](https://doi.org/10.1016/j.dib.2022.108723). Documents the data collection and sampling rates.
2. Lebreton, C. et al. “PV System Failures Diagnosis Based on Multiscale Dispersion Entropy.” *Entropy* 24(9) (2022), 1311. [DOI 10.3390/e24091311](https://doi.org/10.3390/e24091311). Documents the system configuration, target line, module characteristics, and experimental context.

## Computed audit outputs

Exact row counts, observed date ranges, nulls, numeric ranges, timestamp intervals, duplicate/out-of-order counts, label counts, checksums, exact-pair overlap, and weather overlap belong in `results/data_quality_report.json`. Those values are generated only after file bytes pass the recorded size and MD5 checks; no prior dossier counts are copied into the result.
