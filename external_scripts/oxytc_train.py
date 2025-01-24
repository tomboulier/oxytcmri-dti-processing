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


def compute_normal_values(image_file, atlas_file, output_csv, output_pkl, pmin=None, pmax=None):
    dataimg = nib.load(image_file).get_fdata()
    datatls = nib.load(atlas_file).get_fdata().astype(int)

    print(dataimg.shape, datatls.shape)
    if dataimg.shape != datatls.shape:
        raise ValueError(f"Image and atlas shapes do not match. "
                         f"Image shape: {dataimg.shape}, Atlas: {datatls.shape}. "
                         f"Image file: {image_file}, Atlas file: {atlas_file}")

    labels = np.unique(datatls)
    results = {}
    for label in labels:
        # if label in results:
        results[label] = {'mean': dataimg[datatls == label].mean(),
                          'std': dataimg[datatls == label].std()}
        if pmin and pmax:
            percentilemin, percentilemax = np.percentile(dataimg[datatls == label], [pmin, pmax])
            results[label]['pmin'] = percentilemin
            results[label]['pmax'] = percentilemax

        quartile_1, quartile_3 = np.percentile(dataimg[datatls == label], [25, 75])
        iqr = quartile_3 - quartile_1
        results[label]['25'] = quartile_1
        results[label]['75'] = quartile_3
        results[label]['iqr'] = iqr

    pickle.dump(results, open(output_pkl, "wb"))
    with open(output_csv, 'w') as f:
        w = csv.writer(f)
        w.writerow(results.keys())
        w.writerow([x['mean'] for x in results.values()])
        w.writerow([x['std'] for x in results.values()])
        w.writerow([x['25'] for x in results.values()])
        w.writerow([x['75'] for x in results.values()])
        w.writerow([x['iqr'] for x in results.values()])
        if pmin and pmax:
            w.writerow([x['pmin'] for x in results.values()])
            w.writerow([x['pmax'] for x in results.values()])

    print(f"Results saved to {output_csv} and {output_pkl}")

    # img = nib.load(args.i)
    # lab = nib.load(args.l)

    # image_data = img.get_data()
    #

    # if args.m:
    #    print(np.mean(image_data[label_data]))

    # if args.s:
    #    print(np.std(image_data[label_data]))

    # if args.min:
    #    print(np.min(image_data[label_data]))

    # if args.max:
    #    print(np.max(image_data[label_data]))


def parseargs():
    """ parse ArgumentParser
        """
    parser = argparse.ArgumentParser(description='calculate stuff')

    parser.add_argument('--i', action='append',
                        default=[],
                        help='Image Files')

    parser.add_argument('--a', action='append',
                        default=[],
                        help='Image Files')

    parser.add_argument('-ocsv', help='csv', required=True, type=str)
    parser.add_argument('-opkl', help='pkl', required=True, type=str)
    parser.add_argument('-pmin', help='percentile min', required=False, default=None, type=float)
    parser.add_argument('-pmax', help='percentile max', required=False, default=None, type=float)

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

    compute_normal_values(args.i, args.a, args.ocsv, args.opkl, args.pmin, args.pmax)
