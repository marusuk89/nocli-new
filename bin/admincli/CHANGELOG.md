# Admin API changelog
## 3.4.6
- rollback to svn

## 3.4.5
- fix admin-cli.bb for CB

## 3.4.4
- send cli tool zips to artifactory instead of svn

## 3.4.3
- improve event handling for win32

## 3.4.2
- add relnotes of SBTS25R1

## 3.4.1
- enable 24R3 to take this CLI version

## 3.4.0
- upgrade to nodejs 20.17.0

## 3.3.14
- modify example back to legacy format

## 3.3.13
- move migrateScf exmaple

## 3.3.12
- add permission for script

## 3.3.11
- modify incorrect examples

## 3.3.10
- add check.ghc in verification pipeline

## 3.3.9
- add validation for input and output files

## 3.3.8
- add generateNokiaCompliantORUSWPackage example

## 3.3.7
- upgrade nodejs version to 18.20.4

## 3.3.6
- CB009447-B support inputfiles

## 3.3.5
- add support for lazy file output

## 3.3.4
- add relnotes of SBTS24R3 and SBTS24R3_FSM

## 3.3.3
- CB012204/CNI-116183 fix bug of version request for legacy bts(24R1 or before), need to use post request instead of get request

## 3.3.2
- CB010780 - Support fetch extra bpf in CLI

## 3.3.1
- CB012204 change RD api originator to RD_API

## 3.3.0
CNI-116183 - Fix "Session token in URL" issue reported from Burp scan

## 3.2.10
- remove check message in CI

## 3.2.9
- upgrade node version to 18.20.3

## 3.2.8
- upgrade node version to 18.20.2

## 3.2.7
- PR763210: [PET][FiVe] Admin CLI operations timeout in CLI server mode (websocket)

## 3.2.6
- upgrade node version to 18.20.0

## 3.2.5
- add relnotes of SBTS24R2

## 3.2.4
- fix verify.bitbake job by workaround in verifyBB.sh to adapt yocto env after poky update
-
## 3.2.3
- Add mandatory log for cli info

## 3.2.2
- reverts version 3.2.1

## 3.2.1
- Add mandatory log for cli info

## 3.2.0
- upgrade node version to 18.19.0

## 3.1.7
- add relnotes of SBTS00_FSM3

## 3.1.6
- update bb files for CB012664 poky update; add relnotes of SBTS24R1

## 3.1.5
- revert 3.1.4

## 3.1.4
- update bb files for CB012664 poky update

## 3.1.3
- update release to wft job and make SBTS23R4 take this version via PR730348

## 3.1.2
- make SBTS23R4 take this version via PR730348

## 3.1.1
- add encode-type validation for cli

## 3.1.0
- make it compatible with SBTS23R1 bundle

## 3.0.5
- adapt outputjson stream

## 3.0.4
- hot fix gerrit commit message for svn.

## 3.0.3
- use gerrit commit message for svn.

## 3.0.2
- improve CI bitbake verify

## 3.0.1
- fix WFT ENB integration issue

## 3.0.0
- upgrade to nodejs18 compatible with nodejs16

## 2.8.32
- revert 2.8.30

## 2.8.31
- add relnotes of SBTS23R4

## 2.8.30
- adapt source code for nodejs18 while remaining nodejs to v16

## 2.8.29
- modify svn commit message format

## 2.8.28
- revert node from 18.16.0 to 16.5.0

## 2.8.27
- upgrade error and exception handling

## 2.8.26
- upgrade webpack to 5.64.1

## 2.8.25
- fix release job in pipeline

## 2.8.24
- implement nrm in pipeline

## 2.8.23
- upgrade nodejs version to 18.16.0

## 2.8.22
- add node version log

## 2.8.21
- add relnotes of SBTS23R3

## 2.8.20
- add cliPerformanceEnhance flag

## 2.8.19
- support close server from agent request

## 2.8.18
- add require bundle file error note and node version checking.

## 2.8.17
- update release bitbake script

## 2.8.16
- update release bitbake script
-
## 2.8.15
- fix "write after end" error when add --debug and api command is failed

## 2.8.14
- add relnotes of SBTS23R2

## 2.8.13
- upgrade nodejs from 12 to 16

## 2.8.12
- add relnotes of SBTS23R1

## 2.8.11
- add relnotes of SBTS22R4

## 2.8.10
- update api saveAntlMonitoringData

## 2.8.9
- add api saveAntlMonitoringData

## 2.8.8
- update pipeline.json to v3.5

## 2.8.7
- add SCBT in CI

## 2.8.6
- add client tool limitation of imsFromCurrentSession request when disconnect in server mode and relnotes of SBTS22R1, SBTS22R2, SBTS22R3.

## 2.8.5
- add change node of 2.8.4

## 2.8.4
- add milliseconds to logs

## 2.8.3
- add option "--encodeType"

## 2.8.2
- update release note version to 12

## 2.8.1
- add coop promotion support
- promotion tag prefix is used in ci/promotion.json

## 2.8.0
- add 3600 port since CB007672

## 2.7.14
- add coop support

## 2.7.13
- fix CI bitbake script issue

## 2.7.12
- add es5 file

## 2.7.11
- remove node modules

## 2.7.10
- add UTs

## 2.7.9
- add login bundle path

## 2.7.8
- add 5G21A branch tag

## 2.7.7
- add SBTS21A branch tag

## 2.7.6
- add time stamp for cli log in cli log file

## 2.7.5
- add log in xhr2 when http error occurred.

## 2.7.4
- remove message 'fetch login bundle error'

## 2.7.3
- update author email address to I_NSB_MN_BTSOAM_RD_OM_OMUI_ADMIN_CLI@internal.nsn.com

## 2.7.2
- update admin-cli-5g, admin-cli-5gdu bb files, copy bundle.js or bundle.*.js to ${NOKIA_PACKAGE_DESTDIR}/bundle.js(since PR556690)

## 2.7.1
- add admin-cli-5g, admin-cli-5gdu bb files

## 2.7.0
- fetch login bundle

## 2.6.6
- add 5G00 branch tag

## 2.6.5
- the getSfpData.sh, getSfpData.bat should change to sfpData.sh, sfpData.bat

## 2.6.4
- release main.bundle.js to "./bin" (since PR541507)

## 2.6.3
- add IPv6 instruction into rd-readme

## 2.6.2
- fix the dirname for webpack

## 2.6.1
- update Operating systems supported description, insecure not supported by PR515918 in readme

## 2.6.0
- add webpack for package admin-cli

## 2.5.15
- since 5GC001866, When --input-file is passed, inputFileName would be injected to requested parameters so that corresponding API code would be able to know what file name is passed by the user.

## 2.5.14
- upgrade yargs

## 2.5.13
- increase fetch bundle timeout

## 2.5.12
- add verify-bitbake ci step after make tag

## 2.5.11
- add release-bitbake-to-wft.sh file

## 2.5.10
- update dependencies 'request' to 'node-fetch', reinstall npm

## 2.5.9
- fix log.warn instead of log.info(since PR515180)

## 2.5.8
- add error handling for unhandled rejection and uncaught exception(since PR515180)

## 2.5.7
- suppress node tls warnings

## 2.5.6
- update client readme, bts-port remarks

## 2.5.5
- update client readme, rd readme file

## 2.5.4
- collect ims2 when cli server disconnect

## 2.5.3
- add outputFileName in output of agent-cli when --output-file is specified in agent-cli(since PR494460)

## 2.5.2
- Removed option "--timeout" from "--help" (since PR492507)

## 2.5.1
- Add -x right to agent-cli.sh

## 2.5.0
- update node version from v10.15.0 to v12.13.0
- Support TLS 1.3

## 2.4.3
- cli parameters refactoring
- use terser instead obsolete uglify-js-es6

## 2.4.2
- bump agent-cli to version 1.0.2

## 2.4.1
- fix linux version

## 2.4.0
- updated yargs to version 13.2.2
- updated ws to version 6.2.1
- auto allocating cli-port when provided as 0

## 2.3.5
- add parameter --timeout

## 2.3.4
- fix for working with paths consist spaces in linux os

## 2.3.3
- Add Agent-cli command line client for admin-cli server mode

## 2.3.2
- fix for working with paths consist spaces in windows os

## 2.3.1
- update node from version v8.11.2 to v10.15.1
- fix missing secp384r1 elliptical curve in ssl ClientHello message

## 2.2.13
- revert backward compatibility removed in 2.2.6

## 2.2.12
- add version info in debug log

## 2.2.11
- enable server mode for client cli
- add usage of migrateScf in readme file

## 2.2.10
- revert remove base64 outputfile for client version

## 2.2.9
- remove base64 outputfile for client version

## 2.2.8
- add plan-scf-file and rat-scf-file parameters.
- Auto removing old bundles if the number exceeds 100.

## 2.2.7
- Correct handling of JSON input with spaces.

## 2.2.6
- Remove legacy code + remove "CLI LOG:" prefix from logs.

## 2.2.5
- Output file added to client help

## 2.2.4
- Changelog added

## 2.2.3
- Fix name for WFT

## 2.2.2
- Logging improvements

## 2.2.1
- Graceful shutdown on ctrl-c
- Log args + graceful server close
