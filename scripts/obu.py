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

class OBU:
    def __init__(self, station_id, path_number):
        self.station_id = station_id
        self.path_coordinates = self.generate_interpolated_path(path_number)
        self.current_position = 0
        self.assigned_signal_group = None
        self.current_signal_state = None
        self.client = mqtt.Client()
        self.intersection_center = (38.726349, -9.134933)
        
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
        
        print(f"OBU {self.station_id}: Rota gerada com {len(full_path)} pontos")
        return full_path
        
    def setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect("192.168.98.10", 1883, 60)
        
    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("vanetza/out/mapem")
        client.subscribe("vanetza/out/spatem")
        print(f"OBU {self.station_id} conectada: {rc}")
        
    def on_message(self, client, userdata, msg):
        try:
            message = json.loads(msg.payload.decode())
            
            if msg.topic == "vanetza/out/mapem":
                self.process_mapem(message)
            elif msg.topic == "vanetza/out/spatem":
                self.process_spatem(message)
                
        except Exception as e:
            print(f"OBU {self.station_id} - Erro: {e}")
    
    def process_mapem(self, mapem_message):
        if not self.assigned_signal_group:
            current_lat, current_lon = self.get_current_position()
            self.assigned_signal_group = self.determine_signal_group(current_lat, current_lon)
            print(f"🚗 OBU {self.station_id} auto-atribuída ao Signal Group {self.assigned_signal_group}")
    
    def process_spatem(self, spatem_message):
        if not self.assigned_signal_group:
            return
            
        for state in spatem_message["intersections"][0]["states"]:
            if state["signalGroup"] == self.assigned_signal_group:
                event_state = state["state-time-speed"][0]["eventState"]
                if event_state == 5:
                    self.current_signal_state = "GREEN"
                    print(f"🟢 OBU {self.station_id}: Semáforo VERDE")
                elif event_state == 3:
                    self.current_signal_state = "RED"
                    print(f"🔴 OBU {self.station_id}: Semáforo VERMELHO - PARANDO")
                break
    
    def determine_signal_group(self, lat, lon):
        center_lat, center_lon = self.intersection_center
        
        if lat > center_lat + 0.0001:
            if lon > center_lon + 0.0001:
                return 3
            elif lon < center_lon - 0.0001:
                return 2
            else:
                return 1
        elif lat < center_lat - 0.0001:
            if lon > center_lon + 0.0001:
                return 6
            elif lon < center_lon - 0.0001:
                return 5
            else:
                return 4
        elif lon > center_lon + 0.0001:
            if lat > center_lat:
                return 10
            else:
                return 9
        elif lon < center_lon - 0.0001:
            if lat > center_lat:
                return 8
            else:
                return 7
        else:
            return 11
    
    def get_current_position(self):
        if self.current_position < len(self.path_coordinates):
            return self.path_coordinates[self.current_position]
        return self.path_coordinates[-1]
    
    def calculate_distance_to_intersection(self):
        lat, lon = self.get_current_position()
        center_lat, center_lon = self.intersection_center
        
        lat_diff = lat - center_lat
        lon_diff = lon - center_lon
        
        distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000
        return distance
    
    def is_near_intersection(self):
        return self.calculate_distance_to_intersection() < 50
    
    def should_stop(self):
        return (self.current_signal_state == "RED" and 
                self.is_near_intersection() and 
                self.current_position < len(self.path_coordinates) - 5)
    
    def publish_cam(self):
        lat, lon = self.get_current_position()
        
        try:
            with open('/app/messages/in_cam.json', 'r') as f:
                cam = json.load(f)
            
            cam["stationID"] = self.station_id
            cam["latitude"] = int(lat * 10000000)
            cam["longitude"] = int(lon * 10000000)
            cam["stationType"] = 5
            
            self.client.publish("vanetza/in/cam", json.dumps(cam))
            
        except Exception as e:
            print(f"OBU {self.station_id} - Erro CAM: {e}")
    
    def move_vehicle(self):
        while True:
            if not self.should_stop():
                if self.current_position < len(self.path_coordinates) - 1:
                    self.current_position += 1
                else:
                    self.current_position = 0
                    print(f"🔄 OBU {self.station_id}: Reiniciando percurso")
            
            self.publish_cam()
            time.sleep(2)
    
    def run(self):
        self.setup_mqtt()
        
        move_thread = Thread(target=self.move_vehicle)
        move_thread.daemon = True
        move_thread.start()
        
        print(f"🚗 OBU {self.station_id} iniciada")
        self.client.loop_forever()

if __name__ == "__main__":
    station_id = int(os.environ.get("VANETZA_STATION_ID", 100))
    path_number = int(os.environ.get("PATH", 1))
    
    obu = OBU(station_id, path_number)
    obu.run()




