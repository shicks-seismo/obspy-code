#!/usr/bin/env python
'''
Script to cut out event waveform files from Frank Vernon's BOLIVAR catalogue
(Antelope format). Looks for certain events, converts date format then uses ObsPy to form event
directories.

S. Hicks
University of Southampton
Mar 2017

'''
import os
import shutil
import datetime
import numpy as np
import matplotlib.path as mplPath
import pdb # For debugging (optional) [pdb.set_trace()]

from obspy.core import read, UTCDateTime
from obspy.core.event import Catalog, Event, Origin, CreationInfo

# Input parameters to define
catalog_file = (os.path.expanduser(
    '~/VOILA/BOLIVAR/catalog_fVernon/final_db/carib_final_review.origin'))
event_dir_path =('vernon_event_dirs/')
cont_data_path = (os.path.expanduser(
    '~/VOILA/BOLIVAR/XT_download_pick_test/waveforms/'))
time_before_origin = 30
time_after_origin = 180
area_of_interest = [-64, -58, 10, 12.5] # [Lon_min, lon_max, lat_min, lat_max]
network = ['XT']
stations = ['BLOS', 'BTBT', 'CUBA', 'CUPC', 'DRKS', 'DKSS', 'MIPC', 'PINA',
            'SOMB', 'SRPC']
channels = ['BDH', 'BH1', 'BH2', 'BHZ', 'BHE', 'BHN']
dt_duplicate = 180  # Time difference to remove duplicate events
verbose = 'n'  # Verbose output [y|n] - shows files not found
# End of input parameters to define

# Open catalog
f = open(os.path.expanduser(catalog_file), 'r')

# Set dummy origin time (for removing duplicates)
prev_orig_time = UTCDateTime(0)

# Prepare QuakeML inventory
creation_string_UCSD = CreationInfo(agency_id='UCSD',
                                    creation_time=UTCDateTime.now(),
                                    author='fvernon')
creation_string_soton = CreationInfo(agency_id='soton',
                                     creation_time=UTCDateTime.now(),
                                     author='sph1r17')
catalog = Catalog()
catalog.creation_info = creation_string_soton
event = Event()
event.creation_info = creation_string_soton

# Loop over events in file
l = 0
for antelope_origin in f:
    l = l + 1
    print('Working on event, ', l)
    orig_time = UTCDateTime(float(antelope_origin[31:47]))
    t_start = UTCDateTime(orig_time) - time_before_origin
    t_end = UTCDateTime(orig_time) + time_after_origin
    latitude = float(antelope_origin[0:9])
    longitude = float(antelope_origin[10:20])
    depth = float(antelope_origin[21:29])

    # Check if origin time is too close to previous event in catalog (likely a
    # duplicate). If so, skip event.
    if (prev_orig_time + dt_duplicate >= orig_time):
        prev_orig_time = orig_time
        continue
    prev_orig_time = orig_time

    # Make a flag if event crosses goes into another day
    if ((orig_time + time_after_origin).day != orig_time.day):
        cross_midnight = 'yes'
    else:
        cross_midnight = 'no'

    # Check if lat, long is in area of interest
    poly = mplPath.Path(np.array([[area_of_interest[0], area_of_interest[1]],
                                  [area_of_interest[1], area_of_interest[2]],
                                  [area_of_interest[2], area_of_interest[3]],
                                  [area_of_interest[3], area_of_interest[0]]])
                                 )
    if poly.contains_point((latitude,longitude)) == True:

        # Get event name, make event dir (remove previous versions first)
        evname = ('e{0:4}{1:02}{2:02}.{3:02}{4:02}{5:02}'.
                  format(orig_time.year, orig_time.month, orig_time.day,
                         orig_time.hour, orig_time.minute, orig_time.second))
        if os.path.exists(event_dir_path + evname):
            shutil.rmtree(event_dir_path + evname)
        os.mkdir(event_dir_path + evname)
        for n_net in range(0, len(network)):
            for n_sta in range(0, len(stations)):
                for n_cha in range(0, len(channels)):
                    try:
                        st = read('{5}{0}/{1}/{2}/{3}.D/{1}.{2}..{3}.D.'
                                 '{0}.{4}.mseed'.format(orig_time.year,
                                                        network[n_net],
                                                        stations[n_sta],
                                                        channels[n_cha],
                                                        orig_time.julday,
                                                        cont_data_path))

                    except FileNotFoundError:
                        if verbose == 'y':
                            print('Day file not found for day: {0}.{1},'
                                  'station = {2}, channel = {3}'
                                  .format(orig_time.year, orig_time.julday,
                                          stations[n_sta], channels[n_cha]))
                        continue

                    # If event runs over midnight, read in, append and merge
                    # next day
                    if (cross_midnight == 'yes'):
                        newdate = orig_time + 86400
                        try:
                            st += read ('{5}{0}/{1}/{2}/{3}.D/{1}.{2}..{3}.D.'
                                        '{0}.{4}.mseed'.format(newdate.year,
                                                               network[n_net],
                                                               stations[n_sta],
                                                               channels[n_cha],
                                                               newdate.julday,
                                                               cont_data_path))
                        except FileNotFoundError:
                            if verbose == 'y':
                                print('Day file not found for new day: {0}.'
                                      '{1} station = {2}, channel = {3}'
                                      .format(orig_time.year, orig_time.julday,
                                              stations[n_sta],
                                              channels[n_cha]))

                    # Merge traces (in case of any gaps or in case next day has
                    # been appended)
                    st.merge()
                    try:
                        st_trim = st.slice(t_start, t_end)
                    except IndexError:
                        print('Cannot cut out event waveforms for {0}, {1},'
                              '{2}. Day file incomplete?)'
                              .format(evname, stations[nsta],channels[n_cha]))
                        continue

                    # Write to mseed file
                    st_trim.write('{9}{0}/{1}.{2}.{3:4}{4:02}{5:02}.{6:02}'
                             '{7:02}{8:02}.mseed'
                             .format(evname, stations[n_sta], channels[n_cha], 
                                     orig_time.year, orig_time.month,
                                     orig_time.day, orig_time.hour,
                                     orig_time.minute, orig_time.second,
                                     event_dir_path), format='MSEED')


        # Check if event directory is empty; if so, remove. Otherwise, finalise
        # by making QuakeML file
        if os.listdir(event_dir_path + evname) == []:
            shutil.rmtree(event_dir_path + evname)
        else:
            origin = Origin(latitude=latitude, longitude=longitude,
                            depth=depth, time=orig_time,
                            creation_info=creation_string_UCSD)
            event.origins.append(origin)
            catalog.append(event)
            catalog.write('{0}{1}/quakeml.xml'.format(event_dir_path, evname),
                          format='QUAKEML')

    else:
        continue

f.close()

