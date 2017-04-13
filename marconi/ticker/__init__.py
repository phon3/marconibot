# -*- coding: utf-8 -*-
# 3rd party
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
# local
from tools import MongoClient, Process, logging

logger = logging.getLogger(__name__)


class WAMPTicker(ApplicationSession):
    """ WAMP application - subscribes to the 'ticker' push api and saves pushed
    data into a mongodb """
    @inlineCallbacks
    def onJoin(self, details):
        # open/create poloniex database, ticker collection/table
        self.db = MongoClient().poloniex['markets']
        initTick = self.api.returnTicker()
        for market in initTick:
            initTick[market]['_id'] = market
            self.db.insert_one(initTick[market])
        yield self.subscribe(self.onTick, 'ticker')
        logger.info('Subscribed to Ticker')

    def onTick(self, *data):
        self.db.update_one(
            {"_id": data[0]},
            {"$set": {'last': data[1],
                      'lowestAsk': data[2],
                      'highestBid': data[3],
                      'percentChange': data[4],
                      'baseVolume': data[5],
                      'quoteVolume': data[6],
                      'isFrozen': data[7],
                      '24hrHigh': data[8],
                      '24hrLow': data[9]
                      }},
            upsert=True)

    def onDisconnect(self):
        # stop reactor if disconnected
        if reactor.running:
            reactor.stop()


class Ticker(object):

    def __init__(self, api):
        self._running = False
        # open/create poloniex database, ticker collection/table
        self.db = MongoClient().poloniex['ticker']
        self.app = WAMPTicker
        self.app.api = api
        # thread namespace
        self._appProcess = None
        self._appRunner = ApplicationRunner(
            u"wss://api.poloniex.com:443", u"realm1"
        )

    def __call__(self, market='USDT_BTC'):
        """ returns ticker from mongodb """
        return self.db.find_one({'_id': market})

    def start(self):
        """ Start WAMP application runner process """
        self._appProcess = Process(
            target=self._appRunner.run, args=(self.app,)
        )
        self._appProcess.daemon = True
        self._appProcess.start()
        self._running = True

    def stop(self):
        """ Stop WAMP application """
        try:
            self._appProcess.terminate()
        except:
            pass
        try:
            self._appProcess.join()
        except:
            pass
        self._running = False