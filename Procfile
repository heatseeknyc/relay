web: gunicorn -w 4 -b "0.0.0.0:$PORT" app:app --log-file=-
worker: python3 -m app.batch
worker: python3 -m app.things_network
