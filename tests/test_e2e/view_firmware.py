#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from time import sleep

from sanji.core import Sanji
from sanji.connection.mqtt import Mqtt


REQ_RESOURCE = "/system/firmware"


class View(Sanji):

    # This function will be executed after registered.
    def run(self):

        for count in xrange(0, 100, 1):
            # Normal CRUD Operation
            #   self.publish.[get, put, delete, post](...)
            # One-to-One Messaging
            #   self.publish.direct.[get, put, delete, post](...)
            #   (if block=True return Message, else return mqtt mid number)
            # Agruments
            #   (resource[, data=None, block=True, timeout=60])

            # case 1: test GET
            print "GET %s" % REQ_RESOURCE
            res = self.publish.get(REQ_RESOURCE)
            if res.code != 200:
                print "GET is supported, code 200 is expected"
                print res.to_json()
                self.stop()

            # case 2: test PUT with no data
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, None)
            if res.code != 400:
                print "data is required, code 400 is expected"
                print res.to_json()
                self.stop()

            # case 3: test PUT with empty data (no required attributes)
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={})
            if res.code != 400:
                print "data.reset, data.server, or data.upgrade is required," \
                      " code 400 is expected"
                print res.to_json()
                self.stop()

            # case 4: test PUT with reset=0
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"reset": 0})
            if res.code != 200:
                print "data.reset=0 should reply code 200"
                print res.to_json()
                self.stop()

            # case 5: test PUT with reset=1 (setdef)
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"reset": 1})
            if res.code != 200:
                print "data.reset=1 should reply code 200 and cause setdef"
                print res.to_json()

            # case 6: test PUT with server="something"
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE,
                                   data={"server": "test.server"})
            if res.code != 200:
                print "data.reset=0 should reply code 200"
                print res.to_json()
                self.stop()

            print "GET %s" % REQ_RESOURCE
            res = self.publish.get(REQ_RESOURCE)
            if res.code != 200:
                print "GET is supported, code 200 is expected"
                print res.to_json()
                self.stop()
            elif "test.server" != res.data["server"]:
                print "PUT failed, server (%s) should be \"test.server\"" \
                      % res.data["server"]
                self.stop()

            # case 7: test PUT with upgrade=0
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"upgrade": 0})
            if res.code != 200:
                print "data.upgrade=0 should reply code 200"
                print res.to_json()
                self.stop()

            # case 8: test PUT with upgrade=1 (upgradehfm)
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"upgrade": 1})
            if res.code != 200:
                print "data.upgrade=1 should reply code 200 and cause" \
                      "upgradehfm"
                print res.to_json()

            # stop the test view
            self.stop()


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Firmware")

    view = View(connection=Mqtt())
    view.start()
