"""Mock integration test: all fields — running the tap with all streams and
fields selected replicates all fields defined in the schema."""
import unittest

from .base import (
    HarvestForecastMockBaseTest,
    ALL_STREAM_IDS,
    STREAM_CONFIG,
)

# Fields present in schema but known to be absent from real API responses.
# Documented here so tests are not broken by these known gaps.
KNOWN_MISSING_FIELDS = {
    'roles': {'updated_at', 'updated_by_id'},
}


class AllFieldsMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def setUp(self):
        self.catalog = self._make_selected_catalog()

    def test_sync_writes_records_for_all_streams(self):
        records, _ = self.run_sync(self.catalog)
        written_streams = {s for s, _ in records}
        for stream in ALL_STREAM_IDS:
            with self.subTest(stream=stream):
                self.assertIn(stream, written_streams)

    def test_records_have_primary_key(self):
        records, _ = self.run_sync(self.catalog)
        for stream in ALL_STREAM_IDS:
            with self.subTest(stream=stream):
                recs = [r for s, r in records if s == stream]
                self.assertTrue(len(recs) > 0, f"No records for {stream}")
                for rec in recs:
                    self.assertIn('id', rec)
                    self.assertIsNotNone(rec['id'])

    def test_correct_record_counts(self):
        records, _ = self.run_sync(self.catalog)
        # Each stream should write exactly record_count unique records (dedup by id)
        for stream, cfg in STREAM_CONFIG.items():
            with self.subTest(stream=stream):
                written_ids = [r['id'] for s, r in records if s == stream]
                self.assertEqual(
                    len(written_ids), cfg['record_count'],
                    f"{stream}: expected {cfg['record_count']} records, got {len(written_ids)}",
                )

    def test_schema_fields_present_in_records(self):
        """Verify that every field from the schema appears in synced records
        (excluding known missing fields)."""
        records, _ = self.run_sync(self.catalog)
        for stream in ALL_STREAM_IDS:
            with self.subTest(stream=stream):
                schema = self._generator.load_schema(stream)
                schema_fields = set(schema.get('properties', {}).keys())
                missing_ok = KNOWN_MISSING_FIELDS.get(stream, set())

                recs = [r for s, r in records if s == stream]
                self.assertGreater(len(recs), 0, f"No records for {stream}")

                for rec in recs:
                    rec_fields = set(rec.keys())
                    unexpected_missing = (schema_fields - missing_ok) - rec_fields
                    self.assertEqual(
                        unexpected_missing, set(),
                        f"{stream}: unexpected missing fields: {unexpected_missing}",
                    )

    def test_sync_only_selected_stream(self):
        """When only one stream is selected, only it writes records."""
        catalog = self._make_selected_catalog(stream_names=['clients'])
        records, _ = self.run_sync(catalog)
        written_streams = {s for s, _ in records}
        self.assertIn('clients', written_streams)
        for other in ALL_STREAM_IDS - {'clients'}:
            self.assertNotIn(other, written_streams,
                f"Stream '{other}' should not have records when not selected")
