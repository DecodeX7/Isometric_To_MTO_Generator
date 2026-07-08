from app.pipeline.postprocess import normalize_and_enrich_mto


def test_postprocess_derives_gasket_and_bolt_for_flanged_items() -> None:
    raw = {
        "drawing_meta": {"nps": "6\""},
        "items": [
            {
                "item_no": 1,
                "category": "PIPE",
                "description": "Pipe",
                "quantity": 1,
                "unit": "M",
                "length_m": 3.2,
            },
            {
                "item_no": 2,
                "category": "FLANGE",
                "description": "WN Flange",
                "quantity": 2,
                "unit": "EA",
                "end_type": "FLGD",
            },
        ],
    }

    result = normalize_and_enrich_mto(raw)

    categories = [item.category for item in result.items]
    assert "GASKET" in categories
    assert "BOLT" in categories
    assert result.summary.total_pipe_length_m == 3.2
    assert result.summary.flanges == 2
    assert result.summary.gaskets == 2
    assert result.summary.bolt_sets == 2
