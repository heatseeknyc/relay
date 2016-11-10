port=5000

relay_db_name=relay_development

[ -z "$RELAY_DB_USERNAME" ] && echo "Need to set RELAY_DB_USERNAME env var" && exit 1;

version=$(awk '/^.set version / {print $3}' db/schema.sql)
if [[ $(psql -U $RELAY_DB_USERNAME -d $relay_db_name -tc 'select version from version' < /dev/null | awk '{print $1}') != $version ]]; then
  echo "Version is not correct"
  exit 1
fi

#    psql -U $RELAY_DB_USERNAME -d $RELAY_DB_NAME -a -f db/schema.sql
#    . dev/run.sh

RELAY_DB_NAME=$relay_db_name gunicorn -w 4 -b "0.0.0.0:$port" app:app --log-file=-
