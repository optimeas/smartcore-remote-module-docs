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

    # Edit port and ip address
    parser.add_argument('--port', dest='port', default=61617, type=int, required=False)
    parser.add_argument('--addr', dest='addr', default='192.168.12.185', type=str, required=False)
    args = parser.parse_args()

    # Establish connection to smartCORE
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
    
    # Wait until getting the ChannelListRequest response
    # Add timeout check if needed
    received = sock.recv(1500)
    header = header_from_buffer(received[:HEADER_SIZE])
    while header.type != CommandType.ChannelListResponse.value:
        received = sock.recv(1500)
        header = header_from_buffer(received[:HEADER_SIZE])
    
    buf = BytesIO()
    buf.write(received[HEADER_SIZE:])
    buf.seek(0)
    unpacker = msgpack.Unpacker(buf, raw=False)
    for unpacked in unpacker:
        channels = unpacked['c']
        print(channels)

    # Map channels
    indexDict = {}    
    for channel in channels:
        indexDict[channel['n']] = channel['i']
    print(indexDict)

    # Select signals index to be requested, depends on the smartcore config
    selected_chn = [0, 1, 2];   # First three channels

    print('\n\nRead Samples Begin')
    # Start reading samples
    buffer = packetHeader(CommandType.ReadSamplesBegin)
    payload = {
        "t": 100,           # how many ms between packets
        "n": 10,            # requested number of samples? 
        "e": False,         # without timestamp  
        "c": selected_chn   # Selected channels 
    }
    print(header)
    buffer += msgpack.packb(payload)
    sock.sendto(buffer, addr)
    
    print('\n\nRead Samples Content')    
    try:
        while True:            
            
            received = sock.recv(1500)
            header = header_from_buffer(received[:HEADER_SIZE])
            if header.type != CommandType.ReadSamplesContent.value:                      
                print(f'Received wrong header type: {header.type}')
                continue

            buf = BytesIO()
            buf.write(received[HEADER_SIZE:])
            buf.seek(0)
            unpacker = msgpack.Unpacker(buf, raw=False)            
            for unpacked in unpacker:                
                channels = unpacked['c']
                channels = sorted(channels, key=lambda item: item['i'])
            
            chn_idx = -1
            for chn_idx in selected_chn:
                chnName = ''
                for k, v in indexDict.items():
                    if v == chn_idx:
                        chnName = k
                        break
                
                if len(chnName) == 0:
                    continue
                             
                # Print timestamps and values of each channel
                if 'v' in channels[chn_idx]:
                    for idx, val in enumerate(channels[chn_idx]['v']):                    
                        timestamp = channels[chn_idx]['t'][idx]          
                        print(str(chn_idx)+ '. ' + chnName +' value received: ' + str(val) + ' ts: ' + str(timestamp) )           
            
    except KeyboardInterrupt:
        # stop receiving samples
        buffer = packetHeader(CommandType.ReadSamplesEnd)
        sock.sendto(buffer, addr)

    # TODO: Parse for expected writable channels
    
if __name__ == "__main__":
    main()