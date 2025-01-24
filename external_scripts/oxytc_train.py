#!/usr/bin/env python

import argparse

import nibabel as nib
import numpy as np
import pickle
import csv


def compute_normal_values(image_files, atlas_files, output_csv, output_pkl, pmin=None, pmax=None):
    dataimg = []
    datatls = []
    for im in image_files:
        dataimg.append(nib.load(im).get_fdata())
    for im in atlas_files:
        datatls.append(nib.load(im).get_fdata().astype(int))

    dataimg = np.array(dataimg)
    datatls = np.array(datatls)

    if dataimg.shape != datatls.shape:
        raise ValueError(f"Image and atlas shapes do not match. "
                         f"Image shape: {dataimg.shape}, Atlas: {datatls.shape}. "
                         f"Image file: {image_files}, Atlas file: {atlas_files}")

    labels = np.unique(datatls)
    results = {}
    for label in labels:
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


def parseargs():
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

    return parser.parse_args()


if __name__ == '__main__':
    args = parseargs()
    print(args)

    compute_normal_values(args.i, args.a, args.ocsv, args.opkl, args.pmin, args.pmax)
