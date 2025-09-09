## ADMIN AGENT CLI

Command line client for admin CLI server mode

Main script: agent-cli (agent-cli.sh for Linux and agent-cli.bat for Windows)

System dependencies: none

Operating systems supported: Linux (x64), Windows (Windows 7 x64 or higher version)

----------------------
Command Line Arguments
----------------------

    > ./admin-cli.sh --help

    Options:
      --data         JSON format request                                                                            [string]
      --input-file   File to be included into the request message                                                   [string]
      --output-file  Payload file extracted from the response message                                               [string]
      --cli-host     CLI socket server host                                       [string] [required] [default: "localhost"]
      --cli-port     CLI socket server port                                                              [number] [required]
      -h, --help     Show help                                                                                     
      -v, --version  Show version number                                                                           

* --cli-host

    admin-cli server IP address (IPv4 or IPv6)

    Remarks:
    - IPv6 format should have such a syntax e.g --cli-host="[0:0:0:0:0:ffff:c0a8:ff01]"

* --cli-port

    admin-cli server PORT

* --data

    With 'data' passed, Agent CLI works this way: send procedure -> receive response -> terminate

* --deployment diagram
    
    <pre>
        ---------
        |  BTS  |
        ---------
            |
            |
        ---------------------
        |  CLI SERVER MODE  |
        ---------------------
            |
            |
        ---------------
        |  AGENT CLI  |
        ---------------
    </pre>

