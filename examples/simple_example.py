import logging
import logging.config
import time

# To use from source
#from src.octane_sdk_wrapper import Octane, OctaneTagReport, OctaneMemoryBank

# To use from installed package
from octane_sdk_wrapper import Octane, OctaneTagReport, OctaneMemoryBank

logging.basicConfig(level=logging.DEBUG)

reader = Octane()
reader.connect(ip='192.168.17.246')

feature_set = reader.query_feature_set()

reader.get_antenna_config()
reader.set_antenna_config([False, True])
reader.get_antenna_config()
reader.set_antenna_config([True, True])
reader.get_antenna_config()

logging.info('Setting valid TX power')
reader.set_tx_power(15)
reader.get_tx_power()
logging.info('Setting too low TX power')
reader.set_tx_power(feature_set.min_tx_power - 10)
reader.get_tx_power()
logging.info('Setting too high TX power')
reader.set_tx_power(feature_set.max_tx_power + 10)
reader.get_tx_power()

logging.info('Setting max TX power')
reader.set_tx_power(feature_set.max_tx_power)
reader.get_tx_power()

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
    reader.write(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, data="1234")
    reader.read(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, word_count=1)
    reader.write(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, data="5678")
    reader.read(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, word_count=1)


reader.disconnect()
