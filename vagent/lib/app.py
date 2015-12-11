#!/usr/bin/python
# -*- coding:  utf-8 -*-

import json
import bottle
import mysql.connector


db = '10.33.37.29'


def get_info(host, user='cloud', password='security421', database='mysql'):
    try:
        conn = mysql.connector.connect(host=host, user=user, password=password,
                                       database=database, port=3306)
        cursor = conn.cursor()

        query = ("SELECT host, user, password FROM user "
                 "WHERE host=%s and user=%s")
        cursor.execute(query, ('localhost', 'root'))

        a_list = cursor.fetchall()
        return a_list

    except mysql.connector.Error as err:
        print("Something went wrong: {}".format(err))
        exit()

    finally:
        conn.commit()
        cursor.close()
        conn.close()


@bottle.route('/')
@bottle.route('/index')
def returnuser():
    bottle.response.content_type = 'application/json'
    ret = get_info(host=db)[0]
    data = {"host": ret[0].decode('utf-8'),
            "user": ret[1].decode('utf-8'),
            "password": ret[2].decode('utf-8')}
    return json.dumps(data)


if __name__ == '__main__':
    bottle.run(host='0.0.0.0', port=8080, reloader=True)
