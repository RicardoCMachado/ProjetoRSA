# scripts/rsu.py
import paho.mqtt.client as mqtt
import json
import time
import math
from threading import Thread

class RSU:
    def __init__(self):
        self.client = mqtt.Client()
        self.vehicles_by_signal_group = {
            1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: [], 10: [], 11: [], 12: []
        }
        self.ambulance_active = False
        self.ambulance_signal_group = None
        self.current_green_signal = 1
        self.intersection_center = (38.726349, -9.134933)
        
    def setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect("192.168.98.10", 1883, 60)
        
    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("vanetza/out/cam")
        client.subscribe("vanetza/out/denm")
        print(f"RSU conectada ao MQTT: {rc}")
        
    def on_message(self, client, userdata, msg):
        try:
            message = json.loads(msg.payload.decode())
            
            if msg.topic == "vanetza/out/cam":
                self.process_cam(message)
            elif msg.topic == "vanetza/out/denm":
                self.process_denm(message)
                
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
    
    def process_cam(self, cam_message):
        station_id = cam_message.get("stationID")
        latitude = cam_message.get("latitude", 0) / 10000000.0
        longitude = cam_message.get("longitude", 0) / 10000000.0
        
        signal_group = self.determine_signal_group(latitude, longitude)
        distance = self.calculate_distance_to_intersection(latitude, longitude)
        
        self.update_vehicle_position(station_id, signal_group, latitude, longitude, distance)
        
    def process_denm(self, denm_message):
        station_id = denm_message.get("stationID")
        latitude = denm_message.get("latitude", 0) / 10000000.0
        longitude = denm_message.get("longitude", 0) / 10000000.0
        
        self.ambulance_active = True
        self.ambulance_signal_group = self.determine_signal_group(latitude, longitude)
        
        print(f"🚨 EMERGÊNCIA: Ambulância {station_id} detectada! Prioridade para signal group {self.ambulance_signal_group}")
        self.set_green_light(self.ambulance_signal_group)
        
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
    
    def calculate_distance_to_intersection(self, lat, lon):
        center_lat, center_lon = self.intersection_center
        
        lat_diff = lat - center_lat
        lon_diff = lon - center_lon
        
        distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000
        return distance
    
    def update_vehicle_position(self, station_id, signal_group, lat, lon, distance):
        for sg in self.vehicles_by_signal_group:
            self.vehicles_by_signal_group[sg] = [
                v for v in self.vehicles_by_signal_group[sg] 
                if v['id'] != station_id
            ]
        
        if signal_group in self.vehicles_by_signal_group:
            self.vehicles_by_signal_group[signal_group].append({
                'id': station_id,
                'lat': lat,
                'lon': lon,
                'distance': distance,
                'timestamp': time.time()
            })
    
    def get_priority_signal_group(self):
        if self.ambulance_active and self.ambulance_signal_group:
            return self.ambulance_signal_group
        
        max_priority = -1
        target_signal_group = 1
        
        for sg, vehicles in self.vehicles_by_signal_group.items():
            if not vehicles:
                continue
                
            num_vehicles = len(vehicles)
            closest_vehicle = min(vehicles, key=lambda v: v['distance'])
            closest_distance = closest_vehicle['distance']
            
            if closest_distance < 50:
                priority = num_vehicles * 100 + (50 - closest_distance)
            else:
                priority = num_vehicles
                
            if priority > max_priority:
                max_priority = priority
                target_signal_group = sg
                
        return target_signal_group
    
    def traffic_light_control(self):
        while True:
            target_sg = self.get_priority_signal_group()
            
            if target_sg != self.current_green_signal:
                self.set_green_light(target_sg)
                print(f"🚦 Mudança de semáforo: Signal Group {target_sg} agora VERDE")
            
            if self.ambulance_active:
                time.sleep(1)
            else:
                time.sleep(5)
                
            self.check_ambulance_status()
    
    def check_ambulance_status(self):
        if self.ambulance_active:
            ambulance_vehicles = self.vehicles_by_signal_group.get(self.ambulance_signal_group, [])
            if not ambulance_vehicles:
                self.ambulance_active = False
                self.ambulance_signal_group = None
                print("🚨 Ambulância passou - voltando ao controlo normal")
    
    def set_green_light(self, signal_group):
        self.current_green_signal = signal_group
        self.publish_spatem()
    
    def publish_mapem(self):
        try:
            with open('/app/messages/in_mapem.json', 'r') as f:
                mapem = json.load(f)
            
            self.client.publish("vanetza/in/mapem", json.dumps(mapem))
            print("📍 MAPEM publicada")
        except Exception as e:
            print(f"Erro ao publicar MAPEM: {e}")
    
    def publish_spatem(self):
        try:
            with open('/app/messages/in_spatem.json', 'r') as f:
                spatem = json.load(f)
            
            for state in spatem["intersections"][0]["states"]:
                signal_group = state["signalGroup"]
                if signal_group == self.current_green_signal:
                    state["state-time-speed"][0]["eventState"] = 5
                else:
                    state["state-time-speed"][0]["eventState"] = 3
            
            self.client.publish("vanetza/in/spatem", json.dumps(spatem))
            print(f"🚦 SPATEM publicada - Verde: SG{self.current_green_signal}")
        except Exception as e:
            print(f"Erro ao publicar SPATEM: {e}")
        
    def run(self):
        self.setup_mqtt()
        
        traffic_thread = Thread(target=self.traffic_light_control)
        traffic_thread.daemon = True
        traffic_thread.start()
        
        mapem_thread = Thread(target=self.periodic_mapem)
        mapem_thread.daemon = True
        mapem_thread.start()
        
        print("🏗️ RSU iniciada e operacional")
        self.client.loop_forever()
    
    def periodic_mapem(self):
        while True:
            self.publish_mapem()
            time.sleep(10)

if __name__ == "__main__":
    rsu = RSU()
    rsu.run()