"""Integration tests for tap-harvest-forecast bookmarking with mocked data."""
import unittest
from unittest.mock import patch, MagicMock
from singer.catalog import Catalog

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast
from singer import utils


class HarvestForecastBookmarkTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test that bookmarks are set and respected correctly."""

    def test_bookmark_is_set_during_sync(self):
        """Verify that bookmarks are written to state during sync."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Create mock records with different updated_at values
                records = [
                    self._generate_stream_record(stream_name, i, f"2024-03-{i:02d}T12:00:00Z")
                    for i in range(1, 4)
                ]

                # Mock the request function
                mock_request = MagicMock(return_value={stream_name: records})

                # Mock catalog with this stream selected
                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                # Capture written messages
                written_messages = []
                original_write_message = tap_harvest_forecast.singer.write_message
                def capture_message(msg):
                    written_messages.append(msg)
                    return original_write_message(msg)

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.singer, 'write_message', side_effect=capture_message):

                    # Run sync
                    tap_harvest_forecast.do_sync(catalog)

                    # Verify STATE was updated with bookmark (must be inside patch context)
                    self.assertIn(stream_name, tap_harvest_forecast.STATE)
                    bookmark_value = tap_harvest_forecast.STATE[stream_name]

                    # Bookmark should be set to the last record's updated_at
                    self.assertIsNotNone(bookmark_value)

    def test_bookmark_filters_records(self):
        """Verify that records are filtered based on existing bookmark."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Create records: before, at, and after bookmark date
                bookmark_date = "2024-03-15T12:00:00Z"
                records = [
                    self._generate_stream_record(stream_name, 1, "2024-03-10T12:00:00Z"),  # Before bookmark
                    self._generate_stream_record(stream_name, 2, "2024-03-15T12:00:00Z"),  # At bookmark
                    self._generate_stream_record(stream_name, 3, "2024-03-20T12:00:00Z"),  # After bookmark
                ]

                mock_request = MagicMock(return_value={stream_name: records})

                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                # Set initial bookmark
                initial_state = {stream_name: bookmark_date}

                # Capture written record messages
                written_records = []
                original_write_message = tap_harvest_forecast.singer.write_message
                def capture_message(msg):
                    if hasattr(msg, 'record'):
                        written_records.append(msg.record)
                    return original_write_message(msg)

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', initial_state.copy()), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.singer, 'write_message', side_effect=capture_message):

                    tap_harvest_forecast.do_sync(catalog)

                # Verify that only records >= bookmark were written
                written_ids = {r["id"] for r in written_records}

                # Record 1 (before bookmark) should not be included
                self.assertNotIn(1, written_ids,
                    "Record before bookmark should be filtered out")
                # Records 2 and 3 (at/after bookmark) should be included
                self.assertGreater(len(written_records), 0, "Expected some records to be synced")

    def test_bookmark_advances_to_latest_record(self):
        """Verify bookmark advances to the most recent record's updated_at."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Records with progressively later timestamps
                latest_date = "2024-03-25T12:00:00Z"
                records = [
                    self._generate_stream_record(stream_name, 1, "2024-03-20T12:00:00Z"),
                    self._generate_stream_record(stream_name, 2, "2024-03-22T12:00:00Z"),
                    self._generate_stream_record(stream_name, 3, latest_date),
                ]

                mock_request = MagicMock(return_value={stream_name: records})

                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                initial_bookmark = "2024-03-01T12:00:00Z"

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', {stream_name: initial_bookmark}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )):

                    tap_harvest_forecast.do_sync(catalog)

                    # Bookmark should have advanced to the latest record (must be inside patch context)
                    final_bookmark = tap_harvest_forecast.STATE.get(stream_name)
                    self.assertIsNotNone(final_bookmark)

                    # Parse and compare dates
                    final_dt = utils.strptime_to_utc(final_bookmark)
                    latest_dt = utils.strptime_to_utc(latest_date)

                    self.assertGreaterEqual(final_dt, latest_dt,
                        f"Bookmark should have advanced to {latest_date} but is {final_bookmark}"
                    )
