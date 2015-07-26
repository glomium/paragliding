#!/usr/bin/python
# ex:set fileencoding=utf-8:

from __future__ import unicode_literals

import argparse
import numpy as np
import re
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from datetime import timedelta
from pytz import utc
from zipfile import ZipFile
from zipfile import ZIP_DEFLATED
from math import factorial

class FlightLog(ET.ElementTree):
    def __init__(self):
        root = ET.Element('kml', xmlns="http://earth.google.com/kml/2.1")
        self.document = ET.SubElement(root, 'Document')
        self.tree = None
        self.flights = []
        name = ET.SubElement(self.document, 'name')
        name.text = "Flights"
        super(FlightLog, self).__init__(element=root)

    def add_flight(self, flight):
        self.flights.append(flight)

    def make_tree(self):
        self.tree = {}
        for flight in self.flights:
            flight.make_tree()
            year = flight.date.strftime('%Y')
            location = flight.location
            date = flight.date.strftime('%d.%m')

            if not location in self.tree:
                self.tree[location] = {}
            if not year in self.tree[location]:
                self.tree[location][year] = {}
            if not date in self.tree[location][year]:
                self.tree[location][year][date] = []
            self.tree[location][year][date].append(flight)

        for location in sorted(self.tree.keys()):
            l_folder = ET.SubElement(self.document, 'Folder')
            name = ET.SubElement(l_folder, 'name')
            name.text = location
            for year in sorted(self.tree[location].keys()):
                y_folder = ET.SubElement(l_folder, 'Folder')
                name = ET.SubElement(y_folder, 'name')
                name.text = year
                for date in sorted(self.tree[location][year].keys()):
                    d_folder = ET.SubElement(y_folder, 'Folder')
                    name = ET.SubElement(d_folder, 'name')
                    name.text = date
                    for flight in self.tree[location][year][date]:
                        d_folder.append(flight)

class Flight(ET.Element):
    colors = [
        (-3.0,   0,   0, 128),
        (-1.0,   0, 128, 128),
        ( 0.0, 200, 200, 200),
        ( 1.0, 186, 186,   0),
        ( 3.0, 222,   0,   0),
        ( 6.0, 186,   0, 186),
    ]

    def __init__(self, root=None):
        super(Flight, self).__init__('Folder')

        self.location = None
        self.pilot = None
        self.glider = None
        self.date = None

        self._root = root
        self.time = []
        self.lat = []
        self.long = []
        self.gpsheight = []
        self.barheight = []
        self.cart = []


    def __str__(self):
        r = self.tag
        return r.encode("utf-8")

    def __repr__(self):
        return "<%s: '%s' at 0x%x>" % (self.__class__.__name__, str(self), id(self))

    def makeelement(self, tag, attrib):
        return ET.Element(tag, attrib)

    def get_color(self, value, alpha=255):

        j = None
        k = None

        for c in range(len(self.colors)):
            if self.colors[c][0] <= value:
                if j == None or self.colors[j] <= self.colors[c]:
                    j = c
            if self.colors[c][0] >= value:
                if k == None or self.colors[k] >= self.colors[c]:
                    k = c

        if j != None and k != None and j != k:
            cdata = [self.colors[j][0], self.colors[k][0]]
            mix = (value - min(cdata)) / (max(cdata) - min(cdata))

            if self.colors[j][0] > self.colors[k][0]:
                r = int(mix * self.colors[j][1] + self.colors[k][1] - mix * self.colors[k][1])
                g = int(mix * self.colors[j][2] + self.colors[k][2] - mix * self.colors[k][2])
                b = int(mix * self.colors[j][3] + self.colors[k][3] - mix * self.colors[k][3])
            else:
                r = int(mix * self.colors[k][1] + self.colors[j][1] - mix * self.colors[j][1])
                g = int(mix * self.colors[k][2] + self.colors[j][2] - mix * self.colors[j][2])
                b = int(mix * self.colors[k][3] + self.colors[j][3] - mix * self.colors[j][3])

        elif j != None and k == None:
            r = self.colors[j][1]
            g = self.colors[j][2]
            b = self.colors[j][3]

        else:
            r = self.colors[k][1]
            g = self.colors[k][2]
            b = self.colors[k][3]

        return format(alpha, '02x') + format(b, '02x') + format(g, '02x') + format(r, '02x')

    @classmethod
    def from_igc(cls, file_or_filename):
        """
        Generates the flight object directly from an igc file
        """
        object = cls()
        object.read_igc(file_or_filename)
        return object

    def read_igc(self, file_or_filename):
        """
        reads igc data into the object
        """
        if hasattr(file_or_filename, "readlines"):
            file = file_or_filename
        else:
            file = open(file_or_filename, "r")

        search = r"B([0-9]{6})([0-9]{6})"
        timedelta_days = 0
        time_old = None
        for line in file.readlines():
            line = line.strip().decode("latin1")
            # line.decode("utf-8").strip()
            coord = re.match(r'B([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{5})(N|S)([0-9]{3})([0-9]{5})(W|E)(A|V)([0-9-]{5})([0-9-]{5})', line)
            if coord:
                a = coord.groups()

                time = timedelta(days=timedelta_days, hours=int(a[0]), minutes=int(a[1]), seconds=int(a[2]))
                if time_old and time < time_old:
                    time += timedelta(1)
                    timedelta_days += 1
                time_old = time

                lat = float(a[3]) + float(a[4])/60000
                if a[5] == "S":
                    lat *= -1

                long = float(a[6]) + float(a[7])/60000
                if a[8] == "W":
                    long *= -1

                barheight = int(a[10])
                gpsheight = int(a[11])

                self.time.append(self.date + time)
                self.lat.append(lat)
                self.long.append(long)
                self.barheight.append(barheight)
                self.gpsheight.append(gpsheight)
                continue

            if "HPSITSITE" in line:
                self.location = line.split(':',1)[1].strip()
                continue

            if "HOPLTPILOT" in line:
                self.pilot = line.split(':',1)[1].strip()
                continue

            if "HOGTYGLIDERTYPE" in line:
                self.glider = line.split(':',1)[1].strip()
                continue

            date = re.match(r"HFDTE([0-9]{2})([0-9]{2})([0-9]{2})", line)
            if date:
                d,m,y = date.groups()
                self.date = datetime(2000+int(y), int(m), int(d), tzinfo=utc)
                continue

            # TODO only log unparsed entries from igc file
            print line.strip()

        self.long = np.array(self.long)
        self.lat = np.array(self.lat)
        self.barheight = np.array(self.barheight)
        self.gpsheight = np.array(self.gpsheight)

#       # WGS84 - http://de.wikipedia.org/wiki/Erdellipsoid
#       a = 6378137.
#       n = 298.257223563 # = 1/f = a/(a-b)
#       b = a*(1-1/n)
#       e = np.sqrt(a**2 - b**2)/a # numerische Exzentrizität
#       N = a/np.sqrt(1-e**2*np.sin(np.radians(self.lat))**2) # Krümmungsradius des Ersten Vertikals

#       self.cart = (
#           (N+self.gpsheight)*np.cos(np.radians(self.lat))*np.cos(np.radians(self.long)),
#           (N+self.gpsheight)*np.cos(np.radians(self.lat))*np.sin(np.radians(self.long)),
#           (N*(1-e**2)+self.gpsheight)*np.sin(np.radians(self.lat)),
#       )

    def make_tree(self):
        self.clear() # delete old tree

        name = ET.SubElement(self, 'name')
        name.text = "%s"%(
            self.date.strftime('%H:%M'),
        )

        folder = ET.SubElement(self, 'Folder')
        name = ET.SubElement(folder, 'name')
        name.text = "Trajectory"

        smooth_height = averages(self.gpsheight, 20, binom)
       #speed = np.gradient(t.cart[0])**2 + np.gradient(t.cart[1])**2 + np.gradient(t.cart[2])**2 - np.gradient(t.gpsheight)**2
       #speed *= speed > 0
       #speed = np.sqrt(speed)*3.6

        for d in range(1, len(self.time)):
            delta = smooth_height[d] - smooth_height[d-1]

            flight = ET.SubElement(folder, 'Placemark')
            data = ET.SubElement(flight, 'name')
            data.text = "%s | %s m | %s km/h | %.1f m/s" % ("time", "alt", "speed", delta)
            data = ET.SubElement(flight, 'Style')
            style = ET.SubElement(data, 'LineStyle')
            data = ET.SubElement(style, 'color')
            data.text = self.get_color(delta)
            data = ET.SubElement(style, 'width')
            data.text = "2"
            coord = ET.SubElement(flight, 'LineString')
            data = ET.SubElement(coord, 'tessellate')
            data.text = "1"
            data = ET.SubElement(coord, 'altitudeMode')
            data.text = "absolute"
            data = ET.SubElement(coord, 'coordinates')
            data.text = "%.7f,%.7f,%d %.7f,%.7f,%d"% (
                self.long[d-1],
                self.lat[d-1],
                self.gpsheight[d-1],
                self.long[d],
                self.lat[d],
                self.gpsheight[d],
            )

    def write_kml(self, file):
        root = ET.Element('kml', xmlns="http://earth.google.com/kml/2.1")
        self.make_tree()
        root.append(self)
        with open(file, 'w') as f:
            f.write(ET.tostring(root))

def moving(N):
    return np.repeat(1.0, N)/N

def binom(N):
    return np.array([factorial(N-1)/factorial(i)/factorial(N-1-i)/2.**(N-1) for i in range(N)])

def averages(data, N, function):
    if N < 2:
        return data
    if len(data) < N:
        N = len(data)
    w = function(N)
    if len(w) != N:
        print "ERROR"
        exit()
    averages = np.convolve(data, w, "same")
    for i in range(0, N/2):
        j = 2*i+1
        w = function(j)
        averages[i] = np.sum(data[:j]*w)
        averages[-i-1] = np.sum(data[-j:]*w)
    return averages

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process a directory with igc files')
    parser.add_argument('dir', metavar='<dir>', type=str, help='directory')
    args = parser.parse_args()

    flights = FlightLog()
    for path, dirs, files in os.walk(args.dir):
        for file in files:
            if file[-3:] == "igc":
                print(file)
                f = Flight.from_igc(os.path.join(path,file))
                flights.add_flight(f)
    flights.make_tree()
    flights.write('test.kml')
    with ZipFile('text.kmz', 'w', ZIP_DEFLATED) as myzip:
        myzip.write('test.kml')
    os.remove('test.kml')
    exit()

  # # use gps height for analysis
  # smooth_height = averages(t.gpsheight, 20, binom)
  # vario = np.gradient(smooth_height)

  # s = np.gradient(t.cart[0])**2 + np.gradient(t.cart[1])**2 + np.gradient(t.cart[2])**2 - np.gradient(t.gpsheight)**2
  # s *= s>0
  # s = np.sqrt(s)*3.6

  # b = 0
  # for d in range(b,len(t.time)-b):
  #     print '2014-06-01-'+str(t.time[d]), t.gpsheight[d], smooth_height[d], s[d], vario[d]
