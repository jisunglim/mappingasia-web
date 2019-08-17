#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask import jsonify
from pymongo import MongoClient
import pandas as pd
import numpy as np
from numpy import random
import json
from flask_cors import CORS
from flask import request

import plotly.offline as pyo
import plotly.graph_objs as go
from plotly.utils import PlotlyJSONEncoder

import datetime

app = Flask(__name__)
CORS(app)


client_mongo = MongoClient('mongodb://root:groundx123@ec2-18-179-37-53.ap-northeast-1.compute.amazonaws.com', 27017)
db = client_mongo.ethereum


@app.route('/user_of_interest')
def user_of_interest():
    user_of_interest = list(db.game_user_list_gt_2_games.aggregate([{'$sample': {'size': 50}}, {'$project': {'_id': 0}}]))
    return jsonify(user_of_interest)


@app.route('/multiple_user_journey', methods=['POST'])
def multiple_user_journey():

    addresses = request.get_json()

    columns = ['id', 'alter', 'value', 'block_timestamp', 'block_date']

    # send
    from_df = pd.DataFrame(list(db.game_user_traces.find(
        {'$and': [
            {'from_address': {"$in": addresses}},
            {'value': {'$gt': 0}}]},
        {
            '_id': 0,
            'from_address': 1,
            'to_address': 1,
            'value': 1,
            'block_timestamp': 1,
            'block_date': 1})))
    from_df = from_df.rename(index=str,
                             columns={
                                 "from_address": "id",
                                 "to_address": "alter"
                             })
    from_df = from_df[columns]
    from_df['tx_type'] = 'send'

    # receive
    to_df = pd.DataFrame(list(db.game_user_traces.find(
        {'$and': [
            {'to_address': {"$in": addresses}},
            {'value': {'$gt': 0}}]},
        {
            '_id': 0,
            'from_address': 1,
            'to_address': 1,
            'value': 1,
            'block_timestamp': 1,
            'block_date': 1})))
    to_df = to_df.rename(index=str,
                         columns={
                             "to_address": "id",
                             "from_address": "alter"
                         })
    to_df = to_df[columns]
    to_df['tx_type'] = 'receive'

    # user traces
    trace_df = pd.concat([from_df, to_df])

    # type conversion
    trace_df['value'] = trace_df['value'].astype(str).astype(float)

    # send / receive
    trace_df['value_send'] = np.where(trace_df['tx_type'] == 'send', trace_df['value'], 0)
    trace_df['value_receive'] = np.where(trace_df['tx_type'] == 'receive', trace_df['value'], 0)

    ####################### co-occurring #######################
    co_occur_df = trace_df.groupby(['alter'])['id'].nunique()
    co_occur_df = co_occur_df.to_frame().rename(index=str, columns={"id": "count"})

    ### Treshold: Shared by half of the addresses ###
    co_occur_df = co_occur_df[co_occur_df['count'] >= len(addresses) * 1. / 2]

    # filter from
    co_trace_df = trace_df.join(co_occur_df, on='alter', how='inner')

    ####################### aggregation #######################
    fa_df = co_trace_df.groupby('alter').first()

    fa_df['total_send'] = co_trace_df.groupby(['alter'], sort=False)['value_send'].sum()
    fa_df['total_receive'] = co_trace_df.groupby(['alter'], sort=False)['value_receive'].sum()
    fa_df['freq'] = co_trace_df.groupby(['alter'], sort=False)['block_timestamp'].count()
    fa_df['active_days'] = co_trace_df.groupby(['alter'], sort=False)['block_date'].nunique()
    fa_df['start_timestamp'] = co_trace_df.groupby(['alter'], sort=False)['block_timestamp'].min()
    fa_df['end_timestamp'] = co_trace_df.groupby(['alter'], sort=False)['block_timestamp'].max()
    fa_df['elapsed_days'] = (fa_df['end_timestamp'] - fa_df['start_timestamp']).dt.days
    fa_df['total_volume'] = (fa_df['total_send'] + fa_df['total_receive'])

    fa_df = fa_df[[
        'start_timestamp', 'freq', 'active_days', 'elapsed_days', 'total_send',
        'total_receive', 'total_volume'
    ]]

    ####################### read user types and roles #######################
    # user types
    type_df = pd.DataFrame(
        list(
            db.types_by_address.find({'id': {
                '$in': list(fa_df.index)
            }}, {'_id': 0})))
    type_df = type_df.rename(index=str, columns={"id": "alter"})
    type_df = type_df.set_index('alter')

    # user roles
    role_df = pd.DataFrame(
        list(
            db.role_by_address.find({'id': {
                '$in': list(fa_df.index)
            }}, {'_id': 0})))
    role_df = role_df.rename(index=str, columns={"id": "alter", "type": "role"})
    role_df = role_df.set_index('alter')

    # join to user traces
    fa_df = fa_df.join(type_df, how='left')
    fa_df = fa_df.join(role_df, how='left')

    ####################### sanitize data #######################
    fa_df = fa_df.reset_index()

    # hover info
    fa_df['info'] = fa_df.apply(
        lambda row:
        'id:{}\ntype:{}\nrole:{}\nname:{}\ntotal_send:{}\ntotal_receive:{}\ntotal_volume:{}\nstart_timestamp:{}\nelapsed_days:{}'
        .format(row['alter'], row['type'], row['role'], row['name'], row[
            'total_send'], row['total_receive'], row['total_volume'], row[
                'start_timestamp'], row['elapsed_days']),
        axis=1)


    # color type
    def get_color(role):
        color_map = {
            # type
            'EOA': '#ffa323',
            'ERC20': '#40a798',
            'ERC721': '#9ea9f0',
            'plain_contract': '#4592af',
            # role
            'cex_relay_node': 'yellow',
            'dex_relay_node': 'yellow',
            'game_dapp': 'pink',
            'game_user': 'blue',
            'others': 'grey',
            'cex': 'red',
            'dex': 'orange'
        }

        return color_map[role]


    fa_df['color_type'] = fa_df.apply(lambda row: get_color(row['type']), axis=1)
    fa_df['color_role'] = fa_df.apply(lambda row: get_color(row['role']), axis=1)

    ####################### distinct roles #######################
    roles = fa_df[['role', 'color_role']]
    roles = roles.drop_duplicates()
    roles = json.loads(roles.to_json(orient='values'))

    ####################### sort by timestamp #######################
    fa_df = fa_df.sort_values('start_timestamp', ascending=True)

    ####################### create traces #######################
    trace0 = go.Scatter(x=fa_df['start_timestamp'],
                        y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                        line=dict(width=0.3, color='black', dash='dash'),
                        hovertext=fa_df['info'],
                        hoverinfo='text+x',
                        mode='markers+lines',
                        name='User Journey',
                        xaxis='x',
                        yaxis='y',
                        marker={
                            'color': fa_df['color_role'],
                            'size':
                            5 + np.power(fa_df['total_volume'], 1. / 3) * 20,
                            'opacity': 0.7,
                            'line': dict(color='#ffffff', width=0.5)})

    trace1 = go.Scatter(
        x=fa_df['start_timestamp'],
        y=fa_df['total_send'],
        hoverinfo='name+x+y',
        fill='tozeroy',
        mode='none',
        # stackgroup='one',
        # mode='lines',
        line=dict(width=0.5, color='rgb(131, 90, 241)'),
        name='Send',
        xaxis='x2',
        yaxis='y2')

    trace2 = go.Scatter(
        x=fa_df['start_timestamp'],
        y=fa_df['total_receive'],
        hoverinfo='name+x+y',
        fill='tozeroy',
        mode='none',
        # stackgroup='one',
        # mode='lines',
        line=dict(width=0.5, color='rgb(111, 231, 219)'),
        name='Receive',
        xaxis='x2',
        yaxis='y2')

    traces = [trace0, trace1, trace2]

    journey_data = {
        "ether_volume":
        go.Scatter(x=fa_df['start_timestamp'],
                   y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                   line=dict(width=0.3, color='black', dash='dash'),
                   hovertext=fa_df['info'],
                   hoverinfo='text+x',
                   mode='markers+lines',
                   name='User Journey',
                   xaxis='x',
                   yaxis='y',
                   marker={
                       'color': fa_df['color_role'],
                       'size':
                       5 + np.power(fa_df['total_volume'], 1. / 3) * 20,
                       'opacity': 0.7,
                       'line': dict(color='#ffffff', width=0.5)}),
        "active_days":
        go.Scatter(x=fa_df['start_timestamp'],
                   y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                   line=dict(width=0.3, color='black', dash='dash'),
                   hovertext=fa_df['info'],
                   hoverinfo='text+x',
                   mode='markers+lines',
                   name='User Journey',
                   xaxis='x',
                   yaxis='y',
                   marker={
                       'color': fa_df['color_role'],
                       'size': fa_df['active_days'] * 10,
                       'opacity': 0.7,
                       'line': dict(color='#ffffff', width=0.5)}),
        "elapsed_days":
        go.Scatter(x=fa_df['start_timestamp'],
                   y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                   line=dict(width=0.3, color='black', dash='dash'),
                   hovertext=fa_df['info'],
                   hoverinfo='text+x',
                   mode='markers+lines',
                   name='User Journey',
                   xaxis='x',
                   yaxis='y',
                   marker={
                       'color': fa_df['color_role'],
                       'size': 5 + np.power(fa_df['elapsed_days'], 1. / 3) * 8,
                       'opacity': 0.7,
                       'line': dict(color='#ffffff', width=0.5)}),
    }

    layout = go.Layout(title='User Journey',
                       grid={
                           'rows': 2,
                           'columns': 1,
                           'pattern': 'independent'
                       },
                       xaxis=dict(range=[
                           datetime.datetime(2015, 7, 30, 15, 26, 13),
                           datetime.datetime.now()
                       ]),
                       yaxis=dict(autorange=True,
                                  showgrid=False,
                                  zeroline=False,
                                  showline=False,
                                  ticks='',
                                  showticklabels=False),
                       xaxis2=dict(range=[
                           datetime.datetime(2015, 7, 30, 15, 26, 13),
                           datetime.datetime.now()
                       ]),
                       yaxis2=dict(autorange=True))

    return json.dumps({'traces': traces, 'layout': layout, 'journey_data': journey_data, 'roles': roles}, cls=PlotlyJSONEncoder)

@app.route('/single_user_journey_agg/<address>')
def single_user_journey_agg(address):
    #%%
    ####################### read user trace #######################
    columns = ['id', 'alter', 'value', 'block_timestamp', 'block_date']

    # send
    from_df = pd.DataFrame(
        list(
            db.game_user_traces.find(
                {'$and': [{
                    'from_address': address
                }, {
                    'value': {
                        '$gt': 0
                    }
                }]}, {
                    '_id': 0,
                    'from_address': 1,
                    'to_address': 1,
                    'value': 1,
                    'block_timestamp': 1,
                    'block_date': 1,
                })))
    from_df = from_df.rename(index=str,
                             columns={
                                 "from_address": "id",
                                 "to_address": "alter"
                             })
    from_df = from_df[columns]
    from_df['tx_type'] = 'send'

    # receive
    to_df = pd.DataFrame(
        list(
            db.game_user_traces.find({'to_address': address}, {
                '_id': 0,
                'from_address': 1,
                'to_address': 1,
                'value': 1,
                'block_timestamp': 1,
                'block_date': 1,
            })))
    to_df = to_df.rename(index=str,
                         columns={
                             "to_address": "id",
                             "from_address": "alter"
                         })
    to_df = to_df[columns]
    to_df['tx_type'] = 'receive'

    # user traces
    trace_df = pd.concat([from_df, to_df])

    # type conversion
    trace_df['value'] = trace_df['value'].astype(str).astype(float)

    # send / receive
    trace_df['value_send'] = np.where(trace_df['tx_type'] == 'send', trace_df['value'], 0)
    trace_df['value_receive'] = np.where(trace_df['tx_type'] == 'receive', trace_df['value'], 0)


    ####################### aggregation #######################
    fa_df = trace_df.groupby('alter').first()

    fa_df['total_send'] = trace_df.groupby(['alter'], sort=False)['value_send'].sum()
    fa_df['total_receive'] = trace_df.groupby(['alter'], sort=False)['value_receive'].sum()
    fa_df['freq'] = trace_df.groupby(['alter'], sort=False)['block_timestamp'].count()
    fa_df['active_days'] = trace_df.groupby(['alter'], sort=False)['block_date'].nunique()
    fa_df['start_timestamp'] = trace_df.groupby(['alter'], sort=False)['block_timestamp'].min()
    fa_df['end_timestamp'] = trace_df.groupby(['alter'], sort=False)['block_timestamp'].max()
    fa_df['elapsed_days'] = (fa_df['end_timestamp'] - fa_df['start_timestamp']).dt.days
    fa_df['total_volume'] = (fa_df['total_send'] + fa_df['total_receive'])

    fa_df = fa_df[[
        'start_timestamp',
        'freq',
        'active_days',
        'elapsed_days',
        'total_send',
        'total_receive',
        'total_volume'
    ]]

    ####################### read user types and roles #######################
    # user types
    type_df = pd.DataFrame(
        list(
            db.types_by_address.find({'id': {
                '$in': list(fa_df.index)
            }}, {'_id': 0})))
    type_df = type_df.rename(index=str, columns={"id": "alter"})
    type_df = type_df.set_index('alter')

    # user roles
    role_df = pd.DataFrame(
        list(
            db.role_by_address.find({'id': {
                '$in': list(fa_df.index)
            }}, {'_id': 0})))
    role_df = role_df.rename(index=str, columns={"id": "alter", "type": "role"})
    role_df = role_df.set_index('alter')

    # join to user traces
    fa_df = fa_df.join(type_df, how='left')
    fa_df = fa_df.join(role_df, how='left')

    ####################### sanitize data #######################
    fa_df = fa_df.reset_index()

    # hover info
    def get_info_agg(row):
        if 'name' in row:
            return 'id:{}\ntype:{}\nrole:{}\nname:{}\ntotal_send:{}\ntotal_receive:{}\ntotal_volume:{}\nstart_timestamp:{}\nelapsed_days:{}'.format(
                row['alter'], row['type'], row['role'], row['name'],
                row['total_send'], row['total_receive'], row['total_volume'],
                row['start_timestamp'], row['elapsed_days'])
        else:
            return 'id:{}\ntype:{}\nrole:{}\ntotal_send:{}\ntotal_receive:{}\ntotal_volume:{}\nstart_timestamp:{}\nelapsed_days:{}'.format(
                row['alter'], row['type'], row['role'],
                row['total_send'], row['total_receive'], row['total_volume'],
                row['start_timestamp'], row['elapsed_days'])

    fa_df['info'] = fa_df.apply(get_info_agg, axis=1)

    # color type
    def get_color(role):
        color_map = {
            # type
            'EOA': '#ffa323',
            'ERC20': '#40a798',
            'ERC721': '#9ea9f0',
            'plain_contract': '#4592af',
            # role
            'cex_relay_node': 'yellow',
            'dex_relay_node': 'yellow',
            'game_dapp': 'pink',
            'game_user': 'blue',
            'others': 'grey',
            'cex': 'red',
            'dex': 'orange'
        }

        return color_map[role]

    fa_df['color_type'] = fa_df.apply(lambda row: get_color(row['type']),
                                      axis=1)
    fa_df['color_role'] = fa_df.apply(lambda row: get_color(row['role']),
                                      axis=1)

    ####################### get distinct roles #######################
    roles = fa_df[['role', 'color_role']]
    roles = roles.drop_duplicates()
    roles = json.loads(roles.to_json(orient='values'))

    ####################### sort by timestamp #######################
    fa_df = fa_df.sort_values('start_timestamp', ascending=True)

    ####################### create traces #######################
    trace0 = go.Scatter(x=fa_df['start_timestamp'],
                        y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                        line=dict(width=0.3, color='black', dash='dash'),
                        hovertext=fa_df['info'],
                        hoverinfo='text+x',
                        mode='markers+lines',
                        name='User Journey',
                        xaxis='x',
                        yaxis='y',
                        marker={
                            'color': fa_df['color_role'],
                            'size': fa_df['active_days'] * 10,
                            'opacity': 0.7,
                            'line': dict(color='#ffffff', width=0.5)})

    trace1 = go.Scatter(
        x=fa_df['start_timestamp'],
        y=fa_df['total_send'],
        hoverinfo='name+x+y',
        fill='tozeroy',
        mode='none',
        # stackgroup='one',
        # mode='lines',
        line=dict(width=0.5, color='rgb(131, 90, 241)'),
        name='Send',
        xaxis='x2',
        yaxis='y2')

    trace2 = go.Scatter(
        x=fa_df['start_timestamp'],
        y=fa_df['total_receive'],
        hoverinfo='name+x+y',
        fill='tozeroy',
        mode='none',
        # stackgroup='one',
        # mode='lines',
        line=dict(width=0.5, color='rgb(111, 231, 219)'),
        name='Receive',
        xaxis='x2',
        yaxis='y2')

    traces = [trace0, trace1, trace2]
    journey_data = {
        "ether_volume":
        go.Scatter(x=fa_df['start_timestamp'],
                   y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                   line=dict(width=0.3, color='black', dash='dash'),
                   hovertext=fa_df['info'],
                   hoverinfo='text+x',
                   mode='markers+lines',
                   name='User Journey',
                   xaxis='x',
                   yaxis='y',
                   marker={
                       'color': fa_df['color_role'],
                       'size': 5 + np.power(fa_df['total_volume'], 1. / 3) * 20,
                       'opacity': 0.7,
                       'line': dict(color='#ffffff', width=0.5)}),
        "active_days":
        go.Scatter(x=fa_df['start_timestamp'],
                   y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                   line=dict(width=0.3, color='black', dash='dash'),
                   hovertext=fa_df['info'],
                   hoverinfo='text+x',
                   mode='markers+lines',
                   name='User Journey',
                   xaxis='x',
                   yaxis='y',
                   marker={
                       'color': fa_df['color_role'],
                       'size': fa_df['active_days'] * 10,
                       'opacity': 0.7,
                       'line': dict(color='#ffffff', width=0.5)}),
        "elapsed_days":
        go.Scatter(x=fa_df['start_timestamp'],
                   y=random.normal(0, 0.1, size=len(fa_df['start_timestamp'])),
                   line=dict(width=0.3, color='black', dash='dash'),
                   hovertext=fa_df['info'],
                   hoverinfo='text+x',
                   mode='markers+lines',
                   name='User Journey',
                   xaxis='x',
                   yaxis='y',
                   marker={
                       'color': fa_df['color_role'],
                       'size': 5 + np.power(fa_df['elapsed_days'], 1. / 3) * 8,
                       'opacity': 0.7,
                       'line': dict(color='#ffffff', width=0.5)}),
    }

    layout = go.Layout(title='User Journey',
                       grid={
                           'rows': 2,
                           'columns': 1,
                           'pattern': 'independent'
                       },
                       xaxis=dict(range=[
                           fa_df['start_timestamp'].min() - datetime.timedelta(days=10),
                           datetime.datetime.now()
                       ]),
                       yaxis=dict(autorange=True,
                                  showgrid=False,
                                  zeroline=False,
                                  showline=False,
                                  ticks='',
                                  showticklabels=False),
                       xaxis2=dict(range=[
                           fa_df['start_timestamp'].min() - datetime.timedelta(days=10),
                           datetime.datetime.now()
                       ]),
                       yaxis2=dict(autorange=True))

    return json.dumps({'traces': traces, 'layout': layout, 'journey_data': journey_data, 'roles': roles}, cls=PlotlyJSONEncoder)

@app.route('/single_user_journey_all/<address>')
def single_user_journey_all(address):

    ####################### read user balance #######################
    balance_df = pd.DataFrame(list(db.ether_ts_balance_by_address.find(
        {'id': address}, {'_id': 0, 'balance': 1, 'block_timestamp': 1})))
    balance_df = balance_df[['block_timestamp', 'balance']]
    balance_df = balance_df.sort_values('block_timestamp', ascending=True)

    ####################### read user trace #######################
    columns = ['id', 'alter', 'value', 'block_timestamp', 'block_date']

    # send
    from_df = pd.DataFrame(list(db.game_user_traces.find({
        '$and': [{
            'from_address': address
        }, {
            'value': {'$gt': 0}
        }]

    }, {
        '_id': 0, 'from_address': 1, 'to_address': 1, 'value': 1,
        'block_timestamp': 1, 'block_date': 1,
    })))
    from_df = from_df.rename(index=str, columns={
        "from_address": "id",
        "to_address": "alter"
    })
    from_df = from_df[columns]
    from_df['tx_type'] = 'send'

    # receive
    to_df = pd.DataFrame(list(db.game_user_traces.find({
        'to_address': address
    }, {
        '_id': 0, 'from_address': 1, 'to_address': 1, 'value': 1,
        'block_timestamp': 1, 'block_date': 1,
    })))
    to_df = to_df.rename(index=str, columns={
        "to_address": "id",
        "from_address": "alter"
    })
    to_df = to_df[columns]
    to_df['tx_type'] = 'receive'

    # user traces
    trace_df = pd.concat([from_df, to_df])

    ####################### read user types and roles #######################
    # user types
    type_df = pd.DataFrame(list(db.types_by_address.find({
        'id': {'$in': list(trace_df['alter'])}}, {'_id': 0})))
    type_df = type_df.rename(index=str, columns={"id": "alter"})
    type_df = type_df.set_index('alter')

    # user roles
    role_df = pd.DataFrame(list(db.role_by_address.find(
        {'id': {'$in': list(trace_df['alter'])}}, {'_id': 0})))
    role_df = role_df.rename(index=str, columns={
        "id": "alter",
        "type": "role"})
    role_df = role_df.set_index('alter')
    role_df.head()

    # join to user traces
    trace_df = trace_df.join(type_df, on='alter', how='left')
    trace_df = trace_df.join(role_df, on=('alter'), how='left')

    ####################### sanitize data #######################
    # type conversion
    trace_df['value'] = trace_df['value'].astype(str).astype(float)

    # hover info
    def get_info_all(row):
        if 'name' in row:
            return 'id:{}\ntype:{}\nrole:{}\nname:{}\nvalue:{}\ntimestamp:{}\ntx_type:{}'.format(
                row['alter'], row['type'], row['role'], row['name'],
                row['value'], row['block_timestamp'], row['tx_type'])
        else:
            return 'id:{}\ntype:{}\nrole:{}\nvalue:{}\ntimestamp:{}\ntx_type:{}'.format(
                row['alter'], row['type'], row['role'],
                row['value'], row['block_timestamp'], row['tx_type'])

    trace_df['info'] = trace_df.apply(get_info_all, axis=1)

    # color type
    def get_color(role):
        color_map = {
            # type
            'EOA': '#ffa323',
            'ERC20': '#40a798',
            'ERC721': '#9ea9f0',
            'plain_contract': '#4592af',
            # role
            'cex_relay_node': 'yellow',
            'dex_relay_node': 'yellow',
            'game_dapp': 'pink',
            'game_user': 'blue',
            'others': 'grey',
            'cex': 'red',
            'dex': 'orange'
        }

        return color_map[role]

    trace_df['color_type'] = trace_df.apply(lambda row: get_color(row['type']), axis=1)
    trace_df['color_role'] = trace_df.apply(lambda row: get_color(row['role']), axis=1)

    # interpolate send / receive
    trace_df['value_send'] = np.where(trace_df['tx_type'] == 'send', trace_df['value'], 0)
    trace_df['value_receive'] = np.where(trace_df['tx_type'] == 'receive', trace_df['value'], 0)


    ####################### get distinct roles #######################
    roles = trace_df[['role', 'color_role']]
    roles = roles.drop_duplicates()
    roles = json.loads(roles.to_json(orient='values'))

    ####################### sort by timestamp #######################
    trace_df = trace_df.sort_values('block_timestamp', ascending=True)

    ####################### create traces #######################
    trace0 = go.Scatter(
        x=trace_df['block_timestamp'],
        # y=np.zeros(len(trace_df['block_timestamp'])),
        y=random.normal(0, 0.1, size=len(trace_df['block_timestamp'])),
        # line=dict(width=1, color='darkgray'),
        hovertext=trace_df['info'],
        hoverinfo='text+x',
        mode='markers+lines',
        name='User Journey',
        xaxis='x',
        yaxis='y',
        line=dict(width=0.3, color='black', dash='dash'),
        marker={
            'color': trace_df['color_role'],
            'size': 10,
            'opacity': 0.7,
            'line': dict(color='#ffffff', width=0.5)
        })

    trace1 = go.Scatter(
        x=trace_df['block_timestamp'],
        y=trace_df['value_send'],
        hoverinfo='name+x+y',
        fill='tozeroy',
        mode='none',
        # stackgroup='one',
        # mode='lines',
        line=dict(width=0.5, color='rgb(131, 90, 241)'),
        name='Send',
        xaxis='x2',
        yaxis='y2')

    trace2 = go.Scatter(
        x=trace_df['block_timestamp'],
        y=trace_df['value_receive'],
        hoverinfo='name+x+y',
        fill='tozeroy',
        mode='none',
        # stackgroup='one',
        # mode='lines',
        line=dict(width=0.5, color='rgb(111, 231, 219)'),
        name='Receive',
        xaxis='x2',
        yaxis='y2')

    trace3 = go.Scatter(
        x=balance_df['block_timestamp'],
        y=balance_df['balance'],
        mode='lines',
        name='Balance',
        xaxis='x3',
        yaxis='y3')

    traces = [trace0, trace1, trace2, trace3]



    layout = go.Layout(title='User Journey',
                       grid={
                           'rows': 3,
                           'columns': 1,
                           'pattern': 'independent'
                       },
                       xaxis=dict(range=[
                           trace_df['block_timestamp'].min() - datetime.timedelta(days=10),
                           datetime.datetime.now()
                       ]),
                       yaxis=dict(autorange=True,
                                  showgrid=False,
                                  zeroline=False,
                                  showline=False,
                                  ticks='',
                                  showticklabels=False),
                       xaxis2=dict(range=[
                           trace_df['block_timestamp'].min() - datetime.timedelta(days=10),
                           datetime.datetime.now()
                       ]),
                       yaxis2=dict(autorange=True),
                       xaxis3=dict(range=[
                           trace_df['block_timestamp'].min() - datetime.timedelta(days=10),
                           datetime.datetime.now()
                       ]),
                       yaxis3=dict(autorange=True))

    return json.dumps({'traces': traces, 'layout': layout, 'roles': roles}, cls=PlotlyJSONEncoder)



if __name__ == "__main__":
    app.run(debug=True)
