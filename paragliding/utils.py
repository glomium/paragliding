#!/usr/bin/python
# ex:set fileencoding=utf-8:

from __future__ import unicode_literals

import numpy as np
from math import factorial


def averages(data, N, f):
    """
    calculate averages with a weight function
    """

    if N < 2:
        return data

    if len(data) < N:
        N = len(data)

    weight = f(N)

    if len(weight) != N:
        print("ERROR")
        exit()

    averages = np.convolve(data, weight, "same")
    for i in range(0, N / 2):
        j = 2 * i + 1
        weight = f(j)
        averages[i] = np.sum(data[:j] * weight)
        averages[-i-1] = np.sum(data[-j:] * weight)

    return averages


def moving(N):
    return np.repeat(1.0, N)/N


def binom(N):
    return np.array([
        factorial(N-1) / factorial(i) / factorial(N-1-i) / 2.**(N-1) for i in range(N)
    ])
