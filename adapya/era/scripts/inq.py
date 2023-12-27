#! /usr/bin/env python
# -*- coding: latin1 -*-
""" ---- inq.py -- Reptor input queue writer ----

 Write messages to the Reptor input queue
 via EntireX Broker ACI call interface

 Usage: python inq.py [options]

 Options:
    -h, --help              display this help
    -b, --broker ..         id of broker ETBxxxxx or hostname:port

    -c, --class ..          server class
    -n, --name ..           server name
    -s, --service ..        service (Reptor input queue)
                              short form: -s class/server/service
    -u, --userid ..         user id to be used
    -x, --password ..       password to be used
    -k, --token             token
    -r, --rnam ..           response destination name
    -e, --arc ..            architecture of input URB* and of data
                              is the integer of the sum of
                              0/1 - high/low order byte first
                              0/2 - ASCII/EBCDIC
                              0/4/8 - IBM390/VAX/IEEE floating point

    -t, --trace ..          sum of trace flags
                            1 - dump buffers before Broker call
                            2 -              after call
                            4 - print broker calls
    for type close destination (CLSD)
    -C, --close             close destination
    -d, --dnam ..           destination

    for type open destination (OPND)
    -o, --open              close destination
    -d, --dnam ..           destination

    for type subscription status (STAT)
    -p, --snam ..           subscription
    -d, --dnam ..           destination

    for type Prior transaction request (TRAN)
    -p, --snam ..           subscription
    -d, --dnam ..           destination
    -q, --tseq ..           transaction sequence number

    for type Initial-state request (INST)
    -a  --dbid ..           database id
    -f  --fnr  ..           file number or fnr_list (see below)
    -i  --inam ..           initial-state name
    -l  --isnl ..           ISN or isn_list (see below)
    -v  --value             value_string for selection criteria
    -g  --acode ..          encoding of alpha values in value_string
    -w  --wcode ..          encoding of wide values in value_string
                            An encoding is specified as cpX with
                              X = ECS code page number, e.g. cp37 for
                              US EBCIDIC code page 37, or
                              as a name defined in ecscodec.py, e.g.
                              utf8 for ECS code page 4091)

    fnr_list                list of files for which initial state
                            is to be requested
                            e.g. (1,2,3,4) requests it for files 1-4
                            no space can be within the parenthesises
                            otherwise it must be surrounded by double
                            quotes

    isn_list                list of ISNs or ISN ranges surrounded by
                            parenthesis. e.g.
                              (1,2,3,4,10-1000,2001-2999,9999)

                            Chunked mode (see blow for details):
                                chunky=<maxisn>,<csize>,<ta-file>

                            No spaces allowed unless list enclosed in
                            double quotes

    value_string            value string matching the selection
                            criterion define in the INIITALSTATE
                            parameters. A sequence of values can be
                            specified by enclosing the comma separated
                            values with parenthesis. No spaces allowed
                            unless enclosed in double quotes. In
                            addition a sequence element may be also:
                            x'hexvalue' for a hexadecimal value
                            e'string'   for a string to be converted
                                        to EBCDIC
    -T <convid>             Send termination message to output queue
Examples:
'inq' in short for 'python inq.py'

Requesting Initial State
------------------------

inq -b ETB50019 -u MM -s REPTOR/MMSERV/IN1 -d OUT1

inq -b ETB50019 --userid MM --class REPTOR --name MMSERV
    --service IN1 --dnam OUT1

inq -b ETB50019 --userid MM --class REPTOR --name MMSERV
    --service IN1 --rnam OUT1 --token TOKTOK
    --inam ICOLOR --dbid 12345 --fnr (1,2)
                                     ----- = file_list
inq ... --isnl (1,2,3,11-20,25)
    requests initial state for ISNs 1,2,3 11 thru 20 and 25

inq ... --value (GR001,x'89AB',e'"ABC "') or alternatively
               "(GR001,x'89AB',e'ABC ')"
        with value being composed of 'GR001',x'89AB',x'C1C2C340'

inq ... --value "A B " --arc 9 --acode cp1252 --wcode utf8


Initial state chunky mode
-------------------------

The processing will be split in se1.3.0 initial state chunks. The
next chunk will only be requested once the previous is completed as
reported on the target adapter log file.

This generates a series of initial state requests initiated
by the --isnl/-i parameter of the form:

  chunky=<maxisn>,<csize>,<ta-log>

  with maxisn = total number of ISNs to process
       csize  = number of ISNs per request
       ta-log = target adapter sequential message file for
                Initial state completion message
Example:

  --isnl chunky=1000000,10000,c:/temp/art.log


Requesting STATUS for destination/subscription
----------------------------------------------

inq --dnam OUT4 --snam PEMU --rnam OUT1 -b host:1234 -u MM -s REPTOR/MMSERV/IN1
    requests status to OUT1 for subscription PEMU on destination OUT4


Requesting OPEN/CLOSE for destination
-------------------------------------

inq --open --dnam OUT4 --rnam OUT1 -b host:1234 -u MM -s REPTOR/MMSERV/IN1
    requests OPEN destination OUT4 with response to OUT1

inq --close --dnam OUT4 --rnam OUT1 -b host:1234 -u MM -s REPTOR/MMSERV/IN1
    requests CLOSE destination OUT4 with response to OUT1

$Date: 2018-06-19 18:08:48 +0200 (Tue, 19 Jun 2018) $
$Rev: 840 $
"""
from __future__ import print_function          # PY3

import sys, time, getopt
from adapya.base import datamap
from adapya.era import reptor
from adapya.entirex.broker import Broker,OPT_COMMIT

tap=0       # set to 1 for Target Adapter
msgn=0

if sys.hexversion > 0x03010100:
    long = int

def reqOpen(dest='', rdest='', token=''):
    global bb
    reptor.makeURBH(bb.send_buffer,msgNo=msgn)
    slen=reptor.requestOpenDest(token=token,destination=dest,rspDest=rdest)
    bb.send_length=slen
    bb.send(conv_id='NEW',option=OPT_COMMIT)

def reqClose(dest='', rdest='', token=''):
    global bb
    reptor.makeURBH(bb.send_buffer,msgNo=msgn)
    slen=reptor.requestCloseDest(token=token,destination=dest,rspDest=rdest)
    bb.send_length=slen
    bb.send(conv_id='NEW',option=OPT_COMMIT)

def reqPrior(dest='', rdest='', subs='',token='', tseq=0):
    global bb
    reptor.makeURBH(bb.send_buffer,msgNo=msgn)
    slen=reptor.requestPriorTrans(token=token,
      destination=dest,subscription=subs,rspDest=rdest,transSeqno=tseq)
    bb.send_length=slen
    bb.send(conv_id='NEW',option=OPT_COMMIT)


def reqStatus(dest='', rdest='', subs='',token=''):
    global bb
    reptor.makeURBH(bb.send_buffer,msgNo=msgn)
    slen=reptor.requestStatus(token=token,
      destination=dest,subscription=subs,rspDest=rdest)
    bb.send_length=slen
    bb.send(conv_id='NEW',option=OPT_COMMIT)


def reqInst(rdest='',token='',instname='', dbid=0, fnr=[], isnl=[], value=''):
    global bb, acode, wcode, arc

    if acode=='' and wcode=='' and arc==2:
        arcd=0
    else:
        arcd=arc

    reptor.makeURBH(bb.send_buffer,msgNo=msgn)

    for f in fnr:
        print('file',f)
        slen=reptor.requestInst(rspDest=rdest,token=token,
          instname=instname,dbid=dbid,fnr=f,isnl=isnl,value=value,
          arc=arcd,acode=acode,wcode=wcode)

    bb.send_length=slen
    bb.send(conv_id='NEW',option=OPT_COMMIT)

def reqTerminat(convid='NEW'):
    # tell reader of output queue to end
    global bb
    bb.send_buffer.write('terminat')
    bb.send_length=8
    bb.send(conv_id=convid,option=OPT_COMMIT)


def chunked( rdest='',token='',instname='', dbid=0, fnr=[], maxisn=0, chunks=0, talog=''):
    global bb, acode, wcode, arc, msgn

    if acode=='' and wcode=='' and arc==2:
        arcd=0
    else:
        arcd=arc

    fd=open(talog)  # open Targe Adapter log file

    loglines = follow(fd)  # lines generator

    for i in range(1,maxisn+1,chunks):
        reptor.makeURBH(bb.send_buffer,msgNo=msgn)

        isnl=([i,min(i+chunks-1,maxisn)],)    # a list in a list

        slen=reptor.requestInst(rspDest=rdest,token=token,
          instname=instname,dbid=dbid,fnr=fnr[0],isnl=isnl,
          arc=arcd,acode=acode,wcode=wcode)

        bb.send_length=slen
        bb.send(conv_id='NEW',option=OPT_COMMIT)
        msgn+=1

        for line in loglines:
            if IS_ended(line,instname):
                break # try to start next initial state

def follow(fd):
    fd.seek(0,2)      # Go to the end of the file
    while True:
         line = fd.readline()[:-1] # line w/o linefeed
         if not line:
             time.sleep(0.3)    # Sleep a short sec
             continue
         yield line

def IS_ended(line,isname):
    if tap:
        print('=out=', line)
        if line.startswith('ART0304I'):
            # verify right Dbid, Fnr and Istate
            return True
    else:
        l = line.lstrip()
        if l.startswith('URBS') or l.startswith('URBT') \
                or l.startswith('subs'):
            print('=out=', line)
            if line.startswith('URBS') and \
                  line.endswith('Initial-state processing completed'):
                return True
    return False

bb=Broker(receive_length=100,send_length=2048)
#bb.trace=1 # dump buffers before Broker calls
#bb.trace=2 # dump buffers after Broker calls
bb.trace=4 # print Broker calls


bb.broker_id=''     # BKR50019 'ETB034'
bb.user_id='MM-Input'

bb.server_class=''
bb.server_name =''
bb.service     ='service'

stype=1 # request type: 2 (TRAN), 3 (OPND), 4 (CLSD), 5 (terminat),  1 (STAT) or 0 (INST)
token='inq.py'

rnam=''  # response destination name
snam=''  # subscription name
dnam=''  # destination name

conv='NEW' # conversation id

tseq=0

inam=''
dbid=0
fnr=[]
isnl=[] # isn list
value=''

chunky=0    # for piecemeal initial states
maxisn=0    # total number of ISNs
talog=''    # target adapter log file

if sys.byteorder == 'little':
    arc=1                       # low oder byte first

else:
    arc=0

if 'A' == '\xC1':
    arc+=2                      # EBCDIC
    datamap.dataIsEbcdic=0

datamap.setNativeByteOrder()
acode=''
wcode=''
pwd=None

try:
    opts, args = getopt.getopt(sys.argv[1:],
      'hb:c:Cn:s:u:k:or:p:d:a:f:i:l:v:t:T:e:g:w:q:x:',
      ['help','broker=','class=','close',
       'name=','service=','userid=','token=',
       'open','rnam=','snam=','dnam=',
       'dbid=','fnr=','inam=','isnl=','value=',
       'trace=','arc=','acode=','wcode=','tseq=','password='])
except getopt.GetoptError:
    print(__doc__)
    print(sys.argv, opts, args)
    sys.exit(2)

for opt, arg in opts:
    if opt in ('-h', '--help'):
        print(__doc__)
        sys.exit()
    elif opt in ('-b', '--broker'):
        bb.broker_id=arg
        print('broker id is now', bb.broker_id)
    elif opt in ('-c', '--class'):
        bb.server_class=arg
    elif opt in ('-C', '--close'):
        if stype != 1:
            print('Conflicting parameters --close/--open (-C/-o)\n\tTerminating.')
            sys.exit()
        stype=4
    elif opt in ('-o', '--open'):
        if stype != 1:
            print('Conflicting parameters --close/--open (-C/-o)\n\tTerminating.')
            sys.exit()
        stype=3
    elif opt in ('-n', '--name'):
        bb.server_name=arg
    elif opt in ('-s', '--service'):
        sss=arg.split('/')      # --service class/server/service
        del sss[3:]             # skip any excessive items
        bb.service=sss.pop()
        if sss:
            bb.server_name=sss.pop()
            if sss:
                bb.server_class=sss.pop()
    elif opt in ('-u', '--userid'):
        bb.user_id=arg
    elif opt in ('-x', '--password'):
        pwd=arg
    elif opt in ('-t', '--trace'):
        bb.trace=int(arg)
    elif opt in ('-T',):
        if stype != 1:
            print('Conflicting parameters (-T)\n\tTerminating.')
            sys.exit()
        stype=5
        conv=arg    # set converstation ID
    elif opt in ('-k', '--token'):
        token=arg
    elif opt in ('-r', '--rnam'):
        rnam=arg
    elif opt in ('-e', '--arc'):
        arc = int(arg)
        if arc&2:
            datamap.dataIsEbcdic=1
        if not arc&1:
            datamap.setNetworkByteOrder()
    elif opt in ('-p', '--snam'):
        snam=arg
    elif opt in ('-d', '--dnam'):
        dnam=arg
    elif opt in ('-i', '--inam'):
        inam=arg
    elif opt in ('-g', '--acode'):
        acode=arg
    elif opt in ('-w', '--wcode'):
        wcode=arg
    elif opt in ('-q', '--tseq'):
        tseq=int(arg)
    elif opt in ('-a', '--dbid'):
        dbid=int(arg)
    elif opt in ('-f', '--fnr'):
        if arg[0]=='(':
            # print(eval(arg))
            fnr+=eval(arg)
        else:
            fnr.append(int(arg))

    elif opt in ('-l', '--isnl'):  # isn or isn list
        if arg[0]=='(':
            # print(eval(arg))
            isns=arg[1:-1]
            L1 = isns.split(',')
            for i in L1:
                L2 = i.split('-')
                if len(L2) == 2:
                    isnl.append([long(L2[0]), long(L2[1])]) # ISN ranges
                else:
                    isnl.append(long(L2[0]))               # single ISN

        elif arg.startswith('chunky='):
            a = arg.split('=')[1].split(',')
            maxisn, chunks, talog = int(a[0]), int(a[1]), a[2]

        else:
            isnl.append(long(arg))

    elif opt in ('-v', '--value'):
        L1=[]
        if arg[0]=='(':                              # list of values
            L1 = arg[1:-1].split(',')
        else:
            L1.append(arg)

        for s in L1:
            if len(s)>3:
                if (s.startswith("X'") or s.startswith("x'")) \
                    and s.endswith("'") :
                    import binascii
                    value+=binascii.unhexlify(s[2:-1])
                elif (s.startswith("E'") or s.startswith("e'")) \
                    and s.endswith("'") :
                    from adapya.base import conv
                    value+=conv.str2ebc(s[2:-1])
                else:
                    value+=s
            else:
                value+=s
        print('value = \t', value)

#for sfnr in args:
#    fnr.append(int(sfnr))


print('\n -- Reptor input queue writer --\n')
print(' broker_id = \t', bb.broker_id)
print(' user_id = \t', bb.user_id)

print('\n server_class =', bb.server_class)
print(' server_name = \t',bb.server_name)
print(' service = \t',bb.service)

print(' token = \t',token)
print(' resp. dest. = \t', rnam)
print(' arc = \t\t', arc)

print(' trace = \t',bb.trace)


if stype == 3 and dnam: # OPND
    print('\n Open request for destination =', dnam)
elif stype == 4 and dnam: # CLSD
    print('\n Close request for destination =', dnam)
elif stype == 5 and conv:
    print('\n Terminate target adapter conversation =', conv)
elif stype == 1: # not yet determined
    if snam > ' ' or dnam > ' ':
        if tseq >0:
            stype = 2 # 'TRAN'
            print('\n Prior transaction request (TRAN) for')
            print(' transaction  = \t', tseq)
            print(' subscription = \t', snam)
            print(' destination  = \t', dnam)

        else:
            stype = 1 # 'STAT'
            print('\n Status request (STAT) for')
            print(' subscription = \t',snam)
            print(' destination = \t', dnam)

    elif inam > ' ' or (dbid > 0 and fnr > 0):
        stype = 0 # 'INST'
        print('\n Initial-state request (INST) for')
        print(' istate name = \t',inam)
        print(' dbid = \t', dbid)
        print(' fnr = \t', fnr)
        print(' isnl =\t', isnl)
        print(' acode =\t', acode)
        print(' wcode =\t', wcode)
        if len(value) > 0:
            dump(value,header=' value =',prefix='   ')
    else:
        print(__doc__)
        sys.exit(2)
else:
    print(__doc__)
    sys.exit(2)


# sys.exit() # test

print('\n Version=%s' % bb.version())

print('\nKernel %s with kernelsecurity=%s' % (
    bb.kernelVersion(), bb.kernelsecurity))

bb.logon(password=pwd)

# detect invalid class/server/service
bb.register()
bb.deregister()

if stype==1:
    reqStatus(token=token,rdest=rnam,dest=dnam,subs=snam)
elif stype==2:
    reqPrior(token=token,rdest=rnam,dest=dnam,subs=snam,tseq=tseq)
elif stype==3: # OPND
    reqOpen(token=token,rdest=rnam,dest=dnam)
elif stype==4: # CLSD
    reqClose(token=token,rdest=rnam,dest=dnam)
elif stype==5: # terminat
    reqTerminat(convid=conv)

elif talog: # chunky mode for initial state by ISN
    chunked(token=token,rdest=rnam,
            dbid=dbid,fnr=fnr,instname=inam,
            maxisn=maxisn,chunks=chunks,talog=talog)
else:
    reqInst(token=token,rdest=rnam,
            dbid=dbid,fnr=fnr,instname=inam,
            isnl=isnl,value=value)
if stype!=5:
    bb.logoff()
else:
    # closes conversation
    bb.logoff()

#  Copyright 2004-2008 Software AG
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
