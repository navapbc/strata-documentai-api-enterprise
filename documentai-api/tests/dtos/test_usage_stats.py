"""Tests for the UsageStats DTO - the shared usage-metric serialization contract."""

from documentai_api.dtos.usage_stats import UsageStats

ALL_FIELDS = {
    "total_records",
    "total_bda_invocations",
    "total_file_size_bytes",
    "total_bda_pages",
    "total_bedrock_input_tokens",
    "total_bedrock_output_tokens",
}


def test_defaults_are_zero():
    stats = UsageStats()
    assert stats.to_dict() == dict.fromkeys(ALL_FIELDS, 0)


def test_to_dict_round_trips_through_from_dict():
    stats = UsageStats(
        total_records=3,
        total_bda_invocations=2,
        total_file_size_bytes=1024,
        total_bda_pages=5,
        total_bedrock_input_tokens=100,
        total_bedrock_output_tokens=50,
    )
    assert UsageStats.from_dict(stats.to_dict()) == stats


def test_from_dict_defaults_missing_fields_to_zero():
    # An old stats.json missing a newly added field must read as 0, not error.
    stats = UsageStats.from_dict({"total_records": 7})
    assert stats.total_records == 7
    assert stats.total_bedrock_output_tokens == 0


def test_from_dict_ignores_extra_fields():
    stats = UsageStats.from_dict({"total_records": 1, "total_pages": 99, "junk": "x"})
    assert stats.total_records == 1
    assert stats.to_dict().keys() == ALL_FIELDS


def test_from_dict_coerces_string_ints():
    # Athena/JSON rows can deliver numeric values as strings.
    stats = UsageStats.from_dict({"total_records": "4", "total_file_size_bytes": "2048"})
    assert stats.total_records == 4
    assert stats.total_file_size_bytes == 2048


def test_from_dict_treats_null_as_zero():
    # A key present with an explicit None (partial/hand-edited stats.json) must
    # read as 0, not raise int(None).
    stats = UsageStats.from_dict({"total_records": 5, "total_bda_pages": None})
    assert stats.total_records == 5
    assert stats.total_bda_pages == 0


def test_from_aggregator_treats_null_as_zero():
    daily_stat = {
        "total_records": None,
        "usage_stats": {"total_bda_pages": None, "total_file_size_bytes": 10},
    }
    stats = UsageStats.from_aggregator(daily_stat)
    assert stats.total_records == 0
    assert stats.total_bda_pages == 0
    assert stats.total_file_size_bytes == 10


def test_sum_fieldwise():
    a = UsageStats(total_records=1, total_bda_pages=2)
    b = UsageStats(total_records=3, total_bedrock_input_tokens=10)
    total = UsageStats.sum([a, b])
    assert total.total_records == 4
    assert total.total_bda_pages == 2
    assert total.total_bedrock_input_tokens == 10


def test_sum_multiple():
    rows = [
        UsageStats(total_records=1),
        UsageStats(total_records=2),
        UsageStats(total_records=3),
    ]
    assert UsageStats.sum(rows).total_records == 6


def test_from_aggregator_reads_nested_and_top_level():
    daily_stat = {
        "total_records": 10,
        "total_bda_invocations": 4,
        "usage_stats": {
            "total_file_size_bytes": 500,
            "total_pages": 20,  # not part of the DTO - must be ignored
            "total_bda_pages": 8,
            "total_bedrock_input_tokens": 300,
            "total_bedrock_output_tokens": 150,
        },
    }
    stats = UsageStats.from_aggregator(daily_stat)
    assert stats == UsageStats(
        total_records=10,
        total_bda_invocations=4,
        total_file_size_bytes=500,
        total_bda_pages=8,
        total_bedrock_input_tokens=300,
        total_bedrock_output_tokens=150,
    )


def test_from_aggregator_handles_missing_usage_stats():
    stats = UsageStats.from_aggregator({"total_records": 2})
    assert stats.total_records == 2
    assert stats.total_bda_pages == 0


def test_usage_stats_fields_match_response_models():
    """Guard against field-set drift between DTO and API response models.

    If a metric is added to UsageStats but not the response models (or vice
    versa), the extra key silently drops from the API response. This test
    fails CI when the sets diverge.
    """
    from dataclasses import fields as dc_fields

    from documentai_api.dtos.usage_stats import UsageStats
    from documentai_api.models.usage import DailyUsage, TenantUsage

    dto_fields = {f.name for f in dc_fields(UsageStats)}

    # TenantUsage has tenant_id as extra; DailyUsage has date + partial as extra
    tenant_usage_fields = set(TenantUsage.model_fields.keys()) - {"tenant_id"}
    daily_usage_fields = set(DailyUsage.model_fields.keys()) - {"date", "partial"}

    assert dto_fields == tenant_usage_fields, (
        f"TenantUsage drift: {dto_fields.symmetric_difference(tenant_usage_fields)}"
    )
    assert dto_fields == daily_usage_fields, (
        f"DailyUsage drift: {dto_fields.symmetric_difference(daily_usage_fields)}"
    )
