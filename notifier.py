# coding: utf-8
import datetime
from datetime import datetime as dt
import tasks

default_message = "Mamo już!"


class Notification:
    def __init__(self, nick, time, message, targeted):
        self.nick = nick
        self.time = time
        self.target = None
        self.message = message
        if targeted:
            self.target = nick

    def get_full_message(self):
        result = "%s: %s %s" % (self.nick, self.time.strftime('%H:%M:%S'), self.message)
        return result


class Notifier:

    def __init__(self):
        self.notifications = []

    def set_timer(self, timestring, nick, host, message=None, targeted=0):
        t = timestring.split(':')  # [h,m,s]
        if not self.timestring_OK(t, True):
            raise TimeFormatException(timestring)
        elif len(t) == 3:
            time = dt.now() + datetime.timedelta(hours=int(t[0]), minutes=int(t[1]), seconds=int(t[2]))
        # n = Notification(nick, time, message, target)
        if message is None:
            message = default_message
        return tasks.add_task(nick, host, tasks.TaskType.alarm.value, time.isoformat(' '), message, targeted)

    def set_alarm(self, timestring, nick, host, message=None, targeted=0):
        t = timestring.split(':')  # [h,m,s]'
        now = dt.now()
        if not self.timestring_OK(t, False):
            raise TimeFormatException(timestring)
        elif len(t) == 3:
            time = now.replace(hour=int(t[0]), minute=int(t[1]), second=int(t[2]))
            if time > now:
                time.replace(day=now.day() + 1)
        # n = Notification(nick, time, message, target)
        if message is None:
            message = default_message
        return tasks.add_task(nick, host, tasks.TaskType.alarm.value, time.isoformat(' '), message, targeted)

    def timestring_OK(self, t, timer):
        if len(t) == 3:
            return not (0 > int(t[0]) > 24 or 0 > int(t[1]) > 59 or 0 > int(t[2]) > 59)
        else:
            return False

    def check_notifications(self):
        now = dt.now()
        for notification in self.notifications:
            if notification.time <= now:
                self.notifications.remove(notification)
                return notification


class TimeFormatException(Exception):

    def __init__(self, timestring):
        self.message = "Zły format czasu: %s. Podaj czas w formacie HH:MM:SS" % timestring
