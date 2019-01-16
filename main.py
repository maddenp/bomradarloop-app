#!/usr/bin/env python

# pylint: disable=no-member

import datetime as dt
import functools
import io
import multiprocessing.dummy
import sys
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
def get_background(location, start): # pylint: disable=unused-argument
    log('Getting background for %s at %s' % (location, start))
    url = get_url('products/radar_transparencies/IDR%s.background.png' % radars[location])
    background = get_image(url)
    for layer in ('topography', 'locations', 'range'):
        log('Getting %s for %s at %s' % (layer, location, start))
        url = get_url('products/radar_transparencies/IDR%s.%s.png' % (radars[location], layer))
        image = get_image(url)
        background = PIL.Image.alpha_composite(background, image)
    return background


def get_frames(location, start):
    log('Getting frames for %s at %s' % (location, start))
    get = lambda time_str: get_wximg(location, time_str)
    raw = multiprocessing.dummy.Pool(nimages).map(get, get_time_strs(start))
    wximages = [x for x in raw if x is not None]
    if not wximages:
        return None
    p = multiprocessing.dummy.Pool(len(wximages))
    background = get_background(location, start)
    composites = p.map(lambda x: PIL.Image.alpha_composite(background, x), wximages)
    legend = get_legend(start)
    frames = p.map(lambda _: legend.copy(), composites)
    p.map(lambda x: x[0].paste(x[1], (0,0)), zip(frames, composites))
    return frames


def get_image(url):
    log('Getting image %s' % url)
    response = requests.get(url)
    if response.status_code == 200:
        return PIL.Image.open(io.BytesIO(response.content)).convert('RGBA')
    return None


@functools.lru_cache(maxsize=len(radars))
def get_legend(start): # pylint: disable=unused-argument
    log('Getting legend at %s' % start)
    url = get_url('products/radar_transparencies/IDR.legend.0.png')
    return get_image(url)


@functools.lru_cache(maxsize=len(radars))
def get_loop(location, start):
    log('Getting loop for %s at %s' % (location, start))
    loop = io.BytesIO()
    frames = get_frames(location, start)
    if frames is None:
        return None
    log('Got %s frames for %s at %s' % (len(frames), location, start))
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
    log('Getting time strings starting at %s' % start)
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    log('Getting URL for path %s' % path)
    return 'http://www.bom.gov.au/%s' % path


@functools.lru_cache(maxsize=len(radars)*6)
def get_wximg(location, time_str):
    log('Getting radar imagery for %s at %s' % (location, time_str))
    url = get_url('/radar/IDR%s.T.%s.png' % (radars[location], time_str))
    return get_image(url)


def log(msg):
    print(msg)
    sys.stdout.flush()


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
    app.run()
