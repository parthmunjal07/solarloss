import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../src/app/App";
import { fixture, listing } from "./fixtures";

function CurrentUrl() {
  const location = useLocation();
  return (
    <output aria-label="Current URL">
      {location.pathname}
      {location.search}
    </output>
  );
}
function mount(path: string) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={[path]}>
        <App />
        <CurrentUrl />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
function mockApi(state = "supported_change" as Parameters<typeof fixture>[0]) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) =>
      Promise.resolve(
        new Response(
          JSON.stringify(
            url.endsWith("/experiments") ? listing() : fixture(state),
          ),
        ),
      ),
    ),
  );
}
describe("routing and reading mode", () => {
  it("restores analyst from a deep link ahead of local preference", async () => {
    localStorage.setItem("solarloss-mode", "summary");
    mockApi();
    mount("/experiments/sample/report?mode=analyst");
    expect(
      await screen.findByRole("heading", { name: "Supported change" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Technical details" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Behind the review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export report" })).toHaveAttribute(
      "href",
      "/api/v1/reviews/sample/report",
    );
  });
  it("switches modes and preserves them on navigation and refresh", async () => {
    const user = userEvent.setup(),
      first = (mockApi(), mount("/experiments/sample/report?mode=summary"));
    await user.click(screen.getByRole("button", { name: "Technical details" }));
    expect(screen.getByLabelText("Current URL")).toHaveTextContent(
      "/experiments/sample/report?mode=analyst",
    );
    expect(localStorage.getItem("solarloss-mode")).toBe("analyst");
    await user.click(
      screen.getAllByRole("link", { name: "Method & limitations" })[0],
    );
    expect(screen.getByLabelText("Current URL")).toHaveTextContent(
      "/method?mode=analyst",
    );
    first.unmount();
    mount("/experiments/sample/report?mode=analyst");
    expect(
      screen.getByRole("button", { name: "Technical details" }),
    ).toHaveAttribute("aria-pressed", "true");
  });
  it("URL summary takes precedence over a saved analyst preference", () => {
    localStorage.setItem("solarloss-mode", "analyst");
    mount("/experiments/sample/report?mode=summary");
    expect(screen.getByRole("button", { name: "Overview" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
  it("uses preference fallback and survives unavailable storage", async () => {
    localStorage.setItem("solarloss-mode", "analyst");
    const first = mount("/experiments/sample/report");
    expect(
      screen.getByRole("button", { name: "Technical details" }),
    ).toHaveAttribute("aria-pressed", "true");
    first.unmount();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    mount("/experiments/sample/report");
    await userEvent.click(
      screen.getByRole("button", { name: "Technical details" }),
    );
    expect(screen.getByLabelText("Current URL")).toHaveTextContent(
      "mode=analyst",
    );
  });
});
describe("API screen states", () => {
  it("shows a loading skeleton while listing is pending", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    mount("/experiments");
    expect(
      screen.getByRole("status", { name: "Loading available experiments" }),
    ).toBeInTheDocument();
  });
  it("shows the actual empty result rather than creating experiments", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response('{"experiments":[]}')),
    );
    mount("/experiments");
    expect(
      await screen.findByText("No reviews are available yet."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Review experiment" }),
    ).not.toBeInTheDocument();
  });
  it("shows a calm 404 and provides a retry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 404 })),
    );
    mount("/experiments/sample/report");
    expect(
      await screen.findByText("This review is not available in the API."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
  });
  it("renders insufficient evidence without an energy assertion", async () => {
    mockApi("insufficient_evidence");
    mount("/experiments/sample/report");
    expect(
      await screen.findByRole("heading", { name: "Insufficient evidence" }),
    ).toBeInTheDocument();
    expect(screen.getByText("What evidence is missing")).toBeInTheDocument();
  });
});
