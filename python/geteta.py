import urllib
import urllib2
import re
import json
import datetime
import time
from HTMLParser import HTMLParser

GOOGLEMAPS_PATTERN = re.compile(r"in current traffic: (\d+) mins", re.I)
GOOGLEMAPS_SECONDARY_PATTERN = re.compile(r"\\x3cspan\\x3e(\d+) mins\\x3c/span\\x3e")
GOOGLEMAPS_BUS_PATTERN = re.compile(r"altid=\\\"0\\\".*?title=\\\"(25A|25C|At 5|At 6|22a)\\\".*?class=\\\"altroute-info\\\"\\x3e[\W]?(\d+:\d+[a|p]m).*?class=\\\"dir-altroute-clear\\\"", re.M)

WMATA_TIME_PATTERN = re.compile(r"<span class=\"strong\">at (\d+:\d+[a|p]m)\W+</span>.*?")
WMATA_ROUTE_PATTERN = re.compile(r"alt=\"Click here to view bus schedule\.\"><!-- mp_trans_disable_start -->(.*)<!-- mp_trans_disable_end -->")

ARDUINO_HOST = "http://fitzduino.local"
ARDUINO_USER = "root"
ARDUINO_PASSWORD = "Argerald"

TIMESHIFT = datetime.timedelta(hours=19)
FIRST_BUS_SHIFT = datetime.timedelta(hours = 1, minutes = 20)
SECOND_BUS_SHIFT = datetime.timedelta(hours = 1, minutes = 35)

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
  else:
    matches = GOOGLEMAPS_SECONDARY_PATTERN.search(resp)
    if matches is not None: 
      return int(matches.group(1))
    else:
      print "Could not determine minutes from google maps request: " + url
    
def get_route_data_from_google_maps_bus(url):
  handle = urllib.urlopen(url)
  resp = handle.read()

  matches = GOOGLEMAPS_BUS_PATTERN.search(resp)
  if matches is not None:
    now = datetime.datetime.now() + TIMESHIFT
    route_name = matches.group(1)
    depart_time_str = matches.group(2)
    depart_time_struct = time.strptime(depart_time_str, "%I:%M%p")
    
    depart_time = datetime.datetime(now.year, now.month, now.day, depart_time_struct.tm_hour, depart_time_struct.tm_min)
    
    minutes = (depart_time - now).total_seconds()/60
    print  url
    print route_name
    print now
    print depart_time
    
    return RouteData(route_name, minutes)
  else:
    return RouteData("----", 60)

def get_route_data_from_wmata(arrive_date_time):
  url = "http://wmata.com/rider_tools/tripplanner/tripplanner.cfm"
  values = {
    'show_email':'on',
    'Minimize':'T',
    'StreetAddressTo':'S STAFFORD ST & 32ND RD S~38.835890~-77.086451~Arlington~0',
    'StreetAddressFrom':'7735 old georgetown rd',
    'StreetAddressTo_Area': '',
    'StreetAddressFrom_Area': '',
    'Mode':'A',
    'WalkDistance':'1.00',
    'ArrDep':'A',
    'Time':str(arrive_date_time.time().strftime('%I:%M')),
    'AMPM':str(arrive_date_time.time().strftime("%p")),
    'dateMonth':str(arrive_date_time.date().month),
    'dateDay':str(arrive_date_time.date().day),
    'dateYear':str(arrive_date_time.date().year),
    'submit.x':'60',
    'submit.y':'21',
    'submit':'adjustTime'
  }
  
  data = urllib.urlencode(values)
  req = urllib2.Request(url, data)
  resp = urllib2.urlopen(req).read()

  matches = WMATA_TIME_PATTERN.search(resp)
  # print resp
  if matches is not None:
    now = datetime.datetime.now() + TIMESHIFT
    
    depart_time_str = matches.group(1)
    depart_time_struct = time.strptime(depart_time_str, "%I:%M%p")
    
    depart_time = datetime.datetime(now.year, now.month, now.day, depart_time_struct.tm_hour, depart_time_struct.tm_min)
    minutes = ((depart_time - now).total_seconds()/60) - 6 #offset by time it takes to walk to metro
    
    route_name = WMATA_ROUTE_PATTERN.search(resp).group(1)
    
    route_name = route_name.replace("DASH BUS", "At").replace("BUS", "")
    
    print "now: " + now.strftime("%X")
    print route_name + ": " + depart_time_str
    return RouteData(route_name, minutes)
  else:
    print resp

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
  data = str(data).ljust(4).replace(" ", "%20")
  print top_level_url + "put/" + key + "/" + data
  opener.open(top_level_url + "put/" + key + "/" + data)

def cap_minutes(mins):
  if mins > 60:
    return 60
  elif mins < 0:
    return 0
  else:
    return mins
    
  

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
config_json = json.loads(open("../config/traveladvisory.json", 'r').read())

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
write_data("CAR_0_MINS", cap_minutes(first.mins))
write_data("CAR_1_CODE", second.code)
write_data("CAR_1_MINS", cap_minutes(second.mins))



bus_routes = config_json["bus"]["routes"]

for route in bus_routes:
  if route["type"] == "googlemapsbus":
    now = datetime.datetime.now() + TIMESHIFT
    d0 = now + FIRST_BUS_SHIFT
    d1 = now + SECOND_BUS_SHIFT

    # for wmata
    first = get_route_data_from_wmata(d0)
    second = get_route_data_from_wmata(d1)

    ## for google maps
    #first_url = route["url"].replace("%%DATE%%", d0.strftime("%x")).replace("%%TIME%%", d0.strftime("%X"))
    #second_url = route["url"].replace("%%DATE%%", d1.strftime("%x")).replace("%%TIME%%", d1.strftime("%X"))

    #first = get_route_data_from_google_maps_bus(first_url)
    #second = get_route_data_from_google_maps_bus(second_url)
    
    first, second = pick2([first, second])
    
    write_data("BUS_0_CODE", first.code)
    write_data("BUS_0_MINS", cap_minutes(first.mins))
    write_data("BUS_1_CODE", second.code)
    write_data("BUS_1_MINS", cap_minutes(second.mins))
    

