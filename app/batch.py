"""Continually transmit temperatures from database to heatseeknyc.com."""

import os
import logging
import time
import datetime
import re

import requests

from . import common

logging.basicConfig(level=logging.INFO)


def transmit_temperature(temperature):
    """Transmit a single temperature to heatseeknyc.com."""
    common.add_temperature(temperature)
    reading = dict(sensor_name=temperature['cell_id'],
                   temp=temperature['temperature'],
                   humidity=temperature['humidity'],
                   time=temperature['hub_time'].timestamp(),
                   verification='c0ffee')
    logging.info('POSTing {}...'.format(reading))
    response = requests.post("{}/readings.json".format(os.environ['RELAY_HEATSEEK_APP']),
                             json=dict(reading=reading))
    if response.status_code != requests.codes.ok:
        logging.error('request %s got %s response %s',
                      response.request.body, response.status_code, response.text)
    return response


def transmit():
    """Continually transmit temperatures from database to heatseeknyc.com."""
    database = common.get_db()
    while True:
        with database:
            fetch_after = datetime.datetime.now() - datetime.timedelta(days=365)
            cursor = database.cursor()
            cursor.execute('select temperatures.id, cell_id, adc, temperature, hub_time, version, humidity'
                           ' from temperatures left join cells on cells.id=cell_id'
                           ' where relay and relayed_time is null and time > %s', (fetch_after.strftime('%Y-%m-%d'),))
            temperatures = cursor.fetchall()
        if temperatures: logging.info('%s unrelayed temperatures', len(temperatures))

        unknown_cell_ids = set()
        for temperature in temperatures:
            cell_id = temperature['cell_id']
            if cell_id not in unknown_cell_ids:
                response = transmit_temperature(temperature)
                if response.status_code == requests.codes.ok:
                    with database:
                        database.cursor().execute('update temperatures set relayed_time = now()'
                                                  ' where id=%(id)s', temperature)
                elif response.status_code == requests.codes.not_found:
                    # give up on this cell's readings for this batch, since it will continue to 404
                    logging.info("404 for cell %s", cell_id)
                    unknown_cell_ids.add(cell_id)
                elif response.status_code == requests.codes.bad_request:
                    if "No user associated with that sensor" in response.text:
                        # give up on this cell's readings for this batch, since it will continue to 400
                        logging.info("no user assocated with cell %s", cell_id)
                        unknown_cell_ids.add(cell_id)
                time.sleep(1)

        time.sleep(1)

        # Notify deadmansnitch that the script is still running properly
        if os.environ.get('BATCH_WORKER_SNITCH_ID'):
            requests.get("https://nosnch.in/{}".format(os.environ["BATCH_WORKER_SNITCH_ID"]))

def main():
    while True:
        try:
            transmit()
        except Exception:
            logging.exception('error, retrying...')
            time.sleep(1)

if __name__ == '__main__':
    main()
