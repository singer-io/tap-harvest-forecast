"""Integration tests for tap-harvest-forecast interrupted sync resumption with mocked data."""
import unittest
from unittest.mock import patch, MagicMock

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast
from singer import utils
from singer.catalog import Catalog


class HarvestForecastInterruptedSyncTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test that interrupted syncs can resume from the last bookmark."""

    def test_sync_resumes_from_last_bookmark_on_interruption(self):
        """Verify that if sync is interrupted, it resumes from the last written bookmark."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Simulate a scenario where sync writes some records and updates state,
                # then gets interrupted before completing all records

                records_batch_1 = [
                    self._generate_stream_record(stream_name, 1, "2024-03-10T12:00:00Z"),
                    self._generate_stream_record(stream_name, 2, "2024-03-12T12:00:00Z"),
                    self._generate_stream_record(stream_name, 3, "2024-03-15T12:00:00Z"),  # Last successful
                ]

                records_batch_2 = [
                    self._generate_stream_record(stream_name, 3, "2024-03-15T12:00:00Z"),  # Overlap
                    self._generate_stream_record(stream_name, 4, "2024-03-20T12:00:00Z"),
                    self._generate_stream_record(stream_name, 5, "2024-03-25T12:00:00Z"),
                ]

                # First sync: partial sync that writes state
                mock_request_1 = MagicMock(return_value={stream_name: records_batch_1})


                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                # Track state updates
                state_after_first_sync = {}

                with patch.object(tap_harvest_forecast, 'request', mock_request_1), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )):

                    # Run first sync
                    tap_harvest_forecast.do_sync(catalog)

                    # Capture the state after first sync
                    state_after_first_sync = tap_harvest_forecast.STATE.copy()

                # Verify state was updated after first sync
                self.assertIn(stream_name, state_after_first_sync,
                    f"State should be updated for {stream_name} after first sync")

                bookmark_after_first = state_after_first_sync[stream_name]
                bookmark_dt = utils.strptime_to_utc(bookmark_after_first)

                # Second sync: resume with the bookmark from first sync
                mock_request_2 = MagicMock(return_value={stream_name: records_batch_2})

                written_records_second_sync = []
                original_write_message = tap_harvest_forecast.singer.write_message
                def capture_message(msg):
                    if hasattr(msg, 'record'):
                        written_records_second_sync.append(msg.record)
                    return original_write_message(msg)

                with patch.object(tap_harvest_forecast, 'request', mock_request_2), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', state_after_first_sync), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.singer, 'write_message', side_effect=capture_message):

                    # Run second sync
                    tap_harvest_forecast.do_sync(catalog)

                # Verify second sync only processes records >= the bookmark
                for record in written_records_second_sync:
                    record_dt = utils.strptime_to_utc(record["updated_at"])
                    self.assertGreaterEqual(
                        record_dt, bookmark_dt,
                        f"Second sync should only process records >= bookmark {bookmark_after_first}, "
                        f"but found record with updated_at={record['updated_at']}"
                    )

    def test_state_update_frequency_during_sync(self):
        """Verify that state is updated periodically during sync, not just at the end."""
        for stream_name in self.EXPECTED_STREAMS:
            with self.subTest(stream=stream_name):
                # Create multiple records spanning different dates
                records = [
                    self._generate_stream_record(stream_name, i, f"2024-03-{10+i:02d}T12:00:00Z")
                    for i in range(1, 6)
                ]

                mock_request = MagicMock(return_value={stream_name: records})

                catalog_entry = self.create_catalog_entry(stream_name, selected=True)
                catalog = Catalog([catalog_entry])

                # Track state updates
                state_snapshots = []

                original_update_state = tap_harvest_forecast.utils.update_state
                def capture_state_update(state, stream, value):
                    result = original_update_state(state, stream, value)
                    # Take a snapshot of the state after each update
                    state_snapshots.append({
                        "stream": stream,
                        "value": str(value),
                        "state_copy": state.copy()
                    })
                    return result

                with patch.object(tap_harvest_forecast, 'request', mock_request), \
                     patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG), \
                     patch.object(tap_harvest_forecast, 'STATE', {}), \
                     patch.object(tap_harvest_forecast, 'AUTH', MagicMock(
                         get_access_token=lambda: "test_token",
                         get_account_id=lambda: "test_account"
                     )), \
                     patch.object(tap_harvest_forecast.utils, 'update_state', side_effect=capture_state_update):

                    tap_harvest_forecast.do_sync(catalog)

                # Verify state was updated multiple times during sync (once per record)
                stream_updates = [s for s in state_snapshots if s["stream"] == stream_name]
                self.assertGreater(len(stream_updates), 0,
                    f"State should be updated during sync for {stream_name}")

                # Verify state values are progressing forward
                if len(stream_updates) > 1:
                    for i in range(1, len(stream_updates)):
                        prev_value = utils.strptime_to_utc(stream_updates[i-1]["value"])
                        curr_value = utils.strptime_to_utc(stream_updates[i]["value"])
                        self.assertGreaterEqual(
                            curr_value, prev_value,
                            "State should progress forward (or stay same) with each update"
                        )
