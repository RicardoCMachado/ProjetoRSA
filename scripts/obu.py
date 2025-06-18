import paho.mqtt.client as mqtt
import time
import json
import sys
from geopy.distance import distance, geodesic
from geopy import Point
import math
import threading
import random


if len(sys.argv) != 4:
    print("Usage: python3 obu.py <ID> <IP> <PATH>")
    sys.exit(1)

ID = int(sys.argv[1])
IP = sys.argv[2]
PATH = int(sys.argv[3])

def calculate_initial_compass_bearing(pointA, pointB):

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)
    compass_bearing = (math.degrees(initial_bearing) + 360) % 360

    return compass_bearing

def get_coordinates(lat1, lon1, lat2, lon2, speed = 30):
    start = Point(latitude=lat1, longitude=lon1)
    end = Point(latitude=lat2, longitude=lon2)
    distance = geodesic(start, end).kilometers
    distance_meters = distance * 1000
    speed = float(speed)
    speedms = speed * 0.277778
    seconds = distance_meters / speedms
    N = 10
    samples = int(seconds * N)
    step = distance_meters / samples
    bearing = calculate_initial_compass_bearing((lat1, lon1), (lat2, lon2))

    coordinates = []
    for i in range(samples+1):
        step_distance = step * i
        step_point = geodesic(meters=step_distance).destination(point=start, bearing=bearing)
        step_point.latitude = round(step_point.latitude, 6)
        step_point.longitude = round(step_point.longitude, 6)
        coordinates.append((step_point.latitude, step_point.longitude))
    return coordinates

def coordinates_to_dict(coordinates):
    return {i+1: (round(coordinate[0], 6), round(coordinate[1], 6)) for i, coordinate in enumerate(coordinates)}

def travel(street_list, delay):
    j = 0
    for street in street_list:
        for key, coord in street.items():
            message = construct_message(coord[0], coord[1])
            publish_message(message)
            time.sleep(delay)
        j += 1
        print("\n")


def publish_message(message):
    client.publish("vanetza/in/cam", message)

def construct_message(latitude,longtitude):
    global ID
    f = open('./in_cam.json')
    m = json.load(f)
    m["latitude"] = latitude
    m["longitude"] = longtitude
    m["stationID"] = ID
    m = json.dumps(m)
    return m


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


def generate_street(path_points):
    coords1 = get_coordinates(*path_points[0], *path_points[1])
    coords2 = get_coordinates(*path_points[1], *path_points[2])
    return coordinates_to_dict(coords1) | coordinates_to_dict(coords2)

north_to_south_street = generate_street(north_to_south)
north_to_west_street = generate_street(north_to_west)
north_to_east_street = generate_street(north_to_east)
south_to_north_street = generate_street(south_to_north)
south_to_west_street = generate_street(south_to_west)
south_to_east_street = generate_street(south_to_east)
west_to_north_street = generate_street(west_to_north)
west_to_south_street = generate_street(west_to_south)
west_to_east_street = generate_street(west_to_east)
east_to_north_street = generate_street(east_to_north)
east_to_south_street = generate_street(east_to_south)
east_to_west_street = generate_street(east_to_west)



def main():
    global PATH

    if PATH == 1:
        path = [north_to_south_street]
    elif PATH == 2:
        path = [north_to_west_street]
    elif PATH == 3:
        path = [north_to_east_street]
    elif PATH == 4:
        path = [south_to_north_street]
    elif PATH == 5:
        path = [south_to_west_street]
    elif PATH == 6:
        path = [south_to_east_street]
    elif PATH == 7:
        path = [west_to_north_street]
    elif PATH == 8:
        path = [west_to_south_street]
    elif PATH == 9:
        path = [west_to_east_street]
    elif PATH == 10:
        path = [east_to_north_street]
    elif PATH == 11:
        path = [east_to_south_street]
    elif PATH == 12:
        path = [east_to_west_street]
    else:
        print("Invalid path")
        return
    
    while True:
        travel(path, 0.1)

client = mqtt.Client()
client.connect(IP, 1883, 60)

threading.Thread(target=client.loop_forever).start()

if __name__ == "__main__":
    main()




