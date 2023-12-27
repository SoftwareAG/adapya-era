#! /usr/bin/env python
# -*- coding: latin1 -*-
""" Replication Target Adapter for Adabas

o to do:
  transaction continuation
  stats() move into reptor URBS handler
  sversion checking
"""
from __future__ import print_function          # PY3


import sys
import datetime as mdt # requires Python 2.3

from adapya.base import stck
from adapya.base.defs import log,LOGBEFORE,LOGCMD,LOGCB,LOGRB,LOGRSP,LOGFB
log(LOGCB+LOGFB+LOGRB)

from adapya.adabas.api import Adabas
from adapya.adabas.api import DatabaseError, adaSetTimeout


# reptor.Replicator.instance.logging
LOGTAPA = 1 << 16
LOGTAPA2 = 1 << 17
LOGTAPA4 = 1 << 18

from adapya.era import reptor,urb
from adapya.era.urb import URBDEYE,URBEEYE,URBHEYE,URBREYE,URBTEYE

dt=mdt.datetime(mdt.MINYEAR,1,1)
DELTA0=mdt.timedelta(0)

# set to 1 if delete record before update or insert
SAFEUPDATE=0


class UexAdabas(Adabas):
    # Special for testing lnkuex_0 exits
    # overrides adabas() call with call to lnkuex_() when lnkuex parm is given
    #
    lnkuexso=None
    def call(self, **cbfields):
        """ issue Call to lnkuex_0 with the Adabas control block class variables

            :param cbfields: list of key value pairs that can be used to
                set the control block before the call

        """
        global totalCalls, lnkuexso
        cb=self.cb

        for (key, val) in cbfields.items():
            setattr(cb,key,val)

        if self.dbid==0 and cb.dbid!=0:
            self.dbid=cb.dbid           # remember dbid if not yet done

        if cb.typ==0x04: # physical call (default is 0x30)
            if self.nucid==0 and cb.pnucid!=0:
                self.nucid=cb.pnucid           # remember dbid if not yet done

            cb.pdbid=self.dbid
            cb.pnucid=self.nucid
            cb.rsp=0    #o cb.dbid=0
        else:
            cb.typ=0x30  # logical call (reset after call adaOS6.1)
            cb.dbid=self.dbid
            cb.pdbid=0
            cb.pnucid=0

        if adabas.logopt&LOGBEFORE:
            log.debug('Before Adabas call')
            self.logapa()

        # --- call lnkuex_0: exit's response is in i ----
        i = self.lnkuexso.lnkuex_0(self.acb, self.fb,self.rb,self.sb,self.vb,self.ib)
        # -----------------------------------------------

        if i:
            self.cb.rsp=i
        else:
            self.cb.rsp=0 # clear dbid

        if self.cb.rsp > 0 and self.cb.rsp != 3:
                # prepare subcode data and error texts
                if sys.byteorder == 'big':
                    self.sub1=self.cb.ad2>>16
                    self.sub2=self.cb.ad2&0xFFFF
                else:
                    self.sub2=self.cb.ad2>>16
                    self.sub1=self.cb.ad2&0xFFFF

                errtext=adaerror.rsptext(self.cb.rsp, self.sub1, self.sub2,
                    cmd=self.cb.cmd, subcmd1=self.cb.op1, subcmd2=self.cb.op2),

        if adabas.logopt&LOGCMD or \
           (adabas.logopt&LOGRSP and \
               (self.cb.rsp not in (0,2,3)) and \
               not (self.cb.rsp == 64 and self.cb.cmd == 'CL')):
            log.debug('After Adabas call')
            self.logapa()

        if self.expected_responses:
            xrsp,xsub = self.expected_responses.pop(0)

            if xsub == None:    # only response code specified
                if adabas.logopt&LOGCMD:
                    log.debug('Checking for expected response %d'%xrsp)
                assert xrsp == self.cb.rsp, \
                    'Unexpected response %d, expected response %d'%(
                        self.cb.rsp, xrsp)
            else:
                if adabas.logopt&LOGCMD:
                    log.debug('Checking for expected response %d/%d'%(xrsp,xsub))
                assert xrsp == self.cb.rsp and xsub == self.sub2, \
                    'Unexpected response %d/subcode %d, expected response %d/%d'%(
                        self.cb.rsp, self.sub2, xrsp, xsub)
            return

        if self.cb.rsp == 0:
            return
        elif self.cb.rsp == 2:  # ignore DE truncation warning
            # self.cb.rsp = 0
            return
        elif self.cb.rsp == 3:
            self.cb.rsp = 0
            raise DataEnd("End of Data",self)
        elif self.cb.rsp > 0 and not \
                (self.cb.rsp == 64 and self.cb.cmd == 'CL'):
            log.debug('Adabas Database Error: %s'% errtext)
            # do not raise if CL and rsp=64
            raise DatabaseError(errtext,self)



class Tapada(reptor.Replicator):
    """Class implements the Adabas Database Update handlers
       and processes input data passed via the process() method
    """
    def __init__(self,subsparm,lnkuexso=None):
        global dt
        super(Tapada,self).__init__()  # initialize Replicator()

        self.setHandler(URBDEYE, self.metUrbd)
        self.setHandler(URBEEYE, self.metUrbe)
        self.setHandler(URBHEYE, self.metUrbh)
        self.setHandler(URBREYE, self.metUrbr)
        self.setHandler(URBTEYE, self.metUrbt)

        if lnkuexso:
            self.c1=UexAdabas(rbl=subsparm.rblmax,fbl=0) # also used for open/close
            self.c2=UexAdabas(rbl=1,fbl=1)               # used for L4
            self.c1.lnkuexso=lnkuexso
            self.c2.lnkuexso=lnkuexso

        else:
            self.c1=Adabas(rbl=subsparm.rblmax,fbl=0) # also used for open/close
            self.c2=Adabas(rbl=1,fbl=1)               # used for L4


        self.c1.cb.dbid=subsparm.tdbid            # set target database

        self.c2.fb.value='.'
        self.c2.cb.dbid=subsparm.tdbid            # set target database

        self.transSeq=0     # current TA sequence number
        self.rcnt=0         # count of records (URBRs) in transaction (urbtrcnt)
                            # also indicator that an input transaction has started
        self.dcnt=0         # count of Data elements (URBD) for current record (URBR)

        self.rsnr=0         # current rec seq nr in transaction, if rcnt == rsnr: do ET
        # self.dsnr=0       # directly from URBD
        self.lastIsn=0
        self.curIsn=0
        self.rtyp=''        # current record type D, I, U or R (initial state)

        self.psf = 0        # current parameter subscr. source file (ParmsSfile)
        self.psu = subsparm     # subscription parameters from configuration module
        self.sfile = 0      # current source file

        # statistics
        self.numIsn=0       # number of records processed (urbrrsp==0)
        self.dt=dt.now()
        self.bytes=0
        self.messages=0
        self.records=0      # total number of records updated or inserted
        self.transactions=0
        self.transUpdCnt=0
        self.firstTransaction=None
        self.lastTransaction=None

    def terminate(self,printstats=0):
        if self.psu.tdbid and self.rcnt:
            self.perrors += 1
            log.error('Error: Transaction %d not completed, BT-ing' %(self.transSeq, ))
            self.c1.bt()
        self.c1.close()
        if __debug__:
            if self.logging & LOGTAPA: log.info('Database %d closed' % (self.psu.tdbid,))

        if printstats:
            print( '\t%10d records updated/inserted' % (self.records,))
            print( '\t%10d transactions processed' % (self.transactions,))
            if self.firstTransaction:
                sub, seq, tim = self.firstTransaction
                print( 'First transaction: sub=%s, seq=%d, ttime=%s' % (sub,seq, stck.sstckd(tim)))
            if self.lastTransaction:
                sub, seq, tim = self.lastTransaction
                print( 'Last transaction : sub=%s, seq=%d, ttime=%s' % (sub,seq, stck.sstckd(tim)))




    def metUrbr(self, rr, substat):
      "URBR Record block handler"

      if not self.rcnt: # skipping records of this subscription
        self.perrors += 1
        log.error('Error: URBR record received without Transaction (URBT)')
        return

      self.rsnr = rr.urbrrsnr    # recno within transaction
      self.dcnt = rr.urbrdcnt    # number of data elements following

      if rr.urbrrsp == 0: # only count successful records
        self.numIsn+=1

        self.curIsn=0 # reset curIsn if record is ignored, used in urbd handler

        if rr.urbrfnr == self.sfile:
          self.curIsn=rr.urbrisn       # set ISN
          self.rtyp=rr.urbrtyp
        else: # set new sfile
          fnr=rr.urbrfnr
          for sf in self.psu.sfiles:
            if fnr == sf.sfnr:    # matched source file
              self.psf = sf
              self.curIsn = rr.urbrisn   # set ISN
              self.sfile = sf.sfnr       # remember source file nr
              self.rtyp = rr.urbrtyp
              self.c1.cb.fnr = sf.tfnr
              self.c2.cb.fnr = sf.tfnr   # for L4/E1
              self.c1.cb.isn = self.curIsn
              if self.psf.rbl:
                self.c1.cb.rbl = self.psf.rbl # set rbl for current file/format
              else:
                self.c1.cb.rbl = self.psu.rblmax
              self.c1.cb.fbl = len( self.psf.fb )
              self.c1.fb = sf.fb
              break # for sf
      else:
        self.perrors += 1
        log.error('Error: URBR record received with Response (URBR)')

    def metUrbd(self, dd, substat):
      "URBD data block handler"
      holding=0     # ISN on hold
      if 0:
        log=log.debug('Enter URBD handler: %s %s, isn %d' %\
          (self.rtyp, dd.urbdtyp, self.curIsn))

      if not self.rcnt: # skipping data of this subscription
        self.perrors += 1
        log.error('Error: URBD Data records received without Transaction (URBT)')
        return

      # ignore record if self.curIsn not zero (no previous URBR)
      if self.curIsn!=0:
        self.c1.cb.isn=self.curIsn
        if dd.urbdtyp=='B': # before image
          if self.rtyp=='D' : # delete // or self.rtyp=='U)' or update
            try:
              self.c1.call(cmd='E1')
              self.transUpdCnt+=1
            except DatabaseError as e:
              if e.apa.cb.rsp == 113: # tolerate rsp-113
                log.debug('Note: Before Image not found ISN %d' % self.curIsn )
                pass
              else:
                raise
        elif dd.urbdtyp=='A': # after image

          if not (self.rtyp=='I' or self.rtyp=='R' or self.rtyp=='U'):
            # it is no (insert or Initial state or update)
            raise 'invalid after image for urbrtyp %s' % self.rtyp

          # elif self.rtyp=='I' or self.rtyp=='R': # insert or Initial state
          else:
            try:
                holding=0
                if SAFEUPDATE: # delete record to be on the safe side
                    self.c2.call(cmd='E1',isn=self.curIsn)
                    self.transUpdCnt+=1
                else:
                    self.c2.call(cmd='L4',isn=self.curIsn)
                    holding=self.curIsn

            except DatabaseError as e:
              if e.apa.cb.rsp == 113: # tolerate rsp-113
                log.warning('Note: Before Image not found ISN %d' % self.curIsn)
                pass
              else:
                log.error(e.value)
                dump(e.apa.acb, header='Control Block',log=log.error)
                raise

          # insert
          self.records+=1
          self.numIsn+=1

          if dd.urbdlend > self.c1.cb.rbl:
            raise reptor.ReptorError(
              'URBD record data length %d bytes > maximum ACBRBL %d .'\
                % (dd.urbdlend, self.c1.cb.rbl))
          else:
            # copy record
            dlen=dd.urbdlend
            self.c1.rb[0:dlen]=dd.buffer[dd.offset+URBDL:dd.offset+URBDL+dd.urbdlend]
            try:
                if 0: log.debug('self.c1.cb.isn %d, curIsn %d' % (self.c1.cb.isn, self.curIsn))

                if holding:
                    self.c1.call(cmd='A1',rbl=dlen)
                    action='Updated'
                else:
                    self.c1.call(cmd='N2',rbl=dlen)
                    action='Inserted'

                self.transUpdCnt+=1

                if __debug__:
                    if self.logging & LOGTAPA: log.debug("%s record %d in file %d " % (
                        action, self.c1.cb.isn, self.c1.cb.fnr))

            except DatabaseError as e:
              print( e.value)
              dump(e.apa.acb, header='Control Block')
              dump(e.apa.fb, header='Format Buffer')
              dump(e.apa.rb, header='Record Buffer')
              raise

        else:
          raise 'Invalid urbdtyp %s' % dd.urbdtyp

      # adarpe writes no URBE
      if not self.typ & reptor.typURBH and \
            self.rcnt == self.rsnr and self.dcnt == dd.urbddsnr:

          try:
            if __debug__:
              if self.logging & LOGTAPA:
                log.debug('End of transaction %d for subscription %s after all %d records, current update count %d' %\
                  (self.transSeq, self.psu.subscription, self.rcnt, self.transUpdCnt))
            self.c1.et()
            self.rcnt=0    # reset transaction record count
            self.dcnt=0    # reset data element count
            self.transactions += 1

          except DatabaseError as e:
            print( e.value)
            dump(e.apa.acb, header='Control Block')
            raise

      if __debug__:
        if self.logging & LOGTAPA4:
            log.debug('URBD: %s %s, isn %d/%d, num recs %d' %\
              (self.rtyp, dd.urbdtyp, self.curIsn,self.c1.cb.isn, self.numIsn))


    def metUrbt(self, tt, substat):
        if not self.firstTransaction:
            self.firstTransaction = (tt.urbtsnam, tt.urbttsnr, tt.urbtttim )
        self.lastTransaction = (tt.urbtsnam, tt.urbttsnr, tt.urbtttim )

        # select only this subscription
        if tt.urbtsnam == self.psu.subscription:
            self.transSeq=tt.urbttsnr
            self.rcnt = tt.urbtrcnt
            self.transUpdCnt=0
            if __debug__:
                if self.logging & LOGTAPA4:
                    log.debug('URBT: Transaction %d for subscription %s with %d records, current update count %d' %\
                        (self.transSeq, tt.urbtsnam, self.rcnt, self.transUpdCnt))
        else:
            if __debug__:
                if self.logging & LOGTAPA:
                    log.debug('Skipping transaction for subscription %s\n' % tt.urbtsnam)


    def metUrbe(self, ee, substat):
      if __debug__:
          if self.logging & LOGTAPA4:
            log.debug('Enter URBE handler: %s tsnr %d, records in TA %d, cnt %d' %\
              (ee.urbesnam, self.transSeq, self.rcnt, self.transUpdCnt))

      if not self.rcnt: # skipping this subscription
        return

      if ee.urbesnam != self.psu.subscription:
        log.debug('Error: Unexpected subscription %s' % ee.urbesnam)

      elif self.rcnt and self.transUpdCnt>0:
        if __debug__:
          if self.logging & LOGTAPA4: log.debug('End Transaction %d for subscription %s with %d updates' %\
               (self.transSeq, self.psu.subscription, self.transUpdCnt))

        if self.transSeq != ee.urbetsnr:
           raise 'Error: Expected ta seq number %d, but received %d' %\
             (self.transSeq, ee.urbetsnr)
        else:
          try:
            self.c1.et()
            self.rcnt=0
            self.transactions += 1
          except DatabaseError as e:
            print( e.value)
            dump(e.apa.acb, header='Control Block')
            raise
      if __debug__:
        if self.logging & LOGTAPA:
          log.debug('URBE: End of transaction %d for subscription %s with %d records, current update count %d' %\
            (self.transSeq, ee.urbesnam, self.rcnt, self.transUpdCnt))


    def metUrbh(self, hh, substat):
      self.messages+=1
      self.bytes+=hh.urbhlent


__version__ = '1.3.0'
if __version__ == '1.3.0':
    _svndate='$Date: 2018-05-30 17:31:49 +0200 (Wed, 30 May 2018) $'
    _svnrev='$Rev: 837 $'
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
