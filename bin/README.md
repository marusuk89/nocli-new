na_query is a tool to query BTS IP address from EMS(NetAct) and BTS integration in EMS.

## Usage

### Run CLI command

#### Configuration
Before run command, please configure it properly. Configuration file example is as below, e.g. filename is `na_query.toml`:
```
[[ems]]
alias = ""
lbwas = ""
user = ""
password = ""
default_mr = ""
```

The only configuration needed is to the `ems` entries configuration.

`lbwas` is the NetAct load balancer IP address or hostname.

`user` is the user of NetAct

`password` is the password of `user`

`default_mr` is default MR DN, e.g. MRC-1/MR-1

If there are multiple `ems` to connect, then just add another section like below:
```
[[ems]]
alias = ""
lbwas = ""
user = ""
password = ""
default_mr = ""
```

#### Show help
```
./na_query --help
Usage: na_query --config-file <CONFIG_FILE> <COMMAND>

Commands:
  Usage: na_query --config-file <CONFIG_FILE> <COMMAND>

Commands:
  get-bts-ip   [aliases: ip]
  exe-bts-int  [aliases: int]
  exe-bts-deint  [aliases: deint]
  help         Print this message or the help of the given subcommand(s)

Options:
  -c, --config-file <CONFIG_FILE>  Config file path [env: NA_QUERY_CONFIG_FILE=]
  -h, --help                       Print help
  -V, --version                    Print version
york@dev:/w10/svn/RUST/tools/nbi/lgu/na_query$ ./release/na_query --help
Usage: na_query --config-file <CONFIG_FILE> <COMMAND>

Commands:
  get-bts-ip   [aliases: ip]
  exe-bts-int  [aliases: int]
  help         Print this message or the help of the given subcommand(s)

Options:
  -c, --config-file <CONFIG_FILE>  Config file path [env: NA_QUERY_CONFIG_FILE=]
  -h, --help                       Print help
  -V, --version                    Print version

```
#### Show version
```
./na_query --version
na_query 1.2.0
```

#### get BTS IP
Example to get IP of MRBTS 1234, assume configuration file is in `na_query.toml` file of current directory, run:
```
./na_query --config-file na_query.toml get-bts-ip 1234
```
Or use short parameter
```
./na_query -c na_query.toml ip 1234
```
Or if there is a environment variable `NA_QUERY_CONFIG_FILE=na_query.toml`, then there is not need to provide `--config-file` in cli.
```
export NA_QUERY_CONFIG_FILE=na_query.toml
./na_query ip 1234

```
If succeed, IP will be print to stdout and exit code will be 0.
```
$QUERY = OK; $RESULT = 127.0.0.1
```
```
echo $?
0
```
If not found in any EMS, then IP will be 0.0.0.0 and exit code will be 0
```
$QUERY = OK; $RESULT = 0.0.0.0
```
```
echo $?
0
```
If failed, error reason will be print to stdout and the exit code will not be 0. Failed example:
```
$QUERY = NOK; $REASON = get BTS IP from EMS: 1266 for 22516 failed

Caused by:
    0: failed to get BTS IDs from ems
    1: error sending request for url (https://abc/netact/cm/open-api/persistency/v1/query): error trying to connect: dns error: failed to lookup address information: Name or service not known
    2: error trying to connect: dns error: failed to lookup address information: Name or service not known
    3: dns error: failed to lookup address information: Name or service not known
    4: failed to lookup address information: Name or service not known
```
```
echo $?
1
```

### BTS integration
#### BTS integration help
```
./na_query exe-bts-int --help
Usage: na_query --config-file <CONFIG_FILE> exe-bts-int [OPTIONS] --bts-id <BTS_ID> --ver <VER> --ems <EMS> --ne-ip <NE_IP>

Options:
      --bts-id <BTS_ID>    BTS ID
      --ver <VER>          BTS version, e.g. SBTS25R2
      --ems <EMS>          EMS alias defined in configuration file
      --mr <MR>            The maintenance region (MR), default use default_mr in the EMS configuration
      --ne-ip <NE_IP>      IP address of MRBTS
      --ne-name <NE_NAME>  The network element name presented on the Monitor
      --http <HTTP>        HTTP port where NE3SWS agent is running [default: 8080]
      --https <HTTPS>      HTTPS port where NE3SWS agent is running [default: 8443]
      --tls                NE3SWS agent security mode
  -h, --help               Print help
```

### BTS deintegration
#### BTS deintegration help
```
./na_query exe-bts-deint --help
Usage: na_query --config-file <CONFIG_FILE> exe-bts-deint --bts-id <BTS_ID> --ems <EMS>

Options:
      --bts-id <BTS_ID>  BTS ID
      --ems <EMS>        EMS alias defined in configuration file
  -h, --help             Print help
```

#### log file for debugging
Log file can be found in `/var/tmp/na_query/<yyyy-mm-dd>.log`