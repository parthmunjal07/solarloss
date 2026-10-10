import { lazy, Suspense } from "react";
import { Route, Routes, Link } from "react-router";
import { ModeProvider, useMode } from "./Mode";
import Layout from "./Layout";
import Landing from "../features/landing/Landing";
import Experiments from "../features/experiments/Experiments";
import Method from "../features/method/Method";
import { Loading } from "../components/ui/Common";

const Investigation = lazy(
  () => import("../features/investigation/Investigation"),
);
const Report = lazy(() => import("../features/report/Report"));
function Missing() {
  const { href } = useMode();
  return (
    <section className="container app-page">
      <p className="eyebrow">Page unavailable</p>
      <h1>This page could not be found.</h1>
      <Link className="button primary" to={href("/experiments")}>
        Browse experiments
      </Link>
    </section>
  );
}
export default function App() {
  return (
    <ModeProvider>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Landing />} />
            <Route path="experiments" element={<Experiments />} />
            <Route path="experiments/:id" element={<Investigation />} />
            <Route path="experiments/:id/report" element={<Report />} />
            <Route path="method" element={<Method />} />
            <Route path="*" element={<Missing />} />
          </Route>
        </Routes>
      </Suspense>
    </ModeProvider>
  );
}
