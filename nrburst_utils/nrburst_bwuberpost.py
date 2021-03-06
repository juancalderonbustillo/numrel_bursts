#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2016-2017 James Clark <james.clark@ligo.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""
nrburst_pickle_bwpost.py

Pull out post-processing results rconstructed waveforms, ASDs, overlaps,
evidence for an injection directory and pickle into a dictionary

"""

import glob
import os,sys
import cPickle as pickle
import numpy as np
import tarfile

import pycbc.types
import pycbc.filter

def extract(parent_directory, member):

    print >> sys.stdout, "extracting %s"%(
            os.path.join(parent_directory,member))

    try:
        tardata = tar.extractfile(os.path.join(parent_directory,member))
    except:
        print >> sys.stderr, "tar extraction failed for %s"%(
                os.path.join(parent_directory,member))
        #sys.exit()

    data_in_tar = tardata.readlines()
    try:
        if data_in_tar[0][0] == "#":
            data_in_tar.pop(0)
    except:
        pass

    if member in ['evidence.dat','snr.txt']:
        data_from_tar = [ val.split() for val in data_in_tar ]

    if member in ['IFO0_asd.dat','IFO1_asd.dat', 'H1_timeInjection.dat',
            'L1_timeInjection.dat']:
        tmp = [ val.split() for val in data_in_tar ]
        data_from_tar = np.zeros(shape=(len(tmp),2))

        for i in xrange(len(data_from_tar)):
            data_from_tar[i,0] = tmp[i][0]
            data_from_tar[i,1] = tmp[i][1]

    if member in ['post/signal_whitened_moments.dat.0',
            'post/signal_whitened_moments.dat.1']:

        data_from_tar = [ val.split() for val in data_in_tar ]

        for i in xrange(1,len(data_from_tar)):
            data_from_tar[i] = [ float(val) for val in data_from_tar[i] ]


    if member in ['post/signal_recovered_whitened_waveform.dat.0',
            'post/signal_recovered_whitened_waveform.dat.1']:

        data_from_tar = [ val.split() for val in data_in_tar ]

        for i in xrange(len(data_from_tar)):
            data_from_tar[i] = [ float(val) for val in data_from_tar[i]]

    if member in ['post/injected_whitened_waveform.dat.0',
            'post/injected_whitened_waveform.dat.1']:

        data_from_tar = [ val.split() for val in data_in_tar ][0]
        data_from_tar = [ float(val) for val in data_from_tar ]

    return data_from_tar


def overlap(wave0,wave1,fmin=16,delta_t=1./1024,norm=True):

    wave0td = pycbc.types.TimeSeries(wave0, delta_t=delta_t)
    wave1td = pycbc.types.TimeSeries(wave1, delta_t=delta_t)

    overlap=pycbc.filter.overlap(wave0td, wave1td, low_frequency_cutoff=fmin,
            normalized=norm)

    return overlap

def whiten(wave, asdarray, delta_t=1./1024):

    wavetd = pycbc.types.TimeSeries(wave, delta_t=delta_t)
    wavefd = wavetd.to_frequencyseries()

    asd=pycbc.types.FrequencySeries(np.zeros(len(wavefd)),
          delta_f=wavefd.delta_f)

    idx = wavefd.sample_frequencies.data >= min(asdarray[:,0])
    asd.data[idx] = asdarray[:,1]
    asd.data[np.invert(idx)]=1.0

    wavefd_white = wavefd/asd

    return wavefd_white.to_timeseries()

def check_ball_size(listoballs):
    """
    reduce list-o-balls to those with non-zero size
    """
    return [val for val in listoballs if os.path.getsize(val)>0]


#
# Input
#

tarballs = glob.glob('bayeswave_*bz2')
print "Full list of balls is %d long"%len(tarballs)
tarballs = check_ball_size(tarballs)
print "Non-zero size balls is %d long"%len(tarballs)

ninj=len(tarballs)

outfile = os.path.basename(os.getcwd())

nmoments=10000
nreconstructions=100
moments_header="snr t_energy_rec hrss t0_rec dur_rec f0_rec band_rec overlap network_overlap h_max t_at_h_max"
moments_names=moments_header.split()

h1overlaps = np.zeros(shape=(ninj, nmoments))
l1overlaps = np.zeros(shape=(ninj, nmoments))
netoverlaps = np.zeros(shape=(ninj, nmoments))
# XXX: modify mynetoverlaps for multiple fmin
fmin=16.0
mynetoverlaps = np.zeros(shape=(ninj, nreconstructions))
myh1overlaps = np.zeros(shape=(ninj, nreconstructions))
myl1overlaps = np.zeros(shape=(ninj, nreconstructions))
netsnr = np.zeros(shape=ninj)
h1snr = np.zeros(shape=ninj)
l1snr = np.zeros(shape=ninj)
snrratio = np.zeros(shape=ninj) 
Zsignal = np.zeros(shape=(ninj,2))


for t,tarball in enumerate(tarballs):

    print "Extracting from %s [%d/%d]"%(tarball, t, len(tarballs))

    tar = tarfile.open(tarball, 'r:bz2')
    parent_directory = os.path.basename(tarball.replace('.tar.bz2',''))

    #
    # Retrieve data
    #


    try:
        evidence=extract(parent_directory, 'evidence.dat')
    except:
        print >> sys.stderr, "No evidence.dat"
        evidence = np.nan

    try:
        snr = extract(parent_directory, 'snr.txt')
    except:
        print >> sys.stderr, "No snr.txt"
        snr = [['H1',np.nan], ['L1',np.nan], ['Network', np.nan]]

    IFO0_signal_moments = extract(parent_directory,
            'post/signal_whitened_moments.dat.0')
    IFO1_signal_moments = extract(parent_directory,
            'post/signal_whitened_moments.dat.1')
    IFO0_whitened_signal = extract(parent_directory,
            'post/signal_recovered_whitened_waveform.dat.0')
    IFO1_whitened_signal = extract(parent_directory,
            'post/signal_recovered_whitened_waveform.dat.1')

    IFO0_whitened_injection = extract(parent_directory,
            'post/injected_whitened_waveform.dat.0')
    IFO1_whitened_injection = extract(parent_directory,
            'post/injected_whitened_waveform.dat.1')

    H1_timeInjection = extract(parent_directory, 'H1_timeInjection.dat')
    L1_timeInjection = extract(parent_directory, 'L1_timeInjection.dat')
    IFO0_ASD = extract(parent_directory, 'IFO0_asd.dat')
    IFO1_ASD = extract(parent_directory, 'IFO1_asd.dat')
#
#
    my_IFO0_whitened_injection = whiten(H1_timeInjection[:,1], IFO0_ASD)
    my_IFO1_whitened_injection = whiten(L1_timeInjection[:,1], IFO1_ASD)


    #
    # Injected SNR
    #
    h1snr[t] = float(snr[0][1])
    l1snr[t] = float(snr[1][1])
    snrratio[t] = max(h1snr[t]/l1snr[t], l1snr[t]/h1snr[t])
    netsnr[t] = float(snr[2][1])

    #
    # Evidence
    #
    Zsignal[t][0] = float(evidence[2][1])
    Zsignal[t][1] = float(evidence[2][2])

    #
    # Overlaps
    #
    h1overlaps[t,:] = [IFO0_signal_moments[j][moments_names.index("overlap")] for j in xrange(nmoments)]
    l1overlaps[t,:] = [IFO1_signal_moments[j][moments_names.index("overlap")] for j in xrange(nmoments)]
    netoverlaps[t,:] = [IFO1_signal_moments[j][moments_names.index("network_overlap")] for j in xrange(nmoments)]

    #
    # Manual calculation of network overlap (to facilitate different fmin)
    #
    for j in xrange(nreconstructions):
        # Loop over reconstructed waveforms


        ri =  overlap(IFO0_whitened_signal[j], IFO0_whitened_injection,
                fmin=fmin, norm=False) + overlap(IFO1_whitened_signal[j],
                        IFO1_whitened_injection, fmin=fmin, norm=False)

        ii =  overlap(IFO0_whitened_injection, IFO0_whitened_injection,
                fmin=fmin, norm=False) + overlap(IFO1_whitened_injection,
                        IFO1_whitened_injection, fmin=fmin, norm=False)

        rr =  overlap(IFO0_whitened_signal[j], IFO0_whitened_signal[j],
                fmin=fmin, norm=False) + overlap(IFO1_whitened_signal[j],
                        IFO1_whitened_signal[j], fmin=fmin, norm=False)

        mynetoverlaps[t,j] = ri / np.sqrt(ii*rr)

        myh1overlaps[t,j] = overlap(IFO0_whitened_signal[j],
                IFO0_whitened_injection, fmin=fmin, norm=True)
        myl1overlaps[t,j] = overlap(IFO0_whitened_signal[j],
                IFO1_whitened_injection, fmin=fmin, norm=True)

#    sys.exit()



#
# Now clean up and save the useful stuff
#
# This gives us almost all the characteristics we need to compare injection sets
np.savez(file=outfile, 
        netoverlaps    = netoverlaps,
        h1overlaps     = h1overlaps,
        l1overlaps     = l1overlaps,
        mynetoverlaps  = mynetoverlaps,
        myh1overlaps   = myh1overlaps,
        myl1overlaps   = myl1overlaps,
        netsnr         = netsnr,
        h1snr          = h1snr,
        l1snr          = l1snr,
        Zsignal        = Zsignal
        )




