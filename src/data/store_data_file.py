import os
import sys

import json
import numpy as np
import pandas as pd
from pandas.io.json import json_normalize
import hashlib 

from sqlalchemy import create_engine, exc, MetaData, select
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import or_, and_
from sqlalchemy.types import JSON as typeJSON

def connect_database(database_dict):

    DATABASE = database_dict

    db_url = URL(**DATABASE)
    engine = create_engine(db_url)
    meta = MetaData()
    meta.bind = engine

    return meta

def tab_raw_data(datafile_s3_key):

    #read data file
    doc = open(datafile_s3_key) #get file with s3 client when in production
    records = json.load(doc)
    raw_data = json_normalize(records) 

    #clean date fields
    raw_data['startTime'] = pd.to_datetime(raw_data['startTime'].str[:-4])
    raw_data['endTime'] = pd.to_datetime(raw_data['endTime'].str[:-4])
    raw_data['startTime'] = raw_data['startTime'].astype(pd.Timestamp)
    raw_data['endTime'] = raw_data['endTime'].astype(pd.Timestamp)

    #get creation time
    raw_data['date_created'] = pd.to_datetime('today')

    #during creation time, date_updated equals date_created
    raw_data['date_updated'] = raw_data['date_created']

    #get_file_name
    raw_data['file_name'] = datafile_s3_key

    #get DataFile hash
    import pdb
    pdb.set_trace()
    aji_list = [json.dumps(raw_data['alerts'].iloc[0],sort_keys=True),
                json.dumps(raw_data['jams'].iloc[0],sort_keys=True),
                json.dumps(raw_data['irregularities'].iloc[0],sort_keys=True),
               ]
    aji_string = "".join(aji_list)
    raw_data['json_hash'] = hashlib.md5(aji_string.encode()).hexdigest()

    return raw_data

def tab_jams(raw_data):
    if 'jams' not in raw_data:
        print("No jams in this data file.")
        return

    df_jams = json_normalize(raw_data['jams'].iloc[0])
    col_dict = {
                'blockingAlertUuid': "blocking_alert_id",
                'startNode': "start_node",
                 'endNode': "end_node",
                 'pubMillis': "pub_millis",
                 'roadType': "road_type",
                 'speedKMH': "speed_kmh",
                 'turnType': "turn_type",
                 }

    other_cols = ['city', 'country','delay', 'length',
                  'uuid', 'street', 'level', 'line']

    df_jams.rename(columns=col_dict, inplace=True)
    col_list = list(col_dict.values())
    col_list = col_list + other_cols
    all_columns = pd.DataFrame(np.nan, index=[0], columns=col_list)
    df_jams,_ = df_jams.align(all_columns, axis=1)
    df_jams = df_jams[col_list]
    df_jams["pub_utc_date"] = pd.to_datetime(df_jams["pub_millis"], unit='ms')

    return df_jams

def tab_irregularities(raw_data):
    if 'irregularities' not in raw_data:
        print("No irregularities in this data file.")
        return

    df_irregs = json_normalize(raw_data['irregularities'].iloc[0])
    col_dict = {
                'detectionDateMillis': "detection_date_millis",
                'detectionDate': "detection_date",
                'updateDateMillis': "update_date_millis",
                'updateDate': "update_date",
                'regularSpeed': "regular_speed",
                'delaySeconds': "delay_seconds",
                'jamLevel': "jam_level",
                'driversCount': "drivers_count",
                'alertsCount': "alerts_count",
                'nThumbsUp': "n_thumbs_up",
                'nComments': "n_comments",
                'nImages': "n_images",
                'id': "uuid",
                 }

    other_cols = ['street', 'city', 'country', 'speed',
                  'seconds', 'length', 'trend', 'type', 'severity', 'line']

    df_irregs.rename(columns=col_dict, inplace=True)
    col_list = list(col_dict.values())
    col_list = col_list + other_cols
    all_columns = pd.DataFrame(np.nan, index=[0], columns=col_list)
    df_irregs,_ = df_irregs.align(all_columns, axis=1)
    df_irregs = df_irregs[col_list]
    df_irregs["detection_utc_date"] = pd.to_datetime(df_irregs["detection_date_millis"], unit='ms')                  
    df_irregs["update_utc_date"] = pd.to_datetime(df_irregs["update_date_millis"], unit='ms')

    return df_irregs

def tab_alerts(raw_data):
    if 'alerts' not in raw_data:
        print("No alerts in this data file.")
        return

    df_alerts = json_normalize(raw_data['alerts'].iloc[0])
    df_alerts["location"] = df_alerts.apply(lambda row: {'x': row["location.x"], 'y': row["location.y"]} , axis=1)
    
    col_dict = {
                'pubMillis': "pub_millis",
                'roadType': "road_type",
                'reportDescription': "report_description",
                'reportRating': "report_rating",
                'nThumbsUp': "thumbs_up",
                'jamUuid': "jam_uuid",
                'irregularityUuid': "irregularity_uuid",
                'reportByMunicipalityUser': 'report_by_municipality_user',
                 }

    other_cols = ['uuid', 'street', 'city', 'country', 'location', 'magvar',
                  'reliability', 'type', 'subtype' ]

    df_alerts.rename(columns=col_dict, inplace=True)
    col_list = list(col_dict.values())
    col_list = col_list + other_cols
    all_columns = pd.DataFrame(np.nan, index=[0], columns=col_list)
    df_alerts,_ = df_alerts.align(all_columns, axis=1)
    df_alerts = df_alerts[col_list]
    df_alerts["pub_utc_date"] = pd.to_datetime(df_alerts["pub_millis"], unit='ms')

    return df_alerts

#Connection and initial setup
DATABASE = {
'drivername': "postgresql",
'host': "localhost", 
'port': 5432,
'username': "tester",
'password': "testmobility123",
'database': "test_mobility",
}

meta = connect_database(DATABASE)

raw_data = tab_raw_data("/home/bogo/Downloads/wazedata_2018_03_20_20_18_43_166.json")

#Store data_file in database
col_dict = {"startTimeMillis": "start_time_millis",
            "endTimeMillis": "end_time_millis",
            "startTime": "start_time",
            "endTime": "end_time",
            "date_created": "date_created" ,
            "date_updated": "date_updated",
            "file_name": "file_name",
            "json_hash": "json_hash",
            }

raw_data_tosql = raw_data.rename(columns=col_dict)
raw_data_tosql = raw_data_tosql[list(col_dict.values())]
try:
    raw_data_tosql.to_sql(name="data_files", schema="waze", con=meta.bind, if_exists="append", index=False)
except exc.IntegrityError:
    print("Data file is already stored in the relational database. Stopping process.")
    sys.exit()

#Introspect data_file table
meta.reflect(schema="waze")
data_files = meta.tables["waze.data_files"]
datafile_result = select([data_files.c.id]).where(and_(data_files.c.file_name == raw_data["file_name"].iloc[0],
                                                     data_files.c.json_hash == raw_data["json_hash"].iloc[0]
                                                    )
                                                ).execute().fetchall()
if len(datafile_result) > 1:
    raise Exception("There should be only one result")

datafile_id = datafile_result[0][0]

#Store jams in database
jams_tosql = tab_jams(raw_data)
jams_tosql["datafile_id"] = datafile_id
jams_tosql.to_sql(name="jams", schema="waze", con=meta.bind, if_exists="append", index=False,
                      dtype={"line": typeJSON}
                     )

#Store alerts in database
alerts_tosql = tab_alerts(raw_data)
alerts_tosql["datafile_id"] = datafile_id
alerts_tosql.to_sql(name="alerts", schema="waze", con=meta.bind, if_exists="append", index=False,
                      dtype={"location": typeJSON}
                     )

#Store irregularities in databse
irregs_tosql = tab_irregularities(raw_data)
irregs_tosql["datafile_id"] = datafile_id
irregs_tosql.to_sql(name="irregularities", schema="waze", con=meta.bind, if_exists="append", index=False,
                      dtype={"line": typeJSON}
                     )
