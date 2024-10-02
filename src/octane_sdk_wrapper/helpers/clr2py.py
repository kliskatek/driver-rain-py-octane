def net_uint16_list_to_py_bytearray(net_list):
    py_bytearray = bytearray()
    for word in net_list:
        py_bytearray += word.to_bytes(2, byteorder='big')
    return py_bytearray
