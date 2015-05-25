#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import logging
import time
import sh
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator

# TODO: logger should be defined in sanji package?
logger = logging.getLogger()

path_root = os.path.abspath(os.path.dirname(__file__))

# Bundle"s profilefirmware
# TODO: add command to stop required services
profile = {
    "upgrade_firmware": path_root + "/tools/upgrade.sh",
    "turn_off_readyled": "/etc/init.d/showreadyled stop"
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
            profile["upgrade_firmware"] = path_root + "/upgradehfm.sh"

        try:
            self.load(path_root)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

    def run(self):
        if "upgrading" in self.model.db:
            if self.model.db["upgrading"] == -1:
                self.publish.event.put(
                    "/system/firmware",
                    data={"code": "FW_UPGRADE_FAIL", "type": "event"})
            else:
                self.publish.event.put(
                    "/system/firmware",
                    data={"code": "FW_UPGRADE_SUCCESS", "type": "event"})
            self.model.db.pop("upgrading")
            self.save()

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

    def check(self):
        """
        apt-get update -o Dir::Etc::sourcelist="sources.list.d/mxcloud.list"
                -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0"
          - finish
          - timeout
        apt-cache policy mxcloud-cg
          - installed
          - not installed: empty output
        dpkg --compare-versions [current] le [candidate]
          - true: there's newer for upgrade if [current] != [candidate]
          - false: need not to be upgraded
        """

        # get the update list
        try:
            sh.apt_get("update", "-o",
                       "Dir::Etc::sourcelist='sources.list.d/mxcloud.list'",
                       "-o", "Dir::Etc::sourceparts='-'", "-o",
                       "APT::Get::List-Cleanup='0'")
        except:
            raise Exception("Update failed.")

        # retrieve version
        output = sh.apt_cache("policy", "mxcloud-cg").splitlines()
        if len(output) < 3:
            raise Exception("Firmware not installed.")

        check = dict()
        check["isLatest"] = 0
        check["installed"] = output[1].split()[1]
        check["candidate"] = output[2].split()[1]
        try:
            output = sh.dpkg("--compare-versions", check["installed"], "le",
                             check["candidate"])
            if check["installed"] == check["candidate"]:
                check["isLatest"] = 1
        except:
            check["isLatest"] = 1
        return check

    def upgrade(self):
        # TODO: backup the configuration for future restore

        # set flags to show the upgrading status
        """
        self.publish.event.put(
            "/system/firmware",
            data={"code": "FW_UPGRADING", "type": "event"})
        """
        self.model.db["upgrading"] = 1
        self.save()

        time.sleep(1)
        try:
            sh.sh(profile["upgrade_firmware"])
            logger.info("Upgrading success, reboot now.")
            self.model.db["upgrading"] = 0
            self.save()
            sh.reboot()
        except:
            logger.error("Upgrading failed, please check if the file is"
                         " correct.")
            self.model.db["upgrading"] = -1
            self.save()

    def setdef(self):
        # TODO: stop the services that may have side effect when setdef
        self.model.db["defaulting"] = 1
        self.save()

        time.sleep(1)
        try:
            sh.setdef()
            logger.info("Resetting to factory default success, reboot now.")
            self.model.db["defaulting"] = 0
            self.save()
            sh.reboot()
        except:
            logger.error("Resetting failed.")
            self.model.db["defaulting"] = -1
            self.save()

    @Route(methods="get", resource="/system/firmware")
    def get(self, message, response):
        """
        {
            "version": "1.0",
            "server": "www.moxa.com"
        }
        """
        output = sh.awk(sh.pversion(), "{print $3}")
        self.model.db["version"] = str(output.split()[0])
        return response(data=self.model.db)

    @Route(methods="get", resource="/system/firmware/check")
    def get_check(self, message, response):
        """
        {
            "isLatest": 1,
            "installed": "1.0.0",
            "candidate": "1.0.0"
        }
        """
        try:
            check = self.check()
        except Exception as e:
            if Exception("Update failed.").args == e.args:
                return response(code=400, data={"message": "Update failed."})
            elif Exception("Firmware not installed.").args == e.args:
                return response(code=400,
                                data={"message": "Firmware not installed."})
            return response(code=400, data={"message": "Unknown error."})
        return response(data=check)

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
