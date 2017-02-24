from datetime import datetime
import json
import os
import sys
import time

import requests
 
# the following 4 are the actual values that pertain to your account and this specific metric
api_key = os.environ['STATUSPAGE_API_KEY']
page_id = 'fzcq6v7wcg65'
metric_id = 'rfcg9djxtg6n'
api_base = 'api.statuspage.io'

github_id = os.environ['GITHUB_OAUTH_KEY']
github_secret = os.environ['GITHUB_OAUTH_SECRET']

def get_rate_limit():
    r = requests.get('https://api.github.com/rate_limit',
        params={
            'client_id': github_id,
            'client_secret': github_secret,
        }
    )
    r.raise_for_status()
    resp = r.json()
    return resp['resources']['core']

def post_data(limit, remaining):
    percent = 100 * remaining / limit
    now = int(datetime.utcnow().timestamp())
    url = "https://api.statuspage.io/v1/pages/{page_id}/metrics/{metric_id}/data.json".format(
        page_id=page_id, metric_id=metric_id,
    )
    
    r = requests.post(url,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "OAuth " + api_key,
        },
        data={
            'data[timestamp]': now,
            'data[value]': percent,
        }
    )
    r.raise_for_status()

while True:
    try:
        limit = get_rate_limit()
        print(json.dumps(limit))
        post_data(limit['limit'], limit['remaining'])
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
    time.sleep(120)
