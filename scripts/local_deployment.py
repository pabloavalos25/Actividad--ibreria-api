"""Helpers for the isolated local simulation of the VPS delivery exercise."""

from decimal import Decimal


def sale_from_seed(response: dict) -> dict:
    """Validate the sale created from the known, isolated TP seed."""
    assert response["id"] > 0
    assert Decimal(response["total"]) == Decimal("50000.00")
    assert response["cliente"]["id"] == 2
    assert len(response["renglones"]) == 1
    line = response["renglones"][0]
    assert line["libro_id"] == 1
    assert line["titulo"] == "Rayuela"
    assert line["cantidad"] == 2
    return {"id": response["id"], "total": Decimal(response["total"]), "title": line["titulo"]}
