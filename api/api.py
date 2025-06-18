from flask import Flask, jsonify
from flask_cors import CORS
import paho.mqtt.client as mqtt
import json
import threading
from datetime import datetime, timezone
from flasgger import Swagger
import time

OBU_MESSAGE = None
RSU_MESSAGE = None
green = {}
vehicles = {}

app = Flask(__name__)
swagger = Swagger(app, template={
    "info": {
        "title": "SmartEM Signals API",
        "description": "Api de Monitorização via MQTT",
        "version": "1.0.0"
    }
}, config={
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,  
            "model_filter": lambda tag: True, 
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
})

CORS(app)

def on_connectCAM(client, userdata, flags, rc):
    print("Connected to RSU CAM with result code "+str(rc))
    client.subscribe("vanetza/out/cam")

def on_messageCAM(client, userdata, msg):
    global OBU_MESSAGE, vehicles
    try:
        message = json.loads(msg.payload.decode())
        OBU_MESSAGE = msg.payload
        
        station_id = message.get("stationID")
        if not station_id:
            print("⚠️  Mensagem CAM sem stationID - ignorada")
            return
            
        cam_data = message.get("cam", {})
        cam_params = cam_data.get("camParameters", {})
        basic_container = cam_params.get("basicContainer", {})
        ref_position = basic_container.get("referencePosition", {})
        
        latitude = ref_position.get("latitude", 0) / 10000000.0
        longitude = ref_position.get("longitude", 0) / 10000000.0
        station_type = basic_container.get("stationType", 5)
        is_ambulance = station_type == 10
        
        # Guardar/atualizar veículo
        vehicles[station_id] = {
            "latitude": latitude,
            "longitude": longitude,
            "isAmbulance": is_ambulance,
            "timestamp": time.time()
        }
        
        print(f"✅ CAM recebido: Vehicle {station_id} at ({latitude:.6f}, {longitude:.6f}) - Total veículos: {len(vehicles)}")
        
    except Exception as e:
        print(f"❌ Erro ao processar mensagem CAM: {e}")
        print(f"📄 Mensagem raw: {msg.payload.decode()}")

def on_connectRSU(client, userdata, flags, rc):
    print("Connected to RSU SPATEM with result code "+str(rc))
    client.subscribe("vanetza/out/spatem")

def on_messageRSU(client, userdata, msg):
    global RSU_MESSAGE, green
    try:
        RSU_MESSAGE = json.loads(msg.payload.decode())
        intersections = RSU_MESSAGE["intersections"]

        green_group = None
        for state in intersections[0]["states"]:
            if state["state-time-speed"][0]["eventState"] == 5:
                green_group = state["signalGroup"]
                break

        green = {"semáforo_verde": green_group}
        print(f"SPATEM recebido: Green light = {green_group}")

    except Exception as e:
        print(f"[ERRO] ao processar SPATEM: {e}")
        green = {"semáforo_verde": None}

def clean_old_vehicles():
    global vehicles
    current_time = time.time()
    vehicles = {
        vehicle_id: data for vehicle_id, data in vehicles.items()
        if current_time - data.get("timestamp", 0) < 10
    }

def start_cleanup_thread():
    def cleanup_loop():
        while True:
            time.sleep(10)
            clean_old_vehicles()
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()

clientCAM = mqtt.Client()
clientCAM.on_connect = on_connectCAM
clientCAM.on_message = on_messageCAM
clientCAM.connect("192.168.98.10", 1883, 60)  
threading.Thread(target=clientCAM.loop_forever, daemon=True).start()

clientRSU = mqtt.Client()
clientRSU.on_connect = on_connectRSU
clientRSU.on_message = on_messageRSU
clientRSU.connect("192.168.98.10", 1883, 60)  
threading.Thread(target=clientRSU.loop_forever, daemon=True).start()

start_cleanup_thread()

@app.route("/", methods=["GET"])
def root():
    """
    Root endpoint
    ---
    responses:
      200:
        description: simple endpoints
    """
    return jsonify(message="SmartEM Signals API online. Use /api/v1/vehicles ou /api/v1/green"), 200

@app.route("/api/v1/vehicles", methods=["GET"])
def get_vehicles():
    """
    Get list of known vehicles
    ---
    responses:
      200:
        description: A list of vehicles with last known location and type
    """
    clean_old_vehicles()
    
    clean_vehicles = {
        vehicle_id: {
            "latitude": data["latitude"],
            "longitude": data["longitude"], 
            "isAmbulance": data["isAmbulance"]
        }
        for vehicle_id, data in vehicles.items()
    }
    
    return jsonify(clean_vehicles), 200

@app.route("/api/v1/green", methods=["GET"])
def get_spatem():
    """
    Get the signal group on which event state is 5
    ---
    responses:
      200:
        description: Latest SPATEM received
    """
    return jsonify(green), 200

if __name__ == "__main__":
    print("Conectando ao RSU principal como broker central...")
    app.run(debug=True, host="0.0.0.0", port=5000)

