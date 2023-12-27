#! /usr/bin/env python
# -*- coding: latin1 -*-
""" readris.py
    Read and process sequential replication output records as
    produced by ADARIS or ADARPE.

    Processing can be
    - prepare the data as input for ADACMP and ADAMUP (-w / --write)
    - apply the data to an Adabas target database (-a / -- ada)


    If the dataset is located on z/OS use the -d otherwise the
    -f parameter to specify a local file.

    The remote dataset is a variable blocked sequential dataset.
    It is fetched per FTP-get from z/OS as binary with RDW record prefix.

    When the -w/--write <file prefix> parameter is specified
    - the records are written to <file prefix>cmpin.d<dbid>f<fnr>
    - the related ISNs are stored to <file prefix>mupisn.d<dbid>f<fnr>

    With the -a/--ada <target config file> the configuration for applying
    the replication data to an Adabas target database.


    Usage: readris [options]

    Options:
        -a  --ada           Adabas database target configuration
                            (e.g tapa2config for tapa12config.py)
        -d  --dsn           remote sequential dataset name
        -f  --fname         local file name
        -n, --numrec        <numrec> number of records to process
        -s, --skiprec       <skiprec> number of records skip before processing

        -v, --verbose       [0]|1|2|4|8|16|32
        -w  --write         file prefix
                            FTP parameters:
        -c, --config        set/show configuration
        -h, --host          <host name> of IBM FTP server             (*)
        -p, --pwd           <password>  FTP ser1.3.0ogin password     (*)
        -u, --user          <userid>                                  (*)
        -C, --certfile      <file> .pem file with server certificates (*)


        -t  --test          <name> testing LNKUEX <name> DLL/SO
                            instead of adalnkx call the exit is called directly
        -?, --help

    defaults marked with (*) are taken from configuration (-c)
    The configuration values are stored ciphered in file ~/.toolz

    verbose 1/2 - FTP, 4 - dump records (exclusive RDW), 8 - display URB fields
            16 - dump CB, 32 - dump FB and RB

    if executed in Python optimized mode no URB short form will be printed
        (python -o readris.py ...)

    Examples:

    1. set configuration user, password

       >> readris --config --user hugo --pwd secret

    2. read remote ADARIS output dataset with verbose FTP operations, user and password
       are taken from configuration creates the output files
       rpe2.cmpin.d10006f024 and rpe2.mupisn.d10006f024

       >> readris -d mm.temp.ris1 -h da3f -v8 -w rpe2.

    3. read local file with ADARIS or ADARPE data and store in Adabas database
       target db/fnr and subscription info is in tapa12config.py

       >> readris -f mm.temp.rpeapemu -a tapa12config

"""
from __future__ import print_function          # PY3

dic2str = lambda d: ','.join(['%s=%s' % (k,v) for k,v in d.items()])
""" Transform dictionary to key=value pairs separated by comma
    >>> dic2str = lambda d: ','.join(['%s=%s' % (k,v) for k,v in d.items()])
    >>> dic2str(dict(blau=1,rot=2))
    'blau=1,rot=2'
    >>> dic2str({})
    ''
"""

dic2str0 = lambda d: ','+dic2str(d) if d else ''
""" prefix dic2str result with comma if dict not empty """


def usage():
    print(__doc__)

def write_isns():
    """Crite out ISNs found in a transaction
    Called from URBE End Transaction block or URBT ET handler

    For consecutive ISNs write ISN1-ISN2 otherwise ISN<n> in separate records
    isns=[1,22,23,24,26,27,29,29,29,270,290,290,291,3000,3001,10007,10008,10009]
    """
    global isns, numIsni, wfi

    i=j=0
    if len(isns):
        j = i = isns.pop(0)
        for k in isns:
            if j == k:      # duplicate isn
                continue
            if j != (k-1):  # isns are not adjacent
                if i == j:  # start value
                    wfi.write('%d\n' % i)
                    numIsni += 1
                else:
                    wfi.write('%d-%d\n' % (i,j))
                    numIsni += 1
                i=j=k
            else:           # isns are adjacent
                j=k         # update last isn in range
        if i == j:
            wfi.write('%d\n' % i)
            numIsni += 1
        else:
            wfi.write('%d-%d\n' % (i,j))
            numIsni += 1
    #end output of ISNs or ISN ranges
    isns=[]


def detailProcess(dd,substat):
    "default URB block handler"
    if verbose & 8:
        dd.dprint()


def endtransProcess(ee,substat):
    "URBE End Transaction block handler"
    global snam, sdbid, transStarted, isns, wfi
    if verbose & 8:
        ee.dprint()

    if wfi and isns:
        write_isns()

    snam=''    # reset subscription name
    sdbid=''   # and dbid
    transStarted = None


def gformatProcess(ff,substat):
    """URBF and URBG Global Format handler

     - optionally Log URBF and URBGs
     - construct Datamap with items defined in URBGs
    """
    global recordmap

    gg=urb.Urbg(buffer=None,offset=0)
    fields = []
    fields_stacked = []
    dlines = ['from adapya.base.datamap import Unicode,String,Bytes,Float,Double',
              'from adapya.base.datamap import Datamap,Periodic,Packed,Unpacked',
              'from adapya.base.datamap import Uint1,Uint2,Uint4,Uint8',
              'from adapya.base.datamap import Int1,Int2,Int4,Int8',
             ]
    peopt = {}  # options for PE group
    pefid = ''  # PE group name (2 chars) (referenced by fields in PE group)
    pename = '' # PE group long name

    if verbose & 8:
        ff.dprint() # print URBF nicely

    datalen = ff.urbflend
    if datalen > 0:
        gg.buffer = ff.buffer
        gg.offset = ff.offset+urb.URBFL

        gg.setEbcdic(ff.ebcdic)
        gg.setByteOrder(ff.byteOrder)

        filename = fixnamestyle( ff.urbffnam, namestyle='_')
        dlines.append('dm_%s = Datamap(%r,' % (filename,filename))

        for i in range(ff.urbfcntg):
            if verbose & 8:
                gg.dprint() # print URBG nicely

            fname = fixnamestyle( gg.urbgfnam, namestyle='_')

            print('pefid=%s peopt=%s pename=%s' % (pefid, dic2str(peopt), pename))

            if pefid and pefid != gg.urbgfgrp:
                print('exit PE group %s: %s' %( pefid, dic2str(peopt)))

                # started in PE group and current element does not reference
                # PE group: need to close PE group
                fields_stacked.append(Periodic(Datamap(pename, *fields), **peopt))
                dlines.append('\t%s),' % (dic2str(peopt),))
                fields = fields_stacked
                pefid = ''
                pename = ''
                peopt = {}

            if gg.urbgffmt == urb.URBGFFNF: # group field

                if gg.urbgtype & urb.URBGFTPE and not (                 # range of PE occs
                        gg.urbgflag & (urb.URBGFPEE | urb.URBGFOPT)):   # non-repeating range in PE group and not optimized
                    #o include startocc=gg.urbgfrfm (datamap does not know it yet)
                    # peopt.update(occurs=gg.urbgfrno)    # number of occurrences not present in PE group element!!!
                    fields_stacked = fields
                    fields = []
                    pename = fname
                    pefid = gg.urbgfid
                    dlines.append('\tPeriodic(Datamap(%r,' % (fname,))
                else:
                    print('Skipping Group element %d' % gg.urbgidx)

                gg.offset += urb.URBGL
                continue

            if gg.urbgtype & urb.URBGFTCT:
                print('Skipping Counter element %d, not yet implemented' % gg.urbgidx)
                gg.offset += urb.URBGL
                continue
            elif gg.urbgtype & urb.URBGFTSC:
                print('Skipping Significance element %d, not yet implemented' % gg.urbgidx)
                gg.offset += urb.URBGL
                continue

            # determine field type to add to datamap

            fieldopt = {}  # collect additional options for field definition
            fieldopt.update(fn=gg.urbgfid)

            if gg.urbgtype & urb.URBGFTPE:      # range of PE occs
                if not peopt:
                    peopt.update(occurs=gg.urbgfrno)    # catch number of occs in PE group
                # fieldopt.update(occurs=gg.urbgfrno)   # number of occurrences (not on field in PE level
                #o include startocc=gg.urbgfrfm (datamap does not allow to set it)
                fieldopt.update(fn=gg.urbgfid)

            if gg.urbgtype & urb.URBGFTMU:    # range of MU occs
                if gg.urbgtype & urb.URBGFTPE:  # MU in PE
                    fieldopt.update(occurs=gg.urbgfono) # from 2nd level
                else:
                    fieldopt.update(occurs=gg.urbgfrno) # from 1st level
                #fieldopt.update(fn='%s1-%d' % (gg.urbgfid,gg.urbgfrno))
                fieldopt.update(fn=gg.urbgfid)

            # add short name

            if gg.urbgffmt == urb.URBGFFAL:     # Alpha
                fields.append(datamap.String(fname, gg.urbgflen, **fieldopt))
                dlines.append("\tString(%s,%d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFWA:   # Wide Alpha
                fields.append(datamap.Unicode(fname, gg.urbgflen, **fieldopt))
                dlines.append("\tUnicode(%s, %d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFBN:   # Binary unsigned
                if gg.urbgflen == 1:
                    fields.append(datamap.Uint1(fname, **fieldopt))
                    dlines.append("\tUint1(%s%s)," % (fname, dic2str0(fieldopt) ))
                if gg.urbgflen == 2:
                    fields.append(datamap.Uint2(fname, **fieldopt))
                    dlines.append("\tUint2(%s%s)," % (fname, dic2str0(fieldopt) ))
                if gg.urbgflen == 4:
                    fields.append(datamap.Uint4(fname, **fieldopt))
                    dlines.append("\tUint4(%s%s)," % (fname, dic2str0(fieldopt) ))
                if gg.urbgflen == 8:
                    fields.append(datamap.Uint8(fname, **fieldopt))
                    dlines.append("\tUint8(%s%s)," % (fname, dic2str0(fieldopt)))
                else:
                    fields.append(datamap.Bytes(fname, gg.urbgflen))
                    dlines.append("\tBytes(%s, %d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFSB:   # Binary signed
                if gg.urbgflen == 1:
                    fields.append(datamap.Int1(fname, **fieldopt))
                    dlines.append("\tInt1(%s%s)," % (fname, dic2str0(fieldopt)))
                if gg.urbgflen == 2:
                    fields.append(datamap.Int2(fname, **fieldopt))
                    dlines.append("\tInt2(%s%s)," % (fname, dic2str0(fieldopt)))
                if gg.urbgflen == 4:
                    fields.append(datamap.Int4(fname, **fieldopt))
                    dlines.append("\tInt4(%s%s)," % (fname, dic2str0(fieldopt)))
                if gg.urbgflen == 8:
                    fields.append(datamap.Int8(fname, **fieldopt))
                    dlines.append("\tInt8(%s%s)," % (fname, dic2str0(fieldopt)))
                else:
                    fields.append(datamap.Bytes(fname, gg.urbgflen, **fieldopt))
                    dlines.append("\tBytes(%s,%d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFBS:   # Binary String
                fields.append(datamap.Bytes(fname, gg.urbgflen, **fieldopt))
                dlines.append("\tBytes(%s,%d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFSF:   # short floating point
                fields.append(datamap.Float(fname, **fieldopt))
                dlines.append("\tFloat(%s%s)," % (fname,dic2str0(fieldopt)))
            elif gg.urbgffmt == urb.URBGFFLF:   # long floating point
                fields.append(datamap.Double(fname, **fieldopt))
                dlines.append("\tDouble(%s%s)," % (fname,dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFPK:   # packed
                fields.append(datamap.Packed(fname, gg.urbgflen, **fieldopt))
                dlines.append("\tPacked(%s,%d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt))) # gg.urbgfprc precision is not added to length
                print(fields[-1],dlines[-1])
            elif gg.urbgffmt == urb.URBGFFPD:   # packed Date (4 bytes)
                fields.append(datamap.Packed(fname, gg.urbgflen, dt='NATDATE', **fieldopt))
                dlines.append("\tPacked(%s,%d,dt='NATDATE'%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))
            elif gg.urbgffmt == urb.URBGFFPT:   # packed Time (7 bytes)
                fields.append(datamap.Packed(fname, gg.urbgflen, dt='NATTIME', **fieldopt))
                dlines.append("\tPacked(%s,%d,dt='NATTIME'%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFDT:   # un?packed Date
                fields.append(datamap.Unpacked(fname, gg.urbgflen, dt='DATE', **fieldopt))
                dlines.append("\tPacked(%s,%d,dt='DATE'%)," % (fname, gg.urbgflen, dic2str0(fieldopt)))
            elif gg.urbgffmt == urb.URBGFFTM:   # un?packed Time
                fields.append(datamap.Unpacked(fname, gg.urbgflen, dt='TIME', **fieldopt))
                dlines.append("\tPacked(%s, %d, dt='TIME'%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            elif gg.urbgffmt == urb.URBGFFUN:  # unpacked
                fields.append(datamap.Unpacked(fname, gg.urbgflen, **fieldopt))
                dlines.append("\tUnpacked(%s,%d%s)," % (fname, gg.urbgflen, dic2str0(fieldopt)))

            else:
                print('Skipping field element %d, format to be implemented' % gg.urbgidx)
                # continue

            gg.offset += urb.URBGL

        if pefid:
            # started in PE group and all elements processed
            # PE group: need to close PE group
                fields_stacked.append(Periodic(Datamap(pename, *fields), **peopt))
                print('finalize periodic:',fields_stacked[-1])
                dlines.append('\t),%s)' % (dic2str(peopt),))
                fields = fields_stacked
                pefid = ''
                pename = ''
                peopt = {}

        recordmap = datamap.Datamap(filename,*fields)

        recordmap.prepare() # adjust lengths (if fixed)

        recordmap.setEbcdic(ff.ebcdic)          # should be set later from URBT
        recordmap.setByteOrder(ff.byteOrder)    # should be set later from URBT

        dlines.append('\t)')

        print('Collected dmap fields:\n')

        for dl in dlines:
            print('\t',dl)




def transProcess(tt,substat):
    "URBT Transaction block handler"
    global snam, sdbid, transStarted, rcnt, isns, wfi, firstTransaction, lastTransaction
    if verbose & 8:
        tt.dprint()

    if transStarted is not None:  # previous transaction start without end
        if repli.typ & reptor.typURBH:
            print('New Transaction %d started without previous %d ended (URBE)' %(
                tt.urbttsnr, transStarted))
        else:
            if rcnt > 0:
                print('New Transaction %d started but previous %d had %d missing records' %(
                    tt.urbttsnr, transStarted, rcnt))
            elif wfi and isns:
                write_isns()
    else:
        if not firstTransaction:
            firstTransaction = (tt.urbtsnam, tt.urbttsnr, tt.urbtttim )

    lastTransaction = (tt.urbtsnam, tt.urbttsnr, tt.urbtttim )
    transStarted = tt.urbttsnr
    rcnt = tt.urbtrcnt
    snam = tt.urbtsnam    # remember subscription name
    sdbid = tt.urbtdbid   # and dbid
    isns = []

def recProcess(rr,substat):
    "URBR Record block handler"
    global numIsn, rtyp, curIsn, rcnt, sdbid, sfnr, transStarted, wf, wfname, wfi, wfiname

    if verbose & 8:
        rr.dprint()

    if transStarted is None:
        print('No Transaction Start: skipping record %d fnr %d' % (
            rr.urbrisn, rr.urbrfnr))
        return

    rcnt -= 1   # count down records in transaction

    if repli.typ & reptor.typURBH and rr.urbrtyp != 'R':
        print('No initial state record from adaris input: skipping')
        rr.dprint()
        repli.perrors += 1
        return

    if rr.urbrrsp != 0:
        print('Record File %d ISN %d with Adabas response code %d: skipping' %(
            rr.urbrfnr, rr.urbrisn, rr.urbrrsp))
        repli.perrors += 1
        curIsn=0
        return

    sfnr=rr.urbrfnr
    curIsn = rr.urbrisn
    numIsn += 1
    isns.append(curIsn) # collect ISNs in a transaction

    if writeprefix:
        if not wf:
            wfname=writeprefix+'cmpin.d%03df%d' % (sdbid,sfnr)
            wf = open(wfname,'wb')
            print('Writing to ADACMP input file CMPIN %r ' %(wfname,))
        if not wfi:
            wfiname=writeprefix+'mupisn.d%03df%d' % (sdbid,sfnr)
            wfi = open(wfiname,'w')
            print('Writing ISNs to ADAMUP input file MUPISN %r ' %(wfiname,))
    return

def dataProcess(dd,substat):
    "URBD Data block handler"
    global numIsn, rtyp, curIsn, sdbid, sfnr, transStarted, wf, wfname, isns, recordmap

    if verbose & 8:
        dd.dprint()

        if recordmap:
            recordmap.buffer = dd.buffer
            recordmap.offset = dd.offset + urb.URBDL
            print('  Record:')
            recordmap.dprint(indent=4)

    if not (snam and sdbid and sfnr):
        raise 'Data record without previous URBT and/or URBR'

    if wf and curIsn:
        start = dd.offset + urb.URBDL
        writerec(wf, dd.buffer[start:start+dd.urbdlend],
            isn=curIsn, recform='RDW')
    return


if __name__=='__main__':

    import sys,os
    import getopt
    from adapya.base.ftptoolz import Ftpzos
    from adapya.base.recordio import readrec, writerec
    from adapya.base.jconfig import getparms,setparms,SHOWCONFIG
    from adapya.base import stck
    from adapya.base.dump import dump
    from adapya.era import reptor, urb
    from adapya.base import datamap
    from adapya.base.datamap import Datamap, Periodic
    from adapya.adabas.sysdic import fixnamestyle

    # default values
    host=None
    user=None
    pwd=None
    certfile=None #''

    numrec=0
    skiprec=0

    config=0
    dsn=''      # Dataset name
    fname=''    # local file name
    verbose=0
    writeprefix=''
    tapacfg=''   # Adabs target database configuration (e.g tapa12config for tapa12config.py)
    lnkuex=''
    lnkuexso=None # shared library with lnkuex_0 user exit (test parameter)


    substat = reptor.SubscriptionStatus()  # keep status of messages received

    wfi=wf=None         # global
    wfifname=wfname=''

    #   global c1, numIsn, rtyp,
    curIsn=0
    numIsni=numIsn=0
    snam=''
    sdbid=0
    sfnr=0
    transStarted=None
    isns=[]
    firstTransaction = None
    lastTransaction = None

    recordmap = None

    try:
      opts, args = getopt.getopt(sys.argv[1:],
        '?a:d:f:h:n:p:s:u:cC:v:t:w:',
        ['help','ada','file','host=','numrec=','pwd=','skiprec=',
            'user=','config','verbose:','test:','write:'])
    except getopt.GetoptError:
      print(sys.argv[1:])
      usage()
      sys.exit(2)
    if len(sys.argv)==1:
        usage()
        sys.exit(2)
    for opt, arg in opts:
       # print(opt, arg)
      if opt in ('-?', '--help'):
        usage()
        sys.exit()
      elif opt in ('-a', '--ada'):
        tapacfg = arg
      elif opt in ('-c', '--config'):
        config=1
      elif opt in ('-d', '--dsn'):
        dsn = "'%s'" % arg
      elif opt in ('-f', '--file'):
        fname = arg
      elif opt in ('-h', '--host'):
          host=arg
      elif opt in ('-n', '--numrec'):
          numrec=int(arg)
      elif opt in ('-p', '--pwd'):
          pwd=arg
      elif opt in ('-s', '--skiprec'):
          skiprec=int(arg)
      elif opt in ('-u', '--user'):
          user=arg
      elif opt in ('-v', '--verbose'):
          verbose=int(arg)
      elif opt in ('-t', '--test'):
          lnkuex=arg
          print('lnkuex', lnkuex)
      elif opt in ('-w', '--write'):
          writeprefix=arg
      elif opt in ('-C', '--certfile'):
          certfile=arg

    if config:
        if host or pwd or user or certfile:
            print('Updating configuration file .ztools')
            setparms('ftp',SHOWCONFIG,host=host,pwd=pwd,user=user,certfile=cerfile) # only update parms if not default
        else:
            print('Reading configuration file .ztools')
            getparms('ftp',SHOWCONFIG,host='',user='',pwd='',certfile='') # emtpy parms
        sys.exit(0)

    print('\n--- readris starting ---')
    if tapacfg:
        tapcfg = __import__(tapacfg)
        psu = tapcfg.psu  # Subscription

        lnkuexso=None

        if lnkuex:
            print('Testing adalnk user exit 0 directly w/o adalnkx')
            import ctypes
            from ctypes import c_char_p, sizeof
            # load
            try:
                print('Running Python Version %s\n\ton platform %s, %d bit, byteorder=%s' % (
                    sys.version, sys.platform, sizeof(c_char_p)*8, sys.byteorder ))
                lnkuexso = ctypes.cdll.LoadLibrary(lnkuex)
                lnkuexso.lnkuex_0.argtypes = [c_char_p,c_char_p,c_char_p,c_char_p,c_char_p,c_char_p]
            except OSError:
                print('"%s" could not be loaded: check that Library directory is in path' %(lnkuex,))
                raise

        from adapya.era import tapada
        repli = tapada.Tapada(psu,lnkuexso=lnkuexso) # keep status of messages received

        if verbose >= 16:
            from adapya.base.defs import log,LOGCMD,LOGCB,LOGFB,LOGRB
            if verbose & 32:
                log(LOGCMD+LOGCB+LOGFB+LOGRB)
            else:
                log(LOGCMD+LOGCB)

    else:
        repli = reptor.Replicator()     # keep status of messages received
        # set Replication Messages Handlers
        repli.setHandler(urb.URBCEYE,   detailProcess)
        repli.setHandler(urb.URBDEYE,     dataProcess)
        repli.setHandler(urb.URBEEYE, endtransProcess)
        repli.setHandler(urb.URBFEYE,  gformatProcess)
        repli.setHandler(urb.URBHEYE,   detailProcess)
        repli.setHandler(urb.URBIEYE,   detailProcess)
        repli.setHandler(urb.URBREYE,      recProcess)
        repli.setHandler(urb.URBSEYE,   detailProcess)
        repli.setHandler(urb.URBTEYE,    transProcess)
        repli.setHandler(urb.URBUEYE,   detailProcess)

    if verbose >= 4:
        repli.logging |= (1<<16)
    if verbose >= 8:
        repli.logging |= reptor.LOGallURB

    if dsn:
        # get ftp parameters (host,user,pwd) if not set by caller
        ftpcfg = getparms('ftp',verbose,host=host,user=user,pwd=pwd,certfile=certfile)
        host=ftpcfg.get('host','') # make sure that parms are not None
        pwd=ftpcfg.get('pwd','')
        user=ftpcfg.get('user','')
        certfile=ftpcfg.get('certfile','')

        if not fname:
            fname = dsn.strip("'") # remove quotes

        ftpz=Ftpzos(host,user,pwd,verbose=verbose&3,test=0,certfile=certfile)  # zos jes extensions
        ftp=ftpz.ftp # ftplib.FTP session for orinary ftp commands

        ftpz.getbinaryfile(dsn,fname,rdw=1) # read file with variable records
        print('Sequential dataset %s copied to local %s' % (dsn, fname))

        ftp.quit()     # do not reuse ftp.
        # now the file is locally accessible

    else:
        if not fname:
            print('Dataset name or local file name must be specified (-d or -f)')
            sys.exit(1)


    if verbose & 8 :
        hdr = 'Input record'
    else:
        hdr = ''


    with open(fname, 'rb') as f:
        for rec in readrec( f, recform='RDW', numrec=numrec, skiprec=skiprec, dumphdr=hdr):
            if len(rec) == 6 and rec in (b'NOSPRE', 'NOSPRE'.encode('cp037')):
                print('Skipping NOSPRE')
                continue
            repli.process(rec, len(rec), 0, substat)

        print('\n\t%10d records from input file %r with\n\t%10d errors ' % (
            repli.pcount, fname, repli.perrors))

    if wfname:
        if isns:
            if rcnt == 0:
                write_isns()
            else:
                print('\tThe following ISNs were not written to MUPISN (missing end of transaction URBE)')
                print(isns)

        print('\t%10d records written to CMPIN file %s' % (numIsn, wfname))
        print('\t%10d records written to MUPISN file %s' % (numIsni, wfiname))
        if firstTransaction:
            sub, seq, tim = firstTransaction
            print('First transaction: sub=%s, seq=%d, ttime=%s' % (sub,seq, stck.sstckd(tim)))
        if lastTransaction:
            sub, seq, tim = lastTransaction
            print('Last transaction : sub=%s, seq=%d, ttime=%s' % (sub,seq, stck.sstckd(tim)))

    elif tapacfg:
        repli.terminate(printstats=1)



    if repli.perrors > 0:
        print('\n--- readris terminated with replication %d errors ---' % repli.perrors)
        sys.exit(1)
    else:
        print('\n--- readris terminated normally ---')
        sys.exit(0)


"""
from rc1 processing:::

print(__doc__)


#o print adabas parameters

try:
  self.c1.open(mode=UPD)

except DatabaseError, e:
  print(e.value)
  dump(e.apa.acb, header='Control Block')
  self.c1.close()
  print('Terminating due to error')
  sys.exit(0)


uowCnt=0
# receive loop
while 1:
    try:
        # bb.receiveNew(wait='1m')

        repli.process(bb.receive_buffer, bb.receive_length, bb.uowStatus)

    except BrokerTimeOut:
        continue
    except KeyboardInterrupt:
        # clean up
        print('Now terminating due to KeyboardInterrupt')
        self.c1.close()
        sys.exit(0)
    except DatabaseError, e:
        print(e.value
        dump(e.apa.acb, header='Control Block')
        print('Now terminating due to DatabaseError')
        self.c1.close()
        sys.exit(0)

    segmentCnt=1
    while # bb.uowStatus==RECV_FIRST or bb.uowStatus==RECV_MIDDLE:
        # bb.receive()
        segmentCnt+=1
        try:
            repli.process(bb.receive_buffer, bb.receive_length, bb.uowStatus)
        except DatabaseError, e:
            print(e.value)
            dump(e.apa.acb, header='Control Block')
            print('Now terminating due to DatabaseError')
            self.c1.close()
            sys.exit(0)

    # bb.commit()
    uowCnt+=1
    if __debug__:
        # print('uow number %d received with %d segments' % (uowCnt, segmentCnt))

"""

__date__='$Date: 2023-12-01 00:54:33 +0100 (Fri, 01 Dec 2023) $'

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

