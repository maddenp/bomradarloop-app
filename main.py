#!/usr/bin/env python

# pylint: disable=no-member

import datetime as dt
import functools
import io
import json
import multiprocessing.dummy
import sys
import time

import flask
import PIL.Image
import requests

with open('radars.json', 'r') as f:
    radars = json.load(f)

app = flask.Flask(__name__)

valids = 'Valid locations are: %s' % ', '.join(sorted(radars.keys()))

@functools.lru_cache(maxsize=len(radars))
def get_background(location, start): # pylint: disable=unused-argument

    '''
    Fetch the background map, then the topography, locations (e.g. city names),
    and distance-from-radar range markings, and merge into a single image. Cache
    one image per location, but also consider the 'start' value when caching so
    that bad background images (e.g. with one or more missing layers) will be
    replaced in the next interval.
    '''

    log('Getting background for %s at %s' % (location, start))
    radar_id = radars[location]['id']
    url = get_url('products/radar_transparencies/IDR%s.background.png' % radar_id)
    background = get_image(url)
    if background is None:
        return None
    for layer in ('topography', 'locations', 'range'):
        log('Getting %s for %s at %s' % (layer, location, start))
        url = get_url('products/radar_transparencies/IDR%s.%s.png' % (radar_id, layer))
        image = get_image(url)
        if image is not None:
            background = PIL.Image.alpha_composite(background, image)
    return background


def get_frames(location, start):

    '''
    Use a thread pool to fetch a set of current radar images in parallel, then
    get a background image for this location, combine it with the colorbar
    legend, and finally composite each radar image onto a copy of the combined
    background/legend image.

    The 'wximages' list is created so that requested images that could not be
    fetched are excluded, so that the set of frames will be a best-effort set of
    whatever was actually available at request time. If the list is empty, None
    is returned; the caller can decide how to handle that.
    '''

    log('Getting frames for %s at %s' % (location, start))
    get = lambda time_str: get_wximg(location, time_str)
    frames = radars[location]['frames']
    raw = multiprocessing.dummy.Pool(frames).map(get, get_time_strs(location, start))
    wximages = [x for x in raw if x is not None]
    if not wximages:
        return None
    p = multiprocessing.dummy.Pool(len(wximages))
    background = get_background(location, start)
    if background is None:
        return None
    composites = p.map(lambda x: PIL.Image.alpha_composite(background, x), wximages)
    legend = get_legend(start)
    if legend is None:
        return None
    loop_frames = p.map(lambda _: legend.copy(), composites)
    p.map(lambda x: x[0].paste(x[1], (0, 0)), zip(loop_frames, composites))
    return loop_frames


def get_image(url):

    '''
    Fetch an image from the BOM.
    '''

    log('Getting image %s' % url)
    response = requests.get(url)
    if response.status_code == 200:
        return PIL.Image.open(io.BytesIO(response.content)).convert('RGBA')
    return None


@functools.lru_cache(maxsize=len(radars))
def get_legend(start): # pylint: disable=unused-argument

    '''
    Fetch the BOM colorbar legend image. See comment in get_background() in re:
    caching.
    '''

    log('Getting legend at %s' % start)
    url = get_url('products/radar_transparencies/IDR.legend.0.png')
    return get_image(url)


@functools.lru_cache(maxsize=len(radars))
def get_loop(location, start):

    '''
    Return an animated GIF comprising a set of frames, where each frame includes
    a background, one or more supplemental layers, a colorbar legend, and a
    radar image. See comment in get_background() in re: caching.
    '''

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


def get_time_strs(location, start):

    '''
    Return a list of strings representing YYYYMMDDHHMM times for the most recent
    set of radar images to be used to create the animated GIF.
    '''

    log('Getting time strings starting at %s' % start)
    delta = radars[location]['delta']
    mkdt = lambda n: dt.datetime.fromtimestamp(start - (delta * n), tz=dt.timezone.utc)
    frames = radars[location]['frames']
    return [mkdt(n).strftime('%Y%m%d%H%M') for n in range(frames, 0, -1)]


def get_url(path):

    '''
    Return a canonical URL for a suffix path on the BOM website.
    '''

    log('Getting URL for path %s' % path)
    return 'http://www.bom.gov.au/%s' % path


@functools.lru_cache(maxsize=len(radars)*6)
def get_wximg(location, time_str):

    '''
    Return a radar weather image from the BOM website. Note that get_image()
    returns None if the image could not be fetched, so the caller must deal
    with that possibility.
    '''

    log('Getting radar imagery for %s at %s' % (location, time_str))
    radar_id = radars[location]['id']
    url = get_url('/radar/IDR%s.T.%s.png' % (radar_id, time_str))
    return get_image(url)


def log(msg):

    '''
    Print log messages to stdout so that e.g. Google App Engine can incorporate
    them into overall app logging. Flush prints so that log messages appear one
    per line.
    '''

    print(msg)
    sys.stdout.flush()


@app.route('/')
def main():

    '''
    The mandatory 'location' URL parameter must match one of the keys of the
    'radars' list, above. An HTTP error with instructive information is returned
    for erroneous requests. Otherwise, a 'start' timestamp corresponding to the
    most recent radar-imagery interval is used to request an animated GIF loop
    for the given location.
    '''

    location = flask.request.args.get('location')
    if location is None:
        flask.abort(400, "No 'location' parameter given. %s" % valids)
    if radars.get(location) is None:
        flask.abort(400, "Bad location '%s'. %s" % (location, valids))
    now = int(time.time())
    delta = radars[location]['delta']
    start = now - (now % delta)
    loop = get_loop(location, start)
    if loop is None:
        flask.abort(404, 'Current radar imagery unavailable for %s' % location)
    return flask.Response(loop, mimetype='image/jpeg')


if __name__ == '__main__':
    app.run()
