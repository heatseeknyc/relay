import os

import flask
import psycopg2
import psycopg2.extras


LIVE_SLEEP_PERIOD = (59*60 + 50) * 100  # 59m50s in centiseconds


def get_db():
    if os.environ.get('DATABASE_URL'):
        return psycopg2.connect(os.environ.get('DATABASE_URL'),
                                cursor_factory=psycopg2.extras.DictCursor)
    else:
        return psycopg2.connect(host='localhost',
                                port=5432,
                                database=os.environ["RELAY_DB_NAME"],
                                user=os.environ["RELAY_DB_USERNAME"],
                                cursor_factory=psycopg2.extras.DictCursor)

def get_xbee_id(id, cursor):
    if len(id) == 16: return id  # already an xbee id
    cursor.execute('select id from xbees where short_id=%s', (id,))
    row = cursor.fetchone()
    if not row: flask.abort(404)
    return row['id']

def get_temperature(adc, cell_version):
    # on Xbee, 0x3FF (highest value on a 10-bit ADC) corresponds to 3.3V...ish:
    voltage = adc / 0x3FF * 3.3
    if cell_version == 'v0.5':
        # on LMT70, 1.098V is 0°C, and every 0.005V difference is -1°C difference:
        celsius = (1.098 - voltage) / 0.005
        # …but we measured 71.4°F (21.89°C) when the LMT70 measured 31.86°C, so:
        celsius += 21.89 - 31.86
    else:
        # on MCP9700A, 0.5V is 0°C, and every 0.01V difference is 1°C difference:
        celsius = (voltage - 0.5) / 0.01
    fahrenheit = celsius * (212 - 32) / 100 + 32
    return round(fahrenheit, 2)

def add_temperature(row):
    if not row['temperature']:
        row['temperature'] = get_temperature(row['adc'], row['version'])
