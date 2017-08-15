# -*- coding: utf-8 -*-
#
#    BTC: 13MXa7EdMYaXaQK6cDHqd4dwr2stBK3ESE
#    LTC: LfxwJHNCjDh2qyJdfu22rBFi2Eu8BjQdxj
#
#    https://github.com/s4w3d0ff/marconibot
#
#    Copyright (C) 2017  https://github.com/s4w3d0ff
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn import preprocessing
from .. import logging, pd, np, time, pickle, shuffleDataFrame


logger = logging.getLogger(__name__)


def customLabels(df, bbLimit=False, rsiLimit=False, pchThreshold=False):
    df['future'] = df['percentChange'].shift(-1)

    def _bbrsiLabels(candle, bbLimit, rsiLimit, pchThreshold):
        score = 0
        if bbLimit:
            bbval = candle['bbpercent']
            if bbval > bbLimit:
                score += -1
            if bbval < -bbLimit:
                score += 1

        if rsiLimit:
            rsi = candle['rsi'] - 50
            if rsi > rsiLimit:
                score += -1
            if rsi < -rsiLimit:
                score += 1

        if pchThreshold:
            fpch = candle['future']
            if fpch > pchThreshold:
                score += 2
            if fpch < -pchThreshold:
                score += -2

        return score

    return df.apply(_bbrsiLabels, axis=1, bbLimit=bbLimit,
                    rsiLimit=rsiLimit, pchThreshold=pchThreshold)


def prepDataframe(df):
    # make infinity nan
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    # drop nan
    return df.dropna()


def splitTrainTestData(df, size=1):
    # split db
    return df.iloc[:-size], df.tail(size)


class Brain(object):

    def __init__(self, lobes=False):
        self._lobes = lobes
        if not self._lobes:
            self._lobes = {'rf': RandomForestClassifier(n_estimators=7,
                                                        random_state=666),
                           'dt': DecisionTreeClassifier()
                           }
        self.votingLobe = VotingClassifier(
            estimators=[(lobe, self._lobes[lobe]) for lobe in self._lobes],
            voting='hard',
            n_jobs=-1)

    def train(self, df, labels='label', split=False):
        # prep df, remove nan
        df = prepDataframe(df)
        # split if needed
        if split:
            df, tdf = splitTrainTestData(df, split)
        # shuffle data for good luck
        df = shuffleDataFrame(df)
        # scale train data and fit lobe
        x = df.drop(labels, axis=1).values
        #x = preprocessing.scale(x)
        logger.info('%d samples to train', len(x))
        self.votingLobe.fit(x, df[labels].values)
        if split:
            return tdf

    def predict(self, X):
        return self.votingLobe.predict(X)

    def score(self, X, y):
        return self.votingLobe.score(X, y)
