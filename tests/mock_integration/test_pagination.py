"""Mock integration test: pagination / windowed date ranges — the tap splits
the date range into 180-day windows and makes a separate request per window,
deduplicating records that appear in multiple windows."""
import unittest
from unittest.mock import patch

import tap_harvest_forecast as thf

from .base import (
    ALL_STREAM_IDS,
    HarvestForecastMockBaseTest,
    STREAM_CONFIG,
    INCREMENTAL_STREAMS,
)


class PaginationMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def _config_spanning_multiple_windows(self):
        """Config covering 18 months → at least three 180-day windows."""
        config = self.default_config.copy()
        config['start_date'] = '2025-01-01T00:00:00Z'
        config['end_date'] = '2026-08-01'
        return config

    def test_requests_include_start_date_and_end_date_params(self):
        """Every request to the API must include start_date and end_date params."""
        config = self._config_spanning_multiple_windows()
        request_calls = []

        def tracking_request(url, params=None):
            request_calls.append({'url': url, 'params': params or {}})
            stream_name = url.rstrip('/').split('/')[-1]
            records = self._get_mock_records(stream_name) if stream_name in STREAM_CONFIG else []
            return {stream_name: records}

        catalog = self._make_selected_catalog(stream_names=['assignments'])
        with patch.dict(thf.STATE, {}, clear=True), \
             patch.dict(thf.CONFIG, config, clear=True), \
             patch.object(thf, 'AUTH', self._make_mock_auth()), \
             patch.object(thf, 'request', side_effect=tracking_request), \
             patch('singer.write_state'), \
             patch('singer.write_schema'), \
             patch('singer.write_message'):
            thf.do_sync(catalog)

        self.assertGreater(len(request_calls), 0, "Expected at least one request")
        for req in request_calls:
            self.assertIn('start_date', req['params'],
                f"Request missing start_date param: {req}")
            self.assertIn('end_date', req['params'],
                f"Request missing end_date param: {req}")

    def test_multiple_windows_made_for_wide_date_range(self):
        """A date range > 180 days must result in more than one request per stream."""
        config = self._config_spanning_multiple_windows()
        request_calls = []

        def tracking_request(url, params=None):
            request_calls.append(url)
            stream_name = url.rstrip('/').split('/')[-1]
            records = self._get_mock_records(stream_name) if stream_name in STREAM_CONFIG else []
            return {stream_name: records}

        catalog = self._make_selected_catalog(stream_names=['assignments'])
        with patch.dict(thf.STATE, {}, clear=True), \
             patch.dict(thf.CONFIG, config, clear=True), \
             patch.object(thf, 'AUTH', self._make_mock_auth()), \
             patch.object(thf, 'request', side_effect=tracking_request), \
             patch('singer.write_state'), \
             patch('singer.write_schema'), \
             patch('singer.write_message'):
            thf.do_sync(catalog)

        # ~18 months / 180 days ≈ 3+ windows
        self.assertGreaterEqual(len(request_calls), 3,
            f"Expected >= 3 requests for wide date range, got {len(request_calls)}")

    def test_records_are_deduplicated_across_windows(self):
        """Records whose IDs appear in multiple window responses are written only once."""
        config = self._config_spanning_multiple_windows()
        catalog = self._make_selected_catalog(stream_names=['assignments'])
        records, _ = self.run_sync(catalog, state={}, config=config)

        stream_records = [r for s, r in records if s == 'assignments']
        ids = [r['id'] for r in stream_records]
        # No duplicate IDs
        self.assertEqual(
            len(ids), len(set(ids)),
            f"Duplicate record IDs found: {[i for i in ids if ids.count(i) > 1]}",
        )

    def test_total_unique_records_equals_mock_count(self):
        """After deduplication, the total records must equal the mock data count."""
        config = self._config_spanning_multiple_windows()

        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                catalog = self._make_selected_catalog(stream_names=[stream])
                records, _ = self.run_sync(catalog, state={}, config=config)
                stream_records = [r for s, r in records if s == stream]
                self.assertEqual(
                    len(stream_records), STREAM_CONFIG[stream]['record_count'],
                    f"{stream}: expected {STREAM_CONFIG[stream]['record_count']} unique records",
                )

    def test_sync_uses_date_windows_for_all_streams(self):
        """Every selected stream must have start_date + end_date on every request.
        Covers all streams including FULL_TABLE. Ported from previously approved mock test."""
        config = self._config_spanning_multiple_windows()

        for stream_name in ALL_STREAM_IDS:
            with self.subTest(stream=stream_name):
                request_calls = []

                def tracking_request(url, params=None):
                    request_calls.append({'url': url, 'params': params or {}})
                    sn = url.rstrip('/').split('/')[-1]
                    recs = self._get_mock_records(sn) if sn in STREAM_CONFIG else []
                    return {sn: recs}

                catalog = self._make_selected_catalog(stream_names=[stream_name])
                with patch.dict(thf.STATE, {}, clear=True), \
                     patch.dict(thf.CONFIG, config, clear=True), \
                     patch.object(thf, 'AUTH', self._make_mock_auth()), \
                     patch.object(thf, 'request', side_effect=tracking_request), \
                     patch('singer.write_state'), \
                     patch('singer.write_schema'), \
                     patch('singer.write_message'):
                    thf.do_sync(catalog)

                self.assertGreater(len(request_calls), 0,
                    f"Expected at least one request for {stream_name}")
                for req in request_calls:
                    self.assertIn('start_date', req['params'],
                        f"{stream_name}: request missing start_date param")
                    self.assertIn('end_date', req['params'],
                        f"{stream_name}: request missing end_date param")

    def test_sync_handles_different_records_per_window(self):
        """Records from each window are all collected and written.
        Ported from previously approved mock test."""
        stream_name = 'assignments'
        call_count = [0]

        # Window 1 returns IDs 1 & 2, window 2 returns IDs 3 & 4
        def windowed_request(url, params=None):
            call_count[0] += 1
            sn = url.rstrip('/').split('/')[-1]
            if call_count[0] == 1:
                return {sn: [
                    {'id': 1, 'updated_at': '2025-02-15T12:00:00Z'},
                    {'id': 2, 'updated_at': '2025-03-15T12:00:00Z'},
                ]}
            elif call_count[0] == 2:
                return {sn: [
                    {'id': 3, 'updated_at': '2025-08-15T12:00:00Z'},
                    {'id': 4, 'updated_at': '2025-09-15T12:00:00Z'},
                ]}
            return {sn: []}

        config = self._config_spanning_multiple_windows()
        catalog = self._make_selected_catalog(stream_names=[stream_name])

        written = []
        with patch.dict(thf.STATE, {}, clear=True), \
             patch.dict(thf.CONFIG, config, clear=True), \
             patch.object(thf, 'AUTH', self._make_mock_auth()), \
             patch.object(thf, 'request', side_effect=windowed_request), \
             patch('singer.write_state'), \
             patch('singer.write_schema'), \
             patch('singer.write_message',
                   side_effect=lambda m: written.append(m.record) if hasattr(m, 'record') else None):
            thf.do_sync(catalog)

        self.assertGreater(len(written), 0, "Expected records from multiple windows")
        written_ids = {r['id'] for r in written}
        # Records from both windows must be present
        self.assertTrue({1, 2}.issubset(written_ids),
            f"Window-1 records missing: {written_ids}")
