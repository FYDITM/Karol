import requests


karol_url = "http://163.172.155.213:5001"


def send_message(message):
    url = karol_url + "/message"
    response = requests.post(url, data={'message': message})
