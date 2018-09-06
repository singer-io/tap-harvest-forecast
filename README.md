# tap-harvest-forecast

A singer.io tap for extracting data from the Harvest Forecast REST API, written in Python 3. Heavily derived from Jordan Ryan's [Harvest Tap](https://github.com/singer-io/tap-harvest). Thanks for your work Jordan!

As the Harvest Forecast API is [not yet public](https://help.getharvest.com/forecast/faqs/faq-list/api/), this tap is experimental and liable to break at any time. Please keep this in mind if you run into any issues (and submit a PR if you can fix something broken).

Author: Robert Benjamin ([@robertbenjamin](https://github.com/robertbenjamin))

## Quick start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    > virtualenv -p python 3 venv
    > source venv/bin/activate
    > python setup.py install
    ```

2. Create your tap's config file which should look like the following:

    ```json
    {
        "start_date": "2017-04-19T13:37:30Z",
        "account_id": "HARVEST_FORECAST_ACCOUNT_ID",
        "access_token": "HARVEST_FORECAST_PERSONAL_ACCESSS_TOKEN"
    }
    ```

3. [Optional] Create the initial state file

    ```json
    {
        "assignments": "2000-01-01T00:00:00Z",
        "clients": "2000-01-01T00:00:00Z",
        "milestones": "2000-01-01T00:00:00Z",
        "people": "2000-01-01T00:00:00Z",
        "projects": "2000-01-01T00:00:00Z"
    }
    ```

4. Run the application

    `tap-harvest-forecast` can be run with:

    ```bash
    tap-harvest-forecast --config config.json [--state state.json]
    ```

---

Copyright &copy; 2018 Stitch
