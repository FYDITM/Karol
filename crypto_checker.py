import requests
import time

base_url = "https://api.cryptowat.ch"
bitbay_url = "https://bitbay.net/API/Public"


def get_price_usd(market, currency):
    url = "{0}/markets/{1}/{2}usd/price".format(base_url, market, currency)
    try:
        response = requests.get(url)
        result = response.json()
        if 'error' in result:
            return result['error']
        return result['result']['price']
    except Exception as ex:
        return "Cholibka, nie widzę wyraźnie. {0}".format(str(ex))


def get_price_pln(currency):
    url = "{0}/{1}pln/ticker.json".format(bitbay_url, currency)
    try:
        response = requests.get(url)
        result = response.json()
        if 'code' in result:
            return result['message']
        return result['last']
    except Exception as ex:
        return "Cholibka, nie widzę wyraźnie. {0}".format(str(ex))
        

def check_change(market, currency, from_time):
    timestamp = time.mktime(from_time.timetuple())
    url = "{0}/markets/{1}/{2}usd/trades".format(base_url, market, currency)
    response = requests.get(url, data={'since': timestamp})
    result = response.json()
    if 'error' in result:
        return result['error']
    first_price = result['result'][0][2]
    last_price = result['result'][-1][2]
    diff = first_price - last_price
    percent = diff / first_price * 100
    return percent


def change_24h(market, currency):
    url = "{0}/markets/{1}/{2}usd/summary".format(base_url, market, currency)
    response = requests.get(url)
    result = response.json()
    if 'error' in result:
        return result['error']
    return result['result']['price']['change']['percentage'] * 100
