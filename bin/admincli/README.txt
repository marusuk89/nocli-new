WebEM Remote Tool README

Main script: admin-cli (admin-cli.sh for Linux and admin-cli.bat for Windows)

Operating systems supported: Linux (x86_64), Windows (Windows 7 x64 or higher version)

----------------------
Command Line Arguments
----------------------

    > ./admin-cli.sh --help

    Options:
      --bts-username  BTS username                                                               [string] [required]
      --bts-password  BTS password                                                               [string] [required]
      --bts-host      BTS host                                                                   [string] [required]
      --bts-port      BTS port                                                                   [number] [required]
      --cli-host      CLI socket server host(for server mode)                                    [string] [default: "localhost"]
      --cli-port      CLI socket server port(for server mode)                                               [number]
      --interval      Specifies how fast updates should arriving in milliseconds            [number] [default: 5000]
      --insecure      Insecure connection                                                 [boolean] [default: false]
      --data          JSON format request                                                                   [string]
      --input-file    File to be included into the request message                                          [string]
      --output-file   Payload file extracted from the response message                                      [string]
      --encodeType    Datatype for transfer files from server to client ('base64' or 'binary')   [string] [default: "base64"]
      --debug         Log file                                                                              [string]
      --bundle-path   Explicit bundle path                                                                  [string]
      --bundles-dir   Bundles directory                                [string] [default: "<admin-cli dir>/bundles"]
      --superuser     Superuser privileges                                                [boolean] [default: false]
      --format        Output format ('compact' or 'human')                             [string] [default: "compact"]
      --gc            Specifies how often garbage collector should be triggered by force   [number] [default: 10000]
      -h, --help      Show help                                                                            
      -v, --version   Show version number                                                                  

* --bts-host *

    BTS's eNB IP address (IPv4 or IPv6)

    Remarks:
    - Default 192.168.255.1
    - IPv6 format should have such a syntax e.g --bts-host="[0:0:0:0:0:ffff:c0a8:ff01]"

* --insecure *

    Be default CLI uses SSL

    Remarks:
     - bts-port=443 | 3600 secure
     - bts-port=80 insecure (not support since admin-cli-2.5.10)

* --cli-host --cli-port *

    With the port passed, CLI works as a websocket server (--data flag is neglected)

    ---------
    |  BTS  |
    ---------
        |
        |
    ---------    ----------
    |  CLI  |----| CLIENT |
    ---------    ----------

    Remarks:
     - Keeps a connection to the BTS open and listens for new procedures incoming from the client


* --data *

    With the data passed, CLI works this way: send prodcedure -> receive response -> terminate

    ---------
    |  BTS  |
    ---------
        |
        |
    ---------
    |  CLI  |
    ---------

    Remarks:
     - Does NOT keep connection open, terminates once it receives requestStatus=<completed/rejected> with exit code 0, with 1 when an error has occurred

* --input-file *

    Takes relative/absolute of the file as an input

* --output-file *

    Takes relative/absolute of the file as an output

* --format *

    Format JSON output ["compact"|"human"]

----------------------
   CLI server mode
----------------------

* Internal messaging - ADMIN API *

    # REQUEST DEFINITION

    {
        "type": "ADMIN_API",
        "payload": <admin api json request>
    }

    Example:

    {
        type: "ADMIN_API",
        payload: {
            requestId: 1,
            requestType: "procedure",
            parameters: {
                name: "imSnapshot",
                parameters: {
                    outputFileContent: [""|"<base64>"]
                }
            }
        }
    }

    Remarks:
    - requestId should be unique
    - outputFileContent/inputFileContent: an empty string means we want to use an internal file transfer messaging
    - inputFileName: 1.Would be filled with the value of --input-file then injected into the requested parameters.
                     2.This is an reserved property to request parameters.

    # RESPONSE DEFINITION

    {
        type: "ADMIN_API",
        payload: <admin api json response>
    }

    Example:

    {
        type: "ADMIN_API",
        payload: {
            requestId: 1,
            requestStatus: "completed",
            requestMessage: "IM Snapshot has been successfully created",
            outputFileContent: [""|"<base64>"]
        }
    }

Remarks:
- outputFileContent/inputFileContent: an empty string means we used an internal file transfer messaging

* Internal messaging - FILE TRANSFER *

    # READ MESSAGE (server -> client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "READ"
            offset: number,
            length: number
        }
    }

    # READ MESSAGE (server <- client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "READ"
            data: "<base64>"
        }
    }

    # SIZE MESSAGE (server -> client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "SIZE"
        }
    }

    # SIZE MESSAGE (server <- client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "SIZE",
            data: number
        }
    }

    # WRITE MESSAGE (server -> client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "WRITE",
            data: "<base64>"
        }
    }

    # CLOSE READER MESSAGE (server -> client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "CLOSE_READER"
        }
    }

    # CLOSE WRITER MESSAGE (server -> client)

    {
        type: "FILE_TRANSFER",
        payload: {
            id: number,
            type: "CLOSE_WRITER"
        }
    }

Remarks:
 - id should be same a number as requestId

----------------------
       Remarks
----------------------

 - Usage(Example) link: https://onion.wroclaw.nsn-rdnet.net/branches/master/cli-docs/

 - Trouble shooting link: https://confluence.int.net.nokia.com/pages/viewpage.action?pageId=940059182#WebEMCLI(admin-cli)-Troubleshooting
