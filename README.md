# octane-sdk-wrapper

[![PyPI - Version](https://img.shields.io/pypi/v/octane-sdk-wrapper.svg)](https://pypi.org/project/octane-sdk-wrapper)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/octane-sdk-wrapper.svg)](https://pypi.org/project/octane-sdk-wrapper)
![OS](https://img.shields.io/badge/os-windows-blue)
-----
*Python driver for Impinj UHF RFID readers wrapping octane SDK*

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Connect to the reader](#connect-to-the-reader)
  - [Get basic information about the reader](#get-basic-information-about-the-reader)
  - [Configure the reader](#configure-the-reader)
  - [Perform continuous asynchronous inventory](#perform-continuous-asynchronous-inventory)
  - [Execute Read/Write operations](#execute-readwrite-operations)

- [License](#license)

## Installation

```console
pip install octane-sdk-wrapper
```

## Usage
### Connect to the reader
```python
# Create driver
reader = Octane()

# Connect
reader.connect(ip='192.168.17.246')

... use the reader ...

# Disconnect reader
reader.disconnect()
```

### Get basic information about the reader
```python
feature_set = reader.query_feature_set()
```
Sample response values:

`
feature_set = OctaneFeatureSet(model_name='Speedway R220', region='US_FCC_Part_15', firmware_version='5.12.2.240', antenna_count=2, min_tx_power=10.0, max_tx_power=32.5)
`


### Configure the reader

```python
# Set antenna configurations
antenna_config: List[bool] = reader.get_antenna_config()
reader.set_antenna_config([True, False])

# Set TX power level
tx_power_per_antenna: List[float] = reader.get_tx_power()
logging.info('Setting max TX power')
reader.set_tx_power(feature_set.max_tx_power)
tx_power_dbm: float = reader.get_tx_power()
```
### Perform continuous asynchronous inventory

```python
# Define callback
def notification_callback(tag_report: OctaneTagReport):
    logging.info(tag_report)


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
```
Sample report:

`
OctaneTagReport(Epc=bytearray(b'\xe2\x00\x00\x195\x10\x02\x07\x08\x80\xc3+'), AntennaPortNumber=1, ChannelInMhz=913.25, PeakRssiInDbm=-66.0)
`
### Execute Read/Write operations
```python
reader.write(target=some_epc, 
             bank=OctaneMemoryBank.User, 
             word_pointer=0, 
             data="1234")

data: bytearray = reader.read(target=some_epc, 
                              bank=OctaneMemoryBank.User, 
                              word_pointer=0, 
                              word_count=1)
```


## License

`octane` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
