port=5000

source env.sh

[ -z "$RELAY_DB_USERNAME" ] && echo "Need to set RELAY_DB_USERNAME env var" && exit 1;
[ -z "$RELAY_DB_NAME" ] && echo "Need to set RELAY_DB_NAME env var" && exit 1;

if psql -U $RELAY_DB_USERNAME -lqt | cut -d \| -f 1 | grep -qw $RELAY_DB_NAME; then
  echo "error - database already exists"
  exit 1
fi

psql -U $RELAY_DB_USERNAME -c "CREATE DATABASE ${RELAY_DB_NAME};"
psql -U $RELAY_DB_USERNAME -d $RELAY_DB_NAME -a -f db/schema.sql
psql -U $RELAY_DB_USERNAME -d $RELAY_DB_NAME -a -f dev/db/sample-data.sql
