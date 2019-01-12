# flask

from functools import lru_cache
from multiprocessing.dummy import Pool
import datetime as dt
import io
import time

from flask import Flask, Response
from PIL import Image
import requests

nimages = 6
radar_interval_sec = 360 # 6 min x 60 sec/min

radar = {
    'Sydney': 'IDR713',
}

app = Flask(__name__)

@lru_cache()
def get_bg(location):
    url = get_url(f'products/radar_transparencies/{radar[location]}.background.png')
    return get_image(url)


@lru_cache()
def get_fg(location, time_str):
    url = get_url(f'/radar/{radar[location]}.T.{time_str}.png')
    return get_image(url)


def get_image(url):
    return Image.open(io.BytesIO(requests.get(url).content)).convert('RGBA')


@lru_cache()
def get_frames(location, start):
    bg = get_bg(location)
    fn = lambda time_str: Image.alpha_composite(bg, get_fg(location, time_str))
    return Pool(nimages).map(fn, get_time_strs(start))


@lru_cache()
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


@lru_cache()
def get_time_strs(start):
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    return f'http://www.bom.gov.au/{path}'


@app.route('/')
def main():
    location = 'Sydney'
    now = int(time.time())
    start = now - (now % radar_interval_sec)
    return Response(get_loop(location, start), mimetype='image/jpeg')
