#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json

from flask_redis import FlaskRedis
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from server.bot import Bot
from server.utils import filter_input

FORMAT = '%(asctime)-15s : %(levelname)s : %(message)s'
SECRET = os.environ.get('SECRET_KEY', 'there_is_no_secret')
LOGLEVEL = os.environ.get('LOG_LEVEL')
PORT = int(os.environ.get('PORT', 5000))
REDIS_URL = os.environ.get('REDIS_URL')
DEFAULT_ROOM_NAME = 'default'

levels = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'error': logging.ERROR}

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = SECRET
app.config['REDIS_URL'] = REDIS_URL

socketio = SocketIO(app)
redis_store = FlaskRedis(app)

logging.basicConfig(format=FORMAT)
logger = logging.getLogger('server')
logger.setLevel(levels.get(LOGLEVEL, logging.DEBUG))

if os.environ.get('HEROKU') is None and os.environ.get('FILE_LOG') is not None:
    FILELOG = os.environ.get('FILE_LOG')
    hdlr = logging.FileHandler(FILELOG)
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)


@socketio.on('names')
def get_names(data):
    requested_name = filter_input(data['name'])
    saved_redis = redis_store.get('names')

    # TODO: fix code duplication
    if not saved_redis:
        emit('accept_name', {'req_name': 'ok'})
        redis_store.set('names', requested_name)
        return

    names = saved_redis.decode()
    logger.debug('active names: %s / %s' % (str(names),
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
    username = filter_input(data['username'])
    command = filter_input(data['command'])
    room = filter_input(data['room'])

    logger.debug('got command for bot: %s' % str(command))
    result = Bot.process(data=command, logger=logger)

    response = 'Yeah, I got your command, %s.' % username
    if result is None:
        response += "</br>.. but I did not understand it, nothing to show </br>"
    else:
        response += '</br>See result:</br>%s' % result
    emit('bot_response', {'response': response}, room=room)


@socketio.on('history')
def get_history(data):
    query = filter_input(data['query'])
    room = filter_input(data['room'])

    history = redis_store.get('history:%s' % room)
    logger.debug('get history: %s' % str(history))

    if history:
        result = []
        json_history = json.loads(history.decode())
        logger.debug('parsed history: %s' % str(json_history))

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
    username = filter_input(data['username'])
    room = filter_input(data['room'])
    message = filter_input(data['message'])

    logger.debug('get message: %s' % str(data))
    emit('response', {'username': username, 'message': message, 'room': room}, room=room)

    item = {'username': username, 'message': message}
    history = redis_store.get('history:%s' % room)
    if not history:
        logger.debug('new, push to history: %s' % str([item]))
        redis_store.set('history:%s' % room, json.dumps([item]))
    else:
        json_history = json.loads(history.decode())
        json_history.append(item)
        redis_store.set('history:%s' % room, json.dumps(json_history))


@socketio.on('message_private')
def handle_message(data):
    username = filter_input(data['username'])
    to = filter_input(data['to'])
    message = filter_input(data['message'])

    username_sid_map = redis_store.hgetall('username_sid_map')
    to_sid = username_sid_map[to.encode()]
    logger.debug('get private message: %s / to: %s' % (str(data), to_sid))
    if to_sid:
        to_sid = to_sid.decode()
        emit('response_private', {'username': username, 'message': message}, room=to_sid)
        emit('response_private', {'username': username, 'message': message})
    else:
        emit('response_private', {'error': 'the user has not found'})

    # TODO: save history for specific user. But why? Need to change @history behavior


@socketio.on('rooms')
def get_rooms(data=None):
    rooms = redis_store.hgetall('rooms')
    rooms = [room.decode() for room in rooms.keys() if room.decode() != DEFAULT_ROOM_NAME]
    emit('info', {'rooms': rooms, 'silent_update': data and 'only_update' in data})
    logger.debug('ask rooms, send: %s' % str(rooms))


@socketio.on('connect')
def on_connect():
    logger.info('on connect')


@socketio.on('disconnect')
def on_disconnect():
    username_sid_map = redis_store.hgetall('username_sid_map')
    names = redis_store.get('names')

    if names:
        for name, sid in username_sid_map.items():
            if sid.decode() == request.sid:
                req_name = name.decode()
                logger.debug('try to erase %s / %s' % (req_name, names))
                arr_names = names.decode().split(':')
                updated_arr = [name for name in arr_names if name != req_name]
                logger.debug('updated %s' % str(updated_arr))
                redis_store.set('names', ':'.join(updated_arr))

    logger.info('on disconnect')
    emit('info', {'info': 'A user has been disconnected'})


@socketio.on('join')
def on_join(data):
    # TODO: too many trust to user input
    username = filter_input(data['username'])
    room_from = filter_input(data['room_from'])
    room = filter_input(data['room_new'])

    # update sid
    username_sid_map = redis_store.hgetall('username_sid_map')
    username_sid_map[username] = request.sid
    logger.debug('updated session map: %s' % str(username_sid_map))
    redis_store.hmset('username_sid_map', username_sid_map)

    if room_from != DEFAULT_ROOM_NAME:
        logger.debug('leave non-default room %s' % room_from)
        leave_room(room_from)
        emit('info', {'info': username + ' has left the room %s.' % room_from}, room=room_from)

    logger.debug('join request: %s' % str(data))
    room_byte = room.encode()
    # TODO: check room name. Remove ':' and etc
    join_room(room)

    rooms = redis_store.hgetall('rooms')
    logger.debug('available rooms: %s' % str(rooms))
    logger.debug('request: %s / %s' % (username, room))

    if room_byte in rooms:
        members = rooms[room_byte].decode()
        logger.debug('members: %s' % (str(members)))
        if username not in members:
            members = members + ':' + username
    else:
        members = username

    rooms[room_byte] = members
    redis_store.hmset('rooms', rooms)

    emit('info', {'info': username + ' has entered the room %s.' % room}, room=room)


@socketio.on('leave')
def on_leave(data):
    # TODO: too many trust to user input
    username = filter_input(data['username'])
    room = filter_input(data['room'])
    byte_room = room.encode()

    logger.debug('leave request: %s' % str(data))
    rooms = redis_store.hgetall('rooms')

    logger.debug('members in %s: %s' % (str(room), str(byte_room)))
    members = rooms[byte_room].decode()

    if members:
        filtered = [member for member in members.split(':') if member != username]
        if len(filtered) > 1:
            rooms[byte_room] = ':'.join(filtered)
            redis_store.hmset('rooms', rooms)
        else:
            redis_store.hdel('rooms', room)

    # else-case won't be possible with a default client
    if room != DEFAULT_ROOM_NAME:
        logger.debug('leave non-default room %s' % room)
        emit('leave_room')
        emit('info', {'info': username + ' has left the room %s.' % room}, room=room)
        leave_room(room)


@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    logger.info('run on %s' % PORT)
    socketio.run(app, port=PORT)
