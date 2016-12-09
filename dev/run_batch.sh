port=5000

source env.sh

[ -z "$RELAY_DB_USERNAME" ] && echo "Need to set RELAY_DB_USERNAME env var" && exit 1;

version=$(awk '/^.set version / {print $3}' db/schema.sql)
if [[ $(psql -U $RELAY_DB_USERNAME -d $RELAY_DB_NAME -tc 'select version from version' < /dev/null | awk '{print $1}') != $version ]]; then
  echo "Version is not correct"
  exit 1
fi

python3 -m app.batch
