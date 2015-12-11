#!/usr/bin/python
# -*- coding:  utf-8 -*-

import bottle
import requests


app = '10.33.39.200'
web = '10.33.39.200'


@bottle.route('/')
def index():
    ret = ''
    try:
        r = requests.get("http://%s:8080/" % app)
        print r.text
        ret = r.text
    except requests.exceptions.RequestException, err:
        ret = err
    return '<h1>Web: %s</h1></br><h2>App: %s, Content: %s</h2>' % (
        web, app, ret)


if __name__ == '__main__':
    bottle.run(host='0.0.0.0', port=80, reloader=True)
