import json

import pytest

_TEST_PROJECT_ARNS = json.dumps(
    {
        "income": "arn:aws:bedrock:us-east-1:123:project/a",
        "expenses": "arn:aws:bedrock:us-east-1:123:project/b",
        "identity": "arn:aws:bedrock:us-east-1:123:project/c",
        "employment": "arn:aws:bedrock:us-east-1:123:project/d",
        "training": "arn:aws:bedrock:us-east-1:123:project/e",
    }
)


@pytest.fixture
def bda_project_arns(monkeypatch):
    """Set BDA_PROJECT_ARNS env var for tests that need document categories."""
    monkeypatch.setenv("BDA_PROJECT_ARNS", _TEST_PROJECT_ARNS)


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
