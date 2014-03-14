#!/usr/bin/env sage -python

from __future__ import print_function

from gradedencoding import GradedEncoding
from branchingprogram import (BranchingProgram, MATRIX_LENGTH)
import utils, fastutils

from sage.all import (flatten, Integer, load, MatrixSpace, randint,
                      random_prime, vector, VectorSpace, ZZ)

import collections, os, sys, time

MS = MatrixSpace(ZZ, MATRIX_LENGTH)

def ms2list(m):
    '''Convert an element in MS to a flat integer list'''
    m = [[long(e) for e in row] for row in m]
    return [long(e) for e in flatten(m)]

ObfLayer = collections.namedtuple('ObfLayer', ['inp', 'zero', 'one'])

def load_layer(directory, inp, zero, one):
    inp = load('%s/%s' % (directory, inp))
    zero = load('%s/%s' % (directory, zero))
    one = load('%s/%s' % (directory, one))
    return ObfLayer(int(inp), zero, one)

def save_layer(layer, directory, idx):
    Integer(layer.inp).save('%s/%d.input' % (directory, idx))
    layer.zero.save('%s/%d.zero' % (directory, idx))
    layer.one.save('%s/%d.one' % (directory, idx))

class Obfuscator(object):

    def _set_params(self, kappa):
        self.kappa = kappa
        self.alpha = self.secparam
        self.beta = self.secparam
        self.rho = self.secparam
        self.rho_f = self.kappa * (self.rho + self.alpha + 2)
        self.eta = self.rho_f + self.alpha + 2 * self.beta + self.secparam + 8
        self.nu = self.eta - self.beta - self.rho_f - self.secparam - 3
        assert self.nu >= self.alpha + self.beta + 5
        # XXX: use smaller n value for now to speed things up
        self.n = self.eta
        # self.n = int(self.eta * math.log(self.secparam, 2))
        self._print_params()

    def _print_params(self):
        self.logger('Graded encoding parameters:')
        self.logger('  Lambda: %d' % self.secparam)
        self.logger('  Kappa: %d' % self.kappa)
        self.logger('  Alpha: %d' % self.alpha)
        self.logger('  Beta: %d' % self.beta)
        self.logger('  Eta: %d' % self.eta)
        self.logger('  Nu: %d' % self.nu)
        self.logger('  Rho: %d' % self.rho)
        self.logger('  Rho_f: %d' % self.rho_f)
        self.logger('  N: %d' % self.n)
    
    def __init__(self, secparam, verbose=False):
        self.secparam = secparam
        self.obfuscation = None
        self._verbose = verbose
        self.logger = utils.make_logger(self._verbose)
        self.logger('Obfuscation parameters:')
        self.logger('  Security Parameter: %d' % self.secparam)

    def save(self, directory):
        assert self.obfuscation is not None
        if not os.path.exists(directory):
            os.mkdir(directory)
        Integer(self.x0).save('%s/x0' % directory)
        Integer(self.pzt).save('%s/pzt' % directory)
        Integer(self.p_enc).save('%s/p_enc' % directory)
        vector(self.s_enc).save('%s/s_enc' % directory)
        vector(self.t_enc).save('%s/t_enc' % directory)
        for idx, layer in enumerate(self.obfuscation):
            save_layer(layer, directory, idx)

    def load(self, directory):
        assert self.obfuscation is None
        x0 = load('%s/x0.sobj' % directory)
        pzt = load('%s/pzt.sobj' % directory)
        files = os.listdir(directory)
        inputs = sorted(filter(lambda s: 'input' in s, files))
        zeros = sorted(filter(lambda s: 'zero' in s, files))
        ones = sorted(filter(lambda s: 'one' in s, files))
        self.obfuscation = [load_layer(directory, inp, zero, one) for inp, zero,
                            one in zip(inputs, zeros, ones)]
        self._set_params(len(self.obfuscation))
        fastutils.loadparams(long(x0), long(pzt))

    def _set_straddling_sets(self, bp):
        # REFACTOR: Ugly, ugly code...
        inpdir = {}
        for layer in bp:
            if layer.inp not in inpdir:
                inpdir[layer.inp] = [layer]
            else:
                inpdir[layer.inp].append(layer)
        last = 0
        for _, v in inpdir.iteritems():
            if len(v) == 1:
                layer = v[0]
                layer.zeroset = set({last})
                layer.oneset = set({last})
                last = last + 1
            else:
                for idx, layer in enumerate(v):
                    if idx == 0:
                        layer.zeroset = set({last})
                        layer.oneset = set({last, last + 1})
                        last = last + 2
                    elif idx == len(v) - 1:
                        layer.zeroset = set({last - 1, last})
                        layer.oneset = set({last})
                        last = last + 1
                    else:
                        layer.zeroset = set({last - 1, last})
                        layer.oneset = set({last, last + 1})
                        last = last + 2
        return last

    def _construct_bookend_vectors(self, bp, p, sidx, tidx):
        VSZp = VectorSpace(ZZ.residue_field(ZZ.ideal(p)), MATRIX_LENGTH)
        s = VSZp.random_element()
        t = VSZp.random_element()
        p = s * t
        penc = fastutils.encode_scalar(long(p), self.rho, sidx, tidx);
        s = s * bp.m0i
        t = bp.m0 * t
        senc = fastutils.encode_vector([long(i) for i in s], self.rho, sidx)
        tenc = fastutils.encode_vector([long(i) for i in t], self.rho, tidx)
        self.s, self.t = s, t
        self.p = p
        return senc, tenc, penc

    def _obfuscate_layer(self, layer):
        self.logger('Obfuscating layer...')
        start = time.time()
        m = ms2list(layer.zero)
        m.extend(ms2list(layer.one))
        half = len(m) / 2
        es = fastutils.encode_layer(m, self.rho, list(layer.zeroset),
                                    list(layer.oneset))
        zero, one = MS(es[:half]), MS(es[half:])
        end = time.time()
        self.logger('Took: %f seconds' % (end - start))
        return ObfLayer(layer.inp, zero, one)

    def obfuscate(self, bp):
        self._set_params(len(bp))
        # set prime to encode under
        p = long(bp.rprime if bp.rprime else random_prime((1 << self.secparam) - 1))

        nzs = self._set_straddling_sets(bp)
        # take bookend vectors into account
        nzs = nzs + 2
        print('Number of Zs: %d' % nzs)

        self.logger('Generating MLM parameters...')
        start = time.time()
        self.x0, self.pzt = fastutils.genparams(self.n, self.alpha, self.beta,
                                                self.eta, self.kappa, nzs, p)
        end = time.time()
        self.logger('Took: %f seconds' % (end - start))

        self.logger('Constructing bookend vectors...')
        start = time.time()
        self.s_enc, self.t_enc, self.p_enc \
            = self._construct_bookend_vectors(bp, p, nzs - 2, nzs - 1)
        end = time.time()
        self.logger('Took: %f seconds' % (end - start))

        self.logger('Obfuscating...')
        start = time.time()
        self.obfuscation = [self._obfuscate_layer(layer) for layer in bp]
        end = time.time()
        self.logger('Obfuscation took: %f seconds' % (end - start))
        self._bp = bp

    def _is_zero(self, c):
        return fastutils.is_zero(long(c), self.nu)
        
    def evaluate(self, inp):
        assert self.obfuscation is not None

        print("INPUT:", inp)
        comp = self._bp._group.one()
        for m in self._bp:
            comp = comp * (m.zero if inp[m.inp] == '0' else m.one)
        p = vector(self.s) * comp * vector(self.t)
        other = self.p
        print("OUTPUT:", p - other)

        comp = MS.identity_matrix()
        for m in self.obfuscation:
            comp = comp * (m.zero if inp[m.inp] == '0' else m.one)
        p = vector(self.s_enc) * comp * vector(self.t_enc)
        other = self.p_enc
        for m in self._bp:
            print(m.zeroset, m.oneset)
            if len(m.zeroset) == 1:
                idx1 = list(m.zeroset)[0]
                idx2 = -1
            else:
                idx1 = list(m.zeroset)[0]
                idx2 = list(m.zeroset)[1]
            other = other * fastutils.encode_scalar(long(1), self.rho, idx1, idx2)
        return not (self._is_zero(p - other) or self._is_zero(other - p))
        # if self._is_zero(comp[0][1]) and self._is_zero(comp[1][0]):
        #     return 0
        # else:
        #     return 1
