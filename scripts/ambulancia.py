# scripts/ambulancia.py
import paho.mqtt.client as mqtt
import json
import time
import os
import math
import numpy as np
from threading import Thread

north_to_south = [
    (38.726774, -9.134941),
    (38.726304959120014, -9.134825),
    (38.725943999943446, -9.134802004046243)
]

north_to_west = [
    (38.726774, -9.134941),
    (38.72631815128129, -9.134865657421392),
    (38.72638099994345, -9.13568699665422)
]

north_to_east = [
    (38.726774, -9.134941),
    (38.72631815128129, -9.134784342578607),
    (38.72629999994344, -9.134190996524385)
]

south_to_north = [
    (38.725944, -9.134917),
    (38.72639504087963, -9.134825),
    (38.72677399994345, -9.13482600271583)
]

south_to_west = [
    (38.725944, -9.134917),
    (38.72638184870438, -9.134865657457487),
    (38.72638099994345, -9.13568699665422)
]

south_to_east = [
    (38.725944, -9.134917),
    (38.72638184870438, -9.134784342542511),
    (38.72629999994344, -9.134190996524385)
]

west_to_north = [
    (38.726381, -9.135572),
    (38.72638184870438, -9.134784342542511),
    (38.72677399994345, -9.13482600271583)
]

west_to_south = [
    (38.726381, -9.135572),
    (38.72631815128129, -9.134784342578607),
    (38.725943999943446, -9.134802004046243)
]

west_to_east = [
    (38.726381, -9.135572),
    (38.72634999998586, -9.134767501697734),
    (38.72629999994344, -9.134190996524385)
]

east_to_north = [
    (38.7263, -9.134076),
    (38.72638184870438, -9.134865657457487),
    (38.72677399994345, -9.13482600271583)
]

east_to_south = [
    (38.7263, -9.134076),
    (38.72631815128129, -9.134865657421392),
    (38.725943999943446, -9.134802004046243)
]

east_to_west = [
    (38.7263, -9.134076),
    (38.72634999998586, -9.134882498302265),
    (38.72638099994345, -9.13568699665422)
]

class Ambulance:
    def __init__(self, station_id, path_number):
        self.station_id = station_id
        self.path_coordinates = self.generate_interpolated_path(path_number)
        self.current_position = 0
        self.client = mqtt.Client()
        
    def get_base_path_coordinates(self, path_number):
        paths = {
            1: north_to_south, 2: north_to_west, 3: north_to_east,
            4: south_to_north, 5: south_to_west, 6: south_to_east,
            7: west_to_north, 8: west_to_south, 9: west_to_east,
            10: east_to_north, 11: east_to_south, 12: east_to_west
        }
        return paths.get(path_number, north_to_south)
    
    def interpolate_coordinates(self, start, end, num_points=10):
        lats = np.linspace(start[0], end[0], num_points)
        lons = np.linspace(start[1], end[1], num_points)
        return list(zip(lats, lons))
    
    def generate_interpolated_path(self, path_number):
        base_path = self.get_base_path_coordinates(path_number)
        
        if len(base_path) < 3:
            return base_path
            
        start, middle, end = base_path[0], base_path[1], base_path[2]
        
        segment1 = self.interpolate_coordinates(start, middle, 15)
        segment2 = self.interpolate_coordinates(middle, end, 15)
        
        full_path = segment1 + segment2[1:]
        
        print(f"🚑 Ambulância {self.station_id}: Rota de emergência gerada com {len(full_path)} pontos")
        return full_path
        
    def setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.connect("192.168.98.10", 1883, 60)
        
    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("vanetza/out/mapem")
        client.subscribe("vanetza/out/spatem")
        print(f"🚑 Ambulância {self.station_id} conectada: {rc}")
        
    def get_current_position(self):
        if self.current_position < len(self.path_coordinates):
            return self.path_coordinates[self.current_position]
        return self.path_coordinates[-1]
    
    def publish_denm(self):
        lat, lon = self.get_current_position()
        
        try:
            with open('/app/messages/in_denm.json', 'r') as f:
                denm = json.load(f)
            
            denm["stationID"] = self.station_id
            denm["latitude"] = int(lat * 10000000)
            denm["longitude"] = int(lon * 10000000)
            denm["stationType"] = 10
            
            denm["situation"] = {
                "informationQuality": 7,
                "eventType": {
                    "causeCode": 1,
                    "subCauseCode": 1
                }
            }
            
            self.client.publish("vanetza/in/denm", json.dumps(denm))
            
        except Exception as e:
            print(f"🚑 Ambulância {self.station_id} - Erro DENM: {e}")
        
    def move_and_alert(self):
        while True:
            if self.current_position < len(self.path_coordinates) - 1:
                self.current_position += 1
            else:
                self.current_position = 0
                print(f"🚑 Ambulância {self.station_id}: Reiniciando percurso de emergência")
            
            self.publish_denm()
            time.sleep(1)
    
    def run(self):
        self.setup_mqtt()
        
        move_thread = Thread(target=self.move_and_alert)
        move_thread.daemon = True
        move_thread.start()
        
        print(f"🚑 Ambulância {self.station_id} em serviço de emergência")
        self.client.loop_forever()

if __name__ == "__main__":
    station_id = int(os.environ.get("VANETZA_STATION_ID", 200))
    path_number = int(os.environ.get("PATH", 1))
    
    ambulance = Ambulance(station_id, path_number)
    ambulance.run()