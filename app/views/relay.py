from datetime import datetime, timedelta
import logging
import operator
import os

import flask
import flask.views
import requests

from .. import app, common, db


def get_short_id(xbee_id, cursor):
    cursor.execute('select short_id from xbees where id=%s', (xbee_id,))
    row = cursor.fetchone()
    if row: return row['short_id']

def with_temperatures(rows):
    for row in rows:
        common.add_temperature(row)
    return rows


def route(path, name):
    """decorator to add a route to a View class"""
    def f(cls):
        app.add_url_rule(path, view_func=cls.as_view(name))
        return cls
    return f

# convert old hub firmware's POSTs to /hubs to PUTs to /hubs/<id>:
@app.route('/hubs', methods=('POST',))
def old_hubs_post():
    return Hub.put(flask.request.form['hub'])

@app.route('/hubs/')
def hubs():
    cursor = db.cursor()
    # select most recent row for each hub, and join on short id:
    cursor.execute('select distinct on (hub_id)'
                   ' hub_id, short_id, sleep_period, disk_free, uptime, version, port, time'
                   ' from hubs left join xbees on xbees.id=hub_id'
                   ' order by hub_id, time desc')
    hubs = sorted(cursor.fetchall(), key=operator.itemgetter('time'), reverse=True)
    return flask.render_template('relay/hubs.html', hubs=hubs)

@route('/hubs/<id>', 'hub')
class Hub(flask.views.MethodView):
    @staticmethod
    def get(id):
        cursor = db.cursor()

        if len(id) != 16:
            return flask.redirect(flask.url_for('hub', id=common.get_xbee_id(id, cursor)))

        cursor.execute('select pi_id, sleep_period, disk_free, uptime, version, port, time from hubs'
                       ' where hub_id=%s order by time desc limit 10', (id,))
        logs = cursor.fetchall()
        cursor.execute('select distinct on (cell_id) cell_id, short_id, version, time'
                       ' from temperatures left join xbees on xbees.id=cell_id left join cells on cells.id=cell_id'
                       ' where hub_id=%s order by cell_id, time desc', (id,))
        cells = sorted(cursor.fetchall(), key=operator.itemgetter('time'), reverse=True)
        cursor.execute('select cell_id, adc, temperature, sleep_period, relay, hub_time, time, relayed_time, version'
                       ' from temperatures left join cells on cells.id=cell_id'
                       ' where hub_id=%s order by hub_time desc limit 100', (id,))
        temperatures = with_temperatures(cursor.fetchall())
        return flask.render_template('relay/hub.html', short_id=get_short_id(id, cursor),
                                     hubs=logs, cells=cells, temperatures=temperatures)

    @staticmethod
    def put(id):
        hub = flask.request.form.copy()
        hub['id'] = id
        for k in ('free', 'up', 'v', 'port'):  # optional parameters
            if not hub.get(k): hub[k] = None  # missing or empty => null
        db.cursor().execute('insert into hubs'
                            ' (hub_id, pi_id, sleep_period, disk_free, uptime, version, port)'
                            ' values (%(id)s, %(pi)s, %(sp)s, %(free)s, %(up)s, %(v)s, %(port)s)',
                            hub)
        return 'ok'

    @staticmethod
    def patch(id):
        if flask.request.form.get('hourly'):
            sleep_period = common.LIVE_SLEEP_PERIOD
        else:
            sleep_period = 1

        db.cursor().execute('insert into commands (hub_id, action, params)'
                            ' values (%s, %s, %s)', (id, "change_sleep_period", sleep_period))
        return 'ok'


# PATCHing doesn't play well with Chrome Data Compression Proxy, so we fake it with POST:
@app.route('/hubs/<id>/patch', methods=('POST',))
def hub_patch(id):
    return Hub.patch(id)

@app.route('/hubs/<id>/commands')
def hub_commands(id):
    cursor = db.cursor()

    if len(id) != 16:
        return flask.redirect(flask.url_for('hub_config', id=common.get_xbee_id(id, cursor)))

    one_minute_ago = datetime.now() - timedelta(minutes=1)
    cursor.execute('select action, params from commands where hub_id=%s'
                   ' and created_at > %s order by created_at desc', (id, one_minute_ago))
    commands = cursor.fetchall()

    return flask.jsonify(commands)


@app.route('/cells/')
def cells():
    cursor = db.cursor()
    # select most recent row for each cell, and join on short id and version:
    cursor.execute('select distinct on (cell_id)'
                   ' cell_id, short_id, version, temperature, time'
                   ' from temperatures left join xbees on xbees.id=cell_id left join cells on cells.id=cell_id'
                   ' order by cell_id, time desc')
    cells = sorted(cursor.fetchall(), key=operator.itemgetter('time'), reverse=True)
    return flask.render_template('relay/cells.html', cells=cells)

@app.route('/cells/<id>')
def cell(id):
    cursor = db.cursor()

    if len(id) != 16:
        return flask.redirect(flask.url_for('cell', id=common.get_xbee_id(id, cursor)))

    cursor.execute('select version from cells where id=%s', (id,))
    cell = cursor.fetchone()
    cursor.execute('select distinct on (hub_id) hub_id, short_id, time'
                   ' from temperatures left join xbees on xbees.id=hub_id'
                   ' where cell_id=%s order by hub_id, time desc', (id,))
    hubs = sorted(cursor.fetchall(), key=operator.itemgetter('time'), reverse=True)
    cursor.execute('select hub_id, adc, temperature, sleep_period, relay, hub_time, time, relayed_time, version'
                   ' from temperatures left join cells on cells.id=cell_id'
                   ' where cell_id=%s order by hub_time desc limit 100', (id,))
    temperatures = with_temperatures(cursor.fetchall())
    return flask.render_template('relay/cell.html', short_id=get_short_id(id, cursor),
                                 cell=cell, hubs=hubs, temperatures=temperatures)

# old hub firmware doesn't use a trailing slash:
@app.route('/temperatures', methods=('POST',))
def old_temperatures_post():
    return Temperatures.post()

@route('/temperatures/', 'temperatures')
class Temperatures(flask.views.MethodView):
    @staticmethod
    def get():
        cursor = db.cursor()
        cursor.execute('select hub_id, cell_id, adc, temperature, sleep_period, relay, hub_time, time, relayed_time, version'
                       ' from temperatures left join cells on cells.id=cell_id'
                       ' order by hub_time desc limit 100')
        temperatures = with_temperatures(cursor.fetchall())
        return flask.render_template('relay/temperatures.html', temperatures=temperatures)

    @staticmethod
    def post():
        d = flask.request.form.copy()
        d['time'] = datetime.fromtimestamp(int(d['time']))
        d['relay'] = int(d['sp']) == common.LIVE_SLEEP_PERIOD

        for k in ('adc', 'temp'):  # optional parameters
            if not d.get(k): d[k] = None  # missing or empty => null
        if bool(d['adc']) == bool(d['temp']):
            return 'must pass exactly one of adc or temp', 400

        db.cursor().execute('insert into temperatures (hub_id, cell_id, adc, temperature, sleep_period, relay, hub_time)'
                            ' values (%(hub)s, %(cell)s, %(adc)s, %(temp)s, %(sp)s, %(relay)s, %(time)s)', d)
        return 'ok'
