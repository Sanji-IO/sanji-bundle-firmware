#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from mock import patch
from mock import MagicMock
from sanji.connection.mockup import Mockup
from sanji.message import Message

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    os.environ["PATH"] = os.path.dirname(os.path.realpath(__file__)) \
        + ":" + os.environ["PATH"]
    from firmware import Firmware
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
        self.name = "firmware"
        self.bundle = Firmware(connection=Mockup())
        self.bundle.publish = MagicMock()

    def tearDown(self):
        self.bundle.stop()
        self.bundle = None
        try:
            os.remove("%s/data/%s.json" % (dirpath, self.name))
        except OSError:
            pass

        try:
            os.remove("%s/data/%s.json.backup" % (dirpath, self.name))
        except OSError:
            pass

    def test__init__no_conf(self):
        """
        init: no configuration file
        """
        with self.assertRaises(IOError):
            with patch("firmware.ModelInitiator") as mock_modelinit:
                mock_modelinit.side_effect = IOError
                self.bundle.init()

    def test__run(self):
        """
        run: normal
        """
        self.bundle.run()

    def test__run__upgrading_success(self):
        """
        run: upgrading success
        """
        self.bundle.model.db["upgrading"] = 1
        self.bundle.run()

    def test__run__upgrading_failed(self):
        """
        run: upgrading failed
        """
        self.bundle.model.db["upgrading"] = -1
        self.bundle.run()

    def test__load__current_conf(self):
        """
        load: load current configuration
        """
        self.bundle.load(dirpath)
        self.assertEqual(self.bundle.model.db["server"], "factory")

    def test__load__backup_conf(self):
        """
        load: load backup configuration
        """
        os.remove("%s/data/%s.json" % (dirpath, self.name))
        self.bundle.load(dirpath)
        self.assertEqual(self.bundle.model.db["server"], "factory")

    def test__load__no_conf(self):
        """
        load: cannot load any configuration
        """
        with self.assertRaises(IOError):
            self.bundle.load("%s/mock" % dirpath)

    def test__save(self):
        """
        save: tested in init()
        """
        # Already tested in init()
        pass

    @patch("firmware.time.sleep")
    @patch("firmware.sh.sh")
    @patch("firmware.sh.reboot")
    def test__upgrade(self, mock_reboot, mock_upgrade, mock_sleep):
        """
        upgrade: success
        """
        mock_upgrade.return_value = 0

        self.bundle.upgrade()
        self.assertEqual(0, self.bundle.model.db["upgrading"])

    @patch("firmware.time.sleep")
    @patch("firmware.sh.sh")
    def test__upgrade__failed(self, mock_upgrade, mock_sleep):
        """
        upgrade: failed
        """
        mock_upgrade.return_value = 1
        mock_upgrade.side_effect = Exception("error")

        self.bundle.upgrade()
        self.assertEqual(-1, self.bundle.model.db["upgrading"])

    @patch("firmware.time.sleep")
    @patch("firmware.sh.setdef")
    @patch("firmware.sh.reboot")
    def test__setdef(self, mock_reboot, mock_setdef, mock_sleep):
        """
        setdef: success
        """
        self.bundle.setdef()
        self.assertEqual(0, self.bundle.model.db["defaulting"])

    @patch("firmware.time.sleep")
    @patch("firmware.sh.setdef")
    def test__setdef__failed(self, mock_setdef, mock_sleep):
        """
        setdef: failed
        """
        mock_setdef.side_effect = Exception("error")

        self.bundle.setdef()
        self.assertEqual(-1, self.bundle.model.db["defaulting"])

    def test__get(self):
        """
        get (/system/firmware)
        """
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("1.0.0", data["version"])
        self.bundle.get(message=message, response=resp, test=True)

    def test__put__no_data(self):
        """
        put (/system/firmware): no data attribute
        """
        msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware"
        }

        def resp(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        message = Message(msg)
        self.bundle.put(message, response=resp, test=True)

    def test__put__empty_data(self):
        """
        put (/system/firmware): data dict is empty
        """
        msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware"
        }

        def resp(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        msg["data"] = dict()
        message = Message(msg)
        self.bundle.put(message, response=resp, test=True)

    def test__put__no_flag(self):
        """
        put (/system/firmware): no reset/upgrade/server flag in data dict
        """
        msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware",
            "data": {
                "test": "test"
            }
        }

        def resp(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        message = Message(msg)
        self.bundle.put(message, response=resp, test=True)

    @patch.object(Firmware, 'setdef')
    def test__put__setdef(self, mock_sleep):
        """
        put (/system/firmware): reset to factory default
        """
        msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware",
            "data": {
                "reset": 1
            }
        }

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        message = Message(msg)
        self.bundle.put(message, response=resp, test=True)

    def test__put__update_server(self):
        """
        put (/system/firmware): update upgrading server
        """
        msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware",
            "data": {
                "server": "firmware.moxa.com"
            }
        }

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        message = Message(msg)
        self.bundle.put(message, response=resp, test=True)
        self.bundle.load(dirpath)
        self.assertEqual(self.bundle.model.db["server"], "firmware.moxa.com")

    @patch.object(Firmware, 'upgrade')
    def test__put__upgrade(self, mock_sleep):
        """
        put (/system/firmware): firmware upgrading
        """
        msg = {
            "id": 12345,
            "method": "put",
            "resource": "/system/firmware",
            "data": {
                "upgrade": 1
            }
        }

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        message = Message(msg)
        self.bundle.put(message, response=resp, test=True)


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Firmware Test")
    unittest.main()
