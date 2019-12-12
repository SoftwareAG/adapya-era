00000  00000 00070  URBF     DSECT
                    *---------------------------------------------------------------------*
                    *        URBF -- Global Format Field Table (GFFT)                     *
                    *                                                                     *
                    *        DSECT URBF is used by the Adabas Replication Facility.       *
                    *                                                                     *
                    *        DSECT URBF contains information related to a global format   *
                    *        field table (GFFT). A GFFT describes a schema of files and   *
                    *        is passed to the destination output user exit. There is one  *
                    *        GFFT per global format definition.                           *
                    *                                                                     *
                    *  DT1   03-01-2007  Support for Mapping Tool                         *
                    *---------------------------------------------------------------------*
00000               URBFEYE  DS    CL4            URBF eye-catcher 'URBF'
00004               URBFLEN  DS    F              Length of URBF + related data (n*URBG)
00008               URBFLENH DS    F              Length of URBF
0000C               URBFLEND DS    F              Length of related data (n*URBG)
                    *
00010               URBFVERS DS    CL2            GFFT version indicator:
       0F0F1        URBFVER1 EQU   C'01'           First version
                    *                             Future releases may allow a new layout of
                    *                             the GFFT. In this case URBFVERS will be
                    *                             set to a different value.
                    *
00012               URBFFNRE DS    CL5            File number eye-catcher
00017               URBFFLAG DS    CL1            Flag for GFFTs                    .DT1.
       00000        URBFFCTP EQU   X'00'           Creation Type Predict -- Default .DT1.
       00001        URBFFCTM EQU   X'01'           Creation Type Mapping Tool       .DT1.
       00010        URBFFOPT EQU   X'10'           Optimize feature:
                    *                               - PE/MU's use occurrences 1-N
                    *                               - They must be proceeded by count field
                    *                               - MU's within a PE are not allowed
00018               URBFGFID DS    CL8            Global format ID related to GFFT
                    *
00020               URBFDBID DS    F              DBID of file
00024               URBFFNR  DS    H              File number
00026               URBFFNML DS    H              Length of file name
00028               URBFFNAM DS    CL32           File/userview name
00048               URBFTIM1 DS    XL8            Time (STCK) GFFT was created/refreshed
00050               URBFCNTG DS    H              Number of following URBG elements
00052               URBFLENG DS    H              Length of each URBG element
00054               URBFTIM2 DS    XL8            Time (STCK) GFFT for ADARDE(DEXIT)
                    *
0005C                        DS    XL20           Reserved area
00070               URBFURBG DS    0D             First URBG element in GFFT
       00070        URBFL    EQU   *-URBF         DSECT length
                             URBG     ,                Global Format Field Table - cont.
00000  00000 00040  URBG     DSECT
                    *---------------------------------------------------------------------*
                    *        URBG -- Global Format Field Table (GFFT) Element             *
                    *                                                                     *
                    *        DSECT URBG is used by the Adabas Replication Facility.       *
                    *                                                                     *
                    *        DSECT URBG contains data describing one GFFT element from    *
                    *        the schema of files being replicated. One or more URBG       *
                    *        structures follow the URBF related to the global format.     *
                    *                                                                     *
                    *---------------------------------------------------------------------*
00000               URBGIDX  DS    H              Element index in GFFT
00002               URBGFID  DS    CL2            Field short name
                    *
00004               URBGFFMT DS    X              Field format:
       00000        URBGFFNF EQU   X'00'           No format (e.g., group)
       00001        URBGFFAL EQU   X'01'           Alphanumeric
       00002        URBGFFBN EQU   X'02'           Binary
       00003        URBGFFPK EQU   X'03'           Packed
       00004        URBGFFUN EQU   X'04'           Unpacked
       00005        URBGFFSF EQU   X'05'           Short floating point
       00006        URBGFFLF EQU   X'06'           Long floating point
       00010        URBGFFDT EQU   X'10'           Date type field
       00013        URBGFFPD EQU   X'13'           Packed date (4 bytes packed)
       00020        URBGFFTM EQU   X'20'           Time type field
       00023        URBGFFPT EQU   X'23'           Packed time (7 bytes packed)
       00040        URBGFFWC EQU   X'40'           Wide character format field setting
       00041        URBGFFWA EQU   X'41'           Wide character (used with URBGFFAL)
       00042        URBGFFBS EQU   X'42'           Binary string (used with URBGFFBN)
       00080        URBGFFS1 EQU   X'80'           Signed        (used with URBGFFBN)
       00082        URBGFFSB EQU   X'82'           Binary Signed (used with URBGFFBN)
                    *
00005               URBGTYPE DS    X              Field type:
       00000        URBGFTN  EQU   X'00'           Normal field
       00001        URBGFTPE EQU   X'01'           Periodic group (PE) field
       00002        URBGFTMU EQU   X'02'           Multiple value (MU) field
       00004        URBGFTCT EQU   X'04'           Counter field for MU or PE
       00008        URBGFTSC EQU   X'08'           S format element as in xxS
       00010        URBGFTKY EQU   X'10'           Primary key
       00020        URBGFTDE EQU   X'20'           Descriptor
       00040        URBGFTUQ EQU   X'40'           Unique descriptor
                    *
00006               URBGFLEN DS    H              Field length
00008               URBGFPRC DS    H              Decimal place/precision
                    *
0000A               URBGFLAG DS    X              Flags:
       00001        URBGFFRO EQU   X'01'           Do not put in output buffer
       00002        URBGFPEE EQU   X'02'           Field is repeating MU/PE element -range
                    *                               e.g. range as in AA1-N,AB1-N,AC1-N...
                    *                               A non-repeating field is an array
                    *                               of fields, e.g. AA1,AB1,AC1,AA2,AB2,AC2
       00004        URBGFSUP EQU   X'04'           Super DE/field
       00008        URBGFSUB EQU   X'08'           Sub DE/field
       00010        URBGFOPT EQU   X'10'           Optimized field
       00020        URBGFDZS EQU   X'20'           Field default zero or space - never null
                    *
0000B                        DS    X              Reserved area
                    *
0000C               URBGFRNG DS    0F             1st level of occurrences:
0000C               URBGFRNO DS     H              Range number
0000E               URBGFRFM DS     H              From-range number
                    *
00010               URBGFOCC DS    0F             2nd level of occurrences:
00010               URBGFONO DS     H              Occurrence number
00012               URBGFOFM DS     H              From-occurrence number
                    *
00014               URBGFNML DS    H              Length of field long name
00016               URBGFNAM DS    CL32           Field long name
00036               URBGFGRP DS    CL2            Name of PE group
                    *
00038               URBGFMTX DS    XL2            External Format Type
                    *
0003A               URBGFRPN DS    XL2            Redefined parent name
                    *
0003C               URBGFFON DS    CL2            Field order number
0003E                        DS    XL2            Reserved area
00040                        DS    0D
       00040        URBGL    EQU   *-URBG         DSECT length
