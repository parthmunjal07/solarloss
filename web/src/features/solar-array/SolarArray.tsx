import {
  Component,
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useMode } from "../../app/Mode";
import type { Review } from "../../lib/types";
import { numeric, timeLabel } from "../../lib/formatters";
import ArraySchematic from "./ArraySchematic";
import {
  arrangementNote,
  installationNote,
  modes,
  modules,
  representativeModule,
  setupSource,
} from "./model";
import type { ArrayMode, CameraAction } from "./model";
import "./solar-array.css";

const Scene = lazy(() => import("./SolarArrayScene"));
class SceneBoundary extends Component<
  { children: ReactNode; fallback: ReactNode; onUnavailable: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    console.warn("Solar array rendering unavailable:", error.message);
    this.props.onUnavailable();
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
function useReducedMotion() {
  const [reduce, setReduce] = useState(
    () =>
      typeof matchMedia === "function" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const query = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduce(query.matches);
    query.addEventListener("change", change);
    return () => query.removeEventListener("change", change);
  }, []);
  return reduce;
}
export default function SolarArray({ review }: { review?: Review }) {
  const { href } = useMode();
  const uid = useId(),
    viewport = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<ArrayMode>("normal"),
    [selected, setSelected] = useState<string | null>(null),
    [highlighted, setHighlighted] = useState<string | null>(null);
  const [visible, setVisible] = useState(false),
    [rendering, setRendering] = useState<"loading" | "ready" | "unavailable">(
      "loading",
    ),
    [schematic, setSchematic] = useState(false);
  const [command, setCommand] = useState({
    action: "reset" as CameraAction,
    sequence: 0,
  });
  const reducedMotion = useReducedMotion();
  const onReady = useCallback(() => setRendering("ready"), []),
    onUnavailable = useCallback(() => setRendering("unavailable"), []);
  useEffect(() => {
    const target = viewport.current;
    if (!target || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "80px" },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, []);
  const active = modes.find((m) => m.id === mode)!;
  const module = modules.find((m) => m.id === selected);
  const is2D = schematic || rendering === "unavailable";
  const camera = (action: CameraAction) =>
    setCommand((c) => ({ action, sequence: c.sequence + 1 }));
  const fallback = (
    <ArraySchematic
      mode={mode}
      selected={selected}
      highlighted={highlighted}
      onSelect={setSelected}
      onHover={setHighlighted}
    />
  );
  return (
    <section
      className="solar-array"
      id="experimental-setup"
      aria-labelledby={`${uid}-title`}
    >
      <div className="array-heading">
        <div>
          <p className="eyebrow">SolarLoss · Interactive Solar Array</p>
          <h2 id={`${uid}-title`}>Understand the experimental setup</h2>
        </div>
        <span className="array-count">
          <strong>24</strong> modules · 2 inverter lines
        </span>
      </div>
      <p className="array-disclaimer">
        {installationNote}. <span className="sr-only">{arrangementNote}</span>
      </p>
      <div
        className="array-modes"
        role="group"
        aria-label="Array explanation mode"
      >
        {modes.map((m, i) => (
          <button
            key={m.id}
            aria-pressed={mode === m.id}
            aria-controls={`${uid}-explanation`}
            onClick={() => {
              setMode(m.id);
              setHighlighted(null);
            }}
          >
            <span aria-hidden="true">0{i + 1}</span>
            {m.label}
          </button>
        ))}
      </div>
      <div className="array-workspace">
        <div className="array-visual">
          <div className="array-labels">
            <div>
              <span className="array-role experimental">01</span>
              <strong>Inverter 1</strong>
              <small>Experimental array</small>
            </div>
            <div className={mode === "reference" ? "reference-active" : ""}>
              <span className="array-role">02</span>
              <strong>Inverter 2</strong>
              <small>Reference array</small>
            </div>
          </div>
          <div
            className="array-viewport"
            ref={viewport}
            data-renderer={
              is2D ? "2d" : rendering === "ready" ? "3d" : "pending"
            }
          >
            {visible && !is2D ? (
              <SceneBoundary fallback={fallback} onUnavailable={onUnavailable}>
                <Suspense fallback={fallback}>
                  <Scene
                    mode={mode}
                    selected={selected}
                    highlighted={highlighted}
                    onSelect={setSelected}
                    onHover={setHighlighted}
                    command={command}
                    reducedMotion={reducedMotion}
                    onReady={onReady}
                    onUnavailable={onUnavailable}
                  />
                </Suspense>
              </SceneBoundary>
            ) : (
              fallback
            )}
          </div>
          <div
            className="array-tools"
            role="group"
            aria-label="Camera and rendering controls"
          >
            <button
              disabled={is2D || rendering !== "ready"}
              onClick={() => camera("left")}
              aria-label="Rotate camera left"
            >
              ↶
            </button>
            <button
              disabled={is2D || rendering !== "ready"}
              onClick={() => camera("right")}
              aria-label="Rotate camera right"
            >
              ↷
            </button>
            <button
              disabled={is2D || rendering !== "ready"}
              onClick={() => camera("in")}
              aria-label="Zoom in"
            >
              +
            </button>
            <button
              disabled={is2D || rendering !== "ready"}
              onClick={() => camera("out")}
              aria-label="Zoom out"
            >
              −
            </button>
            <button
              disabled={is2D || rendering !== "ready"}
              onClick={() => camera("reset")}
            >
              Reset camera
            </button>
            <button
              aria-pressed={is2D}
              disabled={rendering === "unavailable"}
              onClick={() => {
                setSchematic((s) => !s);
                setVisible(true);
              }}
            >
              {is2D ? "Use 3D view" : "Use 2D view"}
            </button>
          </div>
          <p className="small array-render-status" role="status">
            {rendering === "unavailable"
              ? "3D unavailable. The 2D schematic and all module controls remain available."
              : is2D
                ? "2D schematic. Choose a module below to inspect its role."
                : rendering === "ready"
                  ? "Drag to orbit · pinch to zoom · select a module. On touch screens, scroll outside the scene."
                  : "2D schematic shown while the 3D view loads. Module controls are ready."}
          </p>
        </div>
        <div
          className="array-explanation"
          id={`${uid}-explanation`}
          aria-live="polite"
        >
          <p className="eyebrow">{active.label}</p>
          <h3>{active.heading}</h3>
          <p>{active.explanation}</p>
          <div className="array-fact">
            <strong>Each line: 12 modules</strong>
            <span>
              Two parallel strings of six. The diagram uses an illustrative
              arrangement.
            </span>
          </div>
          {mode === "shading" && (
            <p className="array-affected">
              <span aria-hidden="true">▧</span> Amber + hatching: one
              representative affected module.
            </p>
          )}
          {mode === "reference" && (
            <div className="array-model">
              <span>Reference output + weather</span>
              <span aria-hidden="true">↓</span>
              <strong>Calibrated target expectation</strong>
              <span>Compare with measured target output</span>
            </div>
          )}
          {review ? (
            <a className="array-chart-link" href="#performance-comparison">
              Review measured versus expected power ↑
            </a>
          ) : (
            <Link
              className="array-chart-link"
              to={href("/experiments/shading_01#performance-comparison")}
            >
              Open the measured-versus-expected chart →
            </Link>
          )}
        </div>
      </div>
      <div className="array-selection">
        <div>
          <p className="eyebrow">Explore the modules</p>
          <h3>Choose a module</h3>
          <p className="small">
            Hover, focus or select. Module numbers describe this illustration
            only.
          </p>
        </div>
        <div className="array-module-controls">
          {[1, 2].map((inverter) => (
            <fieldset key={inverter}>
              <legend>
                Inverter {inverter} ·{" "}
                {inverter === 1 ? "experimental" : "reference"}
              </legend>
              <div>
                {modules
                  .filter((m) => m.inverter === inverter)
                  .map((m) => (
                    <button
                      key={m.id}
                      aria-label={m.label}
                      aria-pressed={selected === m.id}
                      className={
                        mode === "shading" && m.id === representativeModule
                          ? "affected"
                          : ""
                      }
                      onClick={() => setSelected(m.id)}
                      onFocus={() => setHighlighted(m.id)}
                      onBlur={() => setHighlighted(null)}
                      onPointerEnter={() => setHighlighted(m.id)}
                      onPointerLeave={() => setHighlighted(null)}
                    >
                      {m.string}.{m.number}
                    </button>
                  ))}
              </div>
            </fieldset>
          ))}
        </div>
      </div>
      <div className="array-module-info" role="status" aria-live="polite">
        <strong>{module ? module.label : "Module information"}</strong>
        <p className="small">
          {module
            ? `${module.inverter === 1 ? "Experimental line: its measured output is the target of the comparison." : "Reference line: its recorded output is a comparison input, not the expected target output."} ${mode === "shading" && module.id === representativeModule ? "This is the representative fully shaded module in the illustration." : "No module-level production measurement or physical condition is assigned here."} The actual shaded module location is not established by the review artifact.`
            : "Select any module in the diagram or use the keyboard-accessible module buttons. Individual module power is not measured in this view."}
        </p>
      </div>
      {review && (
        <details className="array-evidence">
          <summary>Connect the setup to this source review</summary>
          <p className="small">
            {review.origin === "research-preview"
              ? "Unapproved development research preview. "
              : "Context from the stored API review. "}
            The diagram explains roles; evidence comes from recorded
            measurements.
          </p>
          <dl className="metadata">
            <div>
              <dt>Source intervention / interval</dt>
              <dd>{review.title}</dd>
            </div>
            <div>
              <dt>Documented intervention bounds</dt>
              <dd>
                {review.event
                  ? `${review.event.start} to ${review.event.end}`
                  : "Not supplied by this artifact"}
              </dd>
            </div>
            <div>
              <dt>Primary detector confirmation</dt>
              <dd>
                {review.alerts[0]
                  ? `${timeLabel(review.alerts[0])} UTC · ${review.alerts[0]}`
                  : "Not supplied by this artifact"}
              </dd>
            </div>
            {[
              review.metrics.expected,
              review.metrics.measured,
              review.metrics.deviation,
            ].map((m) => (
              <div key={m.label}>
                <dt>{m.label}</dt>
                <dd>
                  {m.value === null
                    ? "Not available"
                    : `${numeric(m.value, 6)} ${m.unit}`}
                  . {m.reason}
                </dd>
              </div>
            ))}
            <div>
              <dt>Data coverage</dt>
              <dd>{review.metrics.coverage.reason}</dd>
            </div>
          </dl>
        </details>
      )}
      <p className="small array-source">
        Configuration: <a href={setupSource}>Lebreton et al. (2022), §3</a> ·{" "}
        <a href="https://zenodo.org/records/7291380">
          Graillet et al., Zenodo v2
        </a>
        . No rooftop position, obstruction geometry, sun trajectory, per-module
        power or energy recovery is reconstructed.
      </p>
    </section>
  );
}
