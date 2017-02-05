function printMessageFromUser(user, message, room) {
    var container = "<div class='row message-bubble'>" +
                    "<p class='text-muted'>" + user + ' (' + room + ')' + "</p>" +
                    "<p>" + message + "</p></div>";
    $('#messages-container').append(container);
    $('html, body').animate({scrollTop:$(document).height()}, 'slow');
}

function printMessageInfo(message) {
    var container = "<div class='row message-bubble'>" +
                    "<p class='text-muted'>" + message + "</p></div>";
    $('#messages-container').append(container);
    $('html, body').animate({scrollTop:$(document).height()}, 'slow');
}

function printHelp() {
    var helpMessage = 'Available commands:<br>' +
                      '"@help" - print all possible commands with a short description<br>' +
                      '"@setname name" - define a name for the current user<br>' +
                      '"@rooms" - get list of active rooms<br>' +
                      '"@join room-name" - join to a room<br>' +
                      '"@leave" - leave the current room<br>' +
                      '"@history text" - find message which contains specified text<br>' +
                      '"@bot news" - post random news from news.ycombinator.com<br>' +
                      '"@bot sum of 1 2 3.2" - print sum of numbers<br>' +
                      '"@bot mean of 1.5 2 3" - print mean of numbers';
    var container = "<div class='row message-bubble'>" +
                    "<p class='text-muted'>" + helpMessage + "</p></div>";
    $('#messages-container').append(container);
    $('html, body').animate({scrollTop:$(document).height()}, 'slow');
}

$( document ).ready(function() {

    var origin = window.location.origin;
    var socket = io.connect(origin);
    // TODO: get name from login-procedure
    var username = sessionStorage['username'] || null;
    var try_name = '';
    var currentRoom = sessionStorage['room'] || 'default';

    function connect() {
        printMessageInfo('You has been successfully connected as ' + username);
        join(currentRoom);
    }

    function join(room) {
        currentRoom = room;
        sessionStorage['room'] = currentRoom;
        socket.emit('join', {'username': username, 'room': room});
    }

    function leave() {
        if (currentRoom == 'default') {
            printMessageInfo('You can\'t leave the default room');
        } else {
            socket.emit('leave', {'username': username, 'room': currentRoom});
            join('default');
        }
    }

    function rooms() {
        socket.emit('rooms');
    }

    function post(message) {
        socket.emit('message', {'username': username,
                                'message': message,
                                'room': currentRoom});
    }

    function setname(name) {
        try_name = name;
        socket.emit('names', {'name': name});
    }

    function history(query) {
        socket.emit('history', {'query': query,
                                'room': currentRoom});
    }

    function bot(command) {
        socket.emit('bot', {'command': command,
                            'username': username,
                            'room': currentRoom});
    }

    socket.on('connect', function(data) {
        if (username != null) {
            connect();
        }
    });

    // handle common info messages from the server
    socket.on('info', function(data) {
        if ('info' in data) {
            printMessageInfo(data['info']);
        } else if ('rooms' in data) {
            printMessageInfo('Available rooms: ' + data['rooms']);
        }
    });

    socket.on('bot_response', function(data) {
        if ('response' in data) {
            printMessageFromUser('BOT', data['response'], currentRoom);
        }
    });

    socket.on('accept_name', function(data) {
        var status = data['req_name'];
        if (status == 'ok') {
            username = try_name;
            sessionStorage['username'] = username;
            printMessageInfo('Now you are known as ' + name);
            connect();
        } else if (status == 'no') {
            printMessageInfo('Already used. Try another name');
        } else {
            printMessageInfo('Something wrong');
        }
    });

    socket.on('history_response', function(data) {
        if ('response' in data) {
            printMessageInfo(data['response']);
        } else if ('result' in data) {
            var result = data['result'];
            for (i = 0; i < result.length; i++) {
                var item = result[i];
                printMessageInfo('from: ' + item['username'] + ', message: ' + item['message']);
            }
        }
    });

    socket.on('response', function(msg){
        printMessageFromUser(msg['username'], msg['message'], msg['room']);
    });

    var commandHandler = {'@help': printHelp,
                          '@rooms': rooms,
                          '@leave': leave};
    var commandHandlerParams = {'@join': join,
                                '@setname': setname,
                                '@history': history,
                                '@bot': bot};

    function inputHandling() {
        var msg = $('#input-text').val();

        console.log('handle ' + msg);
        if (username == null && !(msg == '@help' || (msg.startsWith('@setname') &&
                                                     msg.split(' ').length == 2))) {
            printMessageInfo('Please set your name first')
            return
        }

        if (msg.startsWith("@")) {
            var splitted = msg.split(' ');
            var command = splitted[0];
            var params = msg.substr(command.length + 1)
            console.log('command: ' + command);
            console.log('params: ' + params);
            if (command in commandHandler) {
                if (params) {
                    printMessageInfo('This command ignores any arguments');
                }
                commandHandler[command]();
            } else if (command in commandHandlerParams) {
                if (params) {
                    commandHandlerParams[command](params);
                } else {
                    printMessageInfo('This command requires some arguments. Use @help and try again');
                }
            } else{
                printMessageInfo('Incorrect command. Use @help and try again');
            }
        } else {
            post(msg);
        }

        $('#input-text').val('');
    }

    $('#input-text').keypress(function (e) {
        var key = e.which;
        if(key == 13) {
            inputHandling();
        }
    });
    $('#send').click(function(){
        inputHandling();
    });
});