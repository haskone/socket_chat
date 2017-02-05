Simple chat based on socket.io

- just 'setname', a real registration will be added later
- using Redis for keeping active rooms, names, history

- control. Respond only to the user???
    - '@help' - print all possible commands with a short description
    - '@setname <name>' - define a name for the current user
    - '@rooms' - get list of active rooms    
    - '@join <channel-name>' - join to a room
    - '@leave' - leave a current channel
    - '@history <text>' - find message which contains specified text

- bots (use @bot <command>). Post to the channel    
    - '@bot news' - post random news from news.ycombinator.com
    - '@bot sum of 1 2.5 3' - print sum of numbers
    - '@bot mean of 1 2.5 3' - print mean of numbers

- print 'incorrect command' to a user in case of any command error

- logging to file
