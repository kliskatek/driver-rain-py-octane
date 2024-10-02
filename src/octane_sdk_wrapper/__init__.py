from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Callable

import clr
from importlib.resources import files

from dataclasses_json import dataclass_json

from src.octane_sdk_wrapper.helpers.clr2py import net_uint16_list_to_py_bytearray

octane_sdk_dll_path = files('src.octane_sdk_wrapper').joinpath('lib').joinpath('Impinj.OctaneSdk.dll')
clr.AddReference(str(octane_sdk_dll_path))
from Impinj.OctaneSdk import ImpinjReader, TagReport, AntennaConfig, ReaderMode, SearchMode

clr.AddReference('System.Collections')

logger = logging.getLogger(__name__)


class OctaneReaderMode(Enum):
    MaxThroughput = ReaderMode.MaxThroughput
    Hybrid = ReaderMode.Hybrid
    DenseReaderM4 = ReaderMode.DenseReaderM4
    DenseReaderM8 = ReaderMode.DenseReaderM8
    MaxMiller = ReaderMode.MaxMiller
    DenseReaderM4Two = ReaderMode.DenseReaderM4Two


class OctaneSearchMode(Enum):
    ReaderSelected = SearchMode.ReaderSelected
    SingleTarget = SearchMode.SingleTarget
    DualTarget = SearchMode.DualTarget
    TagFocus = SearchMode.TagFocus
    SingleTargetReset = SearchMode.SingleTargetReset
    DualTargetBtoASelect = SearchMode.DualTargetBtoASelect


@dataclass_json
@dataclass
class OctaneTagReport:
    Epc: bytearray = None
    AntennaPortNumber: int = None
    ChannelInMhz: float = None
    # FirstSeenTime: datetime = None
    # LastSeenTime: datetime = None
    PeakRssiInDbm: float = None
    # TagSeenCount: int = None
    # Tid: bytearray = None
    # RfDopplerFrequency: float = None
    # PhaseAngleInRadians: float = None
    # Crc: int = None
    # PcBits: int = None


class Octane:

    def __init__(self):
        self.driver = ImpinjReader()
        self.notification_callback = None

    def _octane_notification_callback(self, sender: ImpinjReader, report: TagReport):
        if self.notification_callback is not None:
            for tag in report.Tags:
                tag_report = OctaneTagReport()
                tag_report.Epc = net_uint16_list_to_py_bytearray(tag.Epc.ToList())
                if tag.IsAntennaPortNumberPresent:
                    tag_report.AntennaPortNumber = tag.AntennaPortNumber
                if tag.IsChannelInMhzPresent:
                    tag_report.ChannelInMhz = tag.ChannelInMhz
                if tag.IsPeakRssiInDbmPresent:
                    tag_report.PeakRssiInDbm = tag.PeakRssiInDbm
                self.notification_callback(tag_report)

    def set_notification_callback(self, notification_callback: Callable[[OctaneTagReport], None]):
        self.notification_callback = notification_callback

    def connect(self, ip):
        try:
            self.driver.Connect(ip)
            self.driver.TagsReported += self._octane_notification_callback
            self.set_default_settings()
            return True
        except Exception as e:
            logger.error(e)
            return False

    def disconnect(self):
        # Disconnect from the reader.
        self.driver.Disconnect()
        return False

    def query_feature_set(self):
        reader_capabilities = self.driver.QueryFeatureSet()
        return reader_capabilities

    def set_default_settings(self):
        try:
            settings = self.driver.QueryDefaultSettings()
            self.driver.ApplySettings(settings)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def set_mode(self, reader_mode: OctaneReaderMode, search_mode: OctaneSearchMode, session: int):
        try:
            # Get current settings.
            settings = self.driver.QuerySettings()

            settings.ReaderMode = reader_mode.value
            settings.SearchMode = search_mode.value
            settings.Session = session

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def set_report_flags(self, include_antenna_port_numbers: bool = False,
                         include_channel: bool = False,
                         include_peadk_rssi: bool = False):
        try:
            # Get current settings.
            settings = self.driver.QuerySettings()
            settings.Report.IncludeAntennaPortNumber = include_antenna_port_numbers
            settings.Report.IncludeChannel = include_channel
            settings.Report.IncludePeakRssi = include_peadk_rssi

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_tx_power(self):
        settings = self.driver.QuerySettings()
        power = []
        for antenna in settings.Antennas:
            power.append(antenna.TxPowerInDbm)
        return power

    def set_tx_power(self, dbm):
        # Same power to all antennas only supported
        try:
            # Get current settings.
            settings = self.driver.QuerySettings()
            settings.Antennas.TxPowerInDbm = dbm

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_antenna_config(self):
        feature_set = self.query_feature_set()
        settings = self.driver.QuerySettings()
        antenna_config = [False] * feature_set.AntennaCount
        n_enabled_antennas = settings.Antennas.Length
        for i in range(0, n_enabled_antennas):
            antenna_config[settings.Antennas.AntennaConfigs[i].PortNumber - 1] = True
        return antenna_config

    def set_antenna_config(self, antenna_config: List[bool]):
        if not True in antenna_config:
            raise Exception('At least one antenna has to be active')

        try:
            # Get current settings.
            settings = self.driver.QuerySettings()

            old_power_dbm = settings.Antennas.AntennaConfigs[0].TxPowerInDbm

            settings.Antennas.AntennaConfigs.Clear()

            for index, enable in enumerate(antenna_config):
                antenna_config = AntennaConfig()
                antenna_config.IsEnabled = enable
                antenna_config.MaxRxSensitivity = True
                antenna_config.MaxTxPower = False
                antenna_config.PortName = 'Antenna Port ' + str(index + 1)
                antenna_config.PortNumber = index + 1
                antenna_config.RxSensitivity = 0.0
                antenna_config.TxPowerInDbm = old_power_dbm
                settings.Antennas.AntennaConfigs.Add(antenna_config)

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def start(self):
        # Start reading.
        self.driver.Start()
        return False

    def stop(self):
        # Stop reading.
        self.driver.Stop()
