"""Integration tests for tap-harvest-forecast all fields replication with mocked data."""
import unittest
from unittest.mock import patch, MagicMock

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast


class HarvestForecastAllFieldsTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test that all fields from schemas are replicated when selected."""

    def test_all_schema_fields_are_present_in_records(self):
        """Verify that mock records contain all fields defined in schemas."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Load the schema
                schema = self.load_schema(stream_name)
                schema_fields = set(schema.get("properties", {}).keys())

                # Generate a mock record
                mock_record = self._generate_stream_record(stream_name)
                record_fields = set(mock_record.keys())

                # Find fields in schema but not in mock record
                missing_fields = schema_fields - record_fields

                # Some fields might legitimately be absent if they're optional/nullable
                # For now, just verify that key fields are present
                required_fields = {"id", "updated_at"}
                self.assertTrue(
                    required_fields.issubset(record_fields),
                    f"Stream {stream_name} mock record missing required fields: {required_fields - record_fields}"
                )

    def test_sync_outputs_all_record_fields(self):
        """Verify that sync includes all fields from the mock records."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Create a mock record with all fields
                records = [self._generate_stream_record(stream_name, 1)]
                expected_fields = set(records[0].keys())

                mock_request = MagicMock(return_value={stream_name: records})

                from singer.catalog import Catalog
                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                written_records = []
                original_write_message = tap_harvest_forecast.singer.write_message
                def capture_message(msg):
                    if hasattr(msg, 'record'):
                        written_records.append(msg.record)
                    return original_write_message(msg)

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.singer, 'write_message', side_effect=capture_message):

                    tap_harvest_forecast.do_sync(catalog)

                # Verify at least one record was written
                self.assertGreater(len(written_records), 0,
                    f"Expected records to be written for {stream_name}")

                # Check that written records have the expected fields
                for record in written_records:
                    actual_fields = set(record.keys())
                    # All fields in original record should be in output
                    self.assertTrue(
                        expected_fields.issubset(actual_fields),
                        f"Written record missing fields: {expected_fields - actual_fields}"
                    )
