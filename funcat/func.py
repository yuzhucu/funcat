#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy as np
import talib

from .utils import FormulaException, rolling_window, handle_numpy_warning
from .time_series import (
    PriceSeries,
    NumericSeries,
    BoolSeries,
    fit_series,
    get_series,
    get_bars,
    ensure_timeseries,
)


class OneArgumentSeries(NumericSeries):
    func = talib.MA

    def __init__(self, series, arg):
        if isinstance(series, NumericSeries):
            series = series.series

            try:
                series[series == np.inf] = np.nan
                series = self.func(series, arg)
            except Exception as e:
                raise FormulaException(e)
        super(OneArgumentSeries, self).__init__(series)
        self.extra_create_kwargs["arg"] = arg


class MovingAverageSeries(OneArgumentSeries):
    """http://www.tadoc.org/indicator/MA.htm"""
    func = talib.MA


class WeightedMovingAverageSeries(OneArgumentSeries):
    """http://www.tadoc.org/indicator/WMA.htm"""
    func = talib.WMA


class ExponentialMovingAverageSeries(OneArgumentSeries):
    """http://www.fmlabs.com/reference/default.htm?url=ExpMA.htm"""
    func = talib.EMA


class SumSeries(NumericSeries):
    """求和"""
    def __init__(self, series, period):
        if isinstance(series, NumericSeries):
            series = series.series
            try:
                series[series == np.inf] = 0
                series[series == -np.inf] = 0
                series = talib.SUM(series, period)
            except Exception as e:
                raise FormulaException(e)
        super(SumSeries, self).__init__(series)
        self.extra_create_kwargs["period"] = period


class AbsSeries(NumericSeries):
    def __init__(self, series):
        if isinstance(series, NumericSeries):
            series = series.series
            try:
                series[series == np.inf] = 0
                series[series == -np.inf] = 0
                series = np.abs(series)
            except Exception as e:
                raise FormulaException(e)
        super(AbsSeries, self).__init__(series)


@handle_numpy_warning
def CrossOver(s1, s2):
    """s1金叉s2
    :param s1:
    :param s2:
    :returns: bool序列
    :rtype: BoolSeries
    """
    s1, s2 = ensure_timeseries(s1), ensure_timeseries(s2)
    series1, series2 = fit_series(s1.series, s2.series)
    cond1 = series1 > series2
    series1, series2 = fit_series(s1[1].series, s2[1].series)
    cond2 = series1 <= series2  # s1[1].series <= s2[1].series
    cond1, cond2 = fit_series(cond1, cond2)
    s = cond1 & cond2
    return BoolSeries(s)


def Ref(s1, n):
    return s1[n]


@handle_numpy_warning
def minimum(s1, s2):
    if len(s1) == 0 or len(s2) == 0:
        raise FormulaException("minimum size == 0")
    s1, s2 = ensure_timeseries(s1), ensure_timeseries(s2)
    series1, series2 = fit_series(s1.series, s2.series)
    s = np.minimum(series1, series2)
    return NumericSeries(s)


@handle_numpy_warning
def maximum(s1, s2):
    if len(s1) == 0 or len(s2) == 0:
        raise FormulaException("maximum size == 0")
    s1, s2 = ensure_timeseries(s1), ensure_timeseries(s2)
    series1, series2 = fit_series(s1.series, s2.series)
    s = np.maximum(series1, series2)
    return NumericSeries(s)


@handle_numpy_warning
def count(cond, n):
    # TODO lazy compute
    series = cond.series
    size = len(cond.series) - n
    try:
        result = np.full(size, 0, dtype=np.int)
    except ValueError as e:
        raise FormulaException(e)
    for i in range(size - 1, 0, -1):
        s = series[-n:]
        result[i] = len(s[s == True])
        series = series[:-1]
    return NumericSeries(result)


@handle_numpy_warning
def every(cond, n):
    return count(cond, n) == n


@handle_numpy_warning
def hhv(s, n):
    # TODO lazy compute
    series = s.series
    size = len(s.series) - n
    try:
        result = np.full(size, 0, dtype=np.float64)
    except ValueError as e:
        raise FormulaException(e)

    result = np.max(rolling_window(series, n), 1)

    return NumericSeries(result)


@handle_numpy_warning
def llv(s, n):
    # TODO lazy compute
    series = s.series
    size = len(s.series) - n
    try:
        result = np.full(size, 0, dtype=np.float64)
    except ValueError as e:
        raise FormulaException(e)

    result = np.min(rolling_window(series, n), 1)

    return NumericSeries(result)


@handle_numpy_warning
def iif(condition, true_statement, false_statement):
    series1 = get_series(true_statement)
    series2 = get_series(false_statement)
    series1, series2 = fit_series(series1, series2)
    cond_series = condition.series[-len(series1):]

    series = series2.copy()
    series[cond_series] = series1[cond_series]

    return NumericSeries(series)


class MACDSeries(PriceSeries):
    def __init__(self, fastperiod=12, slowperiod=26, signalperiod=9, series=None, dynamic_update=False):
        super(MACDSeries, self).__init__(series, dynamic_update=dynamic_update)
        self.extra_create_kwargs.update({
            "fastperiod": fastperiod,
            "slowperiod": slowperiod,
            "signalperiod": signalperiod,
        })

    def __call__(self, fastperiod=12, slowperiod=26, signalperiod=9):
        return MACDSeries(fastperiod, slowperiod, signalperiod, dynamic_update=True)

    def _ensure_series_update(self):
        if self._dynamic_update:
            bars = get_bars()
            if len(bars) > 0:
                close_arr = bars["close"]
                DIF, DEM, OSC = talib.MACD(
                    close_arr, **self.extra_create_kwargs)
                OSC *= 2
                self._series = OSC
            else:
                self._series = bars
