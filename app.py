#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json

from flask_redis import FlaskRedis
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room

from server.bot import Bot

FORMAT = '%(asctime)-15s : %(levelname)s : %(message)s'
SECRET = os.environ.get('SECRET_KEY')
LOGLEVEL = os.environ.get('LOG_LEVEL')
PORT = os.environ.get('PORT')

levels = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'error': logging.ERROR}

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = SECRET

socketio = SocketIO(app)
redis_store = FlaskRedis(app)

logging.basicConfig(format=FORMAT)
logger = logging.getLogger('server')
logger.setLevel(levels.get(LOGLEVEL, logging.DEBUG))

if os.environ.get('HEROKU') is None:
    FILELOG = os.environ.get('FILE_LOG')
    hdlr = logging.FileHandler(FILELOG)
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)


# TODO: check user input and return some fail response

@socketio.on('names')
def get_names(data):
    requested_name = data['name']
    names = redis_store.get('names').decode()
    logger.info('active names: %s / %s' % (str(names),
                                           str(requested_name)))
    arr_names = []
    if names:
        arr_names.extend(names.split(':'))

    if requested_name in arr_names:
        status = 'no'
    else:
        status = 'ok'
        arr_names.append(requested_name)
    redis_store.set('names', ':'.join(arr_names))
    emit('accept_name', {'req_name': status})


@socketio.on('bot')
def bot_handler(data):
    """
    Handle the following scenarios:
        - sum of <list numbers int|double>
        - mean of <list numbers int|double>
        - news --- post random news (header + link) from news.ycombinator.com
    """
    username = data['username']
    command = data['command']
    room = data['room']

    logger.info('got command for bot: %s' % str(command))
    result = Bot.process(data=command, logger=logger)

    response = 'Yeah, I got your command, %s.' % username
    response += '</br>See result:</br>%s' % result
    emit('bot_response', {'response': response}, room=room)


@socketio.on('history')
def get_history(data):
    query = data['query']
    room = data['room']

    history = redis_store.get('history:%s' % room)
    logger.info('get history: %s' % str(history))

    if history:
        result = []
        json_history = json.loads(history.decode())
        logger.info('parsed history: %s' % str(json_history))

        for item in json_history:
            if query in item['message']:
                result.append({'username': item['username'],
                               'message': item['message']})

        if result:
            emit('history_response', {'result': result})
        else:
            emit('history_response', {'response': 'No matched results'})
    else:
        emit('history_response', {'response': 'There is no history record'})


@socketio.on('message')
def handle_message(data):
    logger.info('get message: %s' % str(data))
    # TODO: check data
    username = data['username']
    room = data['room']
    message = data['message']
    emit('response', {'username': username, 'message': message, 'room': room}, room=room)

    item = {'username': username, 'message': message}
    history = redis_store.get('history:%s' % room)
    if not history:
        logger.info('new, push to history: %s' % str([item]))
        redis_store.set('history:%s' % room, json.dumps([item]))
    else:
        json_history = json.loads(history.decode())
        json_history.append(item)
        logger.info('push to history: %s' % str(json_history))
        redis_store.set('history:%s' % room, json.dumps(json_history))


@socketio.on('rooms')
def get_rooms():
    rooms = redis_store.hgetall('rooms')
    rooms = [room.decode() for room in rooms.keys()]
    logger.info('ask rooms, send: %s' % str(rooms))
    emit('info', {'rooms': rooms})


@socketio.on('connect')
def on_connect():
    logger.info('on connect')


@socketio.on('disconnect')
def on_disconnect():
    # TODO: remove name from 'names'
    logger.info('on disconnect')
    emit('info', {'info': 'A user has been disconnected'})


@socketio.on('join')
def on_join(data):
    logger.info('join request: %s' % str(data))
    username = data['username']
    room = data['room']
    room_byte = room.encode()
    # TODO: check room name. Remove ':' and etc
    join_room(room)

    rooms = redis_store.hgetall("rooms")
    logger.info('available rooms: %s' % str(rooms))
    logger.info('request: %s / %s' % (str(username), str(room)))

    if room_byte in rooms:
        members = rooms[room_byte].decode()
        logger.info('members: %s' % (str(members)))
        if username not in members:
            members = members + ':' + username
    else:
        members = username

    rooms[room_byte] = members
    redis_store.hmset('rooms', rooms)
    emit('info', {'info': username + ' has entered the room %s.' % room}, room=room)


@socketio.on('leave')
def on_leave(data):
    logger.info('leave request: %s' % str(data))
    username = data['username']
    room = data['room'].encode()
    rooms = redis_store.hgetall("rooms")

    members = rooms[room].decode()
    logger.info('members in %s: %s' % (str(room), str(members)))

    if members:
        filtered = [member for member in members.split(':') if member != username]
        if len(filtered) > 1:
            rooms[room] = ':'.join(filtered)
            redis_store.hmset('rooms', rooms)
        else:
            redis_store.hdel('rooms', room)

    leave_room(room)
    emit('info', {'info': username + ' has left the room %s.' % room.decode()}, room=room)


@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    socketio.run(app, port=PORT)
