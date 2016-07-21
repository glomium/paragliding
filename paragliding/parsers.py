#!/usr/bin/python
# ex:set fileencoding=utf-8:

from __future__ import unicode_literals

import numpy as np
import re
import xml.etree.ElementTree as ET

from itertools import combinations

from datetime import datetime
from datetime import timedelta
from pytz import utc

from .utils import averages
from .utils import moving
from .utils import binom

import logging
logger = logging.getLogger(__name__)


class FlightLog(ET.ElementTree):

    def __init__(self):
        root = ET.Element('kml', xmlns="http://earth.google.com/kml/2.2")
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

            year = flight.date.strftime('%Y')
            location = flight.location
            date = flight.date.strftime('%d.%m')

            if not year in self.tree:
                self.tree[year] = {}

            if not location in self.tree[year]:
                self.tree[year][location] = {}

            if not date in self.tree[year][location]:
                self.tree[year][location][date] = []

            self.tree[year][location][date].append(flight)

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
                        d_folder = flight.make_tree(d_folder)


class Flight(object):

    colors = [
        (-6.0,  50,  50,  50),
        (-3.0,   0,   0, 128),
        (-1.0,   0, 128, 128),
        ( 0.0, 200, 200, 200),
        ( 1.0, 186, 186,   0),
        ( 2.0, 222,   0,   0),
        ( 4.0, 186,   0, 186),
    ]

    def __init__(self, file_or_filename, name, *args, **kwargs):

        self.location = None
        self.pilot = None
        self.glider = None
        self.date = None

        if name[-4:] == ".igc":
            self.name = name[:-4]
        else:
            self.name = name

        self.time = []
        self.lat = []
        self.lon = []
        self.gpsheight = []
        self.barheight = []
        self.cart = []

        self.datapoints = 0
        self.distances = {}

        self.read_igc(file_or_filename)

    def __str__(self):
        return self.name or "Trajectory"

    def __repr__(self):
        return "<%s: '%s' at 0x%x>" % (self.__class__.__name__, str(self), id(self))

    def color(self, value, alpha=255):
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

    def read_igc(self, file_or_filename):
        """
        reads igc data into the object
        """

        if hasattr(file_or_filename, "readlines"):
            file_obj = file_or_filename
        else:
            file_obj = open(file_or_filename, "r")

        search = r"B([0-9]{6})([0-9]{6})"
        timedelta_days = 0
        time_old = None
        for line in file_obj.readlines():
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

                lat = float(a[3]) + float(a[4]) / 60000
                if a[5] == "S":
                    lat *= -1

                lon = float(a[6]) + float(a[7]) / 60000
                if a[8] == "W":
                    lon *= -1

                barheight = int(a[10])
                gpsheight = int(a[11])

                self.time.append(self.date + time)
                self.lat.append(lat)
                self.lon.append(lon)
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
            logger.debug(line.strip())

        self.lon = np.array(self.lon)
        self.lat = np.array(self.lat)
        self.barheight = np.array(self.barheight)
        self.gpsheight = np.array(self.gpsheight)

        self.datapoints = len(self.lon)
        self.datarange = np.arange(self.datapoints)

        file_obj.close()

    def make_tree(self, root):

        root_folder = ET.SubElement(root, 'Folder')
        name = ET.SubElement(root_folder, 'name')
        name.text = str(self)

        tracks_folder = ET.SubElement(root_folder, 'Folder')
        data = ET.SubElement(tracks_folder, 'name')
        data.text = "Tracks"
        data = ET.SubElement(tracks_folder, 'open')
        data.text = "1"
        style = ET.SubElement(tracks_folder, 'Style')
        style = ET.SubElement(style, 'ListStyle')
        data = ET.SubElement(style, 'listItemType')
        data.text = "radioFolder"
        data = ET.SubElement(style, 'bgColor')
        data.text = "00ffffff"
        data = ET.SubElement(style, 'maxSnippetLines')
        data.text = "2"

        colored_folder = ET.SubElement(tracks_folder, 'Folder')
        data = ET.SubElement(colored_folder, 'name')
        data.text = "Colored"
        data = ET.SubElement(colored_folder, 'visibility')
        data.text = "1"

        mono_folder = ET.SubElement(tracks_folder, 'Folder')
        data = ET.SubElement(mono_folder, 'name')
        data.text = "Mono (green)"
        data = ET.SubElement(mono_folder, 'visibility')
        data.text = "0"

        shadow_folder = ET.SubElement(root_folder, 'Folder')
        data = ET.SubElement(shadow_folder, 'name')
        data.text = "Shadow"

        # SHADOW

        marker = ET.SubElement(shadow_folder, 'Placemark')
        data = ET.SubElement(marker, 'name')
        style = ET.SubElement(marker, 'Style', id="ShadowLine")
        style = ET.SubElement(style, 'LineStyle')
        data = ET.SubElement(style, 'color')
        data.text = '48000000'
        data = ET.SubElement(style, 'width')
        data.text = '2.0'
        coordinates = ET.SubElement(marker, 'LineString')
        data = ET.SubElement(coordinates, 'tessellate')
        data.text = '1'
        data = ET.SubElement(coordinates, 'coordinates')
        data.text = ' '.join([
            "%.8f,%.8f,%d" % (
                self.lon[d],
                self.lat[d],
                1,
            )
            for d in range(len(self.time))
        ])

        # Track (mono)

        marker = ET.SubElement(mono_folder, 'Placemark')
        data = ET.SubElement(marker, 'name')
        data.text = "Mono (green)"
        data = ET.SubElement(marker, 'visibility')
        data.text = "0"
        style = ET.SubElement(marker, 'Style', id="MonoLine")
        style = ET.SubElement(style, 'LineStyle')
        data = ET.SubElement(style, 'color')
        data.text = 'ff00ff00'
        data = ET.SubElement(style, 'width')
        data.text = '1.0'
        coordinates = ET.SubElement(marker, 'LineString')
        data = ET.SubElement(coordinates, 'tessellate')
        data.text = '1'
        data = ET.SubElement(coordinates, 'altitudeMode')
        data.text = 'absolute'
        data = ET.SubElement(coordinates, 'coordinates')
        data.text = ' '.join([
            "%.8f,%.8f,%d" % (
                self.lon[d],
                self.lat[d],
                self.gpsheight[d],
            )
            for d in range(len(self.time))
        ])

        smooth_height = averages(self.gpsheight, 20, binom)
        # speed = np.gradient(t.cart[0])**2 + np.gradient(t.cart[1])**2 + np.gradient(t.cart[2])**2 - np.gradient(t.gpsheight)**2
        # speed *= speed > 0
        # speed = np.sqrt(speed)*3.6

        # Track (color)

        for d in range(1, len(self.time)):
            delta = smooth_height[d] - smooth_height[d-1]
            self.calc_bearing(d - 1, d)

            flight = ET.SubElement(colored_folder, 'Placemark')

            data = ET.SubElement(flight, 'name')
            # data.text = "%s | %s m | %s km/h | %.1f m/s" % ("time", "alt", "speed", delta)
            data.text = "%.1f m/s" % delta
            data = ET.SubElement(flight, 'Style')
            style = ET.SubElement(data, 'LineStyle')
            data = ET.SubElement(style, 'color')
            data.text = self.color(delta)
            data = ET.SubElement(style, 'width')
            data.text = "2.5"
            coord = ET.SubElement(flight, 'LineString')
            data = ET.SubElement(coord, 'tessellate')
            data.text = "1"
            data = ET.SubElement(coord, 'altitudeMode')
            data.text = "absolute"
            data = ET.SubElement(coord, 'coordinates')
            data.text = "%.8f,%.8f,%d %.8f,%.8f,%d"% (
                self.lon[d-1],
                self.lat[d-1],
                self.gpsheight[d-1],
                self.lon[d],
                self.lat[d],
                self.gpsheight[d],
            )

        return root

    def max_turning_points(self, iterator, coords=None, distance=-1, count=0):
        changed = False
        keep = set()
        data = set()
        for test_coords in iterator:

            for i in test_coords:
                data.add(i)

            new_distance = self.calc_turning_point_distance(test_coords)
            if new_distance > distance:
                coords = test_coords
                changed = True
                distance = new_distance
            elif new_distance > (0.95 + 0.02 * count) * distance:
                for i in test_coords:
                    keep.add(i)

        return coords, distance, keep, data, changed

    def calc_turning_points(self, points, guess=0, maxiter=20):
        count = 0
        if guess < points + 2:
            guess = points + 2
        coords, distance, keep, data, changed = self.max_turning_points(
            combinations(
                np.uint16(np.arange(guess) * (self.datapoints - 1) / (guess - 1)), points + 2
            )
        )
        keep = set()
        data = set()

        while changed and count < maxiter:
            iter_coords = keep.copy()
            for n in range(len(coords)):

                j = coords[n]
                if n == 0:
                    i = 0
                    k = coords[n + 1]
                elif n == (len(coords) - 1):
                    i = coords[n - 1]
                    k = self.datapoints - 1
                else:
                    i = coords[n - 1]
                    k = coords[n + 1]

                dist_i = self.get_distances(i)
                dist_j = self.get_distances(j)
                dist_k = self.get_distances(k)

                iter_coords.add(j)

                n_ik = (np.argmax((dist_i[i:k+1] + dist_k[i:k+1])) + i)
                iter_coords.add(n_ik)

                if n == 0:
                    n_k = np.argmax(dist_k[0:k+1])
                    iter_coords.add(n_k)
                elif n == (len(coords) - 1):
                    n_i = np.argmax(dist_i[i:k + 1]) + i
                    iter_coords.add(n_i)

                if i < j:
                    n_ij = (np.argmax((dist_i[i:j+1] + dist_j[i:j+1])) + i)
                    iter_coords.add(n_ij)

                if j < k:
                    n_jk = (np.argmax((dist_j[j:k+1] + dist_k[j:k+1])) + j)
                    iter_coords.add(n_jk)

            if not bool(iter_coords - data):
                # no new items to process
                logger.info("no new items to process")
                break

            coords, distance, keep, data, changed = self.max_turning_points(
                combinations(sorted(iter_coords), points + 2), coords, distance, count
            )
            count += 1

        return self.calc_turning_point_distance(coords), coords

    def calc_turning_point_distance(self, coords):
        d = 0
        for n in range(len(coords) - 1):
            i = coords[n]
            j = coords[n+1]
            d += self.get_distances(i)[j]
        return d

    def calc_bearing(self, i, j):
        if i == j:
            return False, 0

        if self.calc_distance(i, j) < 2.5:
            # print "FALSE", self.calc_distance(i, j)
            return False, 0

        # x = cos(φ1)*sin(φ2) - sin(φ1)*cos(φ2)*cos(λ2-λ1)
        x = np.cos(self.lat[i]) * np.sin(self.lat[j]) - np.sin(self.lat[i]) * np.cos(self.lat[j]) * np.cos(self.lon[j] - self.lon[i])
        # y = sin(λ2-λ1) * cos(φ2)
        y = np.sin(self.lon[j] - self.lon[i]) * np.cos(self.lat[j])
        # normalise the result to a compass bearing, cause atan2 returns values in the range -pi .. +pi
        value = (180 * np.arctan2(x, y) / np.pi + 360) % 360
        # print value, x, y
        return True, value

        # difference in bearing: ((delta + 180) % 360) - 180

    def get_distances(self, i):
        if i in self.distances.keys():
            return self.distances[i]
        self.distances[i] = np.zeros(self.datapoints, np.float64)
        for n in range(self.datapoints):
            self.distances[i][n] = self.calc_distance(i, n)
        return self.distances[i]

    def calc_FAI_distance(self, i, j):
        # FAI earth-radius in meter
        R = 6371000.0

        latx = np.radians(self.lat[i])
        lonx = np.radians(self.lon[i])

        laty = np.radians(self.lat[j])
        lony = np.radians(self.lon[j])

        sinlat = np.sin((latx-laty)/2)
        sinlon = np.sin((lonx-lony)/2)

        return 2 * R * np.arcsin(np.sqrt(
            sinlat * sinlat + sinlon * sinlon * np.cos(latx) * np.cos(laty)
        ))

    def calc_distance(self, i, j):
        return self.calc_FAI_distance(i, j)

        # # WGS84 - http://de.wikipedia.org/wiki/Erdellipsoid
        # a = 6378137.
        # n = 298.257223563 # = 1/f = a/(a-b)
        # b = a*(1-1/n)
        # e = np.sqrt(a**2 - b**2)/a # numerische Exzentrizität
        # N = a/np.sqrt(1-e**2*np.sin(np.radians(self.lat))**2) # Krümmungsradius des Ersten Vertikals

        # self.cart = (
        #     (N+self.gpsheight)*np.cos(np.radians(self.lat))*np.cos(np.radians(self.lon)),
        #     (N+self.gpsheight)*np.cos(np.radians(self.lat))*np.sin(np.radians(self.lon)),
        #     (N*(1-e**2)+self.gpsheight)*np.sin(np.radians(self.lat)),
        # )
