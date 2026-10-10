import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import type { Plugin } from "vite";

// Development middleware only. No scientific files are imported into the client bundle.
export function researchPreview(): Plugin {
  return {
    name: "solarloss-research-preview",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/__research-preview", async (_req, res) => {
        try {
          const root = resolve(server.config.root, "..");
          const files = [
            "analysis/results/example_cases_v2.json",
            "analysis/results/shading_evaluation_v2.json",
            "analysis/results/demo_measured_series_v2.csv",
          ];
          const contents = await Promise.all(
            files.map((file) => readFile(resolve(root, file), "utf8")),
          );
          const example = JSON.parse(contents[0]),
            evaluation = JSON.parse(contents[1]);
          const [header, ...lines] = contents[2].trim().split(/\r?\n/);
          const columns = header.split(",");
          const residuals: Record<string, number | null> = {};
          const samples = lines.map((line) => {
            const row = Object.fromEntries(
              line.split(",").map((value, i) => [columns[i], value]),
            );
            const value = (key: string) =>
              row[key]?.trim() ? Number(row[key]) : null;
            const timestamp = new Date(row.timestamp).toISOString();
            residuals[timestamp] = value("residual_w");
            return {
              timestamp,
              measured_power: value("target_power_w"),
              raw_reference_power: value("reference_power_w"),
              expected_power: value("expected_power_w"),
              valid: row.eligible === "True",
            };
          });
          res.setHeader("Content-Type", "application/json");
          res.setHeader("Cache-Control", "no-store");
          res.end(
            JSON.stringify({
              projection_version: "research-preview-1",
              approval_status: "proposed",
              event: example.shading_event,
              samples,
              residuals,
              analysis_version: evaluation.analysis_version,
              produced_at: evaluation.produced_at,
              protocol_sha256: evaluation.protocol_sha256,
              code_sha256: evaluation.code_sha256,
              selected_model: evaluation.selected_model,
              boundaries: evaluation.boundaries,
              detected_episodes: evaluation.detected_episodes,
              episode_count: evaluation.episode_count,
              false_alarm_rate:
                evaluation.healthy_stability["5"]
                  .false_alarm_runs_per_healthy_hour,
              verdict: evaluation.verdicts.E2,
              limitations: evaluation.limitations,
              source_files: files,
              source_hashes: files.map((scope, i) => ({
                algorithm: "SHA-256",
                digest: createHash("sha256").update(contents[i]).digest("hex"),
                scope,
              })),
            }),
          );
        } catch (error) {
          server.config.logger.error(
            `Research preview unavailable: ${String(error)}`,
          );
          res.statusCode = 503;
          res.end("Committed research sources unavailable");
        }
      });
    },
  };
}
