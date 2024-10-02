import json
import logging
import logging.config
import time
from binascii import hexlify

# To use from source
from src.octane_sdk_wrapper import Octane, OctaneTagReport, OctaneMemoryBank

# To use from installed package
# from octane_sdk_wrapper import Octane, OctaneTagReport

logging.basicConfig(level=logging.DEBUG)

reader = Octane()
reader.connect(ip='192.168.17.246')

feature_set = reader.query_feature_set()
reader_info = {
    'model_name': feature_set.ModelName,
    'region': feature_set.CommunicationsStandard.ToString(),
    'firmware_version': feature_set.FirmwareVersion,
    'antenna_count': feature_set.AntennaCount,
    'min_tx_power': feature_set.TxPowers[0].Dbm,
    'max_tx_power': feature_set.TxPowers[len(feature_set.TxPowers) - 1].Dbm
}

logging.info('Reader info:\n' + json.dumps(reader_info, indent=4))

logging.info('Antenna config:\n' + str(reader.get_antenna_config()))
reader.set_antenna_config([False, True])
logging.info('Antenna config:\n' + str(reader.get_antenna_config()))
reader.set_antenna_config([True, True])
logging.info('Antenna config:\n' + str(reader.get_antenna_config()))

logging.info('Setting valid TX power')
reader.set_tx_power(15)
logging.info('Tx power:\n' + str(reader.get_tx_power()))
logging.info('Setting too low TX power')
reader.set_tx_power(reader_info['min_tx_power'] - 10)
logging.info('Tx power:\n' + str(reader.get_tx_power()))
logging.info('Setting too high TX power')
reader.set_tx_power(reader_info['max_tx_power'] + 10)
logging.info('Tx power:\n' + str(reader.get_tx_power()))

logging.info('Setting max TX power')
reader.set_tx_power(reader_info['max_tx_power'])
logging.info('Tx power:\n' + str(reader.get_tx_power()))

some_epc = None


def notification_callback(tag_report: OctaneTagReport):
    global some_epc
    logging.info(tag_report)
    some_epc = tag_report.Epc


reader.set_notification_callback(notification_callback=notification_callback)
reader.set_report_flags(include_antenna_port_numbers=True,
                        include_channel=True,
                        include_peadk_rssi=True)
reader.start()
time.sleep(.5)
reader.stop()
if some_epc is not None:
    data = reader.read(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, word_count=1)
    print(hexlify(data))

reader.disconnect()
