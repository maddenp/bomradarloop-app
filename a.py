from PIL import Image
import datetime as dt
import imageio
import io
import numpy as np
import requests
import time

radar = {
    'Sydney': 'IDR713',
}

def getbg(location):
    url = geturl(f'products/radar_transparencies/{radar[location]}.background.png')
    return getimage(url)

def getfg(location, timestr):
    url = geturl(f'/radar/{radar[location]}.T.{timestr}.png')
    return getimage(url)

def getimage(url):
    return Image.open(io.BytesIO(requests.get(url).content)).convert('RGBA')

def geturl(path):
    return f'http://www.bom.gov.au/{path}'

location = 'Sydney'

nimages = 6
radar_interval_min = 6
radar_interval_sec = radar_interval_min * 60
ts_now = int(time.time())
ts_fix = ts_now - (ts_now % radar_interval_sec)
mkdt = lambda n: dt.datetime.fromtimestamp(ts_fix - (radar_interval_sec * n), tz=dt.timezone.utc)
strs = [mkdt(n).strftime('%Y%m%d%H%M') for n in range(nimages-1, -1, -1)]

# print(dt.datetime.fromtimestamp(ts_now, tz=dt.timezone.utc).strftime('%Y%m%d%H%M'))
# print(dt.datetime.fromtimestamp(ts_fix, tz=dt.timezone.utc).strftime('%Y%m%d%H%M'))
# print()
for x in strs:
    print(x)

ns = ('0254', '0300', '0306', '0312', '0318', '0324')
bg = getbg(location)
merge = lambda bg, fn: np.array(Image.alpha_composite(bg, Image.open(fn).convert('RGBA')))
images = [merge(bg, f'{radar[location]}.T.20190109{n}.png') for n in ns]
imageio.mimsave('loop.gif', images, fps=2)
