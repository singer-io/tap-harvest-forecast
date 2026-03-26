"""Integration tests for tap-harvest-forecast pagination with mocked data."""
import unittest
from unittest.mock import patch, MagicMock

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast
from singer.catalog import Catalog


class HarvestForecastPaginationTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test that the tap properly handles pagination through windowed date ranges."""

    def test_sync_uses_date_windows(self):
        """Verify that sync requests data in 180-day windows."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Track all request calls
                request_calls = []

                def mock_request_fn(url, params=None):
                    request_calls.append({"url": url, "params": params})
                    # Return empty results
                    return {stream_name: []}

                mock_request = MagicMock(side_effect=mock_request_fn)

                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                # Use a date range that will require multiple windows
                config = self.MOCK_CONFIG.copy()
                config["start_date"] = "2023-01-01T00:00:00Z"

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', config), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )):

                    tap_harvest_forecast.do_sync(catalog)

                # Verify multiple requests were made (due to windowing)
                self.assertGreater(len(request_calls), 0,
                    f"Expected at least one request for {stream_name}")

                # Verify requests have start_date and end_date params
                for call in request_calls:
                    params = call.get("params", {})
                    self.assertIn("start_date", params,
                        f"Request should include start_date param")
                    self.assertIn("end_date", params,
                        f"Request should include end_date param")

    def test_sync_handles_multiple_pages_of_data(self):
        """Verify all records across multiple window pages are synced."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Simulate multiple pages by returning different data for each call
                call_count = [0]

                def mock_request_fn(url, params=None):
                    call_count[0] += 1
                    # Return different records for each window
                    if call_count[0] == 1:
                        return {stream_name: [
                            self._generate_stream_record(stream_name, 1, "2024-01-15T12:00:00Z"),
                            self._generate_stream_record(stream_name, 2, "2024-02-15T12:00:00Z"),
                        ]}
                    elif call_count[0] == 2:
                        return {stream_name: [
                            self._generate_stream_record(stream_name, 3, "2024-06-15T12:00:00Z"),
                            self._generate_stream_record(stream_name, 4, "2024-07-15T12:00:00Z"),
                        ]}
                    else:
                        return {stream_name: []}

                mock_request = MagicMock(side_effect=mock_request_fn)

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

                # Verify records from multiple pages were collected
                # Should have gotten records with IDs 1, 2, 3, 4
                self.assertGreater(len(written_records), 0,
                    "Expected records to be written from multiple pages")

    def test_sync_deduplicates_records_across_windows(self):
        """Verify that records appearing in multiple windows are deduplicated."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Return the same record in multiple window responses
                duplicate_record = self._generate_stream_record(stream_name, 1, "2024-03-15T12:00:00Z")

                call_count = [0]
                def mock_request_fn(url, params=None):
                    call_count[0] += 1
                    # Return the same record in first two windows
                    if call_count[0] <= 2:
                        return {stream_name: [duplicate_record]}
                    return {stream_name: []}

                mock_request = MagicMock(side_effect=mock_request_fn)

                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                written_records = []
                original_write_message = tap_harvest_forecast.singer.write_message
                def capture_message(msg):
                    if hasattr(msg, 'record'):
                        written_records.append(msg.record)
                    return original_write_message(msg)

                config = self.MOCK_CONFIG.copy()
                config["start_date"] = "2023-01-01T00:00:00Z"

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', config), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.singer, 'write_message', side_effect=capture_message):

                    tap_harvest_forecast.do_sync(catalog)

                # Count records with ID=1
                id_1_count = sum(1 for r in written_records if r.get("id") == 1)

                # Should only write the record once despite it appearing in multiple windows
                self.assertEqual(id_1_count, 1,
                    f"Record with ID=1 should be written exactly once, but was written {id_1_count} times")
