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
import math
import argparse


class CommandType(Enum):
    LifeSignRequest = 0
    LifeSignResponse = 1
    WriteSamplesByName = 100
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generates test signals and outputs them to smartCORE channels')
    parser.add_argument('--port', dest='port', default=61616, type=int, required=False)
    parser.add_argument('--addr', dest='addr', default='127.0.0.1', type=str, required=False)

    args = parser.parse_args()

    # establish connection to smartCORE
    addr = (args.addr, args.port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(2.0)

    buffer = packetHeader(CommandType.LifeSignRequest)
    buffer += msgpack.packb({})
    sock.sendto(buffer, addr)

    # wait to receive a reply
    received = sock.recv(1500)
    # needs try errorhandling
    header = header_from_buffer(received[:HEADER_SIZE])
    # check that reply has the correct header
    if header.type != CommandType.LifeSignResponse.value:
        # TODO errorhandling
        raise NotImplementedError

    buf = BytesIO()
    buf.write(received[HEADER_SIZE:])
    buf.seek(0)
    unpacker = msgpack.Unpacker(buf, raw=False)
    # ensure smartCORE is running
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
    # check that reply has correct header
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

    # map channel names to their indecies

    indexDict = {}
    
    for channel in channels:
        indexDict[channel['n']] = channel['i']

    print(indexDict)

    # Set up different function generators
    sine = math.sin(int(time.time() * 1_000))
    square = 0
    sharktooth = 0

    # TODO: Parse for expected writable channels

    print('\nGenerating:')
    sys.stdout.flush()
    try:
        while True:
            # Update signal generators
            sine = math.sin(int(time.time() * 1_000))
            square = 6 if int(time.time()) % 4 >= 2 else 0
            sharktooth = time.time() % 51

            buffer = packetHeader(CommandType.WriteSamplesRequest)
            payload = { "a": "some_placeholder",
                "c": [
                    {
                        "i": indexDict["remote.test.sine"],
                        "v": sine,
                        "t": int(time.time() * 1_000)
                    },
                    {
                        "i": indexDict["remote.test.square"],
                        "v": square,
                        "t": int(time.time() * 1_000)
                    },
                    {
                        "i": indexDict["remote.test.sharktooth"],
                        "v": sharktooth,
                        "t": int(time.time() * 1_000)
                    }
                ]
            }
            # print(payload)
            sys.stdout.flush()
            buffer += msgpack.packb(payload)
            sock.sendto(buffer, addr)
            # TODO: needs better read without cutoff

            received = sock.recv(15000)
            # TODO: needs try errorhandling
            header = header_from_buffer(received[:HEADER_SIZE])
            # print(header, flush=True)
            buf = BytesIO()
            buf.write(received[HEADER_SIZE:])
            buf.seek(0)
            # read back smartCORE reply
            unpacker = msgpack.Unpacker(buf, raw=False)
            # for unpacked in unpacker:
            #     print(unpacked)

            time.sleep(0.01)
    except KeyboardInterrupt:
        # stop the loop when the user presses CTRL+C
        pass


if __name__ == "__main__":
    main()
