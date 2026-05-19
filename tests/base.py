"""
Base test class for tap-harvest-forecast integration tests.
"""
import os

from tap_tester.base_suite_tests.base_case import BaseCase


class HarvestForecastBaseTest(BaseCase):
    """Setup expectations for test sub classes.

    Metadata describing streams. A bunch of shared methods that are used
    in tap-tester tests. Shared tap-specific methods (as needed).
    """

    start_date = "2026-03-01T00:00:00Z"

    @staticmethod
    def tap_name():
        """The name of the tap."""
        return "tap-harvest-forecast"

    @staticmethod
    def get_type():
        """The expected connection type in Stitch."""
        return "platform.harvest-forecast"

    @classmethod
    def expected_metadata(cls):
        """The expected streams and metadata about the streams."""
        return {
            "assignments": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"updated_at"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100,
            },
            "clients": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"updated_at"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100,
            },
            "milestones": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"updated_at"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100,
            },
            "people": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"updated_at"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100,
            },
            "projects": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"updated_at"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100,
            },
            "roles": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100,
            },
        }

    @staticmethod
    def get_credentials():
        """Authentication information for the test account."""
        credentials_dict = {}
        creds = {
            'client_id': 'TAP_HARVEST_FORECAST_CLIENT_ID',
            'client_secret': 'TAP_HARVEST_FORECAST_CLIENT_SECRET',
            'refresh_token': 'TAP_HARVEST_FORECAST_REFRESH_TOKEN',
        }

        for cred in creds:
            credentials_dict[cred] = os.getenv(creds[cred])

        return credentials_dict

    def get_properties(self, original: bool = True):
        """Configuration of properties required for the tap."""
        return_value = {
            "start_date": self.start_date,
            "account_id": os.getenv('TAP_HARVEST_FORECAST_ACCOUNT_ID'),
        }
        if original:
            return return_value

        return_value["start_date"] = self.start_date
        return return_value
