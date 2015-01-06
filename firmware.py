#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
# import shutil
import logging
import time
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator

import ezshell

# TODO: logger should be defined in sanji package?
logger = logging.getLogger()

path_root = os.path.abspath(os.path.dirname(__file__))

# Bundle"s profilefirmware
# TODO: add command to stop required services
profile = {
    "firmware_path": "/run/shm/LATEST_FIRMWARE",
    "firmware_version": "kversion | cut -d\" \" -f3",
    "set_factory_default": "setdef",
    "upgrade_firmware": path_root + "tools/upgrade.sh",
    "turn_off_readyled": "/etc/init.d/showreadyled stop",
    "stop_services": "",
    "reboot": "reboot"
}


class Firmware(Sanji):
    """
    A model to handle firmware upgrade and reset to factory default.

    Attributes:
        model: database with json format.
    """
    def init(self, *args, **kwargs):
        try:  # pragma: no cover
            self.bundle_env = kwargs["bundle_env"]
        except KeyError:
            self.bundle_env = os.getenv("BUNDLE_ENV", "debug")

        path_root = os.path.abspath(os.path.dirname(__file__))
        if self.bundle_env == "debug":  # pragma: no cover
            path_root = "%s/tests" % path_root
            profile["firmware_version"] = path_root + "/kversion.sh"
            profile["set_factory_default"] = path_root + "/setdef.sh 0"
            profile["upgrade_firmware"] = path_root + "/upgradehfm.sh 0"
            profile["reboot"] = path_root + "/reboot.sh 0"

        try:
            self.load(path_root)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

    def load(self, path):
        """
        Load the configuration. If configuration is not installed yet,
        initialise them with default value.

        Args:
            path: Path for the bundle, the configuration should be located
                under "data" directory.
        """
        self.model = ModelInitiator("firmware", path, backup_interval=-1)
        if None == self.model.db:
            raise IOError("Cannot load any configuration.")
        self.save()

    def save(self):
        """
        Save and backup the configuration.
        """
        self.model.save_db()
        self.model.backup_db()

    def upgrade(self):
        # TODO: backup the configuration for future restore
        # TODO: stop the services that may have side effect when upgrading
        # ret = ezshell.run(profile["stop_services"])

        # set flags to show the upgrading status
        self.model.db["upgrading"] = 1
        self.save()

        time.sleep(5)
        ret = ezshell.run(profile["upgrade_firmware"])
        ret.output()
        if ret.returncode() == 0:
            logger.info("Upgrading success, reboot now.")
            self.model.db["upgrading"] = 0
        else:
            logger.error("Upgrading failed, please check if the file is"
                         " correct.")
            self.model.db["upgrading"] = -1
        self.save()
        ezshell.run(profile["reboot"])

    def setdef(self):
        # TODO: stop the services that may have side effect when setdef
        # ret = ezshell.run(profile["stop_services"])
        self.model.db["defaulting"] = 1
        self.save()

        time.sleep(5)
        ret = ezshell.run(profile["set_factory_default"])
        ret.output()
        if ret.returncode() == 0:
            logger.info("Resetting to factory default success, reboot now.")
            self.model.db["defaulting"] = 0
        else:
            logger.error("Resetting failed.")
            self.model.db["defaulting"] = -1
        self.save()
        ezshell.run(profile["reboot"])

    @Route(methods="get", resource="/system/firmware")
    def get(self, message, response):
        """
        {
            "version": "1.0",
            "server": "www.moxa.com"
        }
        """
        ret = ezshell.run(profile["firmware_version"])
        self.model.db["version"] = ret.output()
        return response(data=self.model.db)

    @Route(methods="put", resource="/system/firmware")
    def put(self, message, response):
        """
        reset:
        {
            "reset": 1
        }

        upgrade:
        Only save the configuration if server updated.
        {
            "upgrade": 1,
            "server": "www.moxa.com"  (optional)
        }
        """
        # TODO: status code should be added into error message
        if not hasattr(message, "data") or \
                ("reset" not in message.data
                 and "upgrade" not in message.data
                 and "server" not in message.data):
            return response(code=400, data={"message": "Invalid Input."})

        # Resetting to factory default
        if "reset" in message.data and 1 == message.data["reset"]:
            response()
            self.setdef()
            return

        # Update the firmware upgrading server
        if "server" in message.data:
            self.model.db["server"] = message.data["server"]
            self.save()

        # Upgrading the firmware
        if "upgrade" in message.data and 1 == message.data["upgrade"]:
            response()
            self.upgrade()
            return

        return response()


if __name__ == "__main__":  # pragma: no cover
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Firmware")

    firmware = Firmware(connection=Mqtt())
    firmware.start()
