#!/usr/bin/env python3
"""inspect_sensor_json.py - Inspect tomato_water_sensor_data.json"""

import json, pandas as pd

df = pd.DataFrame(json.load(open("data/tomato_water_sensor_data.json")))
print(df.columns.tolist())
print(df.groupby("motorValue")["moisturePercentage"].agg(["count","min","median","max"]))
print("max abs diff vs (1023-raw)/1023*100:", round(((1023-df["moistureValue"])/1023*100-df["moisturePercentage"]).abs().max(), 3))
print(df[["minTomatoMoisture","minTomatoHumidity","maxTomatoHumidity"]].drop_duplicates())
print(df.iloc[[0,-1]].T)