#!/usr/bin/python
# ex:set fileencoding=utf-8:

from __future__ import unicode_literals

import argparse
import os

from zipfile import ZipFile
from zipfile import ZIP_DEFLATED

from paragliding import FlightLog
from paragliding import Flight


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process a directory with igc files')
    parser.add_argument('dir', metavar='<dir>', type=str, help='directory')
    args = parser.parse_args()

    flights = FlightLog()
    for path, dirs, files in os.walk(args.dir):
        for file in files:
            if file[-3:] == "igc":
                f = Flight.from_igc(os.path.join(path,file))
                flights.add_flight(f)
    flights.make_tree()
    flights.write('test.kml')
    with ZipFile('test.kmz', 'w', ZIP_DEFLATED) as myzip:
        myzip.write('test.kml')
    os.remove('test.kml')
