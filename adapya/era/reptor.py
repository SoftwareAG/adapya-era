# -*- coding: latin1 -*-
""" reptor.py - Event Replication for Adabas main module

"""
from __future__ import print_function          # PY3

from adapya.base.defs import adalog as log
from adapya.adabas import adaerror

from adapya.era.urb import Urbc,Urbd,Urbe,Urbh,Urbi,Urbr
from adapya.era.urb import Urbs,Urbsu,Urbt,Urbu,Urbi_isns,New_Urb
from adapya.era.urb import Urbf,Urbg,URBFL,URBGL,URBFVER1,URBFEYE,urbfflag_str
from adapya.era.urb import URBHEYE,URBHL,URBHBORD,URBHVER1
from adapya.era.urb import URBCEYE,URBCL,URBDEYE,URBDL,urbd_type
from adapya.era.urb import URBEEYE,URBEL
from adapya.era.urb import URBIEYE,URBIL,URBIRTIS,URBIIRANGE,URBIIRANGELEN
from adapya.era.urb import URBIISNLEN,URBIRTTA,URBIRTST,URBIRTCD
from adapya.era.urb import URBREYE,URBRL,urbr_type
from adapya.era.urb import URBSEYE,URBSL,URBSSTAU
from adapya.era.urb import URBTEYE,URBTL,URBTRSNY,URBTINSY,URBTCONY
from adapya.era.urb import URBUEYE,URBUL
from adapya.era.urb import urbs_status
from adapya.era.urb import REPTOR_RSP,texts_reptor_subcodes

from adapya.base.dump import dump
from adapya.base import conv
from adapya.base import datamap
from adapya.base import ecscodec
from adapya.base import stck
import binascii
import types

try:
    from adapya.era import xtra  # external optional plugin
except:
    xtra = None

fname=''
substat=None

class ReptorError(Exception): pass

class ParmsSubscription(object):
    "defines parameters for updating the target database"
    rblmax=0
    fblmax=0
    def __init__(self,subscription='',sversion='', sfiles=[]):
        """
        subscription = name of subscription to handle
        version      = 2 byte version string compared with Reptor SVERSION
        sfiles       = list of ParmSubsFile objects
        """
        self.subscription=subscription
        self.sfiles=sfiles

        if len(sfiles) > 0:
            self.tdbid=sfiles[0].tdbid

        for s in self.sfiles:
            if s.dmap:
                sz = s.dmap.getsize()
            else:
                sz = 0x7ff0
            if ParmsSubscription.rblmax < sz:
                ParmsSubscription.rblmax = sz
            if ParmsSubscription.fblmax < len(s.fb):
                ParmsSubscription.fblmax=len(s.fb)
            if self.tdbid != s.tdbid:
                raise ReptorError( 'Multiple target DBIDs not supported in subscription processing')


class ParmsSfile(object):
    """ Defines parameters for updating the target database
        source and target database/file parameters
        and the record format

        :param sdbid: source database id
        :param sfnr:  source file number
        :param tdbid: target database id
        :param tfnr:  target file number
        :param fb:    format buffer when storing data
        :param dmap:  datamap object describing fields in record

    """
    def __init__(self,fb='',dmap=None,handler=None,\
                 sdbid=0,sfnr=0,tdbid=0,tfnr=0):
        self.sdbid=sdbid
        self.sfnr=sfnr
        self.tdbid=tdbid
        self.tfnr=tfnr
        self.fb=fb
        self.handler=handler
        self.dmap=dmap

        if dmap:
            self.rbl = dmap.getsize()  # set size of datamap
        else:
            self.rbl = 0


class SubscriptionStatus(object):
    """Holds current processing status of message(s) received"""
    snam=''
    sdbid=0
    sfnr=0
    smap=None

typURBH = 1     # input type with URBH header (from Message Queue or ADARIS)
                # set in ProcessingStatus().type with the first message


# create datamap objects for each structure
cc=Urbc(buffer=None,offset=0)
dd=Urbd(buffer=None,offset=0)
ee=Urbe(buffer=None,offset=0)
ff=Urbf(buffer=None,offset=0)
gg=Urbg(buffer=None,offset=0)
hh=Urbh(buffer=None,offset=0)
ii=Urbi(buffer=None,offset=0)
nn=New_Urb(buffer=None,offset=0)
rr=Urbr(buffer=None,offset=0)
ss=Urbs(buffer=None,offset=0)
ssu=Urbsu(buffer=None,offset=0)
tt=Urbt(buffer=None,offset=0)
uu=Urbu(buffer=None,offset=0)
ii_isns=Urbi_isns(buffer=None,offset=0)

def setURBebcdic(TrueFalse):
    """Set all URB blocks to EBCDIC or not.
    Implicitely the byte encoding will be set to CP037 or Latin1

    :param TrueFalse: True (set to EBDIC) or False
    """
    cc.setEbcdic(TrueFalse)
    dd.setEbcdic(TrueFalse)
    ee.setEbcdic(TrueFalse)
    ff.setEbcdic(TrueFalse)
    gg.setEbcdic(TrueFalse)
    hh.setEbcdic(TrueFalse)
    ii.setEbcdic(TrueFalse)
    nn.setEbcdic(TrueFalse)
    rr.setEbcdic(TrueFalse)
    ss.setEbcdic(TrueFalse)
    ssu.setEbcdic(TrueFalse)
    tt.setEbcdic(TrueFalse)
    uu.setEbcdic(TrueFalse)
    ii_isns.setEbcdic(TrueFalse)

def setURBnwbo():
    """set all URB blocks to NETWORKBO byte order"""
    cc.byteOrder=dd.byteOrder=ee.byteOrder=hh.byteOrder=ii.byteOrder=datamap.NETWORKBO
    ff.byteOrder=gg.byteOrder=datamap.NETWORKBO
    rr.byteOrder=ss.byteOrder=ssu.byteOrder=tt.byteOrder=uu.byteOrder=datamap.NETWORKBO
    ii_isns=nn.byteOrder=datamap.NETWORKBO


def makeURBH(buffer, msgNo=0, senderName='Admin'):
    """write URB header at beginning of buffer

    :param msgNo:      message number (optional)
    :param senderName: 8 byte name identifying the sender
    """
    hh.buffer=buffer
    hh.offset=0

    hh.urbheye=URBHEYE
    hh.urbhlen=URBHL
    hh.urbhvers=URBHVER1
    hh.urbhbord=URBHBORD
    hh.urbhlent=URBHL     # current / total msg length
    hh.urbhmsnr=msgNo     # msg seq number per sender
    hh.urbhtime=0
    hh.urbhrpid=0
    hh.urbhrpni=0
    hh.urbhname=senderName

def setTotalLength(totalLength):
    if totalLength > len(hh.buffer):
        raise ReptorError( 'new total length %d exceeds buffer size %d' %
                          (totalLength,len(hh.buffer)) )
    hh.urbhlent=totalLength

def makeURBS(token='TEST'):
    """ create an URBS which can be received on an output queue

        :param token: token for URBS
        :return: current message size
    """
    if URBSL+hh.urbhlent > len(hh.buffer):
         raise ReptorError( 'Buffer full: %d + %d > %d' %\
          (hh.urbhlent,URBSL,len(hh.buffer)))

    ss.buffer=hh.buffer
    ss.offset=hh.urbhlent

    ss.urbseye=URBSEYE
    ss.urbslen=URBSL
    ss.urbslenh=URBIL
    ss.urbslend=0
    ss.urbsrtok=token
    ss.urbsrt=''
    ss.urbsst='TEST'

    setTotalLength(ss.offset+URBSL)
    return ss.offset+URBSL  # return current message size




def requestInst(dbid=0,fnr=0,instname='',token='INSTREQU',
        rspDest='',isnl=[],value='',arc=0,acode='',wcode=''):
    """ create URBI with initial state request element for an initial
        state definition

        :param instname: initial state name and
        :param dbid: database id
        :param fnr: file number

        optional are:

        :param rspDest: response destination
        :param isnl: selected ISN list
        :param value: selection value
        :param arc: architecture
        :param acode: alfa encoding
        :param wcode: wide encoding

        :return: current message size
    """
    if URBIL+hh.urbhlent > len(hh.buffer):
         raise ReptorError( 'Buffer full: %d + %d > %d' %\
          (hh.urbhlent,URBIL,len(hh.buffer)))

    ii.buffer=hh.buffer
    ii.offset=hh.urbhlent

    ii.urbieye=URBIEYE
    ii.urbilen=URBIL
    ii.urbilenh=URBIL
    ii.urbilend=0
    ii.urbirtok=token
    ii.urbirnam=rspDest     # destination name for response
    ii.urbirt=URBIRTIS      # Initial-state request type
    ii.urbidbid=dbid
    ii.urbifnr=fnr
    ii.urbiinam=instname
    ii.urbisnam=''
    ii.urbidnam=''

    i0=ii.offset+URBIL

    if len(value) > 0:      # value for selection criterion
        if len(isnl)>0:
            raise ReptorError(
              'ISN(s) and selection value cannot be specified both')

        else:
            hh.buffer[i0:i0+len(value)]=value
            i1=len(value)
            ii.urbilend=i1
            ii.urbilen=i1+URBIL
            i1+=i0
            setTotalLength(i1)

            ii.urbiarc=arc
            ii.urbiacod=ecscodec.getecs(acode)
            ii.urbiwcod=ecscodec.getecs(wcode)

            return i1

    elif len(isnl)==0:     # no ISN list -> complete file
        setTotalLength(i0)
        return i0  # return current message size

    else:                  # ISN list
        ii_isns.buffer=hh.buffer
        ii_isns.offset=ii.offset+URBIL
        for i in isnl:
            if type(i) is list:
                ii_isns.urbiirange=URBIIRANGE
                ii_isns.urbiisn1=i[0]
                ii_isns.urbiisn2=i[1]
                ii_isns.offset+=URBIIRANGELEN
            else:
                ii_isns.urbiisn=i
                ii_isns.offset+=URBIISNLEN
        i1=ii_isns.offset
        ii.urbilend=i1-i0
        ii.urbilen=i1-i0+URBIL
        setTotalLength(i1)
        return i1  # return current message size


def requestPriorTrans(destination='', rspDest='', subscription='',
                  transSeqno=0, token='PRIORRQ'):
    """create URBI Prior Transaction request element for
       subscription, transaction sequence number within subscription
       and destination
       if rspDest (response destination) it will receive
       a status response URBS as well
       returns current message size
    """
    if URBIL+hh.urbhlent > len(hh.buffer):
        raise ReptorError( 'Buffer full: %d + %d > %d' %\
          (hh.urbhlent,URBIL,len(hh.buffer)))

    if transSeqno<=0:
        raise ReptorError( 'transSeqno %d must be > 0' % transSeqno)

    ii.buffer=hh.buffer
    ii.offset=hh.urbhlent

    ii.urbieye=URBIEYE
    ii.urbilen=URBIL
    ii.urbilenh=URBIL
    ii.urbilend=0
    ii.urbirtok=token
    ii.urbirnam=rspDest     # destination name for response
    ii.urbirt=URBIRTTA      # request type: Prior transaction seqno
    ii.urbidbid=0
    ii.urbifnr=0
    ii.urbiinam=''
    ii.urbisnam=subscription
    ii.urbidnam=destination
    ii.urbitsnr=transSeqno

    setTotalLength(ii.offset+URBIL)
    return ii.offset+URBIL  # return current message size


def requestStatus(destination='', rspDest='', subscription='',
                  token='STATUSRQ'):
    """create URBI status request element for
       destination and/or subscription
       if rspDest (response destination) it will receive
       a status response URBS as well
       returns current message size
    """
    if URBIL+hh.urbhlent > len(hh.buffer):
        raise ReptorError( 'Buffer full: %d + %d > %d' %\
          (hh.urbhlent,URBIL,len(hh.buffer)))

    ii.buffer=hh.buffer
    ii.offset=hh.urbhlent

    ii.urbieye=URBIEYE
    ii.urbilen=URBIL
    ii.urbilenh=URBIL
    ii.urbilend=0
    ii.urbirtok=token
    ii.urbirnam=rspDest     # destination name for response
    ii.urbirt=URBIRTST      # status request type
    ii.urbidbid=0
    ii.urbifnr=0
    ii.urbiinam=''
    ii.urbisnam=subscription
    ii.urbidnam=destination

    setTotalLength(ii.offset+URBIL)
    return ii.offset+URBIL  # return current message size


def requestCloseDest(destination='', rspDest='', token='CLSDrqst'):
    """create URBI 'close destination' request element for destination
       if rspDest (response destination) it will receive
       a status response URBS as well
       returns current message size
    """
    if URBIL+hh.urbhlent > len(hh.buffer):
        raise ReptorError( 'Buffer full: %d + %d > %d' %\
          (hh.urbhlent,URBIL,len(hh.buffer)))

    ii.buffer=hh.buffer
    ii.offset=hh.urbhlent

    ii.urbieye=URBIEYE
    ii.urbilen=URBIL
    ii.urbilenh=URBIL
    ii.urbilend=0
    ii.urbirtok=token
    ii.urbirnam=rspDest     # destination name for response
    ii.urbirt=URBIRTCD      # Close destination request type
    ii.urbidbid=0
    ii.urbifnr=0
    ii.urbiinam=''
    ii.urbisnam=''
    ii.urbidnam=destination

    setTotalLength(ii.offset+URBIL)
    return ii.offset+URBIL  # return current message size


def requestOpenDest(destination='', rspDest='', token='OPNDrqst'):
    """create URBI 'open destination' request element for destination
       if rspDest (response destination) it will receive
       a status response URBS as well
       returns current message size
    """
    if URBIL+hh.urbhlent > len(hh.buffer):
        raise ReptorError( 'Buffer full: %d + %d > %d' %\
          (hh.urbhlent,URBIL,len(hh.buffer)))

    ii.buffer=hh.buffer
    ii.offset=hh.urbhlent

    ii.urbieye=URBIEYE
    ii.urbilen=URBIL
    ii.urbilenh=URBIL
    ii.urbilend=0
    ii.urbirtok=token
    ii.urbirnam=rspDest     # destination name for response
    ii.urbirt=URBIRTOD      # 'Open destination' request type
    ii.urbidbid=0
    ii.urbifnr=0
    ii.urbiinam=''
    ii.urbisnam=''
    ii.urbidnam=destination

    setTotalLength(ii.offset+URBIL)
    return ii.offset+URBIL  # return current message size

LOGURBH=1
LOGURBT=2
LOGURBR=4
LOGURBD=8
LOGURBDD=16 # LOG DATA of URBD
LOGURBE=32  # LOG end of transaction
LOGURBDM=64 # LOG datamap of data of URBD
LOGURBC=128
LOGURBU=256
LOGURBS=512
LOGURBI=1024
LOGURBF=2**11 # log URBF and URBG
LOGallURB=2**12-1


class Replicator(object):
    """ Replicator class can process replication data

        A provider or consumer of replication stream
        can set handlers via setHandler() which will be called
        to process the different URB* messages

    """
    handUrbc=None
    handUrbd=None
    handUrbe=None
    handUrbf=None
    handUrbi=None
    handUrbh=None
    handUrbr=None
    handUrbs=None
    handUrbt=None
    handUrbu=None

    typ = 0        # input type   # urbh type
    perrors = 0     # number of errors detected
    pcount = 0      # number of buffers or records processed
    logging = 0
    ecodec = 'cp037'

    def process(self, buffer, length, status=0, substat=None):
        """ Process a message received from Reptor

            :param status: uow status
            :param substat: may reference the subscription status class instance
                for processing subscription data
            :param subconf: may reference the subscription and
                subscription-file configuration for processing subscription data
        """
        self.pcount += 1      # count number of process() calls

        if length < 32:                 # minimum URB header is 32
            self.perrors += 1         # count processing errors
            log.error('Replication Record %d: too short' % self.pcount)
            dump(buffer[:length],log=log.error,ecodec=self.ecodec)
            return

        # the first record or buffer decides for the rest if it is
        # - messages from broker or ADARIS: always starts with URBH
        # - ASCII or EBCDIC format of the URBs
        # - other type is from ADARPE: URBs in EBCDIC and Network byte order

        # if self.pcount == 1:
        if 1: # ADARIS binary output may have records starting with URBH and other URB types
              # intermixed
            # datamap.dataIsEbcdic=0       (default)
            # datamap.setNativeByteOrder() (default)
            if buffer[0:3] == b'\xE4\xD9\xC2':  # URBx in EBCDIC?
                # datamap.dataIsEbcdic = 1
                setURBebcdic(True)
                if buffer[3:4] == b'\xC8':
                    self.typ |= typURBH
                    if buffer[10:12] == b'\x00\x01':
                        # datamap.setNetworkByteOrder()
                        setURBnwbo()
                else: # ADARPE type (no URBH)
                    # datamap.setNetworkByteOrder()
                    self.typ &= ~typURBH # reset possible URBH type
                    setURBnwbo()
            elif buffer[0:3] == b'URB':
                if buffer[3:4] == b'H':
                    self.typ |= typURBH
                    # setURBebcdic(False)  # default
                    if buffer[10:12] == b'\x00\x01':
                        # datamap.setNetworkByteOrder()
                        setURBnwbo()
                else:
                    self.typ &= ~typURBH # reset possible URBH type

            else:
                self.perrors += 1         # count processing errors
                log.error('Replication Record % d: no URB* prefix detected' % self.pcount)
                dump(buffer,header='Buffer received',log=log.error,ecodec=self.ecodec)
                raise ReptorError('No URB* prefix detected but "%s"'% (buffer[:3],))
        if __debug__:
            if self.logging & LOGallURB: # any logging
                log.debug('URB in EBCDIC = %d, URBH messages = %d' % (datamap.dataIsEbcdic, self.typ & typURBH))

        if self.typ & typURBH:
            hh.buffer=buffer
            hh.offset=0

            if hh.urbheye != URBHEYE:
                self.perrors += 1         # count processing errors
                log.error('Replication Record % d: no URBH prefix detected' % self.pcount)
                dump(buffer[:length],log=log.error,ecodec=self.ecodec)
                return
            if hh.urbhvers != URBHVER1:
                log.error('Record %d: incompatible URBH version %s received / expected %s:' %\
                  (self.pcount, hh.urbhvers, URBHVER1))
                dump(buffer[:length],log=log.error,ecodec=self.ecodec)
                return
            total_length=hh.urbhlent

            if __debug__:
                if self.logging & LOGURBH: log.debug('\n\nURBH %s msg %d total-len %d rpid %d/%d %s\n' %
                    (stck.sstckd(hh.urbhtime), hh.urbhmsnr, hh.urbhlent, hh.urbhrpid, hh.urbhrpni, hh.urbhname))
            if self.handUrbh:
                self.handUrbh(hh, substat)

            offset = URBHL
            rest_length = total_length - URBHL
        else:
            offset = 0
            rest_length = length

        while rest_length > 4:

            nn.buffer=buffer
            nn.offset=offset

            if nn.eye == URBDEYE:
                dd.buffer=buffer
                dd.offset=offset
                if __debug__:
                    if self.logging & LOGURBD:
                        log.debug('URBD(%d) %s' % (dd.urbddsnr, urbd_type[dd.urbdtyp]))
                    if self.logging & LOGURBDD:
                        datalen = dd.urbdlend
                        dump(dd.buffer[offset+URBDL:offset+URBDL+datalen],
                             header=None, prefix='    ',log=log.debug,ecodec=self.ecodec)

                if self.handUrbd:
                    self.handUrbd(dd, substat)

                rest_length -= dd.urbdlen
                offset+=dd.urbdlen

            elif nn.eye == URBEEYE:
                ee.buffer=buffer
                ee.offset=offset

                if __debug__:
                    if self.logging & LOGURBE:
                        log.debug('URBE -- end of transaction %d for subscription %s' % \
                            (ee.urbetsnr, ee.urbesnam))
                rest_length -= URBEL
                offset+=URBEL

                if self.handUrbe:
                    self.handUrbe(ee, substat)

            elif nn.eye == URBREYE:
                rr.buffer=buffer
                rr.offset=offset

                if __debug__:
                    if self.logging & LOGURBH:
                        log.debug('URBR -- %s record fnr %d isn %d' % \
                        (urbr_type[rr.urbrtyp], rr.urbrfnr, rr.urbrisn))
                        if rr.urbrrsp:
                            rspTxt=''
                            rspTxt=adaerror.rsptext(rr.urbrrsp,rr.urbrsubc,erri=rr.urbrerrc)
                            log.debug( rspTxt )

                if self.handUrbr:
                    self.handUrbr(rr, substat)

                rest_length-=URBRL
                offset+=URBRL

            elif nn.eye == URBTEYE:
                tt.buffer=buffer
                tt.offset=offset
                if __debug__:
                    if self.logging & LOGURBT:
                        if tt.urbtarc > b'\x00':
                            encstr = 'arc=%d, acode=%s, wcode=%s' %\
                                (ord(tt.urbtarc), ecscodec.getcodec(tt.urbtacod),
                                    ecscodec.getcodec(tt.urbtwcod))
                        else:
                            encstr=''

                        log.debug('URBT -- transaction %d with %d records for subscription %s\n'\
                            '     guid %s\n'\
                            '     ET %s dbid %d/%d\n'\
                            '     RP %s rpid %d/%d %s' %  \
                            (tt.urbttsnr, tt.urbtrcnt, tt.urbtsnam,
                            binascii.hexlify(tt.urbtguid),
                            stck.sstckd(tt.urbtttim),  tt.urbtdbid, tt.urbtnuci,
                            stck.sstckd(tt.urbtptim), tt.urbtrpid, tt.urbtrpni,
                            encstr))
                        if tt.urbtrsnd==URBTRSNY:
                            log.debug('     -- possible double delivery --')
                        if tt.urbtinst==URBTINSY:
                            log.debug('     -- initial state --')
                        if tt.urbtcont==URBTCONY:
                            log.debug('     -- to be continued with next message --')

                if self.handUrbt:
                    self.handUrbt(tt, substat)

                rest_length-=URBTL
                offset+=URBTL

            elif nn.eye == URBCEYE:
                cc.buffer=buffer
                cc.offset=offset
                if __debug__:
                    if self.logging & LOGURBC:
                        log.debug('URBC -- transaction %d continued record %d dseq %d subs %s\n'\
                            % (cc.urbctsnr, cc.urbcrsnr, cc.urbcdsnr, cc.urbcsnam))
                        if cc.urbccont==URBTCONY:
                            log.debug('     -- to be continued with next message --')

                if self.handUrbc:
                    self.handUrbc(cc, substat)

                rest_length-=URBCL
                offset+=URBCL

            elif nn.eye == URBSEYE:
                ss.buffer=buffer
                ss.offset=offset

                if __debug__:
                    if self.logging & LOGURBS:
                        subcTxt = ''
                        if ss.urbsrsp > 0:
                            subcTxt=' -'+str(ss.urbssubc)
                            if ss.urbsrsp==REPTOR_RSP:
                                if 0 < ss.urbssubc < len(texts_reptor_subcodes):
                                    subcTxt += '- '+texts_reptor_subcodes[ss.urbssubc]
                            else:
                                if ss.urbsrsp in adaerror.rspdict:
                                    subcTxt += ' - '+adaerror.rspdict[ss.urbsrsp]

                        log.debug('URBS %s -- %s\n' \
                              '     subs %s dest %s init %s rsp %d%s %s\n'\
                              '     ET %s dbid %d fnr %d\n'\
                              '     RP %s tsnr %d rtok %r' %  \
                            (stck.sstckd(ss.urbstime),
                             urbs_status.get(ss.urbsst,ss.urbsst),
                             ss.urbssnam, ss.urbsdnam, ss.urbsinam,
                             ss.urbsrsp, subcTxt, ss.urbserri,
                             stck.sstckd(ss.urbsttim), ss.urbsdbid, ss.urbsfnr,
                             stck.sstckd(ss.urbsptim), ss.urbstsnr, ss.urbsrtok))

                        datalen = ss.urbslend
                        if datalen > 0:
                            if ss.urbsst == URBSSTAU:  # online utility
                                ssu.buffer=buffer
                                ssu.offset=offset+URBSL
                                ssu.dprint()
                            elif xtra:
                                xtra.urbslog(ss)
                            else:
                                dump(ss.buffer[offset+URBSL:offset+URBSL+datalen],
                                     header='     Reptor Status/Response Data',
                                     prefix='    ',log=log.debug,ecodec=self.ecodec)

                if self.handUrbs:
                    self.handUrbs(ss, substat)

                rest_length -= ss.urbslen
                offset += ss.urbslen

            elif nn.eye == URBIEYE:
                ii.buffer=buffer
                ii.offset=offset

                if __debug__:
                    if self.logging & LOGURBI:
                        if ii.urbirt != URBIRTST and ii.urbirt != URBIRTIS:
                            rtypeText = 'Unknown request type ' + ii.urbirt
                        else:
                            rtypeText = urbi_rtext[ii.urbirt]

                        log.debug('URBI %s -- token %s\n' \
                              '     subs %s dest %s rdest %s\n' \
                              '     init %s dbid %d fnr %d\n' % \
                             (rtypeText, ii.urbirtok,
                             ii.urbisnam, ii.urbidnam, ii.urbirnam,
                             ii.urbiinam, ii.urbidbid, ii.urbifnr))

                        datalen = ii.urbilend
                        if datalen > 0:
                            dump(ii.buffer[offset+URBIL:offset+URBIL+datalen],
                                 header='     Initial-state selection', prefix='    ',log=log.debug)
                if self.handUrbi:
                    self.handUrbi(ii, substat)

                rest_length-=ii.urbilen
                offset+=ii.urbilen

            elif nn.eye == URBUEYE:
                uu.buffer=buffer
                uu.offset=offset
                if __debug__:
                    if self.logging & LOGURBU:
                        log.debug('URBU -- ADARPE %s extract from %s (local time)\n'\
                              % (uu.urbuname, uu.urbudist))
                if self.handUrbu:
                    self.handUrbu(uu, substat)

                rest_length -= URBUL
                offset += URBUL


            elif nn.eye == URBFEYE: # global format field table (GFFT)
                ff.buffer = buffer
                ff.offset = offset

                if __debug__:
                    if self.logging & LOGURBF:
                        # ff.urbffnam[: ff.urbffnml]
                        log.debug('URBF -- gfid=%s db=%d, fnr=%d\n' \
                              '     fnam=%s, items=%d\n' \
                              '     created=%s with %s\n%s' %
                            (ff.urbfgfid, ff.urbfdbid, ff.urbffnr,
                             ff.urbffnam,ff.urbfcntg,
                             stck.sstckd(ff.urbftim1)[0:19],
                             urbfflag_str(ff.urbfflag),
                             '     processed=%s\n' % stck.sstckd(ff.urbftim2)[0:19]
                                                        if ff.urbftim2 else ''
                             ))

                        datalen = ff.urbflend
                        if datalen > 0:
                            gg.buffer = buffer
                            gg.offset = offset+URBFL

                            for i in range(ff.urbfcntg):
                                gg.dprint()
                                gg.offset += URBGL

                rest_length -= ff.urbflen
                offset += ff.urbflen

                if self.handUrbf:
                    self.handUrbf(ff, substat)

            else:
                log.error('Unknown Structure %s' % nn.eye)
                dump(buffer[offset:offset+rest_length],log=log.error,ecodec=self.ecodec)
                break

    def setHandler(self, urbType, function):
        # print( 'setHandler called', urbType, function)
        if urbType=='URBC':
            self.handUrbc=function
        elif urbType=='URBD':
            self.handUrbd=function
        elif urbType=='URBE':
            self.handUrbe=function
        elif urbType=='URBF':
            self.handUrbf=function
        elif urbType=='URBH':
            self.handUrbh=function
        elif urbType=='URBR':
            self.handUrbr=function
        elif urbType=='URBS':
            self.handUrbs=function
        elif urbType=='URBT':
            self.handUrbt=function
        elif urbType=='URBI':
            self.handUrbi=function
        elif urbType=='URBU':
            self.handUrbu=function
        else:
            raise ReptorError( 'unknown structure %s'% (urbType,))


__version__ = '1.3.0'
if __version__ == '1.3.0':
    _svndate='$Date: 2023-12-01 00:54:33 +0100 (Fri, 01 Dec 2023) $'
    _svnrev='$Rev: 1072 $'
    __version__ = 'Dev ' +  _svnrev.strip('$') + \
                  ' '.join(_svndate.strip('$').split()[0:3])

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
