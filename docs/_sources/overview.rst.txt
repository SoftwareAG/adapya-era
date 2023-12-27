********
Overview
********

*adapya-era* is a client services library to the Event Replicator for Adabas.

The Event Replicator for Adabas is an add-on product to Adabas that allows replicating
database data to other systems. Client programs (also called target adapters) receive
event replication data through a messaging system like MQ series or EntireX Broker.

*adapya-era* can be used to write target adapters in Python.

The package also consists of scripts that can send requests to the Replicator and
receive event data via the EntireX Broker messaging system.

*adapya-era* is part of a set of Python packages including adapya-adabas
a client library for Adabas database access and adapya-entirex a client library
to Entirex Broker



For more information about *Event Replicator for Adabas* see

-   Information of the `Software AG Product
    <https://resources.softwareag.com/adabas-natural/event-replicator-for-adabas-on-the-mainframe>`_

-   `Event Replicator for Adabas documentation
    <http://techcommunity.softwareag.com/ecosystem/documentation/adabas/a_distribution/event_replicator_vers.htm>`_
    (free registered access)

-   `Community forum - code samples
    <http://tech.forums.softwareag.com/techjforum/forums/show/171.page>`_
    for useful information about adapya Python packages

**Notes**

1. Prerequisites for *adapya-era*

   * Python version 2.7 or 3.5 or higher

   * packages adapya-base, adapya-adabas and adapya-entirex

2. The **ctypes** module is required (usually included in Python
   on Windows, Linux and Rocket Python on z/OS from version 2.7.12)


Change History
==============

**adapya-era 1.3.0 (Dec 2023)**

- scripts/outq: improved import of metadata for record output


**adapya-era 1.0.0 (May 2018)**

- Support of Python 3.5 and higher
- adapya split into smaller packages for more independence
- adapya-era now requires packages adapya-base and adapya-entirex


**adapya 0.7** is the first public release.



adapya-era License
==================

Copyright 2004-2023 Software AG

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

