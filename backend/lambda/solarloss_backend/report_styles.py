"""Self-contained SolarLoss report typography, layout and print rules."""

V2_REPORT_CSS = """
:root {
  color-scheme: light;
  font:
    15px/1.6 system-ui,
    -apple-system,
    sans-serif;
  color: #14213d;
  background: #faf7f2;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
}
main {
  max-width: 1020px;
  margin: auto;
  padding: 48px 40px 64px;
}
h1,
h2,
h3,
p,
dl {
  margin: 0;
}
h1,
h2,
h3 {
  line-height: 1.2;
}
h1 {
  font-size: 38px;
  letter-spacing: -0.025em;
  max-width: 800px;
  margin: 20px 0;
}
h2 {
  font-size: 25px;
  letter-spacing: -0.015em;
  margin: 12px 0 20px;
}
h3 {
  font-size: 18px;
}
p {
  color: #4a5568;
}
p + p {
  margin-top: 12px;
}
h3 + p {
  margin-top: 12px;
}
.eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: #4a5568;
}
.small {
  font-size: 12px;
  line-height: 1.6;
}
.brand {
  white-space: nowrap;
  font-size: 24px;
  font-weight: 650;
  letter-spacing: -0.025em;
  color: #14213d;
}
.masthead {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid #e4ded3;
  padding-bottom: 20px;
  margin-bottom: 28px;
}
.intro {
  max-width: 830px;
  font-size: 17px;
}
.window {
  margin: 16px 0 24px;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.figures {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 24px;
  border-block: 1px solid #e4ded3;
  padding: 24px 0;
  margin: 24px 0 14px;
  font-variant-numeric: tabular-nums;
}
.figures dt {
  font-size: 11px;
  color: #4a5568;
  min-height: 32px;
}
.figures dd {
  margin: 8px 0 0;
  font-size: 28px;
  line-height: 1.25;
  letter-spacing: -0.025em;
}
.figures small {
  font-size: 12px;
  letter-spacing: 0;
}
.coverage dd {
  font-size: 21px;
}
.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  margin-top: 24px;
  padding: 20px;
  background: #f3efe8;
  border-radius: 6px;
}
.status-grid h3 {
  margin: 6px 0 10px;
}
.notice {
  margin-top: 20px;
  font-size: 12px;
}
section {
  margin-top: 48px;
}
.power-chart {
  display: block;
  width: 100%;
  background: white;
  border: 1px solid #e4ded3;
  border-radius: 6px;
  margin: 20px 0 12px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  font-size: 12px;
  margin-top: 12px;
}
.legend span {
  display: flex;
  align-items: center;
  gap: 8px;
}
.line {
  display: inline-block;
  width: 24px;
  border-top: 2px solid #b45309;
}
.expected {
  border-color: #3b5b8c;
  border-top-style: dashed;
}
.reference {
  border-color: #4a5568;
  border-top-style: dotted;
}
.section-number {
  font-size: 12px;
  color: #3b5b8c;
}
.check-heading {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.tag {
  border: 1px solid #b45309;
  background: #fff7e6;
  color: #92400e;
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 20px;
}
.proposed-check {
  border-top: 1px solid #e4ded3;
  margin-top: 24px;
  padding-top: 24px;
}
.check-record {
  margin-top: 20px;
}
.check-record > div {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 20px;
  margin-top: 14px;
}
dt {
  font-weight: 600;
}
dd {
  margin: 0;
  color: #4a5568;
  overflow-wrap: anywhere;
}
ul {
  padding-left: 20px;
  margin: 8px 0;
}
li + li {
  margin-top: 6px;
}
details {
  border-top: 1px solid #e4ded3;
  margin-top: 16px;
}
summary {
  padding: 14px 0;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}
.detail-body {
  padding: 12px 0 24px;
}
.record {
  font-size: 13px;
}
.record > div {
  padding: 10px 0;
  border-bottom: 1px solid #e4ded3;
}
.record dt {
  text-transform: capitalize;
}
.record dd {
  margin-top: 6px;
}
.record .record {
  padding-left: 14px;
  border-left: 1px solid #e4ded3;
}
.metric-definition + .metric-definition {
  margin-top: 32px;
}
.exact-value {
  font-variant-numeric: tabular-nums;
  margin-top: 8px;
}
.research-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
th,
td {
  text-align: left;
  padding: 9px;
  border-bottom: 1px solid #e4ded3;
  vertical-align: top;
  overflow-wrap: anywhere;
}
th {
  background: #f3efe8;
}
footer {
  border-top: 1px solid #e4ded3;
  margin-top: 48px;
  padding-top: 20px;
}
.print-note {
  padding: 16px;
  border: 1px solid #e4ded3;
  border-radius: 6px;
  margin: 16px 0;
}
:focus-visible {
  outline: 2px solid #3b5b8c;
  outline-offset: 3px;
}
@media (max-width: 640px) {
  main {
    padding: 24px 20px 40px;
  }
  h1 {
    font-size: 29px;
  }
  .masthead {
    align-items: flex-start;
  }
  .figures {
    grid-template-columns: 1fr 1fr;
    gap: 24px 16px;
  }
  .figures dd {
    font-size: 26px;
  }
  .coverage dd {
    font-size: 20px;
  }
  .status-grid,
  .research-metrics {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .check-record > div {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  section {
    margin-top: 36px;
  }
  .record .record {
    padding-left: 8px;
  }
}
@page {
  size: A4;
  margin: 16mm 15mm;
}
@media print {
  :root {
    font-size: 10pt;
    background: white;
  }
  main {
    max-width: none;
    padding: 0;
  }
  h1 {
    font-size: 25pt;
  }
  h2 {
    font-size: 17pt;
  }
  h3 {
    font-size: 12pt;
  }
  p,
  .small {
    color: #344052;
  }
  .figures dd {
    font-size: 22pt;
  }
  .figures {
    gap: 16px;
  }
  section {
    margin-top: 24px;
  }
  .power-chart {
    break-inside: avoid;
  }
  h1,
  h2,
  h3,
  .check-heading,
  .eyebrow {
    break-after: avoid;
  }
  .proposed-check {
    break-inside: avoid;
  }
  .appendix-record {
    display: none !important;
  }
  .print-note {
    font-size: 9pt;
  }
  summary {
    font-size: 10pt;
  }
  .masthead {
    margin-bottom: 20px;
  }
  .status-grid {
    break-inside: avoid;
  }
  .table-wrap {
    overflow: visible;
  }
  thead {
    display: table-header-group;
  }
  tr {
    break-inside: avoid;
  }
  footer {
    margin-top: 24px;
  }
  .tag,
  .status-grid {
    print-color-adjust: exact;
  }
}
"""
