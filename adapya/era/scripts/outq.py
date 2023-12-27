
#! /usr/bin/env python
# -*- coding: latin1 -*-
""" outq.py -- Reptor output queue reader

Reads messages from the Reptor output queue
via EntireX Broker ACI call interface
and prints the data.

With a configuration file it it possible to define EXX broker parameters
and subscription formats


 Usage: python outq.py [options]

 Options:

    -h, --help              display this help
    -b, --broker ..         id of broker ETBxxxxx or hostname:port

    -c, --class ..          server class
    -e  --ecodec            ebcdic codec (default 'cp037')
    -k, --config ..         configuration module with information on
                                subscription:[files..].dmap,sdbid,sfnr
    -a, --xml               Target Adapter XML Stream
    -n, --name ..           server name
    -m, --maxout ..         receive buffer length i.e. MAXOUTPUTSIZE (default 32768)
    -P  --prompt            Confirm to receive next message by prompt
    -s, --service ..        service (Reptor output queue)
                              short: -s class/server/service
    -T, --token ..          token to be used
    -u, --userid ..         user id to be used
    -v, --sconv             single conversation mode (must match ANSERVER
                              destination setting)
    -x, --password ..       password
    -t, --trace ..          sum of trace flags
                            1 - dump buffers before Broker call
                            2 -              after call
                            4 - print broker calls, URB short and data
                            8 - tracking status of URB buffers
                           16 - no URB detail print
    Experimental:
    -i  --convid            conversation id (default ANY if --sconv else NEW)
    -F, --flush             delete all UOWs for given queue and terminate
    -C, --cancel <uowid>    cancel uowid
    -S, --send              Send test URBS to output queue

 Example:
    python outq.py -b ibm1:3000 -u MM -s REPTOR/MMSERV/OUT3 -t 12

    outq -k demo.EmployeeReplication.rcOut1Config


$Date: 2023-12-01 00:54:33 +0100 (Fri, 01 Dec 2023) $
$Rev: 1072 $
"""
from __future__ import print_function          # PY3

from adapya.entirex.broker import *
from adapya.era import reptor
from adapya.era import urb
from adapya.era.reptor import ReptorError

from adapya.base.conv import str2ebc
from adapya.base.datamap import NETWORKBO, funpack
import sys
import getopt


def usage():
    print(__doc__)


if sys.hexversion >= 0x3010100: # PY3
    PY3 = True
    getinput = input
else:
    PY3 = False
    getinput = raw_input

printDetail = 0


if __name__=='__main__':
    # session status
    sstat = 0
    sst_LOGON = 1
    sst_REGISTERED = 2

    brokerid = ''
    btrace=0
    buser=bservice=bclass=bname=''
    buser=''
    canceluow=''
    config=''   # configuration module
    convid=''
    ecodec = 'cp037' # ebcdic codec for printout
    flush = False
    maxout=100000   # ( min 32768)
    prompt = False
    pwd=None
    sconv=0      # single conversation mode
    send=0       # send TEST URBS
    subconf=None # subscription configuration class instance
    substat=None # subscription message processing status
    token=None
    xmls=0
    urbs=0
    try:
        opts, args = getopt.getopt(sys.argv[1:],
            'hab:c:C:e:Fi:k:m:n:Px:Ss:t:T:u:v',
            ['help','broker=','cancel=','class=','convid=','ecodec=','flush',
             'name=','config=','prompt','password=','rcvlen=','sconv','send',
             'service=','token=','trace=','userid=','xml'])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-b', '--broker'):
            brokerid = arg
        elif opt in ('-C', '--cancel'):
            canceluow=arg      # uowid
        elif opt in ('-c', '--class'):
            bclass=arg
        elif opt in ('-i', '--convid'):
            convid=arg
        elif opt in ('-k', '--config'):
            config=arg
            print(config)
        elif opt in ('-e', '--ecodec'):
            ecodec=arg
        elif opt in ('-F', '--flush'):
            flush=True                  # remove all UOWs
        elif opt in ('-n', '--name'):
            bname=arg
        elif opt in ('-x', '--password'):
            pwd=arg
        elif opt in ('-P', '--prompt'):
            prompt = True
        elif opt in ('-r', '--rcvlen'):
            maxout=int(arg)
        elif opt in ('-v', '--sconv'):
            sconv=1                 # single conversation mode
        elif opt in ('-S', '--send'):
            send=1                  # Sent TEST status message to Queue
        elif opt in ('-s', '--service'):
            sss=arg.split('/')      # --service class:server:service
            del sss[3:]             # skip any extranous items
            bservice=sss.pop()
            if sss:
                bname=sss.pop()
                if sss:
                    bclass=sss.pop()
        elif opt in ('-T', '--token'):
            token=arg
        elif opt in ('-u', '--userid'):
            buser=arg
        elif opt in ('-t', '--trace'):
            btrace=int(arg)
            if btrace & 8:
                if btrace & 16:
                    btrace &= 0x0f # reset 16 flag
                else:
                    printDetail = 1

        elif opt in ('-a', '--xml'):    # target adapter XML messages
            xmls=1

    if not convid:
        if sconv and not send:
            convid = 'ANY'
        else:
            convid = 'NEW'


    dumplog=0   # 1 log received buffers into file 'dumplog'
    if dumplog:
        fd=open('dump.log', 'w')

    if config:
        # absolute     'adapya.era.demo.EmployeeReplication.rcOut1Config'
        # relative     'demo.EmployeeReplication.rcOut1Config'
        # cm =__import__(config,globals(),locals(),['psu',],-1) level must be >=0
        ## cm =__import__(config,globals(),locals(),['psu',],0)

        #import importlib
        #cm = importlib.import_module(config, package=None)

        from importlib.machinery import SourceFileLoader
        cm = SourceFileLoader(config,config+'.py').load_module()


        subconf=cm.psu  # currently only one subscription
        print('\n -- Using Configuration %s for Subscription %s --' %(
            config, subconf.subscription))
        for sfile in subconf.sfiles:
            print('\tsdbid=%d, sfnr=%d, datamap=%s' % (
                sfile.sdbid,sfile.sfnr,sfile.dmap.dmname))
        substat=reptor.SubscriptionStatus()  # keep status of messages received
        substat.trace = btrace  # trace setting

        if cm.pbs:
            # broker parameters specified in configuration
            # only override if no startup parameter given
            if not brokerid: brokerid = cm.pbs.broker_id
            if not buser:    buser    = cm.pbs.user_id
            if token != None:
                token    = cm.pbs.token
            if not bclass:   bclass   = cm.pbs.server_class
            if not bname:    bname    = cm.pbs.server_name
            if not bservice: bservice = cm.pbs.service

    # RPT MAXOUTPUTSIZE minimum is 32k
    bb=Broker(receive_length=maxout,send_length=512)

    bb.trace = btrace
    bb.broker_id=brokerid

    bb.server_class = bclass
    bb.server_name  = bname
    bb.service      = bservice
    bb.user_id      = buser
    bb.token        = token if token!=None else bservice+'-Reader'

    bb.use_api_version = 10
    bb.api_version = 10

    print('\n -- Reptor output queue reader --\n')
    print(' broker_id = \t', bb.broker_id)
    print(' user_id = \t', bb.user_id)
    print(' token = \t', bb.token)


    print('\n server_class =', bb.server_class)
    print(' server_name = \t',bb.server_name)
    print(' service = \t',bb.service)

    print(' trace = \t',bb.trace)
    # sys.exit()

    repli = reptor.Replicator()
    repli.ecodec = ecodec

    if xmls:
        import xml.dom.minidom


    def detailPrint(ss,substat):
        if printDetail:
            ss.dprint()

    def transPrint(ss,substat):
        if printDetail:
            ss.dprint()
        if substat:
            substat.snam=ss.urbtsnam    # remember subscription name
            substat.sdbid=ss.urbtdbid    # and dbid

    def recPrint(ss,substat):
        if printDetail:
            ss.dprint()
        if substat:
            substat.sfnr=ss.urbrfnr

    def dataPrint(ss,substat):
        if printDetail:
            ss.dprint()
        if not substat:
            i=ss.offset+urb.URBDL
            j=i+ss.urbdlend
            dump(ss.buffer[i:j],header='Record')
            return       # no config with subscription info specified
        snam=substat.snam
        sdbid=substat.sdbid
        sfnr=substat.sfnr
        if not (snam and sdbid and sfnr):
            return  # all parms must be set
        if not subconf.subscription==snam:
            return
        for sfile in subconf.sfiles:
            if sfile.sdbid==sdbid and sfile.sfnr==sfnr:
                dm=sfile.dmap
                if not dm:
                    return
                dm.buffer=ss.buffer
                dm.offset=ss.offset+urb.URBDL
                dm.dprint()                 # print record details
                return


    def flushuows():
        bb.conv_id=convid if convid and convid != 'NEW' else 'ANY'  # OLD, ANY, don't work Invalid convid 002000185

        try:
            bb.syncpoint(option=OPT_LAST)   # used by sender

            #   if bb.uowStatus == RECEIVED:
            #       bb.syncpoint(option=OPT_BACKOUT)   # remove any open UOW from last session
            # bb.syncpoint(option=OPT_CANCEL)     # used by sender
            bb.syncpoint(option=OPT_DELETE)     # used by sender

        except BrokerError:
            if bb.error_code == '00780305':  # No matching UOW found
                print('\nNo matching UOW found\n')
            else:
                print('BrokerError exception in flushuows() at synpoint(option=last)')
                raise

        sys.exit(0)


    def cancel():
        print('UOW to be cancelled = %r' % canceluow)
        bb.conv_id=convid if convid and convid != 'NEW' else 'ANY'  # OLD, ANY, don't work Invalid convid 002000185
        bb.uowID = canceluow
        bb.syncpoint(option=OPT_CANCEL)
        bb.syncpoint(option=OPT_DELETE)


    def sendURBS():
        if convid and convid not in ('NEW','ANY','NONE'):  # OLD, ANY, don't work Invalid convid 002000185
            bb.conv_id=convid
            print('Get last uow')
            try:
                bb.syncpoint(option=OPT_LAST)

            except BrokerError:
                if bb.error_code == '00780305':  # No matching UOW found
                    print('\nNo matching UOW found\n')
                else:
                    print('BrokerError exception in sendURBS() at synpoint(option=last)')
                    raise
        else:
            bb.conv_id = convid

        print('Sending TEST URBS')

        reptor.makeURBH(bb.send_buffer,msgNo=1)
        slen=reptor.makeURBS()
        bb.send_length=slen

        bb.send(option=OPT_COMMIT)
        sys.exit(0)


    if bb.trace & 4:
        repli.logging |= reptor.LOGallURB  # log all data of URB

    if bb.trace & 8:
        repli.setHandler(urb.URBCEYE, detailPrint)
        repli.setHandler(urb.URBDEYE,   dataPrint)
        repli.setHandler(urb.URBEEYE, detailPrint)
        repli.setHandler(urb.URBHEYE, detailPrint)
        repli.setHandler(urb.URBIEYE, detailPrint)
        repli.setHandler(urb.URBREYE,    recPrint)
        repli.setHandler(urb.URBSEYE, detailPrint)
        repli.setHandler(urb.URBTEYE,  transPrint)

    bb.conv_id='NONE'

    print('\n%s' % bb.version())

    print('\nKernel %s \n    with kernelsecurity=%s' % (
        bb.kernelVersion(), bb.kernelsecurity))

    # bb.kernelsecurity=KERNEL_SECURITY_NO this is set by kernelVersion()
    # when using ACI level 8 or higher

    bb.logon(password=pwd)

    sstat = sst_LOGON  # need to logoff if not sconv


    if not send:
        bb.register()
        sstat |= sst_REGISTERED  # need to logoff if not sconv
        # now registered as server and reading the messages

    if sconv:
        from adapya.entirex.cmdinfo import Cis, CIO_SERVICE, CIC_SET_SINGLE_CONVERSATION

        cis = Cis(cis='CMD',broker=bb.broker_id,user=bb.user_id, trace=btrace)

        cis.icmd(CIO_SERVICE, CIC_SET_SINGLE_CONVERSATION, conv_id=bb.conv_id,
                server_class=bb.server_class, server=bb.server_name, service=bb.service,
                uid=bb.user_id, token=bb.token)
        print('Single conversation mode set with broker')


    uowCnt=0

    try:
        if flush:
            flushuows()
        elif canceluow:
            cancel()
        elif send:
            sendURBS()

        # receive loop
        while 1:
            try:
                if prompt:
                    x = getinput('<Enter> to receive messages? "Stop" to terminate').upper()
                    if x.startswith('S'):
                        break
                bb.conv_id = convid  # start with ANY for single conversation mode else with NEW
                                     # and leave conv_id for whole session  (EOC resets conv_id)

                bb.receive(option=OPT_ANY, wait='1m') # any UOW

                if dumplog:
                    dump(bb.receive_buffer, header='Reptor Data', fd=fd, ecodec=ecodec)
                if not xmls:
                    repli.process(bb.receive_buffer, bb.return_length, bb.uowStatus, substat)
                elif bb.trace & 4 :
                    dump(bb.receive_buffer[:bb.return_length],
                        header='Receive buffer', prefix='    ',ecodec=repli.ecodec)
                    if 1 and bb.receive_buffer[0:7] == str2ebc('ART241E'):
                        # disable if conversion errors with field values to output codepage
                        arts = bb.receive_buffer[7:bb.return_length].decode('cp037','xmlcharrefreplace')
                        print(arts)
                        artx=xml.dom.minidom.parseString(arts)
                        artp = artx.toprettyxml()
                        print(artp)
                    elif 1 and bb.receive_buffer[0:7] == str2ebc('ART241X'):
                        cpnum = funpack(bb.receive_buffer[7:11], 'u', byteorder=NETWORKBO,ebcdic=1)
                        # msglen = funpack(bb.receive_buffer[11:15], 'B', byteorder=NETWORKBO,ebcdic=1)
                        # disable if conversion errors with field values to output codepage
                        arts = bb.receive_buffer[15:bb.return_length].decode('cp%d' % cpnum,'xmlcharrefreplace')
                        # print(arts)
                        artx=xml.dom.minidom.parseString(arts)
                        artp = artx.toprettyxml()
                        print(artp)

            except BrokerError:
                if bb.error_code == '00200094': # message truncated
                    print('\nCancelling truncated message\n')
                    bb.syncpoint(option=OPT_CANCEL)
                    continue
                if bb.error_code == '00740301': # End of UOW in conversation
                    print('\nBackout of UOW due to End of UOW in conv: restart from beginning\n')
                    bb.backout()
                    continue
                else:
                    print('BrokerError exception')
                    raise
            except BrokerTimeOut:
                continue

            segmentCnt=1
            while bb.uowStatus==RECV_FIRST or bb.uowStatus==RECV_MIDDLE:
                bb.receive()
                segmentCnt+=1
                if not xmls:
                    repli.process(bb.receive_buffer, bb.return_length, bb.uowStatus, substat)
                elif bb.trace & 4:
                    dump(bb.receive_buffer[:bb.return_length],
                        header='Receive buffer', prefix='    ',ecodec=repli.ecodec)
                    if 1 and  bb.receive_buffer[0:7] == str2ebc('ART241E'):
                        # disable if conv errors with field values to output codepage (cp1252)
                        arts = bb.receive_buffer[15:bb.return_length].decode('cp037','xmlcharrefreplace')
                        # print(arts)
                        artx=xml.dom.minidom.parseString(arts)
                        artp = artx.toprettyxml()
                        print(artp)
            if sconv:
                bb.commit()
            else:
                bb.commitEndConversation()

            uowCnt+=1
            if bb.trace & 4:
                print('uow number %d received with %d segments\n' % (uowCnt, segmentCnt))


    except ReptorError:
        print('\nCancelling invalid Reptor message\n')
        bb.syncpoint(option=OPT_CANCEL)
        raise
    except KeyboardInterrupt:
        print('Now terminating due to KeyboardInterrupt')
    finally:
        x = 'Y'
        if sconv:
            print('Deregister/Logoff should not be done in SingleConversation mode')
            x = getinput('Enter "Yes" to do it anyway').upper()
        if x.startswith('Y'):
            if sstat&sst_REGISTERED:
                bb.deregister()
            if sstat&sst_LOGON:
                bb.logoff()

        if dumplog:
            fd.close() # close dump log

#  Copyright 2004-2023 Software AG
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
