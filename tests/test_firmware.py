#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import shutil
import logging
import unittest
from mock import patch

from sanji.connection.mockup import Mockup
from sanji.message import Message

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    from firmware import Firmware
    from firmware import profile
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + "/../"
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger()


class TestFirmwareClass(unittest.TestCase):

    def setUp(self):
        profile["data"] = dirpath + "/mockdata/data.json.hide"
        profile["backup"] = dirpath + "/mockdata/data.bak.json.hide"
        profile["factory"] = dirpath + "/mockdata/factory.json"
        self.firmware = Firmware(connection=Mockup())
        self.assertEqual(self.firmware.data["server"], "factory")

    def tearDown(self):
        self.firmware.stop()
        self.firmware = None

    def test_init(self):
        # case: no configuration and exit
        profile["factory"] = dirpath + "/mockdata/factory.json.hide"
        with self.assertRaises(IOError):
            self.firmware.init()

    def test_load(self):
        profile["data"] = dirpath + "/mockdata/data.json"
        profile["backup"] = dirpath + "/mockdata/data.bak.json"
        profile["factory"] = dirpath + "/mockdata/factory.json"

        # case 1: load configuration
        self.firmware.load()
        self.assertEqual(self.firmware.data["server"], "data")

        # case 2: load backup configuration
        profile["data"] = dirpath + "/mockdata/data.json.hide"
        self.firmware.load()
        self.assertEqual(self.firmware.data["server"], "backup")

        # case 3: load factory configuration
        profile["backup"] = \
            dirpath + "/mockdata/data.bak.json.hide"
        self.firmware.load()
        self.assertEqual(self.firmware.data["server"], "factory")

        # case 4: no configuration
        profile["factory"] = \
            dirpath + "/mockdata/factory.json.hide"
        with self.assertRaises(IOError):
            self.firmware.load()

    def test_save(self):
        # case 1: save configuration
        profile["data"] = dirpath + "/mockdata/data.save.json"
        profile["backup"] = dirpath + "/mockdata/data.bak.save.json"
        shutil.copyfile(dirpath + "/mockdata/data.json", profile["data"])
        self.firmware.load()
        self.firmware.data["server"] = "save"
        self.firmware.save()
        self.firmware.load()
        self.assertEqual(self.firmware.data["server"], "save")
        self.assertTrue(os.path.isfile(profile["backup"]))

        # case 2: failed to save configuration
        with self.assertRaises(IOError):
            with patch("firmware.json.dump") as mock_dump:
                mock_dump.side_effect = IOError
                mock_dump.assert_has_calls(self.firmware.save())

        # case 3: failed to backup configuration
        with self.assertRaises(IOError):
            with patch("firmware.shutil.copyfile") as mock_copyfile:
                mock_copyfile.side_effect = IOError
                mock_copyfile.assert_has_calls(self.firmware.save())

        os.remove(profile["data"])
        os.remove(profile["backup"])

    def test_get(self):
        profile["firmware_version"] = dirpath + "/kversion.sh"
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("1.0", data["version"])
        self.firmware.get(message=message, response=resp, test=True)

    @patch("firmware.time.sleep")
    def test_put(self, mock_sleep):
        profile["reboot"] = dirpath + "/reboot.sh 0"
        profile["set_factory_default"] = dirpath + "/setdef.sh 0"
        profile["upgrade_firmware"] = dirpath + "/upgradehfm.sh 0"
        test_msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware"
        }

        # case 1: no data attribute
        def resp1(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        message = Message(test_msg)
        self.firmware.put(message, response=resp1, test=True)

        # case 2: data dict is empty or no reset/upgrade/server exist
        def resp2(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        test_msg["data"] = dict()
        message = Message(test_msg)
        self.firmware.put(message, response=resp2, test=True)

        test_msg["data"]["test"] = "test"
        message = Message(test_msg)
        self.firmware.put(message, response=resp2, test=True)
        test_msg["data"].pop("test", None)

        # case 3: resetting to factory default
        def resp3(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"]["reset"] = 1
        message = Message(test_msg)
        self.firmware.put(message, response=resp3, test=True)
        test_msg["data"].pop("reset", None)

        # case 4: updating firmware upgrading "server"
        profile["data"] = dirpath + "/mockdata/data.put.json"
        profile["backup"] = dirpath + "/mockdata/data.bak.put.json"

        def resp4(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"]["server"] = "firmware.moxa.com"
        message = Message(test_msg)
        self.firmware.put(message, response=resp4, test=True)
        self.firmware.load()
        self.assertEqual(self.firmware.data["server"], "firmware.moxa.com")
        os.remove(profile["data"])
        os.remove(profile["backup"])
        test_msg["data"].pop("server", None)

        # case 5: upgrading the firmware
        def resp5(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"]["upgrade"] = 1
        message = Message(test_msg)
        self.firmware.put(message, response=resp5, test=True)

    @patch("firmware.time.sleep")
    def test_upgrade(self, mock_sleep):
        profile["reboot"] = dirpath + "/reboot.sh 0"

        # case 1: upgrading success
        profile["upgrade_firmware"] = dirpath + "/upgradehfm.sh 0"
        self.firmware.upgrade()

        # case 2: upgrading failed
        profile["upgrade_firmware"] = dirpath + "/upgradehfm.sh 1"
        self.firmware.upgrade()

    @patch("firmware.time.sleep")
    def test_setdef(self, mock_sleep):
        profile["reboot"] = dirpath + "/reboot.sh"

        # case 1: setdef success
        profile["set_factory_default"] = dirpath + "/setdef.sh 0"
        self.firmware.setdef()

        # case 2: setdef failed
        profile["set_factory_default"] = dirpath + "/setdef.sh 1"
        self.firmware.setdef()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Firmware Test")
    unittest.main()
