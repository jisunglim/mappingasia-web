#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import pickle
import zlib
import pandas as pd
import numpy as np
from numpy import random

from flask import Flask, request, jsonify
from flask_cors import CORS

from sqlalchemy import create_engine
import redis

import plotly.offline as pyo
import plotly.graph_objs as go
from plotly.utils import PlotlyJSONEncoder

import datetime


# set flask
app = Flask(__name__)
CORS(app)

# set postgres
pg_id = "datascience"
pg_pw = "TZAUfThGBTL7ps_2C4VU"
pg_url = 'mappingasia-dev.cjteux4pnxoo.ap-northeast-2.rds.amazonaws.com'
pg_port = 5432
pg_database = 'mappingasia'
pg_url_full = f'postgres+psycopg2://{pg_id}:{pg_pw}@{pg_url}:{pg_port}/{pg_database}'
engine = create_engine(pg_url_full)


def _connect_redis(host="localhost",
                   port=6379,
                   password="",
                   charset="utf-8",
                   decode_responses=False):
    r = redis.StrictRedis(host=host,
                          port=port,
                          password=password,
                          charset=charset,
                          decode_responses=decode_responses)
    try:
        r.ping()
        return r
    except:
        return None


r = _connect_redis()

def _select_sdg_goals():
    if r is not None:
        sdg_goals = r.get('sdg_goals')
    else:
        sdg_goals = None

    if sdg_goals is None:
        print('cache miss!')
        sdg_goals = pd.read_sql("""
            select 
                "id", "title", "description"
            from datascience.sdg_goals;
        """, con=engine)
        if r is not None:
            r.set('sdg_goals', zlib.compress(pickle.dumps(sdg_goals)))
        return sdg_goals
    else:
        print('cache shot!')
        return pickle.loads(zlib.decompress(sdg_goals))

def _select_sdg_targets():
    if r is not None:
        sdg_targets = r.get('sdg_targets')
    else:
        sdg_targets = None

    if sdg_targets is None:
        print('cache miss!')
        sdg_targets = pd.read_sql("""
            select 
                "id", "title", "description", "goal_id"
            from datascience.sdg_targets;
        """, con=engine)
        if r is not None:
            r.set('sdg_targets', zlib.compress(pickle.dumps(sdg_targets)))
        return sdg_targets
    else:
        print('cache shot!')
        return pickle.loads(zlib.decompress(sdg_targets))

def _select_sdg_indicators():
    if r is not None:
        sdg_indicators = r.get('sdg_indicators')
    else:
        sdg_indicators = None

    if sdg_indicators is None:
        print('cache miss!')
        sdg_indicators = pd.read_sql("""
            select 
                "id", "description", "tier", "target_id", "goal_id"
            from datascience.sdg_indicators;
        """, con=engine)
        if r is not None:
            r.set('sdg_indicators', zlib.compress(pickle.dumps(sdg_indicators)))
        return sdg_indicators
    else:
        print('cache shot!')
        return pickle.loads(zlib.decompress(sdg_indicators))


def _select_country_list():
    if r is not None:
        country_list = r.get('country_list')
    else:
        country_list = None

    if country_list is None:
        print('cache miss!')
        country_list = pd.read_sql("""
            select 
                "official_name_en" as "name",
                "UNTERM_English_Formal" as "name_long",
                "ISO3166_1_Alpha_2" as "iso_a2",
                "ISO3166_1_Alpha_3" as "iso_a3",
                "ISO3166_1_numeric" as "iso_numeric",
                "M49" as "unsd_m49",
                "Continent" as "continent",
                "Developed_or_Developing_Countries" as "developed_developing",
                "Languages" as "lang",
                "Region_Code" as region_code,
                "Region_Name" as region_name,
                "Sub_region_Code" as subregion_code,
                "Sub_region_Name" as subregion_name,
                "is_independent" as is_independent
            from datascience.country_list;
        """, con=engine)
        if r is not None:
            r.set('country_list', zlib.compress(pickle.dumps(country_list)))
        return country_list
    else:
        print('cache shot!')
        return pickle.loads(zlib.decompress(country_list))

@app.route('/sdg_goals')
def get_sdg_goals():
    sdg_goals = _select_sdg_goals()
    sdg_goals['id_str'] = sdg_goals['id'].apply(str).str.zfill(2)

    return sdg_goals.to_json(orient='records')

@app.route('/sdg_targets_by_goal_id/<goal_id>')
def get_sdg_targets_by_id(goal_id):
    sdg_targets = _select_sdg_targets()
    sdg_targets = sdg_targets[sdg_targets['goal_id'] == int(goal_id)]
    return sdg_targets.to_json(orient='records')

@app.route('/sdg_indicators_by_goal_id/<goal_id>')
def get_sdg_indicators_by_goal_id(goal_id):
    sdg_indicators = _select_sdg_indicators()
    sdg_indicators = sdg_indicators[sdg_indicators['goal_id'] == goal_id]
    return sdg_indicators.to_json(orient='records')

@app.route('/sdg_indicators_by_target_id/<target_id>')
def get_sdg_indicators_by_target_id(target_id):
    sdg_indicators = _select_sdg_indicators()
    sdg_indicators = sdg_indicators[sdg_indicators['target_id'] == target_id]
    return sdg_indicators.to_json(orient='records')

@app.route('/country_by_iso_a3/<iso_a3>')
def get_country_by_iso_a3(iso_a3):
    country_list = _select_country_list()
    country_list = country_list[country_list['iso_a3'] == iso_a3]
    return country_list.iloc[0].to_json()


if __name__ == "__main__":
    app.run(debug=True)
