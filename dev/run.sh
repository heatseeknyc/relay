port=5000

source env.sh

[ -z "$RELAY_DB_USERNAME" ] && echo "Need to set RELAY_DB_USERNAME env var" && exit 1;

version=$(awk '/^.set version / {print $3}' db/schema.sql)
if [[ $(psql -U $RELAY_DB_USERNAME -d $RELAY_DB_NAME -tc 'select version from version' < /dev/null | awk '{print $1}') != $version ]]; then
  echo "Version is not correct"
  exit 1
fi

#    psql -U bolandrm -d relay_development -a -f db/schema.sql
#    psql -U bolandrm -d relay_development -a -f dev/db/sample-data.sql
#    psql -U $RELAY_DB_USERNAME -d $RELAY_DB_NAME -a -f db/schema.sql
#    . dev/run.sh

gunicorn -w 4 -b "0.0.0.0:$port" app:app --log-file=- --error-logfile=- --log-level=debug

# FLASK_APP=app.py FLASK_DEBUG=1 flask run
