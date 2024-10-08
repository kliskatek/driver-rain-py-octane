import logging
import logging.config
import time
from typing import List

# To use from source
from src.octane_sdk_wrapper import Octane, OctaneTagReport, OctaneMemoryBank

# To use from installed package
# from octane_sdk_wrapper import Octane, OctaneTagReport, OctaneMemoryBank

logging.basicConfig(level=logging.DEBUG)

## CONNECT
# Create driver
reader = Octane()

# Connect
reader.connect(ip='192.168.17.246')

## GET INFO
feature_set = reader.query_feature_set()

## MODULE SETUP
# Set antenna configurations
antenna_config: List[bool] = reader.get_antenna_config()
reader.set_antenna_config([True, False])

# Set TX power level
logging.info('Setting max TX power')
reader.set_tx_power(feature_set.max_tx_power)
tx_power_per_antenna: List[float] = reader.get_tx_power()

## INVENTORY ASYNC
some_epc: bytearray | None = None


# Define callback
def notification_callback(tag_report: OctaneTagReport):
    global some_epc
    logging.info(tag_report)
    some_epc = tag_report.Epc


# Configure the callback
reader.set_notification_callback(notification_callback=notification_callback)
# Configure the report options
reader.set_report_flags(include_antenna_port_numbers=True,
                        include_channel=True,
                        include_peadk_rssi=True)

# Start inventory stream
reader.start()

# Do other stuff
time.sleep(.5)

# Stop inventory stream
reader.stop()

## READ WRITE OPERATIONS
if some_epc is not None:
    reader.write(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, data="1234")
    data: bytearray = reader.read(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, word_count=1)
    reader.write(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, data="ABCD")
    data: bytearray = reader.read(target=some_epc, bank=OctaneMemoryBank.User, word_pointer=0, word_count=1)

# Disconnect reader
reader.disconnect()
