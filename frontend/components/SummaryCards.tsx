import type { Summary } from "@/lib/types";

interface SummaryCardsProps {
  summary: Summary;
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  const cards = [
    ["Pipe length", `${summary.total_pipe_length_m.toFixed(2)} m`],
    ["Fittings", summary.fittings],
    ["Flanges", summary.flanges],
    ["Valves", summary.valves],
    ["Gaskets", summary.gaskets],
    ["Bolt sets", summary.bolt_sets]
  ];

  return (
    <div className="summaryGrid">
      {cards.map(([label, value]) => (
        <div className="summaryCard" key={label.toString()}>
          <div className="summaryLabel">{label}</div>
          <div className="summaryValue">{value}</div>
        </div>
      ))}
    </div>
  );
}
