# Development, on a Mac

## Initial Setup

1. Copy `.env-sample.sh` to `.env.sh` and update the variables to reflect postgres user and database name.
1. Install python libraries `pip3 install -r requirements.txt`
1. Run `bash dev/init.sh`

## Running

`bash dev/run.sh` to run the web app
...
`bash dev/run_batch.sh` to run the batch data relay worker

## Connecting to the Database
Examples:
- `bash dev/db.sh`
- `bash dev/db.sh < commands.sql`
- `bash dev/db.sh pg_dump > dump.sql`

# Production, on Heroku

The `Procfile` defines the processes that will run on Heroku.

## Pushing code (via git)

`git push <heroku-remote> master`

See https://devcenter.heroku.com/articles/git

## Connecting to the Database

Once you have access to the heroku app,

`heroku pg:psql -a hs-relay-prod`

## Updating database Schema

For now, schema updates must be done manually.  Depending on the schema changes,
you might want to set the heroku app into maintenance mode and turn off the batch worker
while migrating.

## Status and Logs

`heroku logs -a hs-relay-prod`

## Connecting to a Hub

Hub SSH functionality is now handled by the [tunnel server](https://github.com/heatseeknyc/tunnel)
