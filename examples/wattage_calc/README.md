# Creating a plugin which processes smartCore data
This tutorial expands upon the concepts learned in [Funcgen Tutorial](../funcgen/).

In most cases you'll want to make use of a plugin to calculate data using existing smartCore channels. In this example we'll use mock Voltage and Amperage signals to calculate a Wattage. 
Disclaimer: The math module is better suited to simple calculations such as this one, the usage of the Remote Plugin Module here is for demonstrative purposes only.


## Configuration
Just like in the previous demonstration we'll create a producerChannel for the results of our calculations, though we will also specify a "physicalUnit" in this case, since we're calculating Wattage. In order to read Voltage and Amperage from smartCore channels we have to specify "consumerChannels" in our Remote Module configuration. The only field required is the "name" field, which takes the channel's full key name. In our case we'll also use the built-in "functiongenerator" module to generate said channels for us. 

```JSON

{
    "plugins": [
    "remote"
    ],
    "modules": [
        {
            "factory": "remote",
            "module": "remote",
            "config": {
                "port": 61616,
                "localhost": false,
                "producerChannels": [
                    {
                        "name": "remote.Wattage",
                        "dataType": "float",
                        "physicalUnit": "W"
                    }
                ],
                "consumerChannels": [
                    {
                        "name": "remote.Voltage"
                    },
                    {
                        "name": "remote.Amperage"
                    }
                ]
            }
        },
        {
            "factory": "functiongenerator",
            "module": "Functiongenerator",
            "config": {
                "channels": [{
                    "name": "remote.Voltage",
                    "dataType": "float",
                    "amplitude": 1.5,
                    "offset": 240,
                    "frequency": 0.05,
                    "function": "sine",
                    "physicalUnit": "V"
                },
                {
                    "name": "remote.Amperage",
                    "dataType": "float",
                    "function": "triangle",
                    "amplitude": 10,
                    "frequency": 0.5,
                    "physicalUnit": "A"
                }
            ]
            }
        }
    ]
}

```

## Implementation
Our implementation will start just like the first one, with establishing a connection and getting the channel list. 
Before entering our main loop we'll send a ReadSamplesBegin packet to the smartCORE, which will prompt it to periodically send sample data to our plugin. In the payload of our ReadSamplesBegin packet we'll specify the time between sample data "t" in ms, the amount of samples to be transmitted (if available) "n", whether the samples should be treated as equidistant "e", and which channels "c" we want to monitor. 

```Python
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
```

In our main loop we'll start by waiting for a response from the smartCORE. Once we've received some samples we'll extract the values to variables and perform our calculation. We'll also save the timestamp of our samples to a variable, as this allows us to keep our Wattage channel in time with the input channels.

```Python
# get Volts and Amps
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

# calculate wattage
volts = channels[indexDict['remote.Voltage']]['v'][0]
amps = channels[indexDict['remote.Amperage']]['v'][0]
watts = volts * amps
timestamp = channels[0]['t'][0]
```

Now all that's left to do is to send our result back to the smartCORE.
```Python
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
```

---
    - 
    - Get signals from smartCore and process to produce new signal
    - Config:
        ○ consumerChannels - just their name (generated from functiongenerator in this example)
        ○ Define producerchannel
    - To read channels send a ReadSamplesBegin packet
        ○ Specify time between updates, no. Of samples in packet, timestamps, which channels
    - Enter loop
        ○ Wait for ReadSamplesContent packet
        ○ Extract data, timestamp from sample(s)
        ○ Use data in calculation
        ○ Send WriteSamplesRequest packet with timestamp of received data
