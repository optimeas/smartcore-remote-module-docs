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
import argparse


class CommandType(Enum):
    LifeSignRequest = 0
    LifeSignResponse = 1
    WriteSamplesByName = 100
    ReadSamplesByNameRequest = 101
    ReadSamplesByNameResponse = 102
    ChannelListRequest = 200
    ChannelListResponse = 201
    WriteSamplesRequest = 202
    WriteSamplesResponse = 203
    ReadSamplesBegin = 204
    ReadSamplesContent = 205
    ReadSamplesEnd = 206

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

    # map channels

    indexDict = {}
    
    for channel in channels:
        indexDict[channel['n']] = channel['i']

    print(indexDict)

    print('\n\nRead Samples Begin')
    # Start reading samples
    buffer = packetHeader(CommandType.ReadSamplesBegin)
    payload = {
        "t": 100, # how many ms between packets
        "n": 1, # requested number of samples? 
        "e": False, # without timestamp
        "c": [0, 1]
    }
    print(header)
    buffer += msgpack.packb(payload)
    sock.sendto(buffer, addr)

    print('\n\nRead Samples Content')
    try:
        while True:
            # get Volts and Amps
            # Wait for blablabla
            received = sock.recv(2000)
            header = header_from_buffer(received[:HEADER_SIZE])
            if header.type != CommandType.ReadSamplesContent.value:
                # TODO errorhandling
                # raise NotImplementedError
                # continue
                print(f'Received wrong header type: {header.type}')
                continue


            buf = BytesIO()
            buf.write(received[HEADER_SIZE:])
            buf.seek(0)
            unpacker = msgpack.Unpacker(buf, raw=False)
            print(header)
            # print(unpacker)
            for unpacked in unpacker:
                channels = unpacked['c']
                channels = sorted(channels, key=lambda item: item['i'])
                print(channels)

            # # calculate wattage
            volts = channels[indexDict['remote.Voltage']]['v'][0]
            amps = channels[indexDict['remote.Amperage']]['v'][0]
            watts = volts * amps
            timestamp = channels[0]['t'][0]
            print(f'{round(volts, 2)} V * {round(amps,2)}A = {round(watts, 2)}W')


            # send value to smartcore
            buffer = packetHeader(CommandType.WriteSamplesRequest)
            payload = { 'a': 'wattage written',
                       'c': [{
                           'i': indexDict['remote.Wattage'],
                           'v': watts,
                           't': timestamp
                       }]
            }
            print(payload)
            sys.stdout.flush()
            buffer += msgpack.packb(payload)
            sock.sendto(buffer, addr)
            # TODO: needs better read without cutoff

            received = sock.recv(1500)
            # TODO: needs try errorhandling
            header = header_from_buffer(received[:HEADER_SIZE])
            if header.type != CommandType.ChannelListResponse.value: # apparently the response to WriteSamplesRequest is ChannelListResponse??
                print(header, flush=True)
                buf = BytesIO()
                buf.write(received[HEADER_SIZE:])
                buf.seek(0)
                unpacker = msgpack.Unpacker(buf, raw=False)
                for unpacked in unpacker:
                    print(unpacked)

            time.sleep(0.1)
    except KeyboardInterrupt:
        # stop receiving samples
        buffer = packetHeader(CommandType.ReadSamplesEnd)
        sock.sendto(buffer, addr)

    # TODO: Parse for expected writable channels
    
if __name__ == "__main__":
    main()
