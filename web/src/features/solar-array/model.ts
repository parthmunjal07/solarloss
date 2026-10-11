export type ArrayMode = "normal" | "shading" | "reference";
export type CameraAction = "reset" | "in" | "out" | "left" | "right";
export const arrangementNote =
  "Illustrative arrangement — not a reconstruction of the original rooftop.";
export const installationNote =
  "Illustrative — not a reconstruction of the actual research installation";
export const setupSource =
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC9497466/#sec3-entropy-24-01311";
export const modes: {
  id: ArrayMode;
  label: string;
  heading: string;
  explanation: string;
}[] = [
  {
    id: "normal",
    label: "Normal setup",
    heading: "Two arrays. A calibrated comparison.",
    explanation:
      "The two inverter lines have naturally different production levels. Earlier healthy periods calibrate their relationship; equal-looking arrays do not imply equal output.",
  },
  {
    id: "shading",
    label: "Documented shading",
    heading: "One entire module was deliberately shaded.",
    explanation:
      "The shading_01 source intervention describes one fully shaded module on Inverter 1. Amber marks a representative module; its position and the illustration of its cover were not measured.",
  },
  {
    id: "reference",
    label: "Reference comparison",
    heading: "The reference is an input to the model.",
    explanation:
      "Inverter 2 supplies comparison output. The frozen research model combines it with measured weather conditions to estimate healthy Inverter 1 output. Raw reference power and model-expected target power are different quantities.",
  },
];
export const modules = [1, 2].flatMap((inverter) =>
  Array.from({ length: 12 }, (_, index) => ({
    id: `${inverter}-${index}`,
    inverter,
    index,
    string: Math.floor(index / 6) + 1,
    number: (index % 6) + 1,
    label: `Inverter ${inverter}, string ${Math.floor(index / 6) + 1}, module ${(index % 6) + 1}`,
  })),
);
// Representative position only, never a scientific measurement or per-module output.
export const representativeModule = "1-2";
export interface SceneProps {
  mode: ArrayMode;
  selected: string | null;
  highlighted: string | null;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  command: { action: CameraAction; sequence: number };
  reducedMotion: boolean;
  onReady: () => void;
  onUnavailable: () => void;
}
