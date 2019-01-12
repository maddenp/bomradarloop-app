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
    'Sydney': 'IDR713',
}

app = flask.Flask(__name__)


def error(msg):
    data = {
        'error_message': msg,
        'valid_values': list(radars.keys()),
    }
    return flask.Response(json.dumps(data), status=400, mimetype='application/json')

@functools.lru_cache()
def get_bg(location):
    url = get_url(f'products/radar_transparencies/{radars[location]}.background.png')
    return get_image(url)


@functools.lru_cache()
def get_fg(location, time_str):
    url = get_url(f'/radar/{radars[location]}.T.{time_str}.png')
    return get_image(url)


def get_image(url):
    return PIL.Image.open(io.BytesIO(requests.get(url).content)).convert('RGBA')


@functools.lru_cache()
def get_frames(location, start):
    bg = get_bg(location)
    fn = lambda time_str: PIL.Image.alpha_composite(bg, get_fg(location, time_str))
    return multiprocessing.dummy.Pool(nimages).map(fn, get_time_strs(start))


@functools.lru_cache()
def get_loop(location, start):
    loop = io.BytesIO()
    frames = get_frames(location, start)
    frames[0].save(
        loop,
        append_images=frames[1:],
        duration=500,
        format='GIF',
        save_all=True,
    )
    return loop.getvalue()


@functools.lru_cache()
def get_time_strs(start):
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    return f'http://www.bom.gov.au/{path}'


@app.route('/')
def main():
    location = flask.request.args.get('location')
    if location is None:
        return error('No value received for parameter: location')
    if radars.get(location) is None:
        return error('Bad location value %s' % location)
    now = int(time.time())
    start = now - (now % radar_interval_sec)
    return flask.Response(get_loop(location, start), mimetype='image/jpeg')
