from app import app
from flask import render_template
from app.common.api_requests import Add_request
from time import time

ids = ['frifon', 'id19295913', 'temet__nosce']
values = {}

@app.route('/')
def index():
    return render_template('index.html', users=values)

@app.route('/refresh')
def refresh():
    get_users()
    return ''

def after_users_get(response):
    for res in response:
        res['time'] = time()
        if res['id'] in values.keys():
            values[res['id']].append(res)
        else:
            values[res['id']] = [res]

def get_users():
    for i in range(0, len(ids), 400):   
        values = {
            "user_ids" : ",".join([str(j) for j in ids[i:i+400]]),
            "fields" : "online,online_mobile"
        }
        request = Add_request('users.get', values, after_users_get)
        request.execute_now()