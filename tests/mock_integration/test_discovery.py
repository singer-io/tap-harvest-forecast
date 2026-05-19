"""Mock integration test: discovery produces correct catalog and metadata."""
import unittest

from singer import metadata

from .base import HarvestForecastMockBaseTest, ALL_STREAM_IDS, INCREMENTAL_STREAMS


class DiscoveryMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def setUp(self):
        self.catalog = self._build_catalog()

    def test_discovery_returns_all_streams(self):
        stream_ids = {entry.tap_stream_id for entry in self.catalog.streams}
        self.assertEqual(stream_ids, ALL_STREAM_IDS)

    def test_key_properties_are_id(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                keys = mdata.get((), {}).get('table-key-properties', [])
                self.assertEqual(keys, ['id'])

    def test_schema_properties_exist(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                schema = entry.schema.to_dict()
                self.assertIn('properties', schema)
                self.assertGreater(len(schema['properties']), 0)

    def test_id_and_updated_at_in_schema_where_expected(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                props = entry.schema.to_dict().get('properties', {})
                self.assertIn('id', props)
                if entry.tap_stream_id in INCREMENTAL_STREAMS:
                    self.assertIn('updated_at', props)

    def test_replication_method_set(self):
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                rep_method = mdata.get((), {}).get('forced-replication-method')
                self.assertIn(rep_method, ('INCREMENTAL', 'FULL_TABLE'))

    def test_incremental_streams_have_valid_replication_keys(self):
        for entry in self.catalog.streams:
            if entry.tap_stream_id not in INCREMENTAL_STREAMS:
                continue
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                valid_keys = mdata.get((), {}).get('valid-replication-keys')
                self.assertIsNotNone(valid_keys)
                self.assertIn('updated_at', valid_keys)

    def test_full_table_streams_have_no_replication_keys(self):
        from .base import FULL_TABLE_STREAMS
        for entry in self.catalog.streams:
            if entry.tap_stream_id not in FULL_TABLE_STREAMS:
                continue
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                valid_keys = mdata.get((), {}).get('valid-replication-keys')
                self.assertIsNone(valid_keys)

    def test_discovery_metadata_includes_exact_keys(self):
        """Verify table-key-properties == ['id'] and valid-replication-keys == ['updated_at']
        for each stream — matches assertions from previously approved mock tests."""
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                mdata = metadata.to_map(entry.metadata)
                table_keys = mdata.get((), {}).get('table-key-properties', [])
                self.assertEqual(
                    set(table_keys), {'id'},
                    f"{entry.tap_stream_id}: expected table-key-properties={{'id'}}, got {set(table_keys)}",
                )
                if entry.tap_stream_id in INCREMENTAL_STREAMS:
                    replication_keys = mdata.get((), {}).get('valid-replication-keys', [])
                    self.assertEqual(
                        set(replication_keys), {'updated_at'},
                        f"{entry.tap_stream_id}: expected valid-replication-keys={{'updated_at'}}, "
                        f"got {set(replication_keys)}",
                    )

    def test_discovery_schemas_are_valid(self):
        """Verify each stream schema has type, properties dict, and 'id' field;
        incremental streams also have 'updated_at'. Matches previous approved test."""
        for entry in self.catalog.streams:
            with self.subTest(stream=entry.tap_stream_id):
                schema = entry.schema.to_dict()
                self.assertIn('type', schema,
                    f"{entry.tap_stream_id}: schema missing 'type'")
                self.assertIn('properties', schema,
                    f"{entry.tap_stream_id}: schema missing 'properties'")
                self.assertIsInstance(schema['properties'], dict)
                self.assertIn('id', schema['properties'],
                    f"{entry.tap_stream_id}: schema missing 'id' property")
                if entry.tap_stream_id in INCREMENTAL_STREAMS:
                    self.assertIn('updated_at', schema['properties'],
                        f"{entry.tap_stream_id}: schema missing 'updated_at' property")
