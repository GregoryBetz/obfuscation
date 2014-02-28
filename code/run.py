#!/usr/bin/env sage -python

from __future__ import print_function

from branchingprogram import BranchingProgram, ParseException
from obfuscator import Obfuscator

from sage.all import *

import argparse, sys, time

def test_circuit(path):
    testcases = {}
    print('Testing %s: ' % path, end='')
    with open(path) as f:
        for line in f:
            if line.startswith('#'):
                if 'TEST' in line:
                    _, _, inp, outp = line.split()
                    testcases[inp] = int(outp)
            else:
                continue
    if len(testcases) == 0:
        print('no test cases')
        return
    try:
        bp = BranchingProgram(path, type='circuit')
    except ParseException as e:
        print(e)
        return
    bp.obliviate()
    bp.randomize()
    failed = False
    for k, v in testcases.items():
        if bp.evaluate(k) != v:
            print('\x1b[31mFail\x1b[0m (%s != %d) ' % (k, v), end='')
            failed = True
    if failed:
        print()
    else:
        print('\x1b[32mPass\x1b[0m')

def bp(args):
    testdir = 'circuits'
    if args.test is not None:
        test_circuit(args.test)
    if args.test_all:
        for circuit in os.listdir('circuits'):
            path = os.path.join(testdir, circuit)
            test_circuit(path)

def obf(args):
    start = time.time()
    obf = Obfuscator(args.secparam, verbose=args.verbose,
                     parallel=args.parallel, ncpus=args.ncpus)
    if args.load_obf is not None:
        print('Loading obfuscation from %s' % args.load_obf)
        obf.load_obf(args.load_obf)
    elif args.load_circuit is not None:
        print('Converting circuit -> bp...')
        bp = BranchingProgram(args.load_circuit, type='circuit')
        # bp.obliviate()
        bp.randomize()
        print('Obfuscating BP of length %d...' % len(bp))
        obf.load_bp(bp)
        obf.obfuscate()
    else:
        print('One of --load-obf or --load-circuit must be used!')
        sys.exit(1)
    if args.save is not None:
        print('Saving obfuscation to %s...' % args.save)
        obf.save(args.save)
    if args.eval is not None:
        print('Evaluating on input %s...' % args.eval)
        r = obf.evaluate(args.eval)
        print('Output = %d' % r)
    end = time.time()
    print('Total running time: %f seconds' % (end - start))

def main(argv):
    parser = argparse.ArgumentParser(
        description='Run indistinguishability obfuscator.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers()

    parser_obf = subparsers.add_parser(
        'obf', help='commands for obfuscating a circuit/branching program')
    parser_obf.add_argument('--ncpus', metavar='N', type=int, action='store',
                            default=sage.parallel.ncpus.ncpus(),
                            help='number of CPUs to use (only used when --parallel flag set)')
    parser_obf.add_argument('--eval', metavar='INPUT', type=str, action='store',
                            help='evaluate obfuscation on INPUT')
    parser_obf.add_argument('--load-obf', metavar='DIR', type=str, action='store',
                            help='load obfuscation from DIR')
    parser_obf.add_argument('--load-circuit', metavar='FILE', type=str, action='store',
                            help='load circuit from FILE and obfuscate')
    parser_obf.add_argument('--save', metavar='DIR', type=str, action='store',
                            help='save obfuscation to DIR')
    parser_obf.add_argument('--secparam', metavar='N', type=int,
                             action='store', default=8, help="security parameter")
    parser_obf.add_argument('-p', '--parallel', action='store_true',
                            help='use parallelization')
    parser_obf.add_argument('-v', '--verbose', action='store_true',
                            help='be verbose')
    parser_obf.set_defaults(func=obf)

    parser_bp = subparsers.add_parser(
        'bp', help='commands for circuit -> branching program conversion')
    parser_bp.add_argument('--test', metavar='FILE', type=str, action='store',
                           help='test FILE circuit -> bp conversion')
    parser_bp.add_argument('--test-all', action='store_true',
                           help='test circuit -> bp conversion')

    parser_bp.set_defaults(func=bp)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass