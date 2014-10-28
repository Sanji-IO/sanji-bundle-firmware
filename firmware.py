#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import shutil
import logging
import json
import time
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt

import ezshell

# TODO: logger should be defined in sanji package?
logger = logging.getLogger()

path_root = os.path.abspath(os.path.dirname(__file__))

# Bundle"s profilefirmware
# TODO: add command to stop required services
profile = {
    "data": path_root + "/data/data.json",
    "backup": path_root + "/data/data.bak.json",
    "factory": path_root + "/data/factory.json",
    "firmware_path": "/run/shm/LATEST_FIRMWARE",
    "firmware_version": "kversion | cut -d\" \" -f3",
    "set_factory_default": "setdef",
    "upgrade_firmware": path_root + "tools/upgrade.sh",
    "turn_off_readyled": "/etc/init.d/showreadyled stop",
    "stop_services": "",
    "reboot": "reboot"
}


class Firmware(Sanji):

    def init(self, *args, **kwargs):
        try:
            bundle_env = kwargs["bundle_env"]
        except KeyError:
            bundle_env = os.getenv("BUNDLE_ENV", "debug")

        if "debug" == bundle_env:  # pragma: no cover
            profile["firmware_version"] = path_root + "/tests/kversion.sh"
            profile["set_factory_default"] = path_root + "/tests/setdef.sh 0"
            profile["upgrade_firmware"] = path_root + "/tests/upgradehfm.sh 0"
            profile["reboot"] = path_root + "/tests/reboot.sh 0"

        # TODO: using modelinitiator instead
        self.data = dict()
        try:
            self.load()
        except Exception, e:
            logger.error("Please reinstall the package: %s", e)
            self.stop()
            raise IOError("Please reinstall the package: %s", e)

    def before_stop(self):
        pass

    def load(self):
        """
        Load the configuration, try to load the backup one or factory
        settings if failed.
        """
        try:
            logger.info("file: %s" % profile["data"])
            with open(profile["data"]) as jfile:
                self.data = json.load(jfile)
            return
        except:  # pragma: no cover
            pass  # fallback to backup configuration

        try:
            logger.error("Failed to load current configuration, load "
                         "previous one.")
            with open(profile["backup"]) as jfile:
                self.data = json.load(jfile)
            return
        except:  # pragma: no cover
            pass  # fallback to factory configuration

        try:
            logger.info("Load factory configuration. %s" % profile["factory"])
            with open(profile["factory"]) as jfile:
                self.data = json.load(jfile)
        except:
            raise IOError("Cannot load any configuration.")

    def save(self):
        """
        Save the configuration and make a backup.
        """
        try:
            with open(profile["data"], "w") as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
        except Exception, e:
            logger.error("Cannot save the configuration: %s." % e)
            raise IOError("Failed to save the configuration.")

        try:
            shutil.copyfile(profile["data"], profile["backup"])
        except Exception, e:
            logger.error("Cannot backup the configuration: %s." % e)
            raise IOError("Failed to backup the configuration.")

    @Route(methods="get", resource="/system/firmware")
    def get(self, message, response):
        """
        {
            "version": "1.0",
            "server": "www.moxa.com"
        }
        """
        ret = ezshell.run(profile["firmware_version"])
        self.data["version"] = ret.output()
        return response(data=self.data)

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
            self.data["server"] = message.data["server"]
            self.save()

        # Upgrading the firmware
        if "upgrade" in message.data and 1 == message.data["upgrade"]:
            response()
            self.upgrade()
            return

        return response()

    def upgrade(self):
        # TODO: backup the configuration for future restore
        # TODO: stop the services that may have side effect when upgrading
        # ret = ezshell.run(profile["stop_services"])
        time.sleep(5)
        ret = ezshell.run(profile["upgrade_firmware"])
        ret.output()
        if ret.returncode() == 0:
            logger.info("Upgrading success, reboot now.")
        else:
            logger.error("Upgrading failed, please check if the file is"
                         " correct.")
        ezshell.run(profile["reboot"])

    def setdef(self):
        # TODO: stop the services that may have side effect when setdef
        # ret = ezshell.run(profile["stop_services"])
        time.sleep(5)
        ret = ezshell.run(profile["set_factory_default"])
        ret.output()
        if ret.returncode() == 0:
            logger.info("Resetting to factory default success, reboot now.")
        else:
            logger.error("Resetting failed.")
        ezshell.run(profile["reboot"])


if __name__ == "__main__":  # pragma: no cover
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Firmware")

    firmware = Firmware(connection=Mqtt())
    firmware.start()
