"""Module handles internal (not published) structures of replication
"""
from adapya.base.defs import log
from adapya.base.datamap import Datamap,String,Uint1,Uint4,Uint8,T_NONE,T_STCK
from adapya.base.dtconv import intervalstr
from adapya.base.dump import dump
from adapya.base.stck import sstckd,sec1970 # seconds since STCK epoch 1900
from adapya.era import urb
import time

# additional internal URBS cases
urb.urbs_status.update({
    'RSTA': 'Reptor statistics',
    'SLTI': 'SLOG threshold exceeded information',
    'SLTN': 'SLOG thresholds not exceeded',
    'HRBT': 'Reptor heartbeat', # URBSH structure follows URBS
    })

URBSHL = 0x60
URBSSTHB = 'HRBT' # Reptor heartbeat
URBSHTYP_ETB = 'E'

class Urbsh(Datamap):
    """ URBSH -- Reptor URBS extension for heartbeat data

    Contains heartbeat information sent from the Reptor to a target application.
    """

    def __init__(self, **kw):
        Datamap.__init__(self, 'URBSH',
            String( 'urbsheye', 6),     # URBSH eye-catcher 'URBSH'
            Uint1(  'urbshver'),        # Length of URBS + data (C5DA) + filler
            String( 'urbshtyp',1),      # Destination Broker 'E': if ETBINFO data == 0: no UOWs found (all consumed by target)
            Uint8(  'urbshctm', opt=T_STCK), # Time (STCK) of messaging system commit
            Uint8(  'urbshttm', opt=T_STCK), # Time (STCK) of last transaction processed by destination

            Uint8(  'urbshsdw', opt=T_STCK), # Time (STCK) when heartbeat was written to SLOG
            Uint8(  'urbshsdr', opt=T_STCK), # Time (STCK) when heartbeat was read from SLOG (de-logged)

            # the following fields are set for a EntireX Broker destination
            Uint8(  'urbshbtm', opt=T_STCK), # Time (STCK) of ETBINFO taken (before sending URBS)
            Uint8(  'urbshbtn', opt=T_STCK), # Time (STCK) when newest item was created in Broker queue
            Uint8(  'urbshbto', opt=T_STCK), # Time (STCK) when oldest item was created in Broker queue
            Uint8(  'urbshbcb'), # current number of bytes in Broker queue
            Uint8(  'urbshbcm'), # current number of messages in Broker queue
            Uint8(  'urbshbcu'), # current number of UOWs in Broker queue
            Uint4(  'urbshbxb'), # max number of bytes in one UOW
            Uint4(  'urbshbxm'), # max number of messages in one UOW
            **kw)

def urbslog(ss):
    # log non-public URBS data
    if ss.urbsst == URBSSTHB: # heartbeat
        hb=Urbsh(buffer=ss.buffer,offset=ss.offset+urb.URBSL)

        hb.ebcdic = ss.ebcdic       # copy architecture from URBS to URBSH
        hb.byteOrder = ss.byteOrder

        now = int( time.time())
        ctm = int((hb.urbshctm >> 32) * 1.048576 - sec1970)
        ttm = int((hb.urbshttm >> 32) * 1.048576 - sec1970)
        sdwf, sdw = (1, int((hb.urbshsdw >> 32) * 1.048576 - sec1970)) if hb.urbshsdw else (0,0)
        sdrf, sdr = (1, int((hb.urbshsdr >> 32) * 1.048576 - sec1970)) if hb.urbshsdr else (0,0)
        btmf, btm = (1, int((hb.urbshbtm >> 32) * 1.048576 - sec1970)) if hb.urbshbtm else (0,0)
        btnf, btn = (1, int((hb.urbshbtn >> 32) * 1.048576 - sec1970)) if hb.urbshbtn else (0,0)
        btof, bto = (1, int((hb.urbshbto >> 32) * 1.048576 - sec1970)) if hb.urbshbto else (0,0)

        slogtime =  ('     %s heartbeat written to SLOG, %s ago\n' % (sstckd(hb.urbshsdw), intervalstr(now-sdw))) if sdwf else ''
        delogtime = ('     %s heartbeat delogged from SLOG, %s ago\n' % (sstckd(hb.urbshsdr), intervalstr(now-sdr))) if sdrf else ''
        infotime =  ('     %s ETB Info time, %s ago\n' % (sstckd(hb.urbshbtm), intervalstr(now-btm))) if btmf else ''
        tinewest =  ('     %s newest item entered Broker queue, %s ago\n' % (sstckd(hb.urbshbtn), intervalstr(now-btn))) if btnf else ''
        tioldest =  ('     %s oldest item entered Broker queue, %s ago\n' % (sstckd(hb.urbshbto), intervalstr(now-bto))) if btof else ''
        cubyt =     ('     %d current number of bytes in queue\n' % (hb.urbshbcb,)) if hb.urbshbcb or (hb.urbshtyp == URBSHTYP_ETB) else ''
        cumsg =     ('     %d current number of messages in queue\n' % (hb.urbshbcm,)) if hb.urbshbcm or (hb.urbshtyp == URBSHTYP_ETB) else ''
        cuuow =     ('     %d current number of UOWs in queue\n' % (hb.urbshbcu,)) if hb.urbshbcu or (hb.urbshtyp == URBSHTYP_ETB) else ''

        adalog.debug('URBSH -- Heartbeat received at %s\n' \
              '     Destination %s\n'\
              '     %s Last messaging system commit, %s ago\n'\
              '     %s TA last processed in destination, %s ago\n'\
              '%s%s%s%s%s%s%s%s' %(
             time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(now)),ss.urbsdnam,
             sstckd(hb.urbshctm), intervalstr(now-ctm),
             sstckd(hb.urbshttm), intervalstr(now-ttm),
             slogtime, delogtime,
             infotime, tinewest, tioldest,
             cubyt, cumsg, cuuow
             ))

        dump(ss.buffer[ss.offset+urb.URBSL:ss.offset+urb.URBSL+URBSHL],
                header='     Reptor Heartbeat Data',
                prefix='    ',log=adalog.debug)  # ecodec=repli.ecodec)
    return
