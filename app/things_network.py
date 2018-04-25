"""Read temperatures from things network"""

import os
import logging
import paho.mqtt.client as mqtt
import json
import re
import datetime
from . import common, db
# from pdb import set_trace as bp

logging.basicConfig(level=logging.INFO)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logging.info("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("+/devices/+/up")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        _db = db
        cursor = _db.cursor()
        hub_id = 'lorahub'

        logging.info(msg.topic + " " + str(msg.payload))

        cursor.execute('insert into things_network_updates (content)'
                       ' values (%s)', [msg.payload.decode("utf-8")])
        _db.commit()

        parsed = json.loads(msg.payload.decode("utf-8"))

        cell_id = parsed["dev_id"]
        logging.info(cell_id)

        temp = common.c_to_f(parsed["payload_fields"]["tempC"][0])
        temp = round(temp, 2)
        logging.info(temp)

        time = parsed["metadata"]["time"]
        time = re.sub('\.[0-9]+Z$', 'Z', time)
        time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
        logging.info(time)

        cursor.execute('SELECT COUNT(*) FROM temperatures WHERE hub_id = %s AND cell_id = %s AND hub_time > %s',
                [hub_id, cell_id, time - datetime.timedelta(hours=1)])
        results = cursor.fetchall()

        # If there are no readings for the cell in the last hour, record this one
        if results[0][0] == 0:
            data = {
                'hub': hub_id,
                'cell': cell_id,
                'temp': temp,
                'sp': common.LIVE_SLEEP_PERIOD,
                'relay': False,
                'time': time
            }
            cursor.execute('insert into temperatures (hub_id, cell_id, temperature, sleep_period, relay, hub_time)'
                           ' values (%(hub)s, %(cell)s, %(temp)s, %(sp)s, %(relay)s, %(time)s)', data)
            _db.commit()
        else:
            logging.info('not saving - entry found within last hour')

        # Notify deadmansnitch that the script is still running properly
        if os.environ.get('THINGS_NETWORK_SNITCH_ID'):
            requests.get("https://nosnch.in/{}".format(os.environ["THINGS_NETWORK_SNITCH_ID"]))

    except Exception:
        logging.exception("error: unable to record message: {}".format(msg.payload))

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.username_pw_set("heatseek-r1", os.environ.get('THINGS_NETWORK_API_KEY'))
    client.connect("us-west.thethings.network", 1883, 60)

    client.loop_forever()

if __name__ == '__main__':
    main()
