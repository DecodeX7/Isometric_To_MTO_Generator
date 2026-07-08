import type { MTOItem } from "@/lib/types";

interface MtoTableProps {
  items: MTOItem[];
}

function confidenceClass(confidence?: number | null): string {
  if (confidence == null) return "low";
  if (confidence >= 0.8) return "high";
  if (confidence >= 0.6) return "medium";
  return "low";
}

function formatConfidence(confidence?: number | null): string {
  if (confidence == null) return "-";
  return `${Math.round(confidence * 100)}%`;
}

export function MtoTable({ items }: MtoTableProps) {
  if (items.length === 0) {
    return <div className="warningBox">No MTO rows were extracted. Try a clearer drawing or check the backend logs.</div>;
  }

  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Category</th>
            <th>Description</th>
            <th>Size</th>
            <th>Schedule / Rating</th>
            <th>Material</th>
            <th>End</th>
            <th>Qty</th>
            <th>Unit</th>
            <th>Length m</th>
            <th>Conf.</th>
            <th>Remarks</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.item_no}-${item.category}-${item.description}`}>
              <td>{item.item_no}</td>
              <td><span className="badge">{item.category}</span></td>
              <td className="description">{item.description}</td>
              <td>{item.size_nps}</td>
              <td>{item.schedule_rating}</td>
              <td>{item.material_spec}</td>
              <td>{item.end_type}</td>
              <td>{item.quantity}</td>
              <td>{item.unit}</td>
              <td>{item.length_m ?? "-"}</td>
              <td className={`confidence ${confidenceClass(item.confidence)}`}>{formatConfidence(item.confidence)}</td>
              <td className="description">{item.remarks}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
