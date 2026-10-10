import { createContext, useContext, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import type { PropsWithChildren } from "react";

type Mode = "summary" | "analyst";
const ModeContext = createContext<{
  mode: Mode;
  setMode: (mode: Mode) => void;
  href: (path: string) => string;
  preview: boolean;
}>({ mode: "summary", setMode: () => {}, href: (p) => p, preview: false });
function savedMode(): Mode {
  try {
    return localStorage.getItem("solarloss-mode") === "analyst"
      ? "analyst"
      : "summary";
  } catch {
    return "summary";
  }
}
export function ModeProvider({ children }: PropsWithChildren) {
  const location = useLocation(),
    navigate = useNavigate();
  const [preference, setPreference] = useState<Mode>(savedMode);
  const params = new URLSearchParams(location.search),
    specified = params.get("mode");
  const mode: Mode =
    specified === "summary" || specified === "analyst" ? specified : preference;
  const preview = import.meta.env.DEV && params.get("preview") === "research";
  function setMode(next: Mode) {
    setPreference(next);
    try {
      localStorage.setItem("solarloss-mode", next);
    } catch {
      /* Private browsing can disable storage. */
    }
    params.set("mode", next);
    navigate(
      {
        pathname: location.pathname,
        search: params.toString(),
        hash: location.hash,
      },
      { replace: true },
    );
  }
  function href(path: string) {
    const [base, hash] = path.split("#"),
      [pathname, query] = base.split("?");
    const next = new URLSearchParams(query);
    next.set("mode", mode);
    if (preview) next.set("preview", "research");
    return `${pathname}?${next}${hash ? `#${hash}` : ""}`;
  }
  return (
    <ModeContext.Provider value={{ mode, setMode, href, preview }}>
      {children}
    </ModeContext.Provider>
  );
}
// Kept alongside its provider so URL behavior has one owner.
// eslint-disable-next-line react-refresh/only-export-components
export const useMode = () => useContext(ModeContext);
