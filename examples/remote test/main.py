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
    addr = ("192.168.15.224", 61616)
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
        print("channels:")
        print(channels)

    # TODO: Parse for expected writable channels

    print('\n\nSending test data')
    sys.stdout.flush()

    # set "hello_world" channel to true
    # Request channel list
    buffer = packetHeader(CommandType.WriteSamplesRequest)
    payload = { "a": "Hello Remote Plugin",
        "c": [
            {
                "i": 0, #write to 0th channel
                "v": [
                    True
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


if __name__ == "__main__":
    main()
