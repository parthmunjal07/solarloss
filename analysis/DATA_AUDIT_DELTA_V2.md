# Data audit delta v2

All four cached originals were reverified; no raw values are synthetic. Full row audits were rerun. Source record: [Zenodo 7291380](https://zenodo.org/records/7291380). Cite Graillet et al.; retain original attribution when sharing derivatives. A newer record exists but is not substituted.

| File | Rows | Bytes | MD5 | SHA256 |
|---|---:|---:|---|---|
| dt1_solar_and_meteorological_measurement.csv | 30981240 | 1541026563 | 5b1e14695adbae4918bff49840916616 | a9536c48abd08cdd85a083fe71f3972abf279816f191213cf2ba28c8d084e4aa |
| dt2_electrical_production_inverter_1_with_faults.csv | 1990478 | 135034852 | b97d75f39d9545578f5ee85733a514be | b93934992191eb25a9d5807db1b6652e62c1a3aa114f21ce559c16aeab16aad3 |
| dt3_electrical_production_inverter_2.csv | 1990478 | 126216618 | c03a8016450adb65a260be7be2fff2ca | 703da1d47182f02ed973bff6f9b03573bbcddc059b084d09f2866bd4f0fd9bc5 |
| 00_metadata_variable.jpg | image | 209622 | e0f3296375eb4af0d38add7027f33261 | 45755d44e3bf77a6f0d6e0a44f3ccfaf738f83f3c75cc8f61b88f8601317bca6 |

Exact inverter intersection is 1,990,478/1,990,478; both streams have no duplicate/out-of-order timestamps. All timestamps retain +04:00 source offset and are converted to UTC. Electrical observed median spacing is 6 s, not the 5 s sampling cadence stated in the paper. Weather row audit and actual interval distribution are reported separately. The maximum electrical gap is 2,848,806 s from 2021-12-22T07:00:34+00:00 to 2022-01-24T06:20:40+00:00; never interpolate it.

Target Fault values: 0 (1,905,953), 1 (6,318), 2.1 (2,148), 2.2 (2,460), 2.3 (3,287), 3.1 (2,717), 3.2 (6,292), 4 (61,297), missing (6). Target electrical fields have 10 missing values each; reference electrical fields have none. Known decimals are canonicalized within 1e-6 to repair float32 exact-dictionary-key failures; unknown numeric values stay unknown. The original v1 results/notebook remain byte-identical.

The metadata image labels the column DHI but explicitly describes **Diffuse Tilted Irradiance**; the actual CSV and [data paper Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC9800176/) use DTI with the same physical description. We retain DTI as measured tilted diffuse irradiance in W/m2; no horizontal conversion is invented. The paper reports an SPN1 near the array at the same tilt. Verify installation/calibration records before field deployment; this is metadata-supported semantics, not a fresh radiometric calibration.

[Setup paper §3/Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC9497466/) maps line 1 TE1500 to 175 Wp and line 2 TE1700 to 170 Wp, with twelve modules each, implying 2.10/2.04 kWp. Its prose says 2.04/2.09 kWp and 2.09 does not equal twelve 175 Wp modules. Conflict remains unresolved. Both ratios are evaluated; no identical-capacity assumption is made. Two parallel groups of six series modules per line, north orientation and 26-degree tilt are documented. Energrid/Gridsoft is the monitoring system, not a verified inverter OEM model/firmware for operational alarm settings.

Verified units: Pg W; Va PV operating voltage V; Ia PV current A; Vg grid voltage V; Ig grid current A; Fg Hz; Eg cumulative/reported grid energy kWh; GTI/DTI W/m2; TA/TPV C. Full ranges/nulls are in data_quality_report_v2.json. Raw zeros include non-operating periods and are not automatically daytime faults. Target maxima: Pg2195 W, Va241 V, Ia11.4 A, Vg248 V, Ig9.2 A, Fg50.37 Hz. Reference maxima: Pg2303 W, Va242 V, Ia13.8 A, Vg252 V, Ig9.8 A, Fg50.27 Hz. Weather ranges: GTI1.375–1749; DTI1.341–755.2; TA14.89–44.83 C; TPV12.45–71.77 C. Extreme ranges alone do not establish sensor error or grid faults.

The pre-event availability audit found6,594 nominal bins/63 days; stricter elapsed-quality filtering leaves 6,564 bins across separate training/selection/calibration populations. Actual frozen counts and dates are reported in the experiment report. All 23 episodes lie after these populations. 60 s grouping produces25 groups,300 s and900 s produce23; this confirms grouping sensitivity and does not prove independence. All 23 primary groups occur on distinct days, but closely spaced days share the installation/intervention procedure.
