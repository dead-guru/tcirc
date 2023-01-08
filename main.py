import os
import pickle
import irc.client
import sys
import ssl
import time
import random
import re
import os

from telethon.sync import TelegramClient, events
from telethon.tl.functions.messages import (GetHistoryRequest)

##irc
server = os.environ.get('SERVER_URL', "irc.dead.guru")
port = os.environ.get('PORT', "6697")
channel = os.environ.get('CHANNEL_NAME', "#news")
botnick = os.environ.get('BOT_NICK', "news_bot")
delim = "________________"

##telegram
api_id = os.environ.get('API_ID', 10000001) ## Todo use env variables or configuration file
api_hash = os.environ.get('API_HASH', 'api_hash')

channels = {
    't.me/operativnoZSU': {'url': 't.me/operativnoZSU', 'last': 0, 'peer': None},
    't.me/OP_UA': {'url': 't.me/OP_UA', 'last': 0, 'peer': None},
    't.me/SBUkr': {'url': 't.me/SBUkr', 'last': 0, 'peer': None},
    't.me/mvs_ukraine': {'url': 't.me/mvs_ukraine', 'last': 0, 'peer': None},
    't.me/Ukraine_MFA': {'url': 't.me/Ukraine_MFA', 'last': 0, 'peer': None},
    't.me/spravdi': {'url': 't.me/spravdi', 'last': 0, 'peer': None},
    't.me/dsszzi_official': {'url': 't.me/dsszzi_official', 'last': 0, 'peer': None},
    't.me/air_alert_ua': {'url': 't.me/air_alert_ua', 'last': 0, 'peer': None},
    't.me/dsns_telegram': {'url': 't.me/dsns_telegram', 'last': 0, 'peer': None},
    't.me/DIUkraine': {'url': 't.me/DIUkraine', 'last': 0, 'peer': None}
}

client = TelegramClient('dev-session', api_id, api_hash)
client.start()

def resolve_peer(c):
    global channels #
    chan = channels[c]
    if chan['peer'] is not None:
        return pickle.loads(chan['peer'])
    peer = client.get_entity(chan['url'])
    channels[c]['peer'] = pickle.dumps(peer)
    return peer

## ----- SANITIZER -----
# TODO: convert it in a single class/function/decorator/whatever
def remove_emojis(data):
    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                        "]+", re.UNICODE)
    return re.sub(emoj, '', data)

def remove_urls(data):
    return re.sub(r'http\S+', '', data)

def remove_linebreaks(data):
    return data.replace("\n", " ")

def disarm_hashtags(data):
    '''TG Hashtags are being mistaken as an IRC channels'''
    # with r'(?:^|\W)#(\S+)' we loose the whitespace, that's odd
    return re.sub(r'(^|\W)#(\S+)', r'\g<1>tag:\g<2>', data)

def sanitize_tg_message(data):
    # sequentially apply all the sanitizer functions
    return reduce(remove_emojis, disarm_hashtags, remove_linebreaks, remove_urls, data)
## ----- END SANITIZER -----

#NO OP
def nop():
    pass

def spUtf8(string, byte_limit):
    symbol_size = lambda s : sys.getsizeof(str(s).encode("utf-8"))
    check_the_limit = lambda a, l : symbol_size(a) < l
    w = ' '

    limit = byte_limit - symbol_size('[xx]: ') #spare byte limit minus the preambple of each message
    calibrate = lambda a : check_the_limit(a, limit)

    # message fits in one IRC packet
    if calibrate(string):
        return [string]

    tmpStr = ""
    strings = []
    words = str.split(string)

    # split incomming text into an aray of IRC-fitted messages
    for word in words:
        if calibrate(tmpStr + w + word):
            tmpStr += (w + word)
        else:
            strings.append(f'[{len(strings)}]: {tmpStr}')
            tmpStr = word
    strings.append(f'[{len(strings)}]: {tmpStr}') if len(tmpStr) else nop()
    return strings

def handle(connection):
    connection.privmsg(channel, delim)
    for key in channels:
        chan = channels[key]
        time.sleep(random.randint(2, 10))
        posts = client(GetHistoryRequest(
                        peer=resolve_peer(key),
                        limit=1,
                        offset_date=None,
                        offset_id=0,
                        max_id=0,
                        min_id=0,
                        add_offset=0,
                        hash=0))
        if chan['last'] != posts.messages[0].id:
            chan['last'] = posts.messages[0].id

            # remove links, remove linebreaks, remove emojis
            message = sanitize_tg_message(posts.messages[0].message)
            if len(message) != 0:
                connection.privmsg(channel, chan['url'] + ":")
                for line in spUtf8(message, 470):
                    if line is not None:
                        connection.privmsg(channel, line)

                connection.privmsg(channel, delim)
    connection.quit("done")

def on_connect(connection, event):
    if irc.client.is_channel(channel):
        connection.join(channel)
        return

def on_join(connection, event):
    handle(connection)

def on_disconnect(connection, event):
    storeDB('db.bin')
    raise SystemExit()

def storeDB(filepath):
    f = open(filepath, 'wb')
    f.write(pickle.dumps(channels))

def prepareDB(filepath):
    global channels
    try:
        f = open(filepath,'rb')
        try:
            channels = pickle.loads(f.read())
        except pickle.UnpicklingError:
            os.unlink(filepath)
    except IOError:
        f = open(filepath, 'wb+')
        f.write(pickle.dumps(channels))
        print("DB Created")

def main():
    prepareDB('db.bin')
    ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
    reactor = irc.client.Reactor()
    try:
        c = reactor.server().connect(server, port, botnick, connect_factory=ssl_factory)
    except:
        print("ERROR")
        print(sys.exc_info()[1])
        raise SystemExit(1)
    c.add_global_handler("welcome", on_connect)
    c.add_global_handler("join", on_join)
    c.add_global_handler("disconnect", on_disconnect)
    reactor.process_forever()

if __name__ == "__main__":
    main()
