*adapya-era* - services library of the Event Replicator for Adabas


adapya-era
==========

*adapya-era* is a services library of the Event Replicator for Adabas.

The Event Replicator for Adabas is an add-on product to Adabas that allows replicating
database data to other systems. Client programs (also called target adapters) receive
event replication data through a messaging system like MQ series or EntireX Broker.

adapya-era can be used to write target adapters in Python.

The package also consists of scripts that can send requests to the Replicator and
receive event data via the EntireX Broker messaging system.

adapya-era requires the following adapya packages: adapya.adabas, adapya.base
and adapya.entirex

Prerequisite for adapya is Python version 2.7 or 3.5 and above.

Installation
------------

::

    pip install adapya-era


Links
-----

- Documentation for adapya-era: https://softwareag.github.io/adapya-era/index.html
- About Event Replicator for Adabas: https://resources.softwareag.com/adabas-natural/event-replicator-for-adabas-on-the-mainframe
- Community forum: http://tech.forums.softwareag.com/techjforum/forums/show/171.page
- Event Repliator documentation: http://techcommunity.softwareag.com/ecosystem/documentation/adabas/a_distribution/event_replicator_vers.htm
  (free registered access)


License
-------

Copyright 2004-ThisYear Software AG

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.
