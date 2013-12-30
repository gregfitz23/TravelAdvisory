import urllib
import urllib2
import re
import json
import datetime

GOOGLEMAPS_PATTERN = re.compile(r"in current traffic: (\d+) mins", re.I)

ARDUINO_HOST = "http://fitzduino.local"
ARDUINO_USER = "root"
ARDUINO_PASSWORD = "Argerald"

#\\x3cb\\x3e(\d+) mins\\x3c/b\\x3e


class RouteData(object):
  def __init__(self, code, mins):
    self.code = code
    self.mins = int(mins)
    
  def __str__(self):
    return self.code + ": " + str(self.mins)

def get_minutes_from_google_maps(url):
  handle = urllib.urlopen(url)
  resp = handle.read()

  matches = GOOGLEMAPS_PATTERN.search(resp)
  if matches is not None:
    return int(matches.group(1))


def write_data(key, data):
  # create a password manager
  password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

  # Add the username and password.
  # If we knew the realm, we could use it instead of None.
  top_level_url = ARDUINO_HOST + "/data/"
  password_mgr.add_password(None, top_level_url, ARDUINO_USER, ARDUINO_PASSWORD)

  handler = urllib2.HTTPBasicAuthHandler(password_mgr)

  # create "opener" (OpenerDirector instance)
  opener = urllib2.build_opener(handler)

  # use the opener to fetch a URL
  print top_level_url + "put/" + key + "/" + str(data)
  opener.open(top_level_url + "put/" + key + "/" + str(data))



def pick2(data):  
  first = second = None
  
  for route in data:
    if first is None or route.mins < first.mins:
      second = first
      first = route
    elif second is None or route.mins < second.mins:
      second = route
  
  return first, second
  

# MAIN SCRIPT  
config_json = json.loads(open("../traveladvisory.json", 'r').read())

# process car

car_routes = config_json["car"]["routes"]
car_results = []

for route in car_routes:
  if route["type"] == "googlemaps":
    minutes = get_minutes_from_google_maps(route["url"])
    minutes = int(minutes * route["adjustFactor"])
    data = RouteData(route["displayCode"], minutes)
    
    print data
    car_results.append(data)
    
first, second = pick2(car_results)

write_data("CAR_0_CODE", first.code)
write_data("CAR_0_MINS", first.mins)
write_data("CAR_1_CODE", second.code)
write_data("CAR_1_MINS", second.mins)



# bus_routes = config_json["bus"]["routes"]
# for route in bus_routes:
#   if route["type"] == "googlemapsbus":
#     x = 1



