"""Unit tests for tap_harvest_forecast.__init__"""
import sys
import os
import io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import datetime
import json
import unittest
import requests
from unittest.mock import MagicMock, patch

import tap_harvest_forecast as thf


def _make_mock_auth(access_token="test_token", account_id="acc_123"):
    """Create a mock AUTH object for tests."""
    auth = MagicMock()
    auth.get_access_token.return_value = access_token
    auth.get_account_id.return_value = account_id
    return auth


class TestGetAbsPath(unittest.TestCase):
    def test_returns_absolute_path(self):
        result = thf.get_abs_path("schemas/clients.json")
        self.assertTrue(os.path.isabs(result))

    def test_path_ends_with_provided_suffix(self):
        result = thf.get_abs_path("schemas/clients.json")
        # Normalize separators for cross-platform compatibility
        expected_suffix = os.path.join("schemas", "clients.json")
        self.assertTrue(result.replace("\\", "/").endswith(expected_suffix.replace("\\", "/")))

    def test_different_suffixes(self):
        r1 = thf.get_abs_path("schemas/assignments.json")
        r2 = thf.get_abs_path("schemas/roles.json")
        self.assertNotEqual(r1, r2)


class TestLoadSchema(unittest.TestCase):
    def test_loads_valid_endpoint_schemas(self):
        for endpoint in thf.ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                schema = thf.load_schema(endpoint)
                self.assertIsInstance(schema, dict)
                self.assertIn("properties", schema)

    def test_schema_contains_id_and_updated_at(self):
        # roles is FULL_TABLE and has no updated_at replication key
        incremental_endpoints = [e for e in thf.ENDPOINTS if e != "roles"]
        for endpoint in incremental_endpoints:
            with self.subTest(endpoint=endpoint):
                schema = thf.load_schema(endpoint)
                self.assertIn("id", schema["properties"])
                self.assertIn("updated_at", schema["properties"])

    def test_roles_schema_has_no_updated_at(self):
        schema = thf.load_schema("roles")
        self.assertIn("id", schema["properties"])
        self.assertNotIn("updated_at", schema["properties"])

    def test_missing_schema_raises(self):
        with self.assertRaises(Exception):
            thf.load_schema("nonexistent_stream")


class TestGetStart(unittest.TestCase):
    def setUp(self):
        self._state_patcher = patch.dict(thf.STATE, {}, clear=True)
        self._config_patcher = patch.dict(thf.CONFIG, {"start_date": "2024-01-01T00:00:00Z"}, clear=True)
        self._state_patcher.start()
        self._config_patcher.start()

    def tearDown(self):
        self._config_patcher.stop()
        self._state_patcher.stop()

    def test_returns_config_start_when_state_missing(self):
        result = thf.get_start("assignments")
        self.assertEqual(result, "2024-01-01T00:00:00Z")

    def test_returns_state_value_when_present(self):
        thf.STATE["assignments"] = "2024-06-01T00:00:00Z"
        result = thf.get_start("assignments")
        self.assertEqual(result, "2024-06-01T00:00:00Z")

    def test_sets_state_key_when_missing(self):
        thf.get_start("clients")
        self.assertIn("clients", thf.STATE.get("bookmarks", {}))

    def test_does_not_overwrite_existing_state(self):
        thf.STATE["roles"] = "2025-01-01T00:00:00Z"
        result = thf.get_start("roles")
        self.assertEqual(result, "2025-01-01T00:00:00Z")


class TestGetEnd(unittest.TestCase):
    def setUp(self):
        self._config_patcher = patch.dict(thf.CONFIG, {}, clear=True)
        self._config_patcher.start()

    def tearDown(self):
        self._config_patcher.stop()

    def test_returns_config_end_date_when_set(self):
        thf.CONFIG["end_date"] = "2025-12-31"
        result = thf.get_end("assignments")
        self.assertEqual(result, "2025-12-31")

    def test_returns_future_date_when_no_end_date_configured(self):
        result = thf.get_end("assignments")
        # Should be roughly 2 years in the future — just assert it's a string
        self.assertIsInstance(result, str)
        # And that it's in the future relative to today
        result_dt = datetime.datetime.strptime(result, thf.DATE_FORMAT)
        self.assertGreater(result_dt, datetime.datetime.now())


class TestAppendTimesToDates(unittest.TestCase):
    def test_appends_time_to_date_string(self):
        item = {"start_date": "2024-03-15", "end_date": "2024-06-30"}
        thf.append_times_to_dates(item, ["start_date", "end_date"])
        self.assertEqual(item["start_date"], "2024-03-15T00:00:00Z")
        self.assertEqual(item["end_date"], "2024-06-30T00:00:00Z")

    def test_skips_none_values(self):
        item = {"start_date": None}
        thf.append_times_to_dates(item, ["start_date"])
        self.assertIsNone(item["start_date"])

    def test_skips_missing_keys(self):
        item = {"other_field": "value"}
        thf.append_times_to_dates(item, ["start_date"])
        self.assertNotIn("start_date", item)

    def test_no_op_when_date_fields_is_none(self):
        item = {"start_date": "2024-01-01"}
        thf.append_times_to_dates(item, None)
        self.assertEqual(item["start_date"], "2024-01-01")

    def test_no_op_when_date_fields_is_empty_list(self):
        item = {"start_date": "2024-01-01"}
        thf.append_times_to_dates(item, [])
        self.assertEqual(item["start_date"], "2024-01-01")


class TestWindow(unittest.TestCase):
    def _dt(self, s):
        return datetime.datetime.strptime(s, "%Y-%m-%d")

    def test_single_window_when_range_smaller_than_width(self):
        start = self._dt("2024-01-01")
        end = self._dt("2024-02-01")
        width = datetime.timedelta(days=180)
        windows = list(thf.window(start, end, width))
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0][0], start)
        self.assertEqual(windows[0][1], end)

    def test_multiple_windows_cover_full_range(self):
        start = self._dt("2024-01-01")
        end = self._dt("2025-01-01")
        width = datetime.timedelta(days=180)
        windows = list(thf.window(start, end, width))
        self.assertGreater(len(windows), 1)
        # First window starts at start
        self.assertEqual(windows[0][0], start)

    def test_each_window_end_does_not_exceed_overall_end(self):
        start = self._dt("2024-01-01")
        end = self._dt("2025-06-01")
        width = datetime.timedelta(days=180)
        for ws, we in thf.window(start, end, width):
            self.assertLessEqual(we, end)

    def test_windows_are_non_overlapping(self):
        start = self._dt("2024-01-01")
        end = self._dt("2025-01-01")
        width = datetime.timedelta(days=90)
        windows = list(thf.window(start, end, width))
        for i in range(len(windows) - 1):
            self.assertEqual(windows[i][1], windows[i + 1][0])

    def test_empty_range_returns_no_windows(self):
        start = self._dt("2024-01-01")
        end = self._dt("2024-01-01")  # same day
        width = datetime.timedelta(days=180)
        windows = list(thf.window(start, end, width))
        self.assertEqual(len(windows), 0)

    def test_exact_multiple_windows(self):
        start = self._dt("2024-01-01")
        end = self._dt("2024-07-01")   # 182 days
        width = datetime.timedelta(days=91)
        windows = list(thf.window(start, end, width))
        self.assertEqual(len(windows), 2)


class TestAuthClass(unittest.TestCase):
    def _make_auth(self, access_token="test_token", expires_in=3600):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": access_token,
            "expires_in": expires_in,
        }
        with patch.object(thf.Auth, "_make_refresh_token_request", return_value=mock_resp):
            auth = thf.Auth("account_123", "client_id", "client_secret", "refresh_token")
        return auth

    def test_init_sets_access_token(self):
        auth = self._make_auth(access_token="abc123")
        self.assertEqual(auth._access_token, "abc123")

    def test_get_access_token_returns_valid_token(self):
        auth = self._make_auth(access_token="valid_token")
        self.assertEqual(auth.get_access_token(), "valid_token")

    def test_get_account_id_returns_account_id(self):
        auth = self._make_auth()
        self.assertEqual(auth.get_account_id(), "account_123")

    def test_expired_token_triggers_refresh(self):
        auth = self._make_auth()
        # Force expiry
        auth._expires_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        new_resp = MagicMock()
        new_resp.json.return_value = {"access_token": "refreshed_token", "expires_in": 3600}
        with patch.object(auth, "_make_refresh_token_request", return_value=new_resp):
            token = auth.get_access_token()
        self.assertEqual(token, "refreshed_token")

    def test_missing_access_token_in_response_raises_key_error(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "invalid_client", "error_description": "Bad credentials"}
        with patch.object(thf.Auth, "_make_refresh_token_request", return_value=mock_resp):
            with self.assertRaises(KeyError):
                thf.Auth("account_123", "client_id", "client_secret", "refresh_token")


class TestRequestFunction(unittest.TestCase):
    def setUp(self):
        self._config_patcher = patch.dict(thf.CONFIG, {"user_agent": "test-agent"}, clear=True)
        self._auth_patcher = patch.object(thf, 'AUTH', _make_mock_auth())
        self._config_patcher.start()
        self._auth_patcher.start()

    def tearDown(self):
        self._auth_patcher.stop()
        self._config_patcher.stop()

    def test_makes_get_request_and_returns_json(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"assignments": [{"id": 1}]}
        mock_response.raise_for_status = MagicMock()
        with patch.object(thf.SESSION, "send", return_value=mock_response) as mock_send:
            result = thf.request("https://api.forecastapp.com/assignments", {})
        mock_send.assert_called_once()
        self.assertEqual(result, {"assignments": [{"id": 1}]})

    def test_raises_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        with patch.object(thf.SESSION, "send", return_value=mock_response):
            with self.assertRaises(requests.exceptions.HTTPError):
                thf.request("https://api.forecastapp.com/missing", {})

    def test_authorization_header_set(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        captured_requests = []

        def capture(prepared_req, **kwargs):
            captured_requests.append(prepared_req)
            return mock_response

        with patch.object(thf.SESSION, "send", side_effect=capture):
            thf.request("https://api.forecastapp.com/people", {})

        self.assertTrue(len(captured_requests) > 0)
        headers = captured_requests[0].headers
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))

    def test_forecast_account_id_header_set(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        captured_requests = []

        def capture(prepared_req, **kwargs):
            captured_requests.append(prepared_req)
            return mock_response

        with patch.object(thf.SESSION, "send", side_effect=capture):
            thf.request("https://api.forecastapp.com/people", {})

        headers = captured_requests[0].headers
        self.assertIn("Forecast-Account-ID", headers)
        self.assertEqual(headers["Forecast-Account-ID"], "acc_123")


class TestDoDiscover(unittest.TestCase):
    def setUp(self):
        self._access_patcher = patch.object(
            thf, "_get_accessible_endpoints", return_value=thf.ENDPOINTS
        )
        self._access_patcher.start()

    def tearDown(self):
        self._access_patcher.stop()

    def test_outputs_valid_catalog_json(self):
        captured = []
        with patch("sys.stdout", new_callable=lambda: type("W", (), {"write": lambda s, x: captured.append(x), "flush": lambda s: None})()):
            with patch("json.dump") as mock_dump:
                thf.do_discover()
                mock_dump.assert_called_once()
                catalog_arg = mock_dump.call_args[0][0]
        self.assertIn("streams", catalog_arg)
        self.assertEqual(len(catalog_arg["streams"]), len(thf.ENDPOINTS))

    def test_each_stream_has_required_keys(self):
        with patch("json.dump") as mock_dump:
            thf.do_discover()
            catalog_arg = mock_dump.call_args[0][0]
        for stream in catalog_arg["streams"]:
            self.assertIn("stream", stream)
            self.assertIn("tap_stream_id", stream)
            self.assertIn("schema", stream)
            self.assertIn("metadata", stream)

    def test_stream_names_match_endpoints(self):
        with patch("json.dump") as mock_dump:
            thf.do_discover()
            catalog_arg = mock_dump.call_args[0][0]
        stream_ids = [s["tap_stream_id"] for s in catalog_arg["streams"]]
        self.assertEqual(set(stream_ids), set(thf.ENDPOINTS))

    def test_metadata_has_table_key_properties(self):
        with patch("json.dump") as mock_dump:
            thf.do_discover()
            catalog_arg = mock_dump.call_args[0][0]
        for stream in catalog_arg["streams"]:
            breadcrumb_map = {tuple(m["breadcrumb"]): m["metadata"] for m in stream["metadata"]}
            self.assertIn((), breadcrumb_map)
            self.assertIn("table-key-properties", breadcrumb_map[()])
            self.assertEqual(breadcrumb_map[()]["table-key-properties"], ["id"])

    def test_id_and_updated_at_have_automatic_inclusion(self):
        with patch("json.dump") as mock_dump:
            thf.do_discover()
            catalog_arg = mock_dump.call_args[0][0]
        for stream in catalog_arg["streams"]:
            breadcrumb_map = {tuple(m["breadcrumb"]): m["metadata"] for m in stream["metadata"]}
            id_key = ("properties", "id")
            self.assertEqual(breadcrumb_map[id_key]["inclusion"], "automatic")
            # roles is FULL_TABLE — no updated_at replication key
            if stream["tap_stream_id"] != "roles":
                updated_at_key = ("properties", "updated_at")
                self.assertEqual(breadcrumb_map[updated_at_key]["inclusion"], "automatic")


class TestConstants(unittest.TestCase):
    def test_endpoints_list(self):
        expected = ["assignments", "clients", "milestones", "people", "projects", "roles"]
        self.assertEqual(thf.ENDPOINTS, expected)

    def test_required_config_keys(self):
        expected = ["start_date", "account_id", "client_id", "client_secret", "refresh_token"]
        self.assertEqual(thf.REQUIRED_CONFIG_KEYS, expected)

    def test_base_url(self):
        self.assertTrue(thf.BASE_URL.startswith("https://"))

    def test_date_format(self):
        # Should be parseable by datetime
        dt = datetime.datetime.strptime("2024-03-15", thf.DATE_FORMAT)
        self.assertEqual(dt.day, 15)

    def test_primary_key_is_id(self):
        self.assertEqual(thf.PRIMARY_KEY, "id")

    def test_replication_key_is_updated_at(self):
        self.assertEqual(thf.REPLICATION_KEY, "updated_at")


class TestGetUrl(unittest.TestCase):
    def test_returns_full_url_for_endpoint(self):
        url = thf.get_url("assignments")
        self.assertEqual(url, "https://api.forecastapp.com/assignments")

    def test_url_starts_with_base_url(self):
        for endpoint in thf.ENDPOINTS:
            url = thf.get_url(endpoint)
            self.assertTrue(url.startswith(thf.BASE_URL))


class TestSyncEndpoint(unittest.TestCase):
    def setUp(self):
        self._state_patcher = patch.dict(thf.STATE, {}, clear=True)
        self._config_patcher = patch.dict(thf.CONFIG, {"start_date": "2024-01-01T00:00:00Z", "end_date": "2024-12-31"}, clear=True)
        self._auth_patcher = patch.object(thf, 'AUTH', _make_mock_auth())
        self._state_patcher.start()
        self._config_patcher.start()
        self._auth_patcher.start()

    def tearDown(self):
        self._auth_patcher.stop()
        self._config_patcher.stop()
        self._state_patcher.stop()

    def _make_catalog_entry(self, stream_id="assignments"):
        from singer.catalog import CatalogEntry
        schema = thf.load_schema(stream_id)
        catalog_entry = CatalogEntry(
            tap_stream_id=stream_id,
            stream=stream_id,
            schema=MagicMock(to_dict=lambda: schema),
            metadata=[],
        )
        return catalog_entry, schema

    def test_writes_schema_message(self):
        catalog_entry, schema = self._make_catalog_entry("assignments")
        mdata = {}

        sample_record = {
            "id": 1,
            "updated_at": "2024-03-01T12:00:00Z",
            "start_date": "2024-03-01",
            "end_date": "2024-03-31",
        }
        mock_response = {"assignments": [sample_record]}

        with patch("singer.write_schema") as mock_ws, \
             patch("singer.write_message") as mock_wm, \
             patch("singer.write_state") as mock_wst, \
             patch.object(thf, "request", return_value=mock_response):
            thf.sync_endpoint(catalog_entry, schema, mdata)

        mock_ws.assert_called_once_with(
            "assignments", schema, ["id"], bookmark_properties=["updated_at"]
        )

    def test_writes_records_for_each_row(self):
        catalog_entry, schema = self._make_catalog_entry("assignments")
        mdata = {}

        records = [
            {"id": 1, "updated_at": "2024-03-01T12:00:00Z"},
            {"id": 2, "updated_at": "2024-03-02T12:00:00Z"},
        ]
        mock_response = {"assignments": records}

        with patch("singer.write_schema"), \
             patch("singer.write_message") as mock_wm, \
             patch("singer.write_state"), \
             patch.object(thf, "request", return_value=mock_response):
            thf.sync_endpoint(catalog_entry, schema, mdata)

        # write_message called once per unique record (spanning all windows)
        self.assertGreaterEqual(mock_wm.call_count, len(records))

    def test_deduplicates_records_by_id(self):
        catalog_entry, schema = self._make_catalog_entry("assignments")
        mdata = {}

        # Same record appears in multiple windows
        record = {"id": 1, "updated_at": "2024-03-01T12:00:00Z"}
        mock_response = {"assignments": [record]}

        written_records = []
        with patch("singer.write_schema"), \
             patch("singer.write_message", side_effect=lambda m: written_records.append(m)), \
             patch("singer.write_state"), \
             patch.object(thf, "request", return_value=mock_response):
            thf.sync_endpoint(catalog_entry, schema, mdata)

        ids = [m.record["id"] for m in written_records]
        self.assertEqual(len(ids), len(set(ids)))

    def test_writes_state_after_sync(self):
        catalog_entry, schema = self._make_catalog_entry("assignments")
        mdata = {}
        mock_response = {"assignments": []}

        with patch("singer.write_schema"), \
             patch("singer.write_message"), \
             patch("singer.write_state") as mock_wst, \
             patch.object(thf, "request", return_value=mock_response):
            thf.sync_endpoint(catalog_entry, schema, mdata)

        mock_wst.assert_called_once()


class TestDoSync(unittest.TestCase):
    def test_calls_sync_endpoint_for_selected_streams(self):
        mock_stream = MagicMock()
        mock_stream.tap_stream_id = "assignments"
        mock_stream.schema.to_dict.return_value = thf.load_schema("assignments")
        mock_stream.metadata = []

        from singer import metadata as singer_metadata
        mdata = singer_metadata.new()
        singer_metadata.write(mdata, (), "selected", True)
        mock_stream.metadata = singer_metadata.to_list(mdata)

        mock_catalog = MagicMock()
        mock_catalog.streams = [mock_stream]

        with patch.object(thf, "sync_endpoint") as mock_se:
            thf.do_sync(mock_catalog)

        mock_se.assert_called_once()

    def test_skips_unselected_streams(self):
        mock_stream = MagicMock()
        mock_stream.tap_stream_id = "clients"
        mock_stream.metadata = []  # no 'selected' metadata → not selected

        mock_catalog = MagicMock()
        mock_catalog.streams = [mock_stream]

        with patch.object(thf, "sync_endpoint") as mock_se:
            thf.do_sync(mock_catalog)

        mock_se.assert_not_called()


class TestMainImpl(unittest.TestCase):
    def _make_args(self, discover=False, catalog=None, state=None):
        args = MagicMock()
        args.config = {
            "start_date": "2024-01-01T00:00:00Z",
            "account_id": "acc",
            "client_id": "cid",
            "client_secret": "csec",
            "refresh_token": "rtok",
        }
        args.state = state or {}
        args.discover = discover
        args.catalog = catalog
        return args

    def _mock_auth(self):
        mock_auth = MagicMock()
        mock_auth.get_access_token.return_value = "tok"
        mock_auth.get_account_id.return_value = "acc"
        return mock_auth

    def test_discover_mode_calls_do_discover(self):
        args = self._make_args(discover=True)
        with patch("singer.utils.parse_args", return_value=args), \
             patch.object(thf, "Auth", return_value=self._mock_auth()), \
             patch.object(thf, "do_discover") as mock_dd:
            thf.main_impl()
        mock_dd.assert_called_once()

    def test_sync_mode_calls_do_sync(self):
        mock_catalog = MagicMock()
        args = self._make_args(catalog=mock_catalog)
        with patch("singer.utils.parse_args", return_value=args), \
             patch.object(thf, "Auth", return_value=self._mock_auth()), \
             patch.object(thf, "do_sync") as mock_ds:
            thf.main_impl()
        mock_ds.assert_called_once_with(mock_catalog)

    def test_main_catches_exception_and_re_raises(self):
        with patch.object(thf, "main_impl", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                thf.main()


# ---------------------------------------------------------------------------
# Tests for check_stream_access
# ---------------------------------------------------------------------------

class TestCheckStreamAccess(unittest.TestCase):
    """Unit tests for check_stream_access()."""

    def setUp(self):
        self._auth_patcher = patch.object(thf, "AUTH", _make_mock_auth())
        self._auth_patcher.start()

    def tearDown(self):
        self._auth_patcher.stop()

    def _make_403_error(self):
        resp = MagicMock()
        resp.status_code = 403
        exc = requests.exceptions.HTTPError(response=resp)
        return exc

    def test_returns_true_when_request_succeeds(self):
        with patch.object(thf, "request", return_value={"assignments": []}):
            result = thf.check_stream_access("assignments")
        self.assertTrue(result)

    def test_returns_false_on_403(self):
        with patch.object(thf, "request", side_effect=self._make_403_error()):
            result = thf.check_stream_access("assignments")
        self.assertFalse(result)

    def test_reraises_non_403_http_error(self):
        resp = MagicMock()
        resp.status_code = 500
        exc = requests.exceptions.HTTPError(response=resp)
        with patch.object(thf, "request", side_effect=exc):
            with self.assertRaises(requests.exceptions.HTTPError):
                thf.check_stream_access("assignments")

    def test_reraises_connection_error(self):
        with patch.object(thf, "request", side_effect=requests.exceptions.ConnectionError("timeout")):
            with self.assertRaises(requests.exceptions.ConnectionError):
                thf.check_stream_access("assignments")

    def test_uses_today_as_date_window(self):
        """check_stream_access must pass start_date and end_date params."""
        captured = {}

        def fake_request(url, params=None):
            captured["params"] = params
            return {"assignments": []}

        with patch.object(thf, "request", side_effect=fake_request):
            thf.check_stream_access("assignments")

        self.assertIn("start_date", captured["params"])
        self.assertIn("end_date", captured["params"])
        self.assertEqual(captured["params"]["start_date"], captured["params"]["end_date"])


# ---------------------------------------------------------------------------
# Tests for _get_accessible_endpoints
# ---------------------------------------------------------------------------

class TestGetAccessibleEndpoints(unittest.TestCase):
    """Unit tests for _get_accessible_endpoints()."""

    ALL_ENDPOINTS = ["assignments", "clients", "milestones", "people", "projects", "roles"]

    def test_returns_all_when_all_accessible(self):
        with patch.object(thf, "check_stream_access", return_value=True):
            result = thf._get_accessible_endpoints(self.ALL_ENDPOINTS)
        self.assertEqual(result, self.ALL_ENDPOINTS)

    def test_excludes_inaccessible_streams(self):
        def access_side_effect(ep):
            return ep != "roles"

        with patch.object(thf, "check_stream_access", side_effect=access_side_effect):
            result = thf._get_accessible_endpoints(self.ALL_ENDPOINTS)

        self.assertNotIn("roles", result)
        self.assertIn("assignments", result)

    def test_raises_when_all_inaccessible(self):
        with patch.object(thf, "check_stream_access", return_value=False):
            with self.assertRaises(thf.ForecastForbiddenError) as ctx:
                thf._get_accessible_endpoints(self.ALL_ENDPOINTS)
        self.assertIn("403", str(ctx.exception))

    def test_partial_access_does_not_raise(self):
        def access_side_effect(ep):
            return ep in ["assignments", "clients"]

        with patch.object(thf, "check_stream_access", side_effect=access_side_effect):
            result = thf._get_accessible_endpoints(self.ALL_ENDPOINTS)

        self.assertEqual(set(result), {"assignments", "clients"})

    def test_preserves_endpoint_order(self):
        endpoints = ["roles", "assignments", "clients"]

        def access_side_effect(ep):
            return ep != "roles"

        with patch.object(thf, "check_stream_access", side_effect=access_side_effect):
            result = thf._get_accessible_endpoints(endpoints)

        self.assertEqual(result, ["assignments", "clients"])


# ---------------------------------------------------------------------------
# Tests for do_discover with access checks
# ---------------------------------------------------------------------------


class TestDoDiscoverAccessChecks(unittest.TestCase):
    """Verify do_discover() honours _get_accessible_endpoints()."""

    def setUp(self):
        self._auth_patcher = patch.object(thf, "AUTH", _make_mock_auth())
        self._auth_patcher.start()

    def tearDown(self):
        self._auth_patcher.stop()

    def test_discover_includes_only_accessible_streams(self):
        accessible = ["assignments", "clients"]
        captured = io.StringIO()
        with patch.object(thf, "_get_accessible_endpoints", return_value=accessible), \
             patch("sys.stdout", captured):
            thf.do_discover()
        catalog = json.loads(captured.getvalue())

        stream_ids = [s["tap_stream_id"] for s in catalog["streams"]]
        self.assertEqual(set(stream_ids), {"assignments", "clients"})

    def test_discover_with_all_accessible_streams(self):
        captured = io.StringIO()
        with patch.object(thf, "_get_accessible_endpoints", return_value=thf.ENDPOINTS), \
             patch("sys.stdout", captured):
            thf.do_discover()
        catalog = json.loads(captured.getvalue())

        stream_ids = [s["tap_stream_id"] for s in catalog["streams"]]
        self.assertEqual(set(stream_ids), set(thf.ENDPOINTS))

    def test_discover_raises_when_no_streams_accessible(self):
        with patch.object(thf, "_get_accessible_endpoints",
                          side_effect=thf.ForecastForbiddenError("no access")):
            with self.assertRaises(thf.ForecastForbiddenError):
                thf.do_discover()
