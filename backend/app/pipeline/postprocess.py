from math import ceil

from app.models.mto import Category, ExtractionInfo, MTOItem, MTOResponse, Summary


def _as_int_count(value: float | int | None) -> int:
    if value is None:
        return 0
    return int(ceil(float(value)))


def _has_flanged_end(item: MTOItem) -> bool:
    text = f"{item.end_type} {item.description}".upper()
    return "FLG" in text or "FLANGED" in text or "FLANGE" in text


def normalize_and_enrich_mto(raw_data: dict | MTOResponse) -> MTOResponse:
    """Validate, normalize, derive missing joint consumables, and compute summary.

    This layer is intentionally deterministic. It makes the AI output safer and
    easier to explain during a code walkthrough.
    """

    response = raw_data if isinstance(raw_data, MTOResponse) else MTOResponse.model_validate(raw_data)

    items: list[MTOItem] = []
    for index, item in enumerate(response.items, start=1):
        item.item_no = index
        item.unit = item.unit or ("M" if item.category == Category.PIPE.value else "EA")
        if item.confidence is None:
            item.confidence = 0.5
        items.append(item)

    has_gasket = any(item.category == Category.GASKET.value for item in items)
    has_bolt = any(item.category == Category.BOLT.value for item in items)

    flange_count = sum(
        _as_int_count(item.quantity) for item in items if item.category == Category.FLANGE.value
    )
    flanged_valve_count = sum(
        _as_int_count(item.quantity)
        for item in items
        if item.category == Category.VALVE.value and _has_flanged_end(item)
    )
    flanged_joint_count = max(flange_count, flanged_valve_count * 2)

    # Assessment-friendly heuristic: if visible flanged components exist but the
    # LLM missed consumables, derive them and label the assumption in remarks.
    if flanged_joint_count > 0 and not has_gasket:
        items.append(
            MTOItem(
                item_no=len(items) + 1,
                category=Category.GASKET,
                description="Spiral Wound Gasket, ASME B16.20",
                size_nps=response.drawing_meta.nps if response.drawing_meta.nps != "Unknown" else "",
                schedule_rating="CL150",
                material_spec="SS316/Graphite",
                end_type="FLGD",
                quantity=flanged_joint_count,
                unit="EA",
                confidence=0.62,
                remarks="Derived by backend: one gasket per assumed flanged joint.",
            )
        )

    if flanged_joint_count > 0 and not has_bolt:
        items.append(
            MTOItem(
                item_no=len(items) + 1,
                category=Category.BOLT,
                description="Stud Bolt Set with Nuts, ASTM A193 B7 / A194 2H",
                size_nps=response.drawing_meta.nps if response.drawing_meta.nps != "Unknown" else "",
                schedule_rating="CL150",
                material_spec="ASTM A193 B7 / A194 2H",
                end_type="FLGD",
                quantity=flanged_joint_count,
                unit="SET",
                confidence=0.62,
                remarks="Derived by backend: one bolt set per assumed flanged joint.",
            )
        )

    for index, item in enumerate(items, start=1):
        item.item_no = index

    summary = compute_summary(items)
    response.items = items
    response.summary = summary
    if not response.extraction_info:
        response.extraction_info = ExtractionInfo()
    return response


def compute_summary(items: list[MTOItem]) -> Summary:
    total_pipe_length = 0.0
    fittings = flanges = valves = gaskets = bolt_sets = supports = field_welds = 0

    for item in items:
        quantity = _as_int_count(item.quantity)
        category = item.category
        if category == Category.PIPE.value:
            total_pipe_length += float(item.length_m or 0)
        elif category == Category.FITTING.value:
            fittings += quantity
        elif category == Category.FLANGE.value:
            flanges += quantity
        elif category == Category.VALVE.value:
            valves += quantity
        elif category == Category.GASKET.value:
            gaskets += quantity
        elif category == Category.BOLT.value:
            bolt_sets += quantity
        elif category == Category.SUPPORT.value:
            supports += quantity
        elif category == Category.WELD.value:
            field_welds += quantity if "FIELD" in item.remarks.upper() or "FW" in item.remarks.upper() else 0

        if category != Category.WELD.value and (
            "FIELD WELD" in item.remarks.upper() or " FW" in f" {item.remarks.upper()}"
        ):
            field_welds += 1

    return Summary(
        total_pipe_length_m=round(total_pipe_length, 3),
        fittings=fittings,
        flanges=flanges,
        valves=valves,
        gaskets=gaskets,
        bolt_sets=bolt_sets,
        supports=supports,
        field_welds=field_welds,
    )
