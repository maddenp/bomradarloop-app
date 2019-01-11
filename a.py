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


def get_bg(location):
    url = get_url(f'products/radar_transparencies/{radar[location]}.background.png')
    return get_image(url)


def get_fg(location, timestr):
    url = get_url(f'/radar/{radar[location]}.T.{timestr}.png')
    return get_image(url)


def get_fgs(location):
    bg = get_bg(location)
    merge = lambda bg, fg: np.array(Image.alpha_composite(bg, fg))
    return [merge(bg, get_fg(location, timestr)) for timestr in get_time_strs()]


def get_image(url):
    return Image.open(io.BytesIO(requests.get(url).content)).convert('RGBA')


def get_time_strs():
    nimages = 6
    radar_interval_min = 6
    radar_interval_sec = radar_interval_min * 60
    ts_now = int(time.time())
    ts_fix = ts_now - (ts_now % radar_interval_sec)
    mkdt = lambda n: dt.datetime.fromtimestamp(ts_fix - (radar_interval_sec * n), tz=dt.timezone.utc)
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages, 0, -1)]


def get_url(path):
    return f'http://www.bom.gov.au/{path}'


def write_gif(location):
    imageio.mimsave('loop.gif', get_fgs(location), fps=2)


write_gif('Sydney')
