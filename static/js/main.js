function previewLink(link) {
    wrappedLink = '<a id="demo" href=' + link + '>' + link + '</a>';
    return wrappedLink;
}

function checkLink(message) {
    //some dummy check
    return (message.search('http://') >= 0 || message.search('https://') >= 0);
}

function urlify(text, id) {
    var urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, function(url) {
        return '<a id="' + id + '" href="' + url + '">' + url + '</a>';
    })
}

function printMessageFromUser(user, message, type, room) {
    var linkContainer = '';
    var id = sessionStorage['id'] + 1 || 1;
    sessionStorage['id'] = id;
    if (checkLink(message)) {
        message = urlify(message, id);
        linkContainer = '<div class="urlive-container' + id + '"></div>';
    }

    if (type == 'own') {
        classUserMsg = 'bg-primary';
    } else if (type == 'common') {
        classUserMsg = 'text-muted';
    } else if (type == 'private') {
        classUserMsg = 'bg-success';
    }
    var container = "<div class='row message-bubble'>" +
                    "<p class='" + classUserMsg + "'>" + user + ' (' + room + ')' + "</p>" +
                    "<p>" + message + "</p>" + linkContainer + "</div>";

    $('#messages-container').append(container);
    $('html, body').animate({scrollTop:$(document).height()}, 'slow');

    $('#' + id).urlive({ container: '.urlive-container' + id }).hover(function(){
        $(this).urlive('open');
    });
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
                      '"@private user text" - send to a specific user<br>' +
                      '"@history piece_of_text_you_looking_for" - find message which contains specified text<br>' +
                      '"@bot news" - post random news from news.ycombinator.com<br>' +
                      '"@bot sum of 1 2 3.2" - print sum of numbers<br>' +
                      '"@bot mean of 1.5 2 3" - print mean of numbers';
    var container = "<div class='row message-bubble'>" +
                    "<p class='text-muted'>" + helpMessage + "</p></div>";
    $('#messages-container').append(container);
    $('html, body').animate({scrollTop:$(document).height()}, 'slow');
}

$( document ).ready(function() {
    var autocompleteList = ['@help', '@setname', '@rooms', '@join', '@leave', '@private', '@bot'];
    $('#input-text').autocomplete({
        source: autocompleteList
    });

    var default_room = 'default';
    var origin = window.location.origin;
    var socket = io.connect(origin);
    // TODO: get name from login-procedure
    var username = sessionStorage['username'] || null;
    var try_name = '';
    var currentRoom = sessionStorage['room'] || default_room;

    function connect() {
        printMessageInfo('You has been successfully connected as ' + username + ' to ' + currentRoom + ' room');
        join(currentRoom);
    }

    function join(room) {
        socket.emit('join', {'username': username, 'room_new': room, 'room_from': currentRoom});
        currentRoom = room;
        sessionStorage['room'] = currentRoom;
    }

    function leave() {
        if (currentRoom == default_room) {
            printMessageInfo('You can\'t leave the default room.');
        } else {
            socket.emit('leave', {'username': username, 'room': currentRoom});
            currentRoom = default_room;
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

    function private(to, message) {
        socket.emit('message_private', {'username': username,
                                        'message': message,
                                        'to': to});
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

    socket.on('leave_room', function() {
        join(default_room);
    });

    // handle common info messages from the server
    socket.on('info', function(data) {
        if ('info' in data) {
            printMessageInfo(data['info']);
        } else if ('rooms' in data) {
            if ('silent_update' in data && data['silent_update']) {
                var rooms = data['rooms'];
                var forAutoComplete = rooms.map(function(room) {
                    return '@join ' + room;
                });
                var duplicates = autocompleteList.concat(forAutoComplete);
                var unique = duplicates.filter(function(elem, index, self) {
                    return index == self.indexOf(elem);
                });
                autocompleteList = unique;
                $('#input-text').autocomplete({
                    source: autocompleteList
                });
            } else {
                printMessageInfo('Available rooms: ' + data['rooms']);
            }
        }
    });

    socket.on('bot_response', function(data) {
        if ('response' in data) {
            printMessageFromUser('BOT', data['response'], 'common', currentRoom);
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
        var color = msg['username'] == username ? 'own' : 'common';
        printMessageFromUser(msg['username'], msg['message'], color, msg['room']);
    });

    socket.on('response_private', function(msg){
        if ('error' in msg) {
            printMessageInfo('The message has not been sent: ' + msg['error']);
        } else {
            printMessageFromUser(msg['username'], msg['message'], 'private', 'private');
        }
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
        if (username == null && !(msg == '@help' || (msg.startsWith('@setname') &&
                                                     msg.split(' ').length == 2))) {
            printMessageInfo('Please set your name first')
            return
        }

        if (msg.startsWith("@")) {
            var splitted = msg.split(' ');
            var command = splitted[0];
            var params = msg.substr(command.length + 1);
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
            // TODO: make it in a common way. Looks like a weird hack
            } else if (command == '@private' && splitted.length >= 2) {
                var privateMsg = msg.substr(command.length + splitted[1].length + 2);
                private(splitted[1], privateMsg);
            } else {
                printMessageInfo('Incorrect command. Use @help and try again');
            }
        } else {
            post(msg);
        }

        $('#input-text').val('');
    }

    $('#input-text').keydown(function () {
        var msg = $('#input-text').val();
        // there is no sense to update rooms
        // every keydown but possible to update
        // just before start joining to some of them
        if (msg == '@join') {
            socket.emit('rooms', {'only_update': true});
        }
    });

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