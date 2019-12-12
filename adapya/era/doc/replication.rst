Event Replication for Adabas
============================

The adapya-era implements the messaging API for the mainframe Event
Replicator for Adabas using EntireX broker.



The Event Replication for Adabas (ARF) is an add-on product to Adabas
that allows replicating database data to other systems. Client programs
(also called target adapters) receive event replication data through a
messaging system like MQ series or EntireX Broker.

In the following the command line clients and the Emptel sample
replication with Adabas to Adabas replication via Entire X are
described.



Additional Prerequisites
------------------------

Install

-  EntireX V7.1 or higher
-  alternatively install the entirexminiruntime.exe
   On Windows this file can be found in the EntireX/Etc/ folder.
   Optionally unzip the file Control.zip in the EntireX/Etc/ folder.
   This zip file contains the EntireX control center GUI program that
   allows to view and control the status of EntireX broker and its
   resources.



outq.py - Reptor Output Queue Client
------------------------------------

outq.py listens to the Reptor output queue and prints each Reptor
message according to its interpreted URB\* blocks.

The program is terminated by CTRL-C or when some severe Broker return
code occurs.
::

 > outq.py -h

 outq.py -- Reptor output queue reader
 Reads messages from the Reptor output queue
 via EntireX Broker ACI call interface
 and prints the data

 Usage: python [-O] outq.py [options]

 -O run optimzied, debug code not generated

 do not display interpreded URB\*

 Options:
 -h, --help display this help

 -b, --broker .. id of broker ETBxxxxx or hostname:port

 -c, --class .. server class

 -n, --name .. server name

 -s, --service .. service (Reptor output queue)

 -u, --userid .. user id to be used

 -t, --trace .. sum of trace flags

 1 - dump buffers before Broker call

 2 - after call

 4 - print broker calls

 8 - detailed print of URB buffers

 Example:
 python outq.py -b ETB50019 -u MM -s MMSERV


inq.py - Reptor Input Queue Client
----------------------------------

inq.py sends input requests to the Reptor and terminates.


The following input requests are defined:

- Status
- Initial-state-request
- Prior-transaction request

::

 >inq.py

 ---- inq.py -- Reptor input queue writer ----

 Write messages to the Reptor input queue via EntireX Broker ACI call interface

 Usage: python inq.py [options]

 Options:

 -h, --help display this help
 -b, --brokerid .. id of broker ETBxxxxx or hostname:port
 -c, --class .. server class
 -n, --name .. server name
 -s, --service .. service (Reptor input queue)
 -u, --userid .. user id to be used
 -k, --token token
 -r, --rnam .. response destination name
 -e, --arc .. architecture of input URB\* and of data

 is the integer of the sum of
 0/1 - high/low order byte first
 0/2 - ASCII/EBCDIC
 0/4/8 - IBM390/VAX/IEEE floating point

 -t, --trace .. sum of trace flags
 1 - dump buffers before Broker call
 2 - after call
 4 - print broker calls

 for type subscription status (STAT)
 -p, --snam .. subscription
 -d, --dnam .. destination

 for type Prior transaction request (TRAN)
 -p, --snam .. subscription
 -d, --dnam .. destination
 -q, --tseq .. transaction sequence number

 for type Initial-state request (INST)
 -a --dbid .. database id
 -f --fnr .. file number or fnr_list (see below)
 -i --inam .. initial-state name
 -l --isnl .. ISN or isn_list (see below)
 -v --value value_string for selection criteria
 -g --acode .. encoding of alpha values in value_string
 -w --wcode .. encoding of wide values in value_string

 An encoding is specified as cpX with

 X = ECS code page number, e.g. cp37 for US EBCIDIC code page 37,
     or as a name defined in ecscodec.py, e.g. utf8 for ECS code
     page 4091)

 fnr_list list of files for which initial state is to be requested

 e.g. (1,2,3,4) requests it for files 1-4

 no space can be within the parenthesises otherwise it must be
 surrounded by double quotes


 isn_list list of ISNs or ISN ranges surrounded by parenthesis. e.g.

   (1,2,3,4,10-1000,2001-2999,9999)

 No spaces allowed unless list enclosed in double quotes


 value_string value string matching the selection criterion defined
 in the INIITALSTATE parameters. A sequence of values can be
 specified by enclosing the comma separated values with parenthesis.
 No spaces allowed unless enclosed in double quotes. In addition a
 sequence element may be also:

   x'hexvalue' for a hexadecimal value
   e'string' for a string to be converted to EBCDIC

 Examples:

 python inq.py -b ETB50019 -u MM -c REPTOR -n MMSERV -s IN1 -d OUT1

 python inq.py -b ETB50019 --userid MM --class REPTOR --name MMSERV --service IN1 -dnam OUT1


 python inq.py -b ETB50019 --userid MM --class REPTOR --name MMSERV --service IN1 --rnam OUT1 --token TOKTOK
    --inam ICOLOR --dbid 12345 --fnr (1,2)
                                     ----- = file\_list

 python inq.py ... --isnl (1,2,3,11-20,25)     requests initial state for ISNs 1,2,3 11 thru 20 and 25

 python inq.py ... --value (GR001,x'89AB',e'"ABC "') or alternatively "(GR001,x'89AB',e'ABC ')"

    with value being composed of 'GR001',x'89AB',x'C1C2C340'

 python inq.py ... --value "A B " --arc 9 --acode cp1252 --wcode utf8



Demo Application Employee Telephone List
----------------------------------------

The demo application processes the replication for the Adabas example
file EMPLOYEE.

In the Reptor definitions the format EMPLTEL defines a subset of the
original EMPLOYEE fields. This shows how to reduce overhead in only
replicating required information or how to hide sensitive information.


Reptor Parameters
^^^^^^^^^^^^^^^^^
::

 ADARPD SUBSCRIPTION NAME=EMPLOYEE
 ADARPD   SACODE=819,SWCODE=4091,SARC=9
 ADARPD   SDESTINATION='OUT1'
 ADARPD   SFILE=11,SFDBID=10006
 ADARPD   SGFORMATAI=EMPLTEL

 ADARPD GFORMAT NAME=EMPLTEL Fields extracted for Telephone List Webapp
 ADARPD GFB='AA,AC,AD,AE,' PERSONNEL-ID FIRST-NAME MIDDLE LAST-NAME
 ADARPD GFB='AH,8,U,AL,' BIRTH COUNTRY
 ADARPD GFB='AN,AM,AO,AP.' AREA-CODE PHONE DEPT JOB-TITLE


Configuration
^^^^^^^^^^^^^

The following lines configure the client program - see out1Config.py:
::

 # define the mapping of data in record buffer to attributes
 # of EmpTel class

 empTelFormat='AA,AC,AD,AE,AH,8,U,AL,AN,AM,AO,AP.'

 # create datamap object for Employees-Telephone-List

 emp=Datamap('EmplTel',
     String('personnel\_id', 8),
     String('firstname', 20),
     String('m\_initial', 20),
     String('lastname', 20),
     String('birth', 8),
     String('country', 3),
     String('areacode', 6),
     String('phone', 15),
     String('department', 6),
     String('jobtitle', 25)
     )

 # define formats and mapping for each file specified in subscription
 psf=ParmsSfile(sdbid=10006,sfnr=9,tdbid=12,tfnr=7,
                fb=empTelFormat,dmap=emp)

 # define subscription with all its sfiles defined
 psu=ParmsSubscription(subscription='EMPLOYEE',sversion='01',sfiles=[psf])

 # define Reptor Broker parameters
 pbs=ParmsBrokerService(
     broker_id='ETB50019',
     server_class='REPTOR',
     server_name='MMSERV',
     service='OUT1',
     user_id='UEmplTel')


Intial-State Request for Selected Records
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following requests Initial-state for the EMPLOYEE file selecting
records 20002000 through 20003999::

 >python inq.py --inam IEMPLAA --dbid 10006 --fnr 9
                --value 2000200020003999
                --acode cp819 --wcode utf8 --arc 9
                --rnam OUT2 --token TOKTOTOK


Trace of Client Processing a Record
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

 >python rcOut1.py

 URBR -- initial state record fnr 9 isn 828

 URBD(1) after image
 0000 32303030 32393030 544F4D20 20202020 20002900TOM
 0010 20202020 20202020 20202020 20202020
 1 identical line(s) suppressed
 0030 44494C57 4F525448 20202020 20202020 DILWORTH
 0050 31303120 20283231 39293436 342D3234 101 (219)464-2
 0060 32312020 4D474D54 31305345 43524554 21 MGMT10SECRE
 0070 41525920 20202020 20202020 20202020 ARY
 0080 202020

 Enter URBD handler: R A, isn 828
 cmd=E1 op1/2= / dbid=12 fnr=7 rsp=113
 cid= isn=828 isl=0 isq=0

 Note: Before Image not found ISN 828

 cmd=N2 op1/2= / dbid=12 fnr=7 rsp=0
 cid= isn=828 isl=0 isq=0

 Exit URBD handler: R A, isn 828/828, num recs 18

 URBE -- end of transaction 0 for subscription EMPLOYEE

 Enter URBE handler: EMPLOYEE tsnr 0, in TA 1, cnt 9
 End Transaction 0 for subscription EMPLOYEE with 9 updates

 cmd=ET op1/2= / dbid=12 fnr=7 rsp=0
 cid= isn=828 isl=0 isq=0

 Exit URBE handler: EMPLOYEE, tsnr 0, in TA 0, cnt 9


Reading the Replicated File on the Target Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The replicated records can be read in the target database with the adapya-adabas script search.py

::

  > search -d 12 -f 7 --read ISN --format AA,2X,AC,12,AE,15,AH,8,U,AL,AN,AM,AO,AP.

  1     1 50005500 ALEXANDRE   BRAUN          00550626F  1033  42452720       VENT56 CHEF DE SERVICE
  2    10 50007600 JEAN-MARIE  MARX           00490426F  1033  40738871       MARK06 DIRECTEUR COMMERCIAL
  3    11 50003500 MARC        LEROUGE        00510823F  1033  47894194       COMP70 CONTROLEUR DE GESTION
  4    12 50003300 ANDRE       GRUMBACH       00480320F  1033  45487063       COMP73 CONTROLEUR DE GESTION
  5    13 50003100 MICHEL      HEURTEBISE     00421118F  1033  45482056       COMP01 CONTROLEUR DE GESTION
  6    14 50003000 JEAN-CLAUDE REISKEIM       00550816F  1033  48477160       VENT30 CONTROLEUR DE GESTION
  7    15 50002900 JACQUELINE  REIGNARD       00520615F  1033  48472153       VENT29 CONTROLEUR DE GESTION
  8    16 50002700 PAUL        GUELIN         00490112F  1033  46065022       VENT27 CONTROLEUR DE GESTION


