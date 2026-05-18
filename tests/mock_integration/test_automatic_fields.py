"""Mock integration test: automatic fields — primary key and replication key
are marked inclusion=automatic in discover metadata."""
import unittest

from singer import metadata

from .base import (
    HarvestForecastMockBaseTest,
    STREAM_CONFIG,
    INCREMENTAL_STREAMS,
)


class AutomaticFieldsMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def setUp(self):
        self.catalog = self._build_catalog()

    def test_primary_key_is_automatic(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                inclusion = mdata.get(('properties', 'id'), {}).get('inclusion')
                self.assertEqual(inclusion, 'automatic')

    def test_replication_key_is_automatic_for_incremental(self):
        for entry in self.catalog.streams:
            if entry.tap_stream_id not in INCREMENTAL_STREAMS:
                continue
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                inclusion = mdata.get(('properties', 'updated_at'), {}).get('inclusion')
                self.assertEqual(inclusion, 'automatic')

    def test_non_key_fields_are_available(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                cfg = STREAM_CONFIG[entry.tap_stream_id]
                auto_fields = {'id'}
                if cfg['replication_key']:
                    auto_fields.add(cfg['replication_key'])

                schema_props = entry.schema.to_dict().get('properties', {})
                for field in schema_props:
                    breadcrumb = ('properties', field)
                    inclusion = mdata.get(breadcrumb, {}).get('inclusion')
                    if field in auto_fields:
                        self.assertEqual(
                            inclusion, 'automatic',
                            f"'{entry.tap_stream_id}.{field}' expected 'automatic', got '{inclusion}'",
                        )
                    else:
                        self.assertEqual(
                            inclusion, 'available',
                            f"'{entry.tap_stream_id}.{field}' expected 'available', got '{inclusion}'",
                        )

    def test_primary_key_in_schema(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                props = entry.schema.to_dict().get('properties', {})
                self.assertIn('id', props)

    def test_automatic_fields_always_present_in_records(self):
        """Verify automatic fields appear in synced records even with minimal selection."""
        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                catalog = self._make_selected_catalog(stream_names=[stream_name])
                records, _ = self.run_sync(catalog)
                stream_records = [r for s, r in records if s == stream_name]
                self.assertGreater(len(stream_records), 0,
                    f"Expected records for {stream_name}")
                for rec in stream_records:
                    self.assertIn('id', rec)
                    self.assertIn('updated_at', rec)

    def test_primary_key_always_populated(self):
        """Verify primary key (id) is present and non-null in every synced record.
        Matches previously approved mock test."""
        for stream_name in STREAM_CONFIG:
            with self.subTest(stream=stream_name):
                catalog = self._make_selected_catalog(stream_names=[stream_name])
                records, _ = self.run_sync(catalog)
                stream_records = [r for s, r in records if s == stream_name]
                self.assertGreater(len(stream_records), 0,
                    f"Expected records for {stream_name}")
                for rec in stream_records:
                    self.assertIn('id', rec,
                        f"{stream_name}: 'id' missing from record")
                    self.assertIsNotNone(rec['id'],
                        f"{stream_name}: 'id' should not be null")

    def test_replication_key_always_populated(self):
        """Verify replication key (updated_at) is present and non-null in every
        synced record for INCREMENTAL streams. Matches previously approved mock test."""
        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                catalog = self._make_selected_catalog(stream_names=[stream_name])
                records, _ = self.run_sync(catalog)
                stream_records = [r for s, r in records if s == stream_name]
                self.assertGreater(len(stream_records), 0,
                    f"Expected records for {stream_name}")
                for rec in stream_records:
                    self.assertIn('updated_at', rec,
                        f"{stream_name}: 'updated_at' missing from record")
                    self.assertIsNotNone(rec['updated_at'],
                        f"{stream_name}: 'updated_at' should not be null")
