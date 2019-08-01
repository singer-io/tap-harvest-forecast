# Harvest Forecast

## Connecting Harvest Forecast

### Requirements

To set up this Harvest Forecast in Stitch, you need to create a personal access
token in the developer tools section of Harvest's website.

### Setup

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    virtualenv -p python 3 ~/virtualenvs/tap-harvest-forecast
    source ~/virtualenvs/tap-harvest-forecast/bin/activate
    python setup.py install
    ```

    We will also install a target, which isn't required but will let us save the
    output nicely
    ```bash
    virtualenv -p python 3 ~/virtualenvs/target-csv
    source ~/virtualenvs/target-csv/bin/activate
    python setup.py install
    ```
    The reason for this is that taps and targets both need their own
    environments to work properly. More on development is [in the singer
    docs](https://github.com/singer-io/getting-started/blob/master/docs/RUNNING_AND_DEVELOPING.md)

2. Create your tap's `tap_config.json` file which should look like the following:
Create a `config.json` file in
the following format, where `client_id`, `client_secret` and `refresh_token` are the credentials
you just created in the [Requirements](#requirements), and `start_date` is the date you want to start the sync from

```json
{
    "client_id": "OAUTH_CLIENT_ID",
    "client_secret": "OAUTH_CLIENT_SECRET",
    "refresh_token": "YOUR_OAUTH_REFRESH_TOKEN",
    "start_date": "2017-04-19T13:37:30Z",
    "user_agent": "tap-harvest-forecast (your.email@example.com)"
}
```

---

## Developing on Windows

Windows users will need to install WSL and develop within a linux environment as
a result of a formatting issue on windows, see [this
issue](https://github.com/singer-io/singer-python/issues/86)

Singer.io should work inside the bash environment as it would on linux

---

## Harvest Forecast Replication

- All available data from the Harvest Forecast API is replicated. Currently, this includes information returned from the assignments, clients, milestones, people, and projects endpoints.
- Calls to the Harvest Forecast API is limited to 100 every 15 seconds, with 5 max tries if a request isn't completed successfully. The tap should remain well below this max during normal use.

---

## Harvest Forecast Table Schemas

Each header denotes the table name.

### assigments
- Description: Assigments of projects to users.
- Primary key column(s): id
- Replicated fully or incrementally _(uses a bookmark to maintain state)_: Fully
- Bookmark column: `updated_at`
- Link to API endpoint documentation: https://help.getharvest.com/forecast/faqs/faq-list/api/

### clients
- Description: All clients.
- Primary key column(s): id
- Replicated fully or incrementally _(uses a bookmark to maintain state)_: Incrementally
- Bookmark column: `updated_at`
- Link to API endpoint documentation: https://help.getharvest.com/forecast/faqs/faq-list/api/

### milestones
- Description: All milestones and their project ids.
- Primary key column(s): id
- Replicated fully or incrementally _(uses a bookmark to maintain state)_: Incrementally
- Bookmark column: `updated_at`
- Link to API endpoint documentation: https://help.getharvest.com/forecast/faqs/faq-list/api/

### people
- Description: All people and the details pertaining to them.
- Primary key column(s): id
- Replicated fully or incrementally _(uses a bookmark to maintain state)_: Incrementally
- Bookmark column: `updated_at`
- Link to API endpoint documentation: https://help.getharvest.com/forecast/faqs/faq-list/api/

### projects
- Description: All projects and the details pertaining to them.
- Primary key column(s): id
- Replicated fully or incrementally _(uses a bookmark to maintain state)_: Incrementally
- Bookmark column: `updated_at`
- Link to API endpoint documentation: https://help.getharvest.com/forecast/faqs/faq-list/api/
