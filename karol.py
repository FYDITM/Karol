# coding: utf-8
import codecs
import configparser
from datetime import datetime
from datetime import timedelta
import logging
import logging.handlers
import re
import socket
import time
import threading
import dateutil.parser
from random import choice
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
import crypto_checker as crypto
from tasks import *


import notifier

CLI = 1
LOG = 1

data_lock = threading.Lock()
bot = None
logger = None  # globalny logger żeby zawsze korzystać z jednego
app = None
api_port = 9001


def initialize():
    global CLI, LOG, bot
    init_logger()
    create_tables()
    bot = BotEngine()
    bot.connect()
    bot_thread = threading.Thread(target=main_loop)
    bot_thread.start()
    crypto_thread = threading.Thread(target=keep_checking_crypto)
    crypto_thread.start()
    app = Flask(__name__)
    return app


def keep_checking_crypto():
    check_crypto_change('btc')
    check_crypto_change('eth')
    check_crypto_change('xmr')
    time.sleep(3600 * 6)


def check_crypto_change(currency):
    log("Sprawdzam zmianę {0}...".format(currency))
    try:
        change = crypto.change_24h('bitfinex', currency)
        log("Zmiana {0}: {1}".format(currency, change))
        if abs(change) >= 10:
            bot.send_message("FYDITM: {0} zmieniło się o {1:.2f} % w ciągu ostatinch 24h!".format(currency, change))
    except Exception as ex:
        log(str(ex), logging.ERROR)


def main_loop():
    while True:
        try:
            bot.keep_alive()
        except Exception as ex:
            if ex.args[0] == 'timed out':
                continue  # bez logowania timeoutów
            log(str(ex), logging.ERROR)
            if "Istniejące połączenie zostało gwałtownie zamknięte przez zdalnego hosta" in ex.args[0]:
                # zamknięte połączenie logujemy i wychodzimy z programu
                return


def init_logger():
    global logger
    max_file_size = 52428800  # 50 MB
    log_filename = "logi_watykanu.log"
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=max_file_size, backupCount=5)
    logger.addHandler(handler)


def log(text, level=logging.INFO):
    global CLI, LOG, logger
    t = str(datetime.now())
    line = t + ": " + text
    if CLI:
        try:
            print(line)
        except:
            pass
    if LOG:
        logger.log(level, line)


class QuotePicker:
    def __init__(self, quotes_file):
        with codecs.open(quotes_file, 'r', 'utf-8') as file:
            self.quotes = file.readlines()

    def pick_quote(self):
        return choice(self.quotes).strip()


class BotEngine:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read_file(codecs.open('settings.ini', 'r', 'utf-8'))
        self.serv_options = self.config['server_options']
        self.password = self.serv_options['password']
        self.mail = self.serv_options['mail']
        self.crypto_trigger = "$"
        self.bot_options = self.config['bot_options']
        self.quote_picker = QuotePicker(self.bot_options['quotesFilename'])
        self.triggers = self.bot_options['triggers'].strip().split('\n')
        self.input_trigger = self.bot_options['input'].strip()
        self.cmd_trigger = self.bot_options['cmd'].strip()
        self.channel = self.serv_options['channel']
        self.alarm_trigger = self.bot_options['alarm']
        self.timer_trigger = self.bot_options['timer']
        self.nick = self.serv_options['nickName'].strip()
        self.help_trigger = self.bot_options['help']
        self.jak_trigger = self.bot_options[
            'jak'].strip().replace('_', ' ').split('\n')
        self.man = self.bot_options['man']
        self.greet_triggers = self.bot_options[
            'greet_triggers'].strip().split('\n')
        self.greet_answers = self.bot_options[
            'greet_answers'].strip().split('\n')
        self.bye_triggers = self.bot_options[
            'bye_triggers'].strip().split('\n')
        self.bye_answers = self.bot_options['bye_answers'].strip().split('\n')
        self.readbuffer = ""
        self.message_buffer = []
        self.on_channel = False
        self.notifier = notifier.Notifier()

        self.url_pattern = re.compile(
            pattern="https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}([-a-zA-Z0-9@:%_,\+.~#?&//=]*)?")
        self.nick_begin = ":"
        self.nick_end = "!"

    def priv(self, line):
        return "privmsg " + self.nick.lower() in line.lower()

    def connect(self):
        self.server = socket.socket()
        endpoint = (self.serv_options['host'], int(self.serv_options['port']))
        log("Próbuję połączyć się z " + endpoint[0])
        self.server.connect(endpoint)
        # NICK <username>
        line = "NICK %s\r\n" % self.serv_options['nickName']
        self.server.send(line.encode())
        id = (self.serv_options['nickName'], self.serv_options[
              'hostname'], self.serv_options['servername'], self.serv_options['realName'])
        line = "USER %s %s %s: %s\r\n" % id
        # USER < username > < hostname > < servername >: < realname >
        self.server.send(line.encode())
        # czekamy na rejestrację na serwerze
        pinged = False
        while not pinged:
            pinged = self.keep_alive()

        self.identify(self.password)
        line = "JOIN " + self.channel + "\r\n"
        log("Próbuję wejść na kanał " + self.channel)
        log(line)
        self.server.send(line.encode())
        time.sleep(3)
        try:
            self.keep_alive()
        except:
            pass
        # przez pierwsze X sekund ignorujemy wiadomości, aby nie trigerował się
        # z historii
        x = 1
        start_time = datetime.now()
        delay = timedelta(seconds=x)
        d = timedelta(seconds=0)
        while d < delay:
            self.keep_alive(True)
            d = datetime.now() - start_time
            print("Aktywacja za " + str(x - d.seconds))

        self.send_message("Szczęść Boże!")
        self.on_channel = True
        self.server.settimeout(1)
        self.readbuffer = ""
        # self.register_on_server(self.password, self.mail)

    def keep_alive(self, ignore=False):
        self.handle_tasks()
        self.readbuffer += self.server.recv(1024).decode()
        temp = self.readbuffer.split('\n')
        self.readbuffer = temp.pop()

        for line in temp:
            if line == "timed out":
                continue
            if "PING" not in line:
                log(line)
            if "VERSION" in line:
                return True
            if self.on_channel and not ignore:
                if self.any_triggers(line):
                    continue
            self.ping(line)

        if ignore:
            return False
        self.send_to_server()

    def any_triggers(self, line):
        text = line.lower()
        if self.check_quote_triggers(text) or self.check_for_input(line) or self.check_for_notifications(line) or self.check_for_url(line) \
                or self.manual(line) or self.check_jak_trigger(text) or self.check_greet_trigger(line) or self.check_bye_trigger(line) or self.check_crypto_trigger(line):
            return True
        return False

    def send_to_server(self):
        if self.message_buffer:
            for message in self.message_buffer:
                self.server.send(message.encode())
                log(message)
                self.message_buffer.remove(message)

    def ping(self, line):
        line = line.strip()
        line = line.split()
        if line[0] == "PING":
            response = "PONG %s\r\n" % line[1]
            self.server.send(response.encode())
            return True
        return False

    def handle_tasks(self):
        db = Session()
        now = datetime.now()
        now_str = str(now)[0:-8]
        log("pobieram zadania z " + now_str, logging.DEBUG)
        tasklist = db.query(Task).filter(Task.execution.like("{0}%".format(now_str)))
        log("pobrano " + str(tasklist.count()), logging.DEBUG)
        for t in tasklist:
            task_time = dateutil.parser.parse(t.execution)
            if task_time <= now:
                if t.type == TaskType.alarm.value:
                    n = notifier.Notification(t.nick, dateutil.parser.parse(t.execution), t.arguments, t.targeted)
                    self.send_message(n.get_full_message(), target=n.target, priority=True)
                db.delete(t)
        db.commit()
        db.close()

    def manual(self, line):
        target = None
        if self.help_trigger in line:
            if self.priv(line):
                end = line.find(self.nick_end)
                target = line[1:end]
            self.send_message(self.man, target)

    def check_for_url(self, line):
        if "Quit:" in line:  # niektóre klienty w Quit dają adres aplikacji
            return False
        url = self.url_pattern.search(line)
        if url:
            target = None
            if self.priv(line):
                end = line.find(self.nick_end)
                target = line[1:end]
            self.get_title(url.group(), target)
            return True
        return False

    def check_quote_triggers(self, text):
        target = None
        for t in self.triggers:
            if t in text:
                if self.priv(text):
                    end = text.find(self.nick_end)
                    target = text[1:end]
                self.send_message(self.quote_picker.pick_quote(), target)
                return True
        return False

    def check_for_input(self, line):
        if not self.priv(line):
            return False
        i = line.find(self.input_trigger)
        c = line.find(self.cmd_trigger)
        if i >= 0:
            text = line[i + len(self.input_trigger):]
            self.send_message(text)
            return True
        elif c >= 0:
            command = line[c + len(self.cmd_trigger):]
            log("Komenda: " + command)
            if "nick" in command.lower():
                self.nick = command[command.find("NICK") + 5:].strip()
                log("Nowy nick: " + self.nick)
            text = "%s \r\n" % command.strip()
            log(text)
            self.server.send(text.encode())
            return True
        return False

    def check_jak_trigger(self, text):
        target = None
        for t in self.jak_trigger:
            if t in text:
                if self.priv(text):
                    end = text.find(self.nick_end)
                    target = text[1:end]
                self.send_message("Tak jak Pan Jezus powiedział", target)
                return True
        return False

    def check_greet_trigger(self, line):
        target = None
        nick_end = line.find(self.nick_end)
        nick = line[1:nick_end]
        text = line.lower()
        for t in self.greet_triggers:
            if t in text:
                if self.priv(text):
                    end = text.find(self.nick_end)
                    target = text[1:end]
                answer = nick + ": " + choice(self.greet_answers)
                self.send_message(answer, target)
                return True
        return False

    def check_crypto_trigger(self, line):
        target = None
        nick_end = line.find(self.nick_end)
        nick = line[1:nick_end]
        text_start = line[1:].find(":")
        text = line[text_start + 2:].lower()
        result = ""
        currency = text[1:4]
        if text[0] == self.crypto_trigger:
            if self.priv(text):
                end = text.find(self.nick_end)
                target = text[1:end]
            result = nick + ": "
            if ":" in text:
                result += "{0:.2f} PLN".format(crypto.get_price_pln(currency))
            elif "%" in text:
                result += "{0:.2f} % w ciągu 24h".format(crypto.change_24h('bitfinex', currency))
            else:
                result += "{0:.2f} USD".format(crypto.get_price_usd('bitfinex', currency))
            self.send_message(result, target)
            return True
        return False

    def check_bye_trigger(self, line):
        target = None
        nick_end = line.find(self.nick_end)
        nick = line[1:nick_end]
        text = line.lower()
        for t in self.bye_triggers:
            if t in text:
                if self.priv(text):
                    end = text.find(self.nick_end)
                    target = text[1:end]
                answer = nick + ": " + choice(self.bye_answers)
                self.send_message(answer, target)
                return True
        return False

    def check_for_notifications(self, line):
        # :nick!imie@host PRIVMSG #kanał :wiadomość
        # :necro666!Jakub@irc-l29s8s.finemedia.pl PRIVMSG #vichan :notify: 13:15:00 tekst
        nick_end = line.find(self.nick_end)
        nick = line[1:nick_end]
        targeted = False
        target = None
        if self.priv(line):
            targeted = True
            target = nick
        a = line.find(self.alarm_trigger)
        t = line.find(self.timer_trigger)
        mask = "*!*" + self.get_host(line)
        if a > 0 or t > 0:
            time_start = None
            if a > 0:
                time_start = a + len(self.alarm_trigger) + 1
                log("alarm (od {0})".format(time_start))
            if t > 0:
                time_start = t + len(self.timer_trigger) + 1
                log("timer (od {0})".format(time_start))
            timestring = line[time_start:time_start + 8].strip()
            log("timestring=" + timestring, logging.DEBUG)
            message = line[time_end:].strip()
            if self.antywojak(nick, mask, message):
                return False
            log("message=" + message, logging.DEBUG)
            if len(message) == 0:
                message = None
            try:
                result = None
                if a > 0:
                    result = self.notifier.set_alarm(timestring, nick, mask, message, targeted)
                    if result == Result.OK:
                        self.send_message(nick + ": Ustawiono powiadomienie na " + timestring, target)
                elif t > 0:
                    result = self.notifier.set_timer(timestring, nick, mask, message, targeted)
                    if result == Result.OK:
                        self.send_message(nick + ": Ustawiono odliczanie " + timestring, target)
                if result == Result.Warn:
                    self.send_message(nick + ": Dość", target)
                elif result == Result.Ban:
                    self.kick(self.channel, nick, "Powiedziałem dość")
                    self.ban(self.channel, mask)
            except notifier.TimeFormatException as err:
                self.send_message(nick + ": " + err.message, target)
            return True
        return False

    def send_message(self, text, target=None, priority=False):
        if not target:
            target = self.channel
        line = "PRIVMSG %s %s \r\n" % (target, text)
        if priority:
            self.server.send(line.encode())
        else:
            self.message_buffer.append(line)
        log(line)

    def get_title(self, url, target=None):
        try:
            site = BeautifulSoup(requests.get(
                url).content.decode(), "html.parser")
            title = site.title.string.strip()
            self.send_message(" » " + title + " «", target)
        except requests.HTTPError as er:
            self.send_message(
                "Cholibka, nie mogę odczytać tytułu bez okularów. " + er.msg, target)
        except requests.ConnectionError:
            self.send_message("Nie wiem nic o takiej stronie", target)
        except Exception as ex:
            log(str(ex), logging.ERROR)

    def register_on_server(self, pword, mail):
        line = "PRIVMSG nickserv register {0} {1} \r\n".format(pword, mail)
        self.server.send(line.encode())

    def identify(self, pword):
        line = "IDENTIFY {0} \r\n".format(pword)
        log(line)
        self.server.send(line.encode())

    def recover(self, pword):
        line = "PRIVMSG NickServ recover {0} {1} \r\n".format(self.nick, pword)
        log(line)
        self.server.send(line.encode())

    def kick(self, channel, target, reason=""):
        line = "KICK {0} {1} {2} \r\n".format(channel, target, reason)
        log(line)
        self.server.send(line.encode())

    def ban(self, channel, target):
        line = "MODE {0} +b {1} \r\n".format(channel, target)
        log(line)
        self.server.send(line.encode())

    def antywojak(self, nick, mask, message):
        restricted = ["iwat", "adamczyk", "patryk", "icuck", "rogacz",
                      "cuck", "kciuck", "kuk", "kciuk", "fyditm", "poraż", "fryty"]  # wyrzucić do settingsów
        m = message.lower()
        for word in restricted:
            if word in m:
                log("Znaleziono zakazane słowo '{0}' w wiadomości '{1}'".format(word, m), logging.DEBUG)
                self.kick(self.channel, nick, "Autodenuncjacja")
                self.ban(self.channel, mask)
                return True
        return False

    def get_host(self, line):
        return line[line.find("@"):line.find(" PRIVMSG")]


app = initialize()


@app.route("/message", methods=["POST"])
def send_message():
    message = request.form["message"]
    print(message)
    if bot:
        bot.send_message(message, priority=True)
    return app.make_response("OK")


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5555)
    except Exception as ex:
        log(str(ex), logging.ERROR)
