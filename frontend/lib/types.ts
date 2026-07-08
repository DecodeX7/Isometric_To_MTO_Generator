export type JobStatus = "queued" | "processing" | "completed" | "failed";

export type Category =
  | "PIPE"
  | "FITTING"
  | "FLANGE"
  | "VALVE"
  | "GASKET"
  | "BOLT"
  | "SUPPORT"
  | "INSTRUMENT"
  | "WELD"
  | "OTHER";

export interface DrawingMeta {
  drawing_no: string;
  revision: string;
  line_number: string;
  nps: string;
  material_class: string;
  service: string;
}

export interface MTOItem {
  item_no: number;
  category: Category;
  description: string;
  size_nps: string;
  schedule_rating: string;
  material_spec: string;
  end_type: string;
  quantity: number;
  unit: string;
  length_m?: number | null;
  confidence?: number | null;
  remarks: string;
}

export interface Summary {
  total_pipe_length_m: number;
  fittings: number;
  flanges: number;
  valves: number;
  gaskets: number;
  bolt_sets: number;
  supports: number;
  field_welds: number;
}

export interface ExtractionInfo {
  provider: string;
  model: string;
  mode: string;
  warnings: string[];
}

export interface MTOResult {
  drawing_meta: DrawingMeta;
  items: MTOItem[];
  summary: Summary;
  extraction_info: ExtractionInfo;
}

export interface UploadResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  filename: string;
  result: MTOResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}
