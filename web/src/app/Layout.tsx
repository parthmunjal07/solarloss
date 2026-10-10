import { useEffect, useRef } from "react";
import { Link, NavLink, Outlet, useLocation, useMatch } from "react-router";
import { ArrowUpRight, Sun } from "lucide-react";
import { useMode } from "./Mode";

export default function Layout() {
  const { mode, setMode, href, preview } = useMode(),
    { pathname, hash } = useLocation();
  const id = useMatch("/experiments/:id/*")?.params.id;
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    document.title = `${pathname === "/" ? "Evidence before action" : pathname === "/method" ? "Method & limitations" : pathname.endsWith("/report") ? "Evidence review" : id ? "Performance investigation" : "Experiment explorer"} | SolarLoss`;
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    else {
      window.scrollTo({ top: 0 });
      main.current?.focus({ preventScroll: true });
    }
  }, [pathname, hash, id]);
  const step = pathname.endsWith("/report") ? 3 : id ? 2 : 1;
  const app = pathname.startsWith("/experiments");
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" to={href("/")} aria-label="SolarLoss home">
            <Sun aria-hidden size={28} strokeWidth={1.7} />
            SolarLoss
            <span className="brand-caption">Evidence before action</span>
          </Link>
          <nav aria-label="Main navigation">
            <NavLink to={href("/experiments")}>Experiments</NavLink>
            <NavLink to={href("/method")}>Method & limitations</NavLink>
          </nav>
          <div className="mode-switch" role="group" aria-label="Reading mode">
            {(["summary", "analyst"] as const).map((m) => (
              <button
                key={m}
                aria-pressed={mode === m}
                onClick={() => setMode(m)}
              >
                {m === "summary" ? "Summary" : "Analyst"}
              </button>
            ))}
          </div>
        </div>
      </header>
      {preview && (
        <div className="preview-notice" role="status">
          <div className="container">
            <strong>Research preview</strong>
            <span>Not an approved API review. Development only.</span>
            <Link to={`${pathname}?mode=${mode}`}>Return to API reviews</Link>
          </div>
        </div>
      )}
      {app && (
        <nav className="stepper container" aria-label="Review progress">
          <span className="mobile-step">Step {step} of 5</span>
          <ol>
            {[
              "Select experiment",
              "Analyse performance",
              "Check evidence",
              "Issue review decision",
              "Export report",
            ].map((s, i) => (
              <li key={s} aria-current={i + 1 === step ? "step" : undefined}>
                {i + 1 < step ? (
                  <Link
                    to={href(i === 0 ? "/experiments" : `/experiments/${id}`)}
                  >
                    {s}
                  </Link>
                ) : (
                  <span>{s}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <main id="main" tabIndex={-1} ref={main}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <div className="footer-brand">
            SolarLoss
            <p>
              Evidence review for solar performance.
              <br />
              WeMakeDevs Environmental Hacks · October 2026
            </p>
          </div>
          <div>
            <Link to={href("/method")}>Method & limitations</Link>
            <a href="https://github.com/parthmunjal07/solarloss">
              Source on GitHub <ArrowUpRight size={14} aria-hidden />
            </a>
            <a href="https://zenodo.org/records/7291380">
              Dataset: Graillet et al. · Zenodo 7291380
            </a>
          </div>
          <p className="small">
            Retrospective research.
            <br />
            No live inverter connection.
          </p>
        </div>
      </footer>
    </>
  );
}
