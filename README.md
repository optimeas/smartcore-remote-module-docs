# optiMEAS Remote Plugin Module

The remote plugin module is used for the simple connection of scripts / programs to the smartCORE. It provides an IPC interface that allows customers to communicate with the smartCORE from software they have written themselves. It can also start, stop and monitor this software.  
Without an external plugin, the module has **no** function. 

In this repository you will find documentation on the API of the module, as well as a few examples that should make it easy to get started with development.

**Notes on script development:**
- If you are working on Windows, make sure that scripts only contain `\n`, not `\r\n`


# Table of Contents
- optiMEAS Remote Plugin Module](#optimeas-remote-plugin-module)
- Table of Contents](#table-of-contents)
- Tutorials](#tutorials)
- JSON configuration](#json-configuration)
  - [Configuration of network parameters](#configuration-of-network-parameters)
  - [Configuration of the process control](#configuration-of-process-control)
  - Configuration of the producer channels ( producerChannels )](#configuration-of-producer-channels--producerchannels-)
  - [Configuration of the consumer channels ( consumerChannels )](#configuration-of-the-consumer-channels--consumerchannels-)
  - Example configuration](#exampleconfiguration)
- API/Protocol](#apiprotocol)
  - Header](#header)
    - Header metadata](#header-metadata)
    - Commands](#commands)
  - Payload structure (JSON content)](#payload-structure-json-content)
    - byName Commands](#byname-commands)
      - Write values to smartCORE](#werte-in-smartcore-schreiben)
      - Read values from smartCORE (polling)](#values-read-from-smartcore-polling)
    - byIndex Commands](#byindex-commands)
      - Query channel list](#kanalliste-abfragen)
      - Write values to smartCORE](#values-in-smartcore-write-1)
      - Read continuous values from smartCORE](#continuous-values-read-from-smartcore)


# Tutorials
[Development on external PC](./examples/remote%20test/)  
[Simple data-write plugin](./examples/funcgen/)  
[Data read and write plugin](./examples/wattage_calc/)  
[[Advanced] Installation of new Python libraries (e.g. NumPy)](./examples/numpy/)  

# JSON configuration

## Configuration of the network parameters
| keyword | explanation |
| ------------- | --------------------------------------------------------------- |
| port | UDP port on which the plugin is listening (default: 61616) |
| localhost | Restriction to “localhost only” communication (default: true) |

## Configuration of the process control
| Name | Explanation |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| enable | Specifies whether the process should be started and monitored (default: false) |
| logOutput | Transfer output (stdout & stderr) of the process to the smartCORE log file (default: true) |
| watchdogTimeout | Maximum time between 2x IPC messages until RESTART of the process |
| disableKillAllProcesses | Disable all processes at startup or in case of problems (default: false) |
| command | Name (with optional path) of the process |
| arguments | Command line arguments for the process |


## Configuration of the producer channels ( producerChannels )
| keyword | explanation |
| ------------- | ------------------- |
| name | Name of the channel |
| dataType | Data type of the channel |
| physicalUnit | Unit of the channel |


## Configuration of the consumer channel ( consumerChannels )
| keyword | explanation |
| ------------- | ------------------------------------------- |
| name | Name of the channel to be read |


## Example configuration
```JSON
{
      “module": ‘remote’,
      “factory": ‘remote’,
      “config": {
        “port": 61616,
        “localhost": true,
        “process":
        {
            “enable": true,
            “logOutput": false,
            “watchdogTimeout": 60, 
            “disableKillAllProcesses": false,
            “command": ‘i2c-sen5x-cpp’,
            “arguments": ”--device-path=/dev/i2c-1 --interval=1”
        },
        “producerChannels": [
          {
            “name": ‘sen5x_pm1p0’,
            “dataType": ‘float’,
            “physicalUnit": ”µg/m³”
          },
          {
            “name": ‘sen5x_pm2p5’,
            “dataType": ‘float’,
            “physicalUnit": ”µg/m³”
          }
        ],
        “consumerChannels": [
            {
                “name": ”scd40_co2”
            }
        ]
      }
    }

```



# API/Protocol
The protocol consists of a mostly static header, in which a command code is specified, and (if necessary) a JSON payload.

## Header

### Header metadata
| Offset and data type | Name | Description |
| ------------------- | --------------- | ------------------------------------------------------------------------------------------- |
| [0] uint32_t | magicToken | Recognition of the protocol (fixed 0x45554C42) |
| [4] uint8_t | version | Protocol version (currently always 1; open for extensions) |
| [5] uint8_t | payloadType | Support and differentiation of different payload types (currently always 2) |
| [6] uint16_t | reserved | Reserved for later extensions (header size should be divisible by 4) |
| 8] uint64_t | senderPid | Process ID of the sending process |
| [16] uint64_t | senderTime_msSE | Time in milliseconds when the packet was sent (for diagnostic purposes) |
| [24] uint16_t | group | Identifier of the service to which the RPC call was sent or from which the response came (here fixed at 1000) |
| [26] uint16_t | command | Number of the RPC call (see following table) |

### Commands
| Command No | Name | Explanation |
| ---------- | ------------------------- | ----------------------------------------------------------------------------------------- |
| 0 | LifeSignRequest | smartCORE status request |
| 1 | LifeSignResponse | Response to LifeSignRequest |
| 100 | WriteSamplesByName | Send individual samples with channel name |
| 101 | ReadSamplesByNameRequest | Query individual channels by channel name |
| 102 | ReadSamplesByNameResponse | Response to ReadSamplesByNameRequest (measured values) |
| 200 | ChannelListRequest | Query channel list (assignment of channel name => index) |
| 201 | ChannelListResponse | Response to ChannelListRequest (channel list) |
| 202 | WriteSamplesRequest | Send samples (optionally with timestamp) via index |
| 203 | WriteSamplesResponse | Optional response to WriteSamplesRequest if a token was passed for confirmation |
| 204 | ReadSamplesBegin | Switching on the cyclical sending of measured values by the smartCORE |
| 205 | ReadSamplesContent | Measured values of the cyclical transmission |
| 206 | ReadSamplesEnd | Switch off cyclical transmission |
| 300 | AlarmMessageRequest | Writing an alarm to the smartCORE alarm center |
| 301 | AlarmMessageResponse | Acknowledgement of AlarmMessageRequest |

## Payload structure (JSON content)

### byName Commands

#### Write values to smartCORE

RPC: WriteSamplesByName (Client => smartCORE)

| Parameters | Description |
| --------- | ----------------------- |
| c | Array of channels |
| n | Channel name |
| v | Measured value |
| t | Time Stamp (optional) |

```JSON
{
  “c": [
    {
      “n": ‘sen5x_pm1p0’,
      “v": 1.0099999904632568,
      “t": 1720074467000000
    },
    {
      “n": ‘sen5x_pm2p5’,
      “v": 2.009999990463257,
      “t": 1720074467000000
    }
  ]
}
```

#### Read values from smartCORE (polling)

RPC: ReadSamplesByNameRequest (Client => smartCORE)

| Parameter | Description |
| --------- | --------------------- |
| c | Array of channel names |

```JSON
{
  “c": [
    “sen5x_pm1p0”,
    “sen5x_pm2p5”
  ]
}
```

RPC: ReadSamplesByNameResponse (smartCORE => Client)

| Parameters | Description |
| --------- | ---------------- |
| c | Array of channels |
| n | Channel name |
| v | Measured value |
| t | Time Stamp |

```JSON
{
  “c": [
    {
      “n": ‘sen5x_pm1p0’,
      “v": 1.0099999904632568,
      “t": 1720074467000000
    },
    {
      “n": ‘sen5x_pm2p5’,
      “v": 2.009999990463257,
      “t": 1720074467000000
    }
  ]
}
```


### byIndex Commands
#### Query channel list

RPC: ChannelListRequest (Client => smartCORE)

An empty request can be sent here to request the names of all channels.
Alternatively, only selected channel names can be requested:

| Parameter | Description |
| --------- | ------------------------------------------------------------ |
| c | Array of channel names |
| f | Request special fields such as “d” (data type) [optional] |

```JSON
{
  “f": [
    “d”
  ],
  “c": [
    “sen5x_pm1p0”,
    “sen5x_pm2p5”
  ]
}
```

RPC: ChannelListResponse (smartCORE => Client)

| Parameter | Description |
| --------- | ------------------------------------------------------- |
| c | Array of channels |
| n | Channel name |
| i | Index of the channel |
| w | Writable (producer channel) [not available if false] |
| d | Data type (optional; if requested) |

```JSON
{
  “c": [
    {
      “n": ‘sen5x_pm1p0’,
      “i": 0,
      “w": true,
      “d": ”float”
    },
    {
      “n": ‘sen5x_pm2p5’,
      “i": 1,
      “d": ”int32”
    }
  ]
}
```

#### Write values to smartCORE

RPC: WriteSamplesRequest (Client => smartCORE)

There are three possible payloads here:
    - Single samples per channel
    - Multiple samples with time stamp per channel
    - Equidistant samples per channel

| Parameter | Description |
| --------- | ------------------------------------------------- |
| a | Token to receive acknowledge packet (optional) |
| c | Array of channels |
| i | channel index |
| v | Measured value |
| t | Time stamp (optional) |
| s | Different time for equidistant samples |

Payload variant 1: individual samples per channel

```JSON
{
  “a": ‘xyz’,
  “t": 1720074467000000,
  “c": [
    {
      “i": 0,
      “v": 1.0099999904632568,
      “t": 1720074467000000
    },
    {
      “i": 1,
      “v": 2.009999990463257,
    }
  ]
}
```

Payload variant 2: Multiple samples with time stamp per channel

```JSON
{
  “a": ‘xyz’,
  “c": [
    {
      “i": 0,
      “v": [
        1,
        2,
        3
      ],
      “t": [
        1720074467000000,
        1720074467000100,
        1720074467000200
      ]
    },
    {
      “i": 1,
      “v": [
        1,
        2,
        3
      ],
      “t": 1720074467000000,
      “s": 200
    }
  ]
}
```

Payload variant 3: Equidistant samples per channel

```JSON
{
  “a": ‘xyz’,
  “t": 1720074467000000,
  “s": 200,
  “c": [
    {
      “i": 0,
      “v": [
        1,
        2,
        3
      ],
      “t": 1720074467000000,
      “s": 200
    },
    {
      “i": 1,
      “v": [
        1,
        2,
        3
      ]
    }
  ]
}
```

RPC: WriteSamplesResponse (smartCORE => Client)

If a token was specified in the request packet, the smartCORE sends a packet with the token for confirmation.

| Parameter | Description |
| --------- | --------------------------- |
| a | Token from the request packet |

```JSON
{
  “a": ”xyz”
}
```

#### Read continuous values from smartCORE

RPC: ReadSamplesBegin (Client => smartCORE)

| Parameters | Description |
| --------- | ----------------------------------------------------------------------------------------------- |
| t | Time in milliseconds between two packets (sending interval) |
| n | Desired number of samples (number of identical consumption intervals per sending interval) |
| e | Equidistant (without transmission of the time stamp) |
| c | List of channel indices |

```JSON
{
  “t": 100,
  “n": 10,
  “e": true,
  “c": [
    2,
    5
  ]
}
```

RPC: ReadSamplesContent (smartCORE => Client)

| Parameters | Description |
| --------- | ------------------------------------------------------------------------ |
| x | Consecutive packet index since start (e.g. to determine data loss) |
| c | Array of channels |
| i | Channel index |
| v | Measured value |
| t | Time stamp |

Notes:
    - If fewer than the required number of samples are available, only the available samples are transmitted.
    - If no current sample is available, only the “Last Value” is sent.

Payload variant 1: with time stamp ( e = “false”)

```JSON
{
  “x": 123,
  “c": [
    {
      “i": 2,
      “v": [
        1.0099999904632568,
        5.009999990463257,
        6.009999990463257
      ],
      “t": [
        1720074467000000,
        1720074467000100,
        1720074467000200
      ]
    },
    {
      “i": 5,
      “v": [
        1.0099999904632568,
        5.009999990463257,
        6.009999990463257
      ],
      “t": [
        1720074467000000,
        1720074467000100,
        1720074467000200
      ]
    }
  ]
}
```

Payload variant 2: without time stamp ( e = “true”)

```JSON
{
  “x": 123,
  “t": 1720074467000000,
  “s": 100,
  “c": [
    {
      “i": 2,
      “v": [
        1.0099999904632568,
        5.0099999904632568,
        6.0099999904632568
      ]
    },
    {
      “i": 5,
      “v": [
        1.0099999904632568,
        5.0099999904632568,
        6.0099999904632568
      ]
    }
  ]
}
```

RPC: ReadSamplesEnd (Client => smartCORE)

Empty request to switch off the transmission.


<!-- ### Alarms (TBD)
Create alarm in smartCORE

RPC: AlarmMessageRequest (Client => smartCORE)

| Parameter | Description |
| --------- | ------------------------------- |
| token | Token to assign acknowledgement |

```JSON
{
  “token": ‘xyz’,
  “uuid": ‘9643’,
  “time": 1720074467000000,
  “action": ‘event’,
  “context": ‘component_x’,
  “message": ‘condition_y’,
  “level": ‘info’,
  “metadata": {
    “hello": ”world”
  },
  “snapshot": [
    {
      “n": ‘name’,
      “v": ‘value’,
      “u": ”unit”
    },
    {
      “n": ‘name’,
      “v": ‘value’,
      “u": ”unit”
    }
  ]
}
```

RPC: AlarmMessageResponse (smartCORE => Client)

| Parameter | Description |
| --------- | ----------------------------------------- |
| token | Token to assign acknowledgement |
| uuid | UUID of the alarm in the smartCORE database |

```JSON
{
  “token": ‘xyz’,
  “uuid": ”9643”
}
```

 -->