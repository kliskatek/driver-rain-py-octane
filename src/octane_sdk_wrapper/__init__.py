import datetime
import logging
import time
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import List, Callable, Any

import clr
from importlib.resources import files

from dataclasses_json import dataclass_json

from .helpers.clr2py import net_uint16_list_to_py_bytearray

# Detect Source or Package mode
top_package = __name__.split('.')[0]
if top_package == 'src':
    octane_sdk_wrapper_package = files('src.octane_sdk_wrapper')
else:
    octane_sdk_wrapper_package = files('octane_sdk_wrapper')
octane_sdk_dll_path = octane_sdk_wrapper_package.joinpath('lib').joinpath('Impinj.OctaneSdk.dll')
clr.AddReference(str(octane_sdk_dll_path))
from Impinj.OctaneSdk import ImpinjReader, TagReport, AntennaConfig, ReaderMode, SearchMode, MemoryBank, TagOpSequence, \
    TagReadOp, BitPointers, TagData, TagOpReport, TagReadOpResult, ReadResultStatus, TagWriteOp, TagWriteOpResult, \
    WriteResultStatus

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


class OctaneMemoryBank(Enum):
    Reserved = MemoryBank.Reserved
    Epc = MemoryBank.Epc
    Tid = MemoryBank.Tid
    User = MemoryBank.User


@dataclass_json
@dataclass
class OctaneFeatureSet:
    model_name: str
    region: str
    firmware_version: str
    antenna_count: int
    min_tx_power: float
    max_tx_power: float


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
        self._reader_is_on = False
        self._tag_read_op_queue: Queue = Queue()
        self._tag_write_op_queue: Queue = Queue()

    def _octane_notification_callback(self, sender: ImpinjReader, report: TagReport):
        if self.notification_callback is not None and self._reader_is_on:
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
            self.driver.TagOpComplete += self._octane_tag_op_complete_callback
            logger.debug('connect: Success')
            self.set_default_settings()
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('connect: Error')
            return False

    def disconnect(self):
        try:
            # Disconnect from the reader.
            self.driver.Disconnect()

            logger.debug('disconnect: Success')
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('disconnect: Error')
            return False

    def query_feature_set(self) -> OctaneFeatureSet:
        try:
            feature_set = self.driver.QueryFeatureSet()
            processed_feature_set = OctaneFeatureSet(
                model_name=feature_set.ModelName,
                region=feature_set.CommunicationsStandard.ToString(),
                firmware_version=feature_set.FirmwareVersion,
                antenna_count=feature_set.AntennaCount,
                min_tx_power=feature_set.TxPowers[0].Dbm,
                max_tx_power=feature_set.TxPowers[len(feature_set.TxPowers) - 1].Dbm
            )
            logger.debug('query_feature_set: ' + str(processed_feature_set))
            return processed_feature_set
        except Exception as e:
            logger.error(e)
            logger.debug('query_feature_set: Error')
            return False

    def set_default_settings(self):
        try:
            settings = self.driver.QueryDefaultSettings()
            self.driver.ApplySettings(settings)
            logger.debug('set_default_settings: Success')
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('set_default_settings: Error')
            return False

    def set_mode(self, reader_mode: OctaneReaderMode, search_mode: OctaneSearchMode, session: int):
        try:
            logger.debug('set_mode:' +
                         ' ' + str(reader_mode) +
                         ', ' + str(search_mode) +
                         '), session(' + str(session) + ')')
            # Get current settings.
            settings = self.driver.QuerySettings()

            settings.ReaderMode = reader_mode.value
            settings.SearchMode = search_mode.value
            settings.Session = session

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            logger.debug('set_mode: Success')
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('set_mode: Error')
            return False

    def set_report_flags(self, include_antenna_port_numbers: bool = False,
                         include_channel: bool = False,
                         include_peadk_rssi: bool = False):
        try:
            logger.debug('set_report_flags:' +
                         ' include_antenna_port_numbers(' + str(include_antenna_port_numbers) +
                         '), include_channel(' + str(include_channel) +
                         '), include_peadk_rssi(' + str(include_peadk_rssi) + ')')
            # Get current settings.
            settings = self.driver.QuerySettings()
            settings.Report.IncludeAntennaPortNumber = include_antenna_port_numbers
            settings.Report.IncludeChannel = include_channel
            settings.Report.IncludePeakRssi = include_peadk_rssi

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            logger.debug('set_report_flags: Success')
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('set_report_flags: Error')
            return False

    def get_tx_power(self):
        settings = self.driver.QuerySettings()
        power = []
        for antenna in settings.Antennas:
            power.append(antenna.TxPowerInDbm)
        logger.debug('get_tx_power: ' + str(power))
        return power

    def set_tx_power(self, dbm):
        # Same power to all antennas only supported
        try:
            logger.debug('set_tx_power: ' + str(dbm))
            # Get current settings.
            settings = self.driver.QuerySettings()
            settings.Antennas.TxPowerInDbm = dbm

            # Apply the newly modified settings.
            self.driver.ApplySettings(settings)
            logger.debug('set_tx_power: Success')
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('set_tx_power: Error')
            return False

    def get_antenna_config(self):
        feature_set = self.query_feature_set()
        settings = self.driver.QuerySettings()
        antenna_config = [False] * feature_set.antenna_count
        n_enabled_antennas = settings.Antennas.Length
        for i in range(0, n_enabled_antennas):
            antenna_config[settings.Antennas.AntennaConfigs[i].PortNumber - 1] = True
        logger.debug('get_antenna_config: ' + str(antenna_config))
        return antenna_config

    def set_antenna_config(self, antenna_config: List[bool]):
        if not True in antenna_config:
            raise Exception('At least one antenna has to be active')

        try:
            logger.debug('set_antenna_config: ' + str(antenna_config))
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
            logger.debug('set_antenna_config: Success')
            return True
        except Exception as e:
            logger.error(e)
            logger.debug('set_antenna_config: Error')
            return False

    def start(self):
        # Start reading.
        self.driver.Start()
        self._reader_is_on = True
        logger.debug('start')

    def stop(self):
        # Stop reading.
        self.driver.Stop()
        self._reader_is_on = False
        logger.debug('stop')

    def _octane_tag_op_complete_callback(self, reader: ImpinjReader, report: TagOpReport):
        for result in report.Results:
            if type(result) is TagReadOpResult:
                if result.Result == ReadResultStatus.Success:
                    data = net_uint16_list_to_py_bytearray(result.Data.ToList())
                    self._tag_read_op_queue.put(data)
                else:
                    self._tag_read_op_queue.put(None)

            if type(result) is TagWriteOpResult:
                if result.Result == WriteResultStatus.Success:
                    self._tag_write_op_queue.put(True)
                else:
                    self._tag_write_op_queue.put(False)

    def read(self, target: bytearray | str | None, bank: OctaneMemoryBank, word_pointer: int,
             word_count: int) -> bytearray | None:
        seq = TagOpSequence()
        read_op = TagReadOp()
        read_op.MemoryBank = bank.value
        read_op.WordPointer = word_pointer
        read_op.WordCount = word_count
        seq.Ops.Add(read_op)

        seq.TargetTag.MemoryBank = MemoryBank.Epc
        seq.TargetTag.BitPointer = BitPointers.Epc
        if target is None:
            seq.TargetTag.Data = None
        else:
            if type(target) is bytearray:
                target = target.hex()
            seq.TargetTag.Data = target

        logger.debug('Read tag(' + target + '), '
                     + str(bank) + ', pointer(' + str(word_pointer)
                     + '), count(' + str(word_count) + ')')
        self.driver.AddOpSequence(seq)
        if not self._reader_is_on:
            self.driver.Start()

        timeout = datetime.datetime.now() + datetime.timedelta(seconds=3)
        while self._tag_read_op_queue.empty() and (datetime.datetime.now() < timeout):
            time.sleep(0.01)
        if not self._reader_is_on:
            self.driver.Stop()
        if self._tag_read_op_queue.empty():
            logger.debug('Unable to read data (timeout)')
            return None
        data = self._tag_read_op_queue.get()
        if data is None:
            logger.debug('Unable to read data (error)')
        else:
            logger.debug('Read data: 0x' + data.hex())
        return data

    def write(self, target: bytearray | str | None, bank: OctaneMemoryBank, word_pointer: int,
              data: bytearray | str) -> bool:
        seq = TagOpSequence()
        write_op = TagWriteOp()
        write_op.MemoryBank = bank.value
        write_op.WordPointer = word_pointer
        if data is bytearray:
            data = data.hex()
        write_op.Data = TagData.FromHexString(data)
        seq.Ops.Add(write_op)

        seq.TargetTag.MemoryBank = MemoryBank.Epc
        seq.TargetTag.BitPointer = BitPointers.Epc
        if target is None:
            seq.TargetTag.Data = None
        else:
            if type(target) is bytearray:
                target = target.hex()
            seq.TargetTag.Data = target

        logger.debug('Write tag(' + target + '), '
                     + str(bank) + ', pointer(' + str(word_pointer)
                     + '), data(' + str(data) + ')')
        self.driver.AddOpSequence(seq)
        if not self._reader_is_on:
            self.driver.Start()

        timeout = datetime.datetime.now() + datetime.timedelta(seconds=3)
        while self._tag_write_op_queue.empty() and (datetime.datetime.now() < timeout):
            time.sleep(0.01)
        if not self._reader_is_on:
            self.driver.Stop()
        if self._tag_write_op_queue.empty():
            self.driver.DeleteOpSequence(seq.Id)
            logger.debug('Unable to write data (timeout)')
            return False
        result = self._tag_write_op_queue.get()
        if result is False:
            logger.debug('Unable to write data (error)')
        else:
            logger.debug('Write data success.')
        return result
