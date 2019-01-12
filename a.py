# flask

from functools import lru_cache
from multiprocessing.dummy import Pool
import datetime as dt
import io
import time

from PIL import Image
import imageio
import numpy as np
import requests

radar = {
    'Sydney': 'IDR713',
}

nimages = 6
radar_interval_sec = 360 # 6 min x 60 sec/min

@lru_cache()
def get_bg(location):
    url = get_url(f'products/radar_transparencies/{radar[location]}.background.png')
    return get_image(url)


@lru_cache()
def get_fg(location, time_str):
    url = get_url(f'/radar/{radar[location]}.T.{time_str}.png')
    return get_image(url)


@lru_cache()
def get_fgs(location, start):
    bg = get_bg(location)
    fn = lambda time_str: np.array(Image.alpha_composite(bg, get_fg(location, time_str)))
    return Pool(nimages).map(fn, get_time_strs(start))


def get_image(url):
    return Image.open(io.BytesIO(requests.get(url).content)).convert('RGBA')


@lru_cache()
def get_time_strs(start):
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    return f'http://www.bom.gov.au/{path}'


def write_gif(location):
    now = int(time.time())
    start = now - (now % radar_interval_sec)
    imageio.mimsave('loop.gif', get_fgs(location, start), fps=2)


write_gif('Sydney')
