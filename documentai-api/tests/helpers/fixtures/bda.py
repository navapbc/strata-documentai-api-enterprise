import pytest


@pytest.fixture
def bda_result_with_geometry():
    """BDA result fixture with geometry and nested fields."""
    return {
        "explainability_info": [
            {
                "tenant_name": {
                    "confidence": 0.93,
                    "value": "Jane Smith",
                    "type": "string",
                    "geometry": [
                        {
                            "boundingBox": {
                                "top": 0.31,
                                "left": 0.40,
                                "width": 0.04,
                                "height": 0.009,
                            },
                            "page": 1,
                        }
                    ],
                },
                "amount": {
                    "confidence": 0.88,
                    "value": "100.00",
                    "type": "currency",
                },
                "payment_details": {
                    "base_rent": {
                        "confidence": 0.91,
                        "value": "1200",
                        "type": "currency",
                        "geometry": [
                            {
                                "boundingBox": {
                                    "top": 0.5,
                                    "left": 0.3,
                                    "width": 0.1,
                                    "height": 0.02,
                                },
                                "page": 1,
                            }
                        ],
                    },
                    "fees": {
                        "confidence": 0.90,
                        "value": "",
                        "type": "currency",
                    },
                },
            }
        ]
    }
