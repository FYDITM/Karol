# coding: utf-8
import datetime
from datetime import datetime as dt


class Notification:
    default_message = "Mamo już!"

    def __init__(self, nick, time, message=None, target=None):
        self.nick = nick
        self.time = time
        self.target = target
        if message:
            self.message = message
        else:
            self.message = self.default_message

    def get_full_message(self):
        result = "%s: %s %s" % (self.nick, self.time.strftime('%H:%M:%S'), self.message)
        return result


class Notifier:

    def __init__(self):
        self.notifications = []

    def set_timer(self, timestring, nick, message=None, target=None):
        t = timestring.split(':') #[h,m,s]
        if len(t) != 3:
            raise TimeFormatException(timestring)
        if 0 > int(t[0]) > 24 or 0 > int(t[1]) > 59 or 0 > int(t[2]) > 59:
            raise TimeFormatException(timestring)

        time = dt.now() + datetime.timedelta(hours=int(t[0]), minutes=int(t[1]), seconds=int(t[2]))
        n = Notification(nick, time, message, target)
        self.notifications.append(n)

    def set_alarm(self, timestring, nick, message=None, target=None):
        t = timestring.split(':')  # [h,m,s]
        if len(t) != 3:
            raise TimeFormatException(timestring)
        if 0 > int(t[0]) > 24 or 0 > int(t[1]) > 59 or 0 > int(t[2]) > 59:
            raise TimeFormatException(timestring)
        time = dt.now().replace(hour=int(t[0]), minute=int(t[1]), second=int(t[2]))
        n = Notification(nick, time, message, target)
        self.notifications.append(n)

    def check_notifications(self):
        now = dt.now()
        for notification in self.notifications:
            if notification.time <= now:
                self.notifications.remove(notification)
                return notification


class TimeFormatException(Exception):

    def __init__(self, timestring):
        self.message = "Zły format czasu: %s. Podaj czas w formacie HH:MM:SS" % timestring
