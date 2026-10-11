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
            <NavLink to={href("/experiments")}>Cases</NavLink>
            <NavLink to={href("/method")}>Method & limitations</NavLink>
          </nav>
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
        <div className="case-navigation container">
          <nav className="case-breadcrumbs" aria-label="Case navigation">
            <Link
              to={href("/experiments")}
              aria-current={!id ? "page" : undefined}
            >
              Cases
            </Link>
            {id && (
              <>
                <span aria-hidden> / </span>
                <Link
                  to={href(`/experiments/${id}`)}
                  aria-current={
                    !pathname.endsWith("/report") ? "page" : undefined
                  }
                >
                  Investigation
                </Link>
              </>
            )}
            {id && pathname.endsWith("/report") && (
              <>
                <span aria-hidden> / </span>
                <span aria-current="page">Evidence & report</span>
              </>
            )}
          </nav>
          {id && (
            <div className="reading-control">
              <div
                className="mode-switch"
                role="group"
                aria-label="Reading mode"
              >
                {(["summary", "analyst"] as const).map((m) => (
                  <button
                    key={m}
                    aria-pressed={mode === m}
                    onClick={() => setMode(m)}
                  >
                    {m === "summary" ? "Overview" : "Technical details"}
                  </button>
                ))}
              </div>
              <p className="small">
                {mode === "summary"
                  ? "Essential evidence and proposed next checks."
                  : "Source channels, calibration, exclusions and provenance."}{" "}
                Same case, same scientific status.
              </p>
            </div>
          )}
        </div>
      )}
      <main id="main" tabIndex={-1} ref={main}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <div className="footer-brand">
            SolarLoss
            <p>Evidence review for solar performance.</p>
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
          <p className="small">Recorded evidence for the next investigation.</p>
        </div>
      </footer>
    </>
  );
}
