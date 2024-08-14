# Creating a simple plugin to produce smartCORE channels
The simplest (practical) Remote Plugin one can write for smartCORE is one which simply produces its own data without any outside influence. In this example we'll create a plugin, which will generate three different function signals - a sine wave, a square wave, and a shark tooth wave.

## Configuration
First we'll create a configuration for the smartCORE module, which defines the signals we will be producing. To output signals to smartCORE we have to add the "producerChannels" key to our configuration. It contains a list of channels, with configured name, data type, and physical unit. For our signal names we'll choose "remote.test.[sine,square,sharktooth]" and for the dataType we'll choose "float". Here we could also use "int" or "double", as the produced data requires. We won't specify a physical unit, since for our testing purposes these channels produce arbitrary numbers.

```JSON
{
            "factory": "remote",
            "module": "remote",
            "config": {
                "port": 61616,
                "localhost": false,
                "producerChannels": [{
                    "name": "remote.test.sine",
                    "dataType": "float"
                },
                {
                    "name": "remote.test.square",
                    "dataType": "float"
                },
                {
                    "name": "remote.test.sharktooth",
                    "dataType": "float"
                }
            ]
            }
        }
```


## Implementation
Inside our plugin we'll have to prepare to run our main loop. First we'll connect to smartCORE and check whether it's running.

```Python
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
```

Next we'll request the list of channels we have access to. It should contain the ones we specified in our configuration.
```Python
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
```
Additionally we'll create a dictionary, which maps channel names to their indices. We'll use it to send our data to the correct smartCORE channels.
```Python
# map channel names to their indices
indexDict = {}

for channel in channels:
    indexDict[channel['n']] = channel['i']
print(indexDict)
```

Now that we've got the boilerplate out of the way here comes the fun part. We'll create an infinite loop and wrap it within a try-catch statement, to allow us to exit the loop via a keyboard interrupt (CTRL + C). In the loop we'll create three variables for our three channels. Sine, which takes the sine of the current time in ms, Square, which switches between 6 and 0 every two seconds, and Sharktooth which takes the modulo of the current time.
```Python
while True:
    # Update signal generators
    sine = math.sin(int(time.time() * 1_000))
    square = 6 if int(time.time()) % 4 >= 2 else 0
    sharktooth = time.time() % 51
```

With our data ready we'll start creating a WriteSamplesRequest packet, which consists of the WriteSamplesRequest header and a payload containing our data. The payload consists of an "acknowledge" field "a" and a list of channels "c". The channels themselves consist of an index "i", a value "v", and a timestamp "t". We'll fill in these fields with their indices, current values, and the current time.

```Python

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

```
Once we've sent the packet and received the "ack packet" back we should be able to see our signals in optiControl or optiCloud.

[See the full source code here](main.py)
