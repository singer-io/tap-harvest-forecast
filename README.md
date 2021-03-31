# tap-harvest-forecast

A singer.io tap for extracting data from the Harvest Forecast REST API, written in Python 3. Heavily derived from Jordan Ryan's [Harvest Tap](https://github.com/singer-io/tap-harvest). Thanks for your work Jordan!

As the Harvest Forecast API is [not yet public](https://help.getharvest.com/forecast/faqs/faq-list/api/), this tap is experimental and liable to break at any time. Please keep this in mind if you run into any issues (and submit a PR if you can fix something broken).

Author: Robert Benjamin ([@robertbenjamin](https://github.com/robertbenjamin))

## Quick start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    virtualenv -p python3 venv
    source venv/bin/activate
    python setup.py install
    ```

2. Retrieve your oauth credentials from the Harvest Forecast API
    
    Visit the [developer tools](https://id.getharvest.com/developers) page on
    Harvest's website and create a new oauth token

    Paste the Client ID you got from the above page in the url of a browser like
    `https://id.getharvest.com/oauth2/authorize?client_id={OAUTH_CLIENT_ID}&response_type=code`. Now you're
    able to login, click 'authorize app' and then are redirected to a url like
    this
    `https://id.getharvest.com/oauth2/authorize?code={OAUTH_REFRESH_TOKEN}&scope=all`.
    You will use this `OAUTH_REFRESH_TOKEN` in the following step to configure
    the oauth application

3. Create your tap's `tap_config.json` file which should look like the following:

    ```json
    {
        "client_id": "OAUTH_CLIENT_ID",
        "client_secret": "OAUTH_CLIENT_SECRET",
        "refresh_token": "OAUTH_REFRESH_TOKEN",
        "start_date": "2017-04-19T13:37:30Z",
        "user_agent": "tap-harvest-forecast (your.email@example.com)"
    }

4. [Optional] Create the initial state file

    ```json
    {
        "assignments": "2000-01-01T00:00:00Z",
        "clients": "2000-01-01T00:00:00Z",
        "milestones": "2000-01-01T00:00:00Z",
        "people": "2000-01-01T00:00:00Z",
        "projects": "2000-01-01T00:00:00Z"
    }
    ```

5. Setup the catalog
    
    `tap-harvest-forecast` can be run with:

    ```bash
    tap-harvest-forecast --config tap_config.json [--state state.json]
    ```

    Run the tap in discovery mode to obtain the catalog:

    ```bash
    tap-harvest-forecast --config tap_config.json --discover > catalog.json
    ```

    You will need to add metadata in the catalog for stream/field selection, by
    adding `"selected": true` to the `metadata` for each stream you wish to
    select in `tap_config.json`


6. Run the application

    Run the Tap in sync mode:

    ```bash
    tap-harvest-forecast --config tap_config.json --catalog catalog.json
    ```

    The output should consist of SCHEMA, RECORD, STATE, and METRIC messages.
    If you wish to test the tap with a target, see the [documentation](DOCUMENTATION.md)

---

## Common Issues
If you see a completely blank run, like this: 
```
```
This is caused by the catalog.json not containing `"selected": "true"` in the metadata sections for each stream. 
Just add that and you're good to go

Copyright &copy; 2018 Stitch
