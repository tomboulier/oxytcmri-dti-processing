#!/usr/bin/env python

import os
import sys
import argparse

import nibabel as nib
import numpy as np
import pickle
import csv

import scipy
from scipy import stats


def parseargs():
    """ parse ArgumentParser
        """
    parser = argparse.ArgumentParser(description='calculate stuff')


    parser.add_argument('-i', help='in', required=True, type=str)
    parser.add_argument('-a', help='in', required=True, type=str)
    parser.add_argument('-o', help='img', required=True, type=str)
    parser.add_argument('-p', help='pkl', required=True, type=str)
    parser.add_argument('-m', help='mode: percentile, mean or iqr', required=False, default='mean', type=str)
    parser.add_argument('-devcyto', help='nb of deviations to compute outliers for cyto lesions', required=False, default=2, type=float)
    parser.add_argument('-devvaso', help='nb of deviations to compute outliers for vaso lesions', required=False, default=2, type=float)

    #parser.add_argument('-a', help='Atlas', required=True, type=str)
    #parser.add_argument('-m', help='Mean', required=False, action='store_true')
    #parser.add_argument('-s', help='Std Dev', required=False, action='store_true')
    #parser.add_argument('-min', help='Min', required=False, action='store_true')
    #parser.add_argument('-max', help='Max', required=False, action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    args = parseargs()
    print(args)
    # Sanity check
    #if not os.path.exists(args.i):
    #    print("Error: Input file is missing")
    #    sys.exit(-1)


    #img = nib.load(args.i)

    parameters = pickle.load(open(args.p, "rb"))
    #print(parameters)
    img = nib.load(args.i)
    dataimg = img.get_fdata()
    datatls = nib.load(args.a).get_fdata().astype(int)

    labels = np.unique(datatls)
    outimg = np.zeros(dataimg.shape)

    for label in labels:
        if label > 0 and label in parameters:
            if args.m == 'mean':
                thr = parameters[label]['mean'] + parameters[label]['std'] * args.devvaso
            elif args.m == 'percentile':
                thr = parameters[label]['pmax']
            elif args.m == 'iqr':
                thr = parameters[label]['75']  + (parameters[label]['iqr'] * args.devvaso)
            whr = np.logical_and(datatls == label, dataimg > thr)
            outimg[whr] = 1
            if args.m == 'mean':
                thr = parameters[label]['mean'] - parameters[label]['std'] * args.devcyto
            elif args.m == 'percentile':
                thr = parameters[label]['pmin']
            elif args.m == 'iqr':
                thr = parameters[label]['25'] - (parameters[label]['iqr'] * args.devcyto)

            whr = np.logical_and(datatls == label, dataimg < thr)
            outimg[whr] = 2
            #print(label, thr, np.sum([dataimg[datatls == label] > thr]), np.sum(outimg))

    out = nib.Nifti1Image(outimg, affine=img.affine, header=img.header)
    nib.save(out, args.o)
