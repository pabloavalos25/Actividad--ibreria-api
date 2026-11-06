from decimal import Decimal

import pytest

from scripts.local_deployment import sale_from_seed


def test_sale_from_seed_checks_created_sale_and_amount():
    response = {
        "id": 3,
        "total": "50000.00",
        "cliente": {"id": 2, "nombre": "Tomás Ríos", "email": "tomas@example.com"},
        "renglones": [{"libro_id": 1, "titulo": "Rayuela", "cantidad": 2}],
    }

    result = sale_from_seed(response)

    assert result == {"id": 3, "total": Decimal("50000.00"), "title": "Rayuela"}


@pytest.mark.parametrize("response", [
    {"id": 3, "total": "0.00", "cliente": {}, "renglones": []},
    {"id": 3, "total": "50000.00", "cliente": {}, "renglones": [{"libro_id": 2, "titulo": "Ficciones", "cantidad": 2}]},
])
def test_sale_from_seed_rejects_wrong_or_empty_result(response):
    with pytest.raises((AssertionError, KeyError, ValueError)):
        sale_from_seed(response)
