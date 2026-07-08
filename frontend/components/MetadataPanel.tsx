import type { DrawingMeta } from "@/lib/types";

interface MetadataPanelProps {
  meta: DrawingMeta;
}

export function MetadataPanel({ meta }: MetadataPanelProps) {
  const fields = [
    ["Drawing No", meta.drawing_no],
    ["Revision", meta.revision],
    ["Line Number", meta.line_number],
    ["NPS", meta.nps],
    ["Material Class", meta.material_class],
    ["Service", meta.service]
  ];

  return (
    <div className="metaGrid">
      {fields.map(([label, value]) => (
        <div className="metaItem" key={label}>
          <div className="metaLabel">{label}</div>
          <div className="metaValue">{value || "Unknown"}</div>
        </div>
      ))}
    </div>
  );
}
