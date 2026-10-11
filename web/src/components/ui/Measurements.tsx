import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { power, timeLabel } from "../../lib/formatters";
import type { Review } from "../../lib/types";
export default function Measurements({ review }: { review: Review }) {
  const [page, setPage] = useState(0),
    [excludedOnly, setExcludedOnly] = useState(false);
  const samples = review.samples.filter(
    (s) =>
      !excludedOnly ||
      !s.valid ||
      review.exclusions.some(
        (e) =>
          Date.parse(s.timestamp) >= Date.parse(e.start) &&
          Date.parse(s.timestamp) <= Date.parse(e.end),
      ),
  );
  const pages = Math.max(1, Math.ceil(samples.length / 20));
  return (
    <Dialog.Root>
      <Dialog.Trigger className="button secondary">
        Inspect measurements
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="drawer-overlay" />
        <Dialog.Content className="measurement-drawer">
          <div className="drawer-heading">
            <div>
              <Dialog.Title>Original measurements</Dialog.Title>
              <Dialog.Description className="small">
                Original source values. UTC timestamps. Exclusions remain
                visible.
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="icon-button"
              aria-label="Close measurements"
            >
              <X size={20} />
            </Dialog.Close>
          </div>
          <label className="measurement-filter">
            <input
              type="checkbox"
              checked={excludedOnly}
              onChange={(e) => {
                setExcludedOnly(e.target.checked);
                setPage(0);
              }}
            />{" "}
            Show invalid or excluded samples only (
            {
              review.samples.filter(
                (s) =>
                  !s.valid ||
                  review.exclusions.some(
                    (e) =>
                      Date.parse(s.timestamp) >= Date.parse(e.start) &&
                      Date.parse(s.timestamp) <= Date.parse(e.end),
                  ),
              ).length
            }
            )
          </label>
          <label className="small">
            Find a source timestamp (UTC)
            <input
              type="datetime-local"
              step="1"
              onChange={(e) => {
                const t = Date.parse(`${e.target.value}Z`);
                if (!Number.isFinite(t)) return;
                const index = samples.findIndex(
                  (s) => Date.parse(s.timestamp) >= t,
                );
                setPage(
                  Math.floor(
                    Math.max(0, index < 0 ? samples.length - 1 : index) / 20,
                  ),
                );
              }}
            />
          </label>
          <div
            className="table-scroll"
            tabIndex={0}
            aria-label="Scrollable measurement table"
          >
            <table>
              <caption className="sr-only">
                Experimental measured, raw reference and calibrated expected
                power, with source bounds and validity.
              </caption>
              <thead>
                <tr>
                  <th>Timestamp UTC</th>
                  <th>Measured</th>
                  <th>Raw reference</th>
                  <th>Expected</th>
                  <th>Lower</th>
                  <th>Upper</th>
                  <th>Valid</th>
                </tr>
              </thead>
              <tbody>
                {samples.slice(page * 20, (page + 1) * 20).map((s) => (
                  <tr key={s.timestamp}>
                    <th scope="row">
                      <time title={s.timestamp} dateTime={s.timestamp}>
                        {timeLabel(s.timestamp)}
                        <span className="small">
                          :
                          {new Date(s.timestamp)
                            .getUTCSeconds()
                            .toString()
                            .padStart(2, "0")}
                        </span>
                      </time>
                    </th>
                    <td>{power(s.measured_power, review.powerUnit)}</td>
                    <td>{power(s.raw_reference_power, review.powerUnit)}</td>
                    <td>{power(s.expected_power, review.powerUnit)}</td>
                    <td>{power(s.expected_lower_bound, review.powerUnit)}</td>
                    <td>{power(s.expected_upper_bound, review.powerUnit)}</td>
                    <td>
                      {s.valid
                        ? "Valid"
                        : review.v2
                          ? "Invalid source sample"
                          : "Excluded"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button
              className="button secondary"
              disabled={!page}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span className="small num" aria-live="polite">
              Page {page + 1} of {pages}
            </span>
            <button
              className="button secondary"
              disabled={page >= pages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
