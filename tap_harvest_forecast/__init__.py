#!/usr/bin/env python3

import datetime
import json
import os
import requests
import sys

import singer
from singer import metadata
from singer import Transformer, utils
import backoff

LOGGER = singer.get_logger()
SESSION = requests.Session()
REQUIRED_CONFIG_KEYS = [
    "start_date",
    "account_id",
    "client_id",
    "client_secret",
    "refresh_token"
]

ENDPOINTS = [
    "assignments",
    "clients",
    "milestones",
    "people",
    "projects",
    "placeholders",
    "roles"
]

PRIMARY_KEY = "id"
REPLICATION_KEY = 'updated_at'

BASE_URL = "https://api.forecastapp.com/"
BASE_ID_URL = "https://id.getharvest.com/api/v2/"
CONFIG = {}
STATE = {}
AUTH = {}

class Auth:
    def __init__(self, account_id, client_id, client_secret, refresh_token):
        self._account_id = account_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._refresh_access_token()

    @backoff.on_exception(
        backoff.expo,
        requests.exceptions.RequestException,
        max_tries=5,
        giveup=lambda e: e.response is not None and 400 <= e.response.status_code < 500,
        factor=2)
    def _make_refresh_token_request(self):
        return requests.request('POST',
                                url=BASE_ID_URL + 'oauth2/token',
                                data={
                                    'client_id': self._client_id,
                                    'client_secret': self._client_secret,
                                    'refresh_token': self._refresh_token,
                                    'grant_type': 'refresh_token',
                                },
                                headers={"User-Agent": CONFIG.get("user_agent")})

    def _refresh_access_token(self):
        LOGGER.info("Refreshing access token")
        resp_json = self._make_refresh_token_request().json()
        expires_in_seconds = resp_json.get('expires_in', 17 * 60 * 60)
        self._expires_at = utils.now() + datetime.timedelta(seconds=expires_in_seconds)

        try:
            self._access_token = resp_json['access_token']
        except KeyError as key_err:
            if resp_json.get('error'):
                LOGGER.critical(resp_json.get('error'))
            if resp_json.get('error_description'):
                LOGGER.critical(resp_json.get('error_description'))
            raise
        LOGGER.info("Got refreshed access token")

    def get_access_token(self):
        if self._access_token is not None and self._expires_at > utils.now():
            return self._access_token

        self._refresh_access_token()
        return self._access_token

    def get_account_id(self):
        return self._account_id


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

def load_schema(entity):
    return utils.load_json(get_abs_path("schemas/{}.json".format(entity)))


def get_start(key):
    if key not in STATE:
        STATE[key] = CONFIG['start_date']

    return STATE[key]

def get_url(endpoint):
    return BASE_URL + endpoint

@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException),
    max_tries = 5,
    giveup = lambda e: e.response is not None and 400 <= e.response.status_code < 500,
    factor = 2)
@utils.ratelimit(100, 15)
def request(url, params = None):
    params = params or {}
    access_token = AUTH.get_access_token()
    account_id = AUTH.get_account_id()
    headers = {"Accept": "application/json",
               "Forecast-Account-ID": account_id,
               "Authorization": "Bearer " + access_token}
    req = requests.Request("GET", url=url, params=params, headers=headers).prepare()
    LOGGER.info("GET {}".format(req.url))
    resp = SESSION.send(req)
    resp.raise_for_status()
    return resp.json()

def append_times_to_dates(item, date_fields):
    if date_fields:
        for date_field in date_fields:
            if item.get(date_field):
                item[date_field] += "T00:00:00Z"

def sync_endpoint(endpoint, schema, mdata, date_fields = None):
    singer.write_schema(endpoint,
                        schema,
                        [PRIMARY_KEY],
                        bookmark_properties = [REPLICATION_KEY])

    start = get_start(endpoint)
    url = get_url(endpoint)
    data = request(url)[endpoint]
    time_extracted = utils.now()

    for row in data:
        with Transformer() as transformer:
            rec = transformer.transform(row, schema, mdata)
            append_times_to_dates(rec, date_fields)

            updated_at = rec[REPLICATION_KEY]
            if updated_at >= start:
                singer.write_record(endpoint,
                                    rec,
                                    time_extracted = time_extracted)
                utils.update_state(STATE, endpoint, updated_at)

    singer.write_state(STATE)

def do_sync(catalog):
    LOGGER.info("Starting sync")

    for stream in catalog.streams:
        mdata = metadata.to_map(stream.metadata)
        is_selected = metadata.get(mdata, (), 'selected')
        if is_selected:
            sync_endpoint(stream.tap_stream_id, stream.schema.to_dict(), mdata)

    LOGGER.info("Sync complete")

def do_discover():
    streams = []
    for endpoint in ENDPOINTS:
        schema = load_schema(endpoint)

        mdata = metadata.new()

        mdata = metadata.write(mdata, (), 'table-key-properties', [PRIMARY_KEY])
        mdata = metadata.write(mdata, (), 'valid-replication-keys', [REPLICATION_KEY])

        for field_name in schema['properties'].keys():
            if field_name == PRIMARY_KEY or field_name == REPLICATION_KEY:
                mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'automatic')
            else:
                mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'available')

        streams.append({'stream': endpoint,
                        'tap_stream_id': endpoint,
                        'schema': schema,
                        'metadata': metadata.to_list(mdata)})

    catalog = {"streams": streams}
    json.dump(catalog, sys.stdout, indent=2)

def main_impl():
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)
    CONFIG.update(args.config)
    global AUTH # pylint: disable=global-statement
    AUTH = Auth(CONFIG['account_id'], CONFIG["client_id"], CONFIG["client_secret"], CONFIG["refresh_token"])
    STATE.update(args.state)
    if args.discover:
        do_discover()
    elif args.catalog:
        do_sync(args.catalog)

def main():
    try:
        main_impl()
    except Exception as exc:
        LOGGER.critical(exc)
        raise exc

if __name__ == "__main__":
    main()
