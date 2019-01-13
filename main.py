#!/usr/bin/env python

# pylint: disable=no-member

import datetime as dt
import functools
import io
import json
import logging
import multiprocessing.dummy
import time

import flask
import PIL.Image
import requests

nimages = 6
radar_interval_sec = 360 # 6 min x 60 sec/min

radars = {
    'Adelaide': '643',
    'Brisbane': '663',
    'Cairns': '193',
    'Canberra': '403',
    'Darwin': '633',
    'Emerald': '723',
    'Gympie': '083',
    'Hobart': '763',
    'Kalgoorlie': '483',
    'Melbourne': '023',
    'MountIsa': '753',
    'Namoi': '693',
    'Newcastle': '043',
    'Newdegate': '383',
    'NWTasmania': '523',
    'Perth': '703',
    'SouthDoodlakine': '583',
    'Sydney': '713',
    'Townsville': '733',
    'Warruwi': '773',
    'Watheroo': '793',
    'Weipa': '783',
    'Wollongong': '033',
    'Yarrawonga': '493',
}

app = flask.Flask(__name__)

valids = 'Valid locations are: %s' % ', '.join(radars.keys())

@functools.lru_cache(maxsize=len(radars))
def get_bg(location, start): # pylint: disable=unused-argument
    app.logger.info('Getting background for %s at %s', location, start)
    url = get_url('products/radar_transparencies/IDR%s.background.png' % radars[location])
    return get_image(url)


@functools.lru_cache(maxsize=len(radars)*6)
def get_fg(location, time_str):
    app.logger.info('Getting foreground for %s at %s', location, time_str)
    url = get_url('/radar/IDR%s.T.%s.png' % (radars[location], time_str))
    return get_image(url)


def get_image(url):
    app.logger.info('Getting image %s', url)
    response = requests.get(url)
    if response.status_code == 200:
        return PIL.Image.open(io.BytesIO(response.content)).convert('RGBA')
    return None


def get_frames(location, start):
    app.logger.info('Getting frames for %s at %s', location, start)
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
    app.logger.info('Getting loop for %s at %s', location, start)
    loop = io.BytesIO()
    frames = get_frames(location, start)
    if frames is None:
        return None
    app.logger.info('Got %s frames for %s at %s', len(frames), location, start)
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
    app.logger.debug('Getting time strings starting at %s', start)
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    app.logger.debug('Getting URL for path %s', path)
    return 'http://www.bom.gov.au/%s' % path


@app.route('/')
def main():
    location = flask.request.args.get('location')
    if location is None:
        flask.abort(400, "No 'location' parameter given. %s" % valids)
    if radars.get(location) is None:
        flask.abort(400, "Bad location '%s'. %s" % (location, valids))
    now = int(time.time())
    start = now - (now % radar_interval_sec)
    loop = get_loop(location, start)
    if loop is None:
        flask.abort(404, 'Current radar imagery unavailable for %s' % location)
    return flask.Response(loop, mimetype='image/jpeg')


if __name__ == '__main__':
    debug = False
    level = logging.DEBUG if debug else logging.INFO
    datefmt = "%Y-%m-%dT%H:%M:%SZ"
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(format="[%(asctime)s] %(levelname)s %(message)s", datefmt=datefmt, level=level)
    app.run()

lores_radars = {
    'Albany': '313',
    'AliceSprings': '253',
    'Bairnsdale': '683',
    'Bowen': '243',
    'Broome': '173',
    'Carnarvon': '053',
    'Ceduna': '333',
    'Dampier': '153',
    'Esperance': '323',
    'Geraldton': '063',
    'Giles': '443',
    'Gladstone': '233',
    'Gove': '093',
    'Grafton': '283',
    'HallsCreek': '393',
    'Katherine': '423',
    'Learmonth': '293',
    'Longreach': '563',
    'Mackay': '223',
    'Marburg': '503',
    'Mildura': '303',
    'Moree': '533',
    'MorningtonIs': '363',
    'MtGambier': '143',
    'NorfolkIs': '623',
    'PortHedland': '163',
    'SellicksHill': '463',
    'WaggaWagga': '553',
    'Warrego': '673',
    'WillisIs': '413',
    'Woomera': '273',
    'Wyndham': '073',
    }
    
