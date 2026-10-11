import { modules, representativeModule } from "./model";
import type { ArrayMode } from "./model";
export default function ArraySchematic({
  mode,
  selected,
  highlighted,
  onSelect,
  onHover,
}: {
  mode: ArrayMode;
  selected: string | null;
  highlighted: string | null;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  return (
    <svg className="array-schematic" viewBox="0 0 660 360" aria-hidden="true">
      <defs>
        <pattern
          id="pv-cells"
          width="7"
          height="10"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M0 0H7M0 0V10"
            fill="none"
            stroke="#afc4dd"
            strokeWidth="0.5"
          />
        </pattern>
      </defs>
      {[1, 2].map((inverter) => (
        <g
          key={inverter}
          transform={`translate(${inverter === 1 ? 32 : 344} 64)`}
        >
          <rect
            x="-12"
            y="-16"
            width="294"
            height="230"
            rx="12"
            fill={
              mode === "reference" && inverter === 2 ? "#e6eef5" : "#e9e3d9"
            }
            stroke={
              mode === "reference" && inverter === 2 ? "#3b5b8c" : "#c5bdaf"
            }
            strokeWidth="2"
          />
          {modules
            .filter((m) => m.inverter === inverter)
            .map((m) => {
              const affected =
                mode === "shading" && m.id === representativeModule;
              const focus = selected === m.id || highlighted === m.id;
              return (
                <g
                  key={m.id}
                  transform={`translate(${(m.index % 6) * 45} ${Math.floor(m.index / 6) * 95})`}
                  onClick={() => onSelect(m.id)}
                  onPointerOver={() => onHover(m.id)}
                  onPointerOut={() => onHover(null)}
                  style={{ cursor: "pointer" }}
                >
                  <rect
                    width="39"
                    height="82"
                    rx="2"
                    fill={affected ? "#d39a3c" : "#244971"}
                    stroke={
                      focus ? "#0f766e" : affected ? "#92400e" : "#62748a"
                    }
                    strokeWidth={focus ? 4 : 2}
                  />
                  <rect
                    x="3"
                    y="3"
                    width="33"
                    height="76"
                    fill="url(#pv-cells)"
                  />
                  {affected && (
                    <path
                      d="M4 6L35 76M4 30L25 76M16 6L35 50"
                      stroke="#92400e"
                      strokeWidth="2"
                    />
                  )}
                </g>
              );
            })}
          <path
            d="M52 188H218M135 188V215"
            stroke="#62748a"
            strokeWidth="2"
            fill="none"
          />
          <rect x="104" y="215" width="62" height="30" rx="4" fill="#14213d" />
          <text
            x="135"
            y="235"
            textAnchor="middle"
            fill="#faf7f2"
            fontSize="13"
          >
            INV {inverter}
          </text>
        </g>
      ))}
    </svg>
  );
}
