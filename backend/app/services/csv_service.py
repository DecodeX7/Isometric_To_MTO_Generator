import csv
from io import StringIO

from app.models.mto import MTOResponse


CSV_COLUMNS = [
    "item_no",
    "category",
    "description",
    "size_nps",
    "schedule_rating",
    "material_spec",
    "end_type",
    "quantity",
    "unit",
    "length_m",
    "confidence",
    "remarks",
]


def mto_to_csv(result: MTOResponse) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for item in result.items:
        row = item.model_dump()
        writer.writerow({column: row.get(column, "") for column in CSV_COLUMNS})
    return output.getvalue()
