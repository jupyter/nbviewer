#!/usr/bin/env python3

from datetime import datetime
import json
import os
import sys
import time

import requests
 
api_key = os.environ['STATUSPAGE_API_KEY']
page_id = os.environ['STATUSPAGE_PAGE_ID']
metric_id = os.environ['STATUSPAGE_METRIC_ID']
api_base = 'api.statuspage.io'

github_id = os.environ['GITHUB_OAUTH_KEY']
github_secret = os.environ['GITHUB_OAUTH_SECRET']


def get_rate_limit():
    """Retrieve the current GitHub rate limit for our auth tokens"""
    r = requests.get(
        'https://api.github.com/rate_limit',
        auth=(github_id, github_secret)
    )
    r.raise_for_status()
    resp = r.json()
    return resp['resources']['core']


def post_data(limit, remaining, **ignore):
    """Send the percent-remaining GitHub rate limit to statuspage"""
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


def get_and_post():
    data = get_rate_limit()
    print(json.dumps(data))
    post_data(limit=data['limit'], remaining=data['remaining'])


while True:
    try:
        get_and_post()
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
    # post every two minutes
    time.sleep(120)
