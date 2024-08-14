#!/usr/bin/env python3

import time
import sys
import msgpack
import os
import socket
import struct
from io import BytesIO
from dataclasses import dataclass
from enum import Enum

import bme680

class CommandType(Enum):
    LifeSignRequest = 0
    LifeSignResponse = 1
    ChannelListRequest = 200
    ChannelListResponse = 201
    WriteSamplesRequest = 202
    WriteSamplesResponse = 203

def packetHeader(c: CommandType):
    buffer = bytearray()
    buffer += struct.pack('@I', 0x45554C42)  # magicToken
    buffer += struct.pack('@B', 1)  # version
    buffer += struct.pack('@B', 2)  # payloadType
    buffer += struct.pack('@H', 0)  # reserved
    process_id = os.getpid()
    buffer += struct.pack('@Q', process_id)  # senderPid
    unix_timestamp_millisends = int(round(time.time() * 1000))
    buffer += struct.pack('@Q', unix_timestamp_millisends)  # senderTime_msSE
    buffer += struct.pack('@H', 1000)  # group: om::IpcGroup::smartCoreRemotePlugin
    buffer += struct.pack('@H', c.value)  # command
    return buffer


HEADER_SIZE = 28

@dataclass
class Header:
    magic_token: int
    type: int


def header_from_buffer(buf):
    magic_token = struct.unpack('@I', buf[0:4])[0]
    command = struct.unpack('@H', buf[26:28])[0]
    if magic_token != 0x45554C42:
        raise ValueError

    return Header(magic_token, command)


def main():
    addr = ("127.0.0.1", 61616)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(2.0)

    buffer = packetHeader(CommandType.LifeSignRequest)
    buffer += msgpack.packb({})
    sock.sendto(buffer, addr)

    received = sock.recv(1500)
    # needs try errorhandling
    header = header_from_buffer(received[:HEADER_SIZE])
    if header.type != CommandType.LifeSignResponse.value:
        # TODO errorhandling
        raise NotImplementedError

    buf = BytesIO()
    buf.write(received[HEADER_SIZE:])
    buf.seek(0)
    unpacker = msgpack.Unpacker(buf, raw=False)
    for unpacked in unpacker:
        if unpacked["smartcore-state"] != "Running":
            raise RuntimeError("smartcore is not running")

    # Request channel list
    buffer = packetHeader(CommandType.ChannelListRequest)
    buffer += msgpack.packb({})
    sock.sendto(buffer, addr)

    # TODO: needs better read without cutoff
    received = sock.recv(1500)
    # TODO: needs try errorhandling
    header = header_from_buffer(received[:HEADER_SIZE])
    if header.type != CommandType.ChannelListResponse.value:
        # TODO errorhandling
        raise NotImplementedError

    buf = BytesIO()
    buf.write(received[HEADER_SIZE:])
    buf.seek(0)
    unpacker = msgpack.Unpacker(buf, raw=False)
    for unpacked in unpacker:
        channels = unpacked['c']
        print(channels)

    # TODO: Parse for expected writable channels
    try:
        sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
    except (RuntimeError, IOError):
        sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

    # These calibration data can safely be commented
    # out, if desired.
    # print('Calibration data:')
    # for name in dir(sensor.calibration_data):
    #     if not name.startswith('_'):
    #         value = getattr(sensor.calibration_data, name)
    #         if isinstance(value, int):
    #             print('{}: {}'.format(name, value))
    #
    # These oversampling settings can be tweaked to
    # change the balance between accuracy and noise in
    # the data.

    sensor.set_humidity_oversample(bme680.OS_2X)
    sensor.set_pressure_oversample(bme680.OS_4X)
    sensor.set_temperature_oversample(bme680.OS_8X)
    sensor.set_filter(bme680.FILTER_SIZE_3)
    sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

    print('\n\nInitial reading:')
    for name in dir(sensor.data):
        value = getattr(sensor.data, name)

        if not name.startswith('_'):
            print('{}: {}'.format(name, value))

    sensor.set_gas_heater_temperature(320)
    sensor.set_gas_heater_duration(150)
    sensor.select_gas_heater_profile(0)

    # Up to 10 heater profiles can be configured, each
    # with their own temperature and duration.
    # sensor.set_gas_heater_profile(200, 150, nb_profile=1)
    # sensor.select_gas_heater_profile(1)

    print('\n\nPolling:')
    sys.stdout.flush()
    try:
        while True:
            if sensor.get_sensor_data():
                # Request channel list
                buffer = packetHeader(CommandType.WriteSamplesRequest)
                payload = { "a": "some_placeholder",
                    "c": [
                        {
                            "i": 0,
                            "v": [
                                sensor.data.temperature
                            ],
                            "t": [
                                int(time.time() * 1_000),
                            ]
                        }
                    ]
                    }
                print(payload)
                sys.stdout.flush()
                buffer += msgpack.packb(payload)
                sock.sendto(buffer, addr)
                # TODO: needs better read without cutoff

                received = sock.recv(1500)
                # TODO: needs try errorhandling
                header = header_from_buffer(received[:HEADER_SIZE])
                print(header, flush=True)
                buf = BytesIO()
                buf.write(received[HEADER_SIZE:])
                buf.seek(0)
                unpacker = msgpack.Unpacker(buf, raw=False)
                for unpacked in unpacker:
                    print(unpacked)
                # produce samples here 
                    # sensor.data.temperature,
                    # sensor.data.pressure,
                    # sensor.data.humidity)
                if sensor.data.heat_stable:
                    # print('{0},{1} Ohms'.format(
                    #     output,
                    #     sensor.data.gas_resistance))
                    ...

            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
