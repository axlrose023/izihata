from app.database.migrations.schema import MIGRATION_ARCHIVE_TABLES, include_schema_name


def test_only_explicit_migration_archives_are_excluded_from_reflection():
    for name in MIGRATION_ARCHIVE_TABLES:
        assert not include_schema_name(name, "table", {})
        assert include_schema_name(name, "column", {})
    assert include_schema_name("products", "table", {})
    assert include_schema_name("unknown_before_migration", "table", {})
    assert include_schema_name(None, "schema", {})
