"""Integration tests for tap-harvest-forecast start_date filtering with mocked data."""
import unittest
from unittest.mock import patch, MagicMock

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast
from singer import utils
from singer.catalog import Catalog


class HarvestForecastStartDateTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test that start_date configuration is respected."""

    def test_records_before_start_date_are_filtered(self):
        """Verify that records with updated_at before start_date are not synced."""
        start_date = "2024-03-15T00:00:00Z"

        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Create records: some before start_date, some after
                records = [
                    self._generate_stream_record(stream_name, 1, "2024-03-10T12:00:00Z"),  # Before
                    self._generate_stream_record(stream_name, 2, "2024-03-14T12:00:00Z"),  # Before
                    self._generate_stream_record(stream_name, 3, "2024-03-15T00:00:00Z"),  # At start_date
                    self._generate_stream_record(stream_name, 4, "2024-03-20T12:00:00Z"),  # After
                    self._generate_stream_record(stream_name, 5, "2024-03-25T12:00:00Z"),  # After
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

                config = self.MOCK_CONFIG.copy()
                config["start_date"] = start_date

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', config), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.singer, 'write_message', side_effect=capture_message):

                    tap_harvest_forecast.do_sync(catalog)

                # Verify records were written
                self.assertGreater(len(written_records), 0,
                    f"Expected some records to be written for {stream_name}")

                # Verify only records >= start_date were written
                start_dt = utils.strptime_to_utc(start_date)
                for record in written_records:
                    record_dt = utils.strptime_to_utc(record["updated_at"])
                    self.assertGreaterEqual(
                        record_dt, start_dt,
                        f"Record with updated_at={record['updated_at']} should not be synced "
                        f"(before start_date={start_date})"
                    )

    def test_start_date_becomes_initial_bookmark(self):
        """Verify that start_date is used as the initial bookmark when no state exists."""
        start_date = "2024-03-01T00:00:00Z"

        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                records = [
                    self._generate_stream_record(stream_name, 1, "2024-03-15T12:00:00Z"),
                ]

                mock_request = MagicMock(return_value={stream_name: records})

                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                config = self.MOCK_CONFIG.copy()
                config["start_date"] = start_date

                # Start with empty state
                initial_state = {}

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', config), \
                     patch.object(tap_harvest_forecast, 'STATE', initial_state), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )):

                    # Before sync, get_start should return start_date
                    bookmark = tap_harvest_forecast.get_start(stream_name)

                    self.assertEqual(bookmark, start_date,
                        f"Initial bookmark should be start_date when no state exists")

    def test_empty_start_date_uses_config_value(self):
        """Verify that when STATE is empty, start_date from config is used."""
        start_date = "2023-01-01T00:00:00Z"

        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                config = self.MOCK_CONFIG.copy()
                config["start_date"] = start_date

                with patch.object(tap_harvest_forecast, 'CONFIG', config), \
                     patch.object(tap_harvest_forecast, 'STATE', {}):

                    # Call get_start which should pull from config
                    result = tap_harvest_forecast.get_start(stream_name)

                    self.assertEqual(result, start_date,
                        f"get_start should return config start_date when state is empty")

    def test_bookmark_overrides_start_date(self):
        """Verify that existing bookmark takes precedence over start_date."""
        start_date = "2024-01-01T00:00:00Z"
        bookmark_date = "2024-03-15T00:00:00Z"

        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                config = self.MOCK_CONFIG.copy()
                config["start_date"] = start_date

                initial_state = {stream_name: bookmark_date}

                with patch.object(tap_harvest_forecast, 'CONFIG', config), \
                     patch.object(tap_harvest_forecast, 'STATE', initial_state):

                    # Call get_start which should pull from state, not config
                    result = tap_harvest_forecast.get_start(stream_name)

                    self.assertEqual(result, bookmark_date,
                        f"get_start should return bookmark from state, not config start_date")
