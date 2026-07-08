from copy import deepcopy

from app.models.mto import MTOResponse
from app.pipeline.postprocess import normalize_and_enrich_mto


MOCK_MTO = {
    "drawing_meta": {
        "drawing_no": "ISO-1501-01",
        "revision": "2",
        "line_number": "6\"-P-1501-A1A-IH",
        "nps": "6\"",
        "material_class": "A1A",
        "service": "Process",
    },
    "items": [
        {
            "item_no": 1,
            "category": "PIPE",
            "description": "Pipe, Seamless, BE, ASME B36.10",
            "size_nps": "6\"",
            "schedule_rating": "SCH 40",
            "material_spec": "ASTM A106 Gr.B",
            "end_type": "BW",
            "quantity": 1,
            "unit": "M",
            "length_m": 12.45,
            "confidence": 0.91,
            "remarks": "Mock fallback sample; replace with Gemini result when API key is configured.",
        },
        {
            "item_no": 2,
            "category": "FITTING",
            "description": "Elbow 90 Deg LR, BW, ASME B16.9",
            "size_nps": "6\"",
            "schedule_rating": "SCH 40",
            "material_spec": "ASTM A234 WPB",
            "end_type": "BW",
            "quantity": 4,
            "unit": "EA",
            "confidence": 0.88,
            "remarks": "Counted from route direction changes / BOM in mock sample.",
        },
        {
            "item_no": 3,
            "category": "FITTING",
            "description": "Equal Tee, BW, ASME B16.9",
            "size_nps": "6\"",
            "schedule_rating": "SCH 40",
            "material_spec": "ASTM A234 WPB",
            "end_type": "BW",
            "quantity": 1,
            "unit": "EA",
            "confidence": 0.84,
            "remarks": "Branch fitting.",
        },
        {
            "item_no": 4,
            "category": "FLANGE",
            "description": "Weld Neck Flange, RF, ASME B16.5",
            "size_nps": "6\"",
            "schedule_rating": "CL150",
            "material_spec": "ASTM A105",
            "end_type": "FLGD",
            "quantity": 2,
            "unit": "EA",
            "confidence": 0.86,
            "remarks": "Mock flanged connection around inline valve.",
        },
        {
            "item_no": 5,
            "category": "VALVE",
            "description": "Gate Valve, Flanged, ASME B16.5",
            "size_nps": "6\"",
            "schedule_rating": "CL150",
            "material_spec": "ASTM A216 WCB",
            "end_type": "FLGD",
            "quantity": 1,
            "unit": "EA",
            "confidence": 0.82,
            "remarks": "Bowtie valve symbol in mock sample.",
        },
        {
            "item_no": 6,
            "category": "GASKET",
            "description": "Spiral Wound Gasket, ASME B16.20",
            "size_nps": "6\"",
            "schedule_rating": "CL150",
            "material_spec": "SS316/Graphite",
            "end_type": "FLGD",
            "quantity": 2,
            "unit": "EA",
            "confidence": 0.78,
            "remarks": "Derived one per flanged joint.",
        },
        {
            "item_no": 7,
            "category": "BOLT",
            "description": "Stud Bolt Set with Nuts, ASTM A193 B7 / A194 2H",
            "size_nps": "6\"",
            "schedule_rating": "CL150",
            "material_spec": "ASTM A193 B7 / A194 2H",
            "end_type": "FLGD",
            "quantity": 2,
            "unit": "SET",
            "confidence": 0.78,
            "remarks": "Derived one set per flanged joint.",
        },
    ],
    "summary": {},
    "extraction_info": {
        "provider": "mock",
        "model": "mock",
        "mode": "mock",
        "warnings": [
            "No Gemini API key was configured or mock mode was enabled.",
            "This is a deterministic sample MTO for end-to-end evaluation flow.",
        ],
    },
}


class MockPipeline:
    name = "mock"

    def extract(self, file_bytes: bytes, content_type: str, filename: str) -> MTOResponse:
        data = deepcopy(MOCK_MTO)
        data["extraction_info"]["warnings"].append(f"Processed uploaded file name: {filename}")
        return normalize_and_enrich_mto(data)
