# Harvest Forecast

## Connecting Harvest Forecast

### Requirements

To set up this Harvest Forecast in Stitch, you need to create a personal access token in the developer tools section of Harvest's website.

### Setup

Visit the [developer tools](https://id.getharvest.com/developers) page on Harvest's website and create a new personal access token. Create a `config.json` file in the following format, where `account_id` and `access_token` are the credentials you just created, and `start_date` is the date you want to start the sync from:

```json
{
    "start_date": "2017-04-19T13:37:30Z",
    "account_id": "HARVEST_FORECAST_ACCOUNT_ID",
    "access_token": "HARVEST_FORECAST_PERSONAL_ACCESSS_TOKEN"
}
```

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
- Replicated fully or incrementally _(uses a bookmark to maintain state)_: Incrementally
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
