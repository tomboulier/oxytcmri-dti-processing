#!/usr/bin/env python

import argparse

from external_scripts.compute_normal_values_center import compute_normal_values


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
