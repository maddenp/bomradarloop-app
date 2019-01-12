import datetime as dt
import functools
import io
import json
import multiprocessing.dummy
import time

import flask
import PIL.Image
import requests

nimages = 6
radar_interval_sec = 360 # 6 min x 60 sec/min

radars = {
    'Adelaide': '643',
    'Albany': '313',
    'AliceSprings': '253',
    'Bairnsdale': '683',
    'Bowen': '243',
    'Brisbane': '663',
    'Broome': '173',
    'Cairns': '193',
    'Canberra': '403',
    'Carnarvon': '053',
    'Ceduna': '333',
    'Dampier': '153',
    'Darwin': '633',
    'Emerald': '723',
    'Esperance': '323',
    'Geraldton': '063',
    'Giles': '443',
    'Gladstone': '233',
    'Gove': '093',
    'Grafton': '283',
    'Gympie': '083',
    'HallsCreek': '393',
    'Hobart': '763',
    'Kalgoorlie': '483',
    'Katherine': '423',
    'Learmonth': '293',
    'Longreach': '563',
    'Mackay': '223',
    'Marburg': '503',
    'Melbourne': '023',
    'Mildura': '303',
    'Moree': '533',
    'MorningtonIs': '363',
    'MountIsa': '753',
    'MtGambier': '143',
    'Namoi': '693',
    'Newcastle': '043',
    'Newdegate': '383',
    'NorfolkIs': '623',
    'NWTasmania': '523',
    'Perth': '703',
    'PortHedland': '163',
    'SellicksHill': '463',
    'SouthDoodlakine': '583',
    'Sydney': '713',
    'Townsville': '733',
    'WaggaWagga': '553',
    'Warrego': '673',
    'Warruwi': '773',
    'Watheroo': '793',
    'Weipa': '783',
    'WillisIs': '413',
    'Wollongong': '033',
    'Woomera': '273',
    'Wyndham': '073',
    'Yarrawonga': '493',
}

app = flask.Flask(__name__)


def error(msg, values=True):
    data = {'error_message': msg}
    if values:
        data.update({'valid_values': list(radars.keys())})
    return flask.Response(json.dumps(data), status=400, mimetype='application/json')

@functools.lru_cache(maxsize=len(radars))
def get_bg(location, start): # pylint: disable=unused-argument
    print('### get_bg')
    url = get_url(f'products/radar_transparencies/IDR{radars[location]}.background.png')
    return get_image(url)


@functools.lru_cache(maxsize=len(radars)*6)
def get_fg(location, time_str):
    print('### get_fg')
    url = get_url(f'/radar/IDR{radars[location]}.T.{time_str}.png')
    return get_image(url)


def get_image(url):
    print('### get_image')
    response = requests.get(url)
    if response.status_code == 200:
        return PIL.Image.open(io.BytesIO(response.content)).convert('RGBA')
    return None


def get_frames(location, start):
    print('### get_frames')
    bg = get_bg(location, start)
    get = lambda time_str: get_fg(location, time_str)
    raw = multiprocessing.dummy.Pool(nimages).map(get, get_time_strs(start))
    fgs = [x for x in raw if x is not None]
    if not fgs:
        return None
    comp = lambda fg: PIL.Image.alpha_composite(bg, fg)
    return multiprocessing.dummy.Pool(len(fgs)).map(comp, fgs)


@functools.lru_cache(maxsize=len(radars))
def get_loop(location, start):
    print('### get_loop')
    loop = io.BytesIO()
    frames = get_frames(location, start)
    if frames is None:
        return None
    frames[0].save(
        loop,
        append_images=frames[1:],
        duration=500,
        format='GIF',
        loop=0,
        save_all=True,
    )
    return loop.getvalue()


@functools.lru_cache(maxsize=1)
def get_time_strs(start):
    print('### get_time_strs')
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    print('### get_url')
    return f'http://www.bom.gov.au/{path}'


@app.route('/')
def main():
    location = flask.request.args.get('location')
    if location is None:
        return error("No value received for parameter 'location'")
    if radars.get(location) is None:
        return error("Bad location value '%s'" % location)
    now = int(time.time())
    start = now - (now % radar_interval_sec)
    loop = get_loop(location, start)
    if loop is None:
        return error('Radar imagery currently unavailable for %s' % location, values=False)
    return flask.Response(loop, mimetype='image/jpeg')
