"""Integration tests for tap-harvest-forecast automatic fields with mocked data."""
import unittest
from unittest.mock import patch, MagicMock
from singer.catalog import Catalog

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast


class HarvestForecastAutomaticFieldsTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test that automatic fields (primary & replication keys) are always replicated."""

    def test_automatic_fields_always_present(self):
        """Verify primary and replication keys are present even with no field selection."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                records = [self._generate_stream_record(stream_name, 1)]
                mock_request = MagicMock(return_value={stream_name: records})

                # Create catalog with stream selected but no specific fields selected
                # (simulating automatic-only field selection)
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

                # Verify records were written
                self.assertGreater(len(written_records), 0,
                    f"Expected records to be written for {stream_name}")

                # Verify automatic fields are present
                expected_automatic = (
                    self.EXPECTED_METADATA[stream_name]["primary_keys"] |
                    self.EXPECTED_METADATA[stream_name]["replication_keys"]
                )

                for record in written_records:
                    actual_fields = set(record.keys())
                    self.assertTrue(
                        expected_automatic.issubset(actual_fields),
                        f"Automatic fields {expected_automatic} not all present in record. "
                        f"Found: {actual_fields}"
                    )

    def test_primary_key_always_populated(self):
        """Verify primary key field is never null."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                records = [
                    self._generate_stream_record(stream_name, 1),
                    self._generate_stream_record(stream_name, 2),
                    self._generate_stream_record(stream_name, 3),
                ]
                mock_request = MagicMock(return_value={stream_name: records})

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

                # Get primary key field name
                primary_key = next(iter(self.EXPECTED_METADATA[stream_name]["primary_keys"]))

                # Verify all records have non-null primary key
                for record in written_records:
                    self.assertIn(primary_key, record,
                        f"Primary key '{primary_key}' missing from record")
                    self.assertIsNotNone(record[primary_key],
                        f"Primary key '{primary_key}' should not be null")

    def test_replication_key_always_populated(self):
        """Verify replication key field is never null."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                records = [
                    self._generate_stream_record(stream_name, 1, "2024-03-15T12:00:00Z"),
                    self._generate_stream_record(stream_name, 2, "2024-03-16T12:00:00Z"),
                ]
                mock_request = MagicMock(return_value={stream_name: records})

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

                # Get replication key field name
                replication_key = next(iter(self.EXPECTED_METADATA[stream_name]["replication_keys"]))

                # Verify all records have non-null replication key
                for record in written_records:
                    self.assertIn(replication_key, record,
                        f"Replication key '{replication_key}' missing from record")
                    self.assertIsNotNone(record[replication_key],
                        f"Replication key '{replication_key}' should not be null")
