# Remote Development tutorial
While Plugins will usually run on the same device as smartCORE it is possible to run plugins remotely over the network, which allows you to quickly iterate on plugins without having to transmit each version to your smartCORE.

In order to do so simply set the `localhost` flag in your Remote Module configuration to `true`. In this folder you'll find an example configuration file as well as an example program. Specify your device's address by using the `--addr` command line parameter.

If everything works you should find a `hello_world` channel with the value `true` in your smartCORE.


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
                "producerChannels": [{
                    "name": "hello_world",
                    "dataType": "bool"
                }]
            }
        }
    ]
}
```