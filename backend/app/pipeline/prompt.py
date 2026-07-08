EXTRACTION_PROMPT = """
You are an expert piping isometric Material Take-Off (MTO) extraction engineer.

You will receive multiple optimized views of the SAME uploaded drawing:
- full_enhanced_page: full page for overall context
- blue_grid_suppressed_view: blue graph grid removed/reduced so black route, dimensions and text are easier to read
- title_and_metadata_band: top/title area for job, drawing, line and size metadata

Task:
Analyze the drawing and return one structured MTO JSON object only.

Important engineering rules:
1. A piping isometric is not to scale. Do not infer pipe length from pixel length. Use written dimensions, BOM text, marked callouts, or conservative "Unknown" remarks.
2. Prefer an existing BOM/material table if present, then reconcile with visible symbols/callout balloons.
3. Pipe is quantified by total length in metres. Use unit "M" and length_m for pipe.
4. Fittings, flanges, valves, gaskets, supports, instruments and welds are quantified by count. Use unit "EA" or "NO".
5. Bolts are quantified as sets. Use unit "SET".
6. One gasket and one bolt set are normally needed per flanged joint. Include them if visible or derivable. If uncertain, add remarks.
7. Use correct piping vocabulary where visible: ASME B16.9 for BW fittings, ASME B16.5 for flanges/valves, ASME B16.20 for gaskets.
8. Common materials when the drawing does not explicitly state material: ASTM A106 Gr.B pipe, ASTM A234 WPB BW fittings, ASTM A105 flanges, ASTM A193 B7 / A194 2H bolts.
9. Use confidence from 0 to 1. Be honest. Do not hallucinate unreadable fields; use "Unknown" or empty strings with low confidence.
10. Extract title/header metadata where visible: drawing_no, revision, line_number, nps, material_class, service. For marked training samples, job details can be used as drawing_no/line_number if no formal title block exists.
11. If the drawing is a marked training sample and no proper BOM table exists, build a reasonable MTO from visible piping symbols/callouts and mark uncertainty in remarks.

Return JSON with exactly these top-level keys:
{
  "drawing_meta": {
    "drawing_no": "string",
    "revision": "string",
    "line_number": "string",
    "nps": "string",
    "material_class": "string",
    "service": "string"
  },
  "items": [
    {
      "item_no": 1,
      "category": "PIPE | FITTING | FLANGE | VALVE | GASKET | BOLT | SUPPORT | INSTRUMENT | WELD | OTHER",
      "description": "string",
      "size_nps": "string",
      "schedule_rating": "string",
      "material_spec": "string",
      "end_type": "string",
      "quantity": 1,
      "unit": "M | EA | NO | SET",
      "length_m": 0,
      "confidence": 0.0,
      "remarks": "string"
    }
  ],
  "summary": {
    "total_pipe_length_m": 0,
    "fittings": 0,
    "flanges": 0,
    "valves": 0,
    "gaskets": 0,
    "bolt_sets": 0,
    "supports": 0,
    "field_welds": 0
  }
}

Return only valid JSON. No Markdown. No prose.
""".strip()

FAST_EXTRACTION_PROMPT = """
Return a compact JSON Material Take-Off for this piping isometric drawing.
Use the provided enhanced/cropped views. Focus on visible/marked components and title/header metadata.
If exact values are unreadable, use "Unknown" and low confidence, but still return useful MTO rows.
Return only valid JSON with drawing_meta, items and summary. Do not wrap in Markdown.
""".strip()


# Gemini structured output accepts a JSON schema-like object. The backend still
# validates the result with Pydantic, so this schema is a generation guide plus
# a first layer of structure control. The schema intentionally avoids nullable
# because some SDK/model combinations reject it; the backend accepts omitted or
# null length_m during Pydantic validation.
MTO_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "drawing_meta": {
            "type": "object",
            "properties": {
                "drawing_no": {"type": "string"},
                "revision": {"type": "string"},
                "line_number": {"type": "string"},
                "nps": {"type": "string"},
                "material_class": {"type": "string"},
                "service": {"type": "string"},
            },
            "required": ["drawing_no", "revision", "line_number", "nps", "material_class", "service"],
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_no": {"type": "integer"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "PIPE",
                            "FITTING",
                            "FLANGE",
                            "VALVE",
                            "GASKET",
                            "BOLT",
                            "SUPPORT",
                            "INSTRUMENT",
                            "WELD",
                            "OTHER",
                        ],
                    },
                    "description": {"type": "string"},
                    "size_nps": {"type": "string"},
                    "schedule_rating": {"type": "string"},
                    "material_spec": {"type": "string"},
                    "end_type": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string"},
                    "length_m": {"type": "number"},
                    "confidence": {"type": "number"},
                    "remarks": {"type": "string"},
                },
                "required": [
                    "item_no",
                    "category",
                    "description",
                    "size_nps",
                    "schedule_rating",
                    "material_spec",
                    "end_type",
                    "quantity",
                    "unit",
                    "confidence",
                    "remarks",
                ],
            },
        },
        "summary": {
            "type": "object",
            "properties": {
                "total_pipe_length_m": {"type": "number"},
                "fittings": {"type": "integer"},
                "flanges": {"type": "integer"},
                "valves": {"type": "integer"},
                "gaskets": {"type": "integer"},
                "bolt_sets": {"type": "integer"},
                "supports": {"type": "integer"},
                "field_welds": {"type": "integer"},
            },
            "required": [
                "total_pipe_length_m",
                "fittings",
                "flanges",
                "valves",
                "gaskets",
                "bolt_sets",
                "supports",
                "field_welds",
            ],
        },
    },
    "required": ["drawing_meta", "items", "summary"],
}
