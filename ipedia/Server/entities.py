# -*- coding: iso-8859-1 -*-

import re, unicodedata

latin1_refs=dict()
latin1_refs['quot']=34
latin1_refs['amp']=38
latin1_refs['lt']=60
latin1_refs['gt']=62
latin1_refs['copy']=64
latin1_refs['nbsp']=160
latin1_refs['iexcl']=161
latin1_refs['cent']=162
latin1_refs['pound']=163
latin1_refs['curren']=164
latin1_refs['yen']=165
latin1_refs['brvbar']=166
latin1_refs['sect']=167
latin1_refs['uml']=168
latin1_refs['copy']=169
latin1_refs['ordf']=170
latin1_refs['laquo']=171
latin1_refs['not']=172
latin1_refs['shy']=173
latin1_refs['reg']=174
latin1_refs['macr']=175
latin1_refs['deg']=176
latin1_refs['plusmn']=177
latin1_refs['sup2']=178
latin1_refs['sup3']=179
latin1_refs['acute']=180
latin1_refs['micro']=181
latin1_refs['para']=182
latin1_refs['middot']=183
latin1_refs['cedil']=184
latin1_refs['sup1']=185
latin1_refs['ordm']=186
latin1_refs['raquo']=187
latin1_refs['frac14']=188
latin1_refs['frac12']=189
latin1_refs['frac34']=190
latin1_refs['iquest']=191
latin1_refs['Agrave']=192
latin1_refs['Aacute']=193
latin1_refs['Acirc']=194
latin1_refs['Atilde']=195
latin1_refs['Auml']=196
latin1_refs['Aring']=197
latin1_refs['AElig']=198
latin1_refs['Ccedil']=199
latin1_refs['Egrave']=200
latin1_refs['Eacute']=201
latin1_refs['Ecirc']=202
latin1_refs['Euml']=203
latin1_refs['Igrave']=204
latin1_refs['Iacute']=205
latin1_refs['Icirc']=206
latin1_refs['Iuml']=207
latin1_refs['ETH']=208
latin1_refs['Ntilde']=209
latin1_refs['Ograve']=210
latin1_refs['Oacute']=211
latin1_refs['Ocirc']=212
latin1_refs['Otilde']=213
latin1_refs['Ouml']=214
latin1_refs['times']=215
latin1_refs['Oslash']=216
latin1_refs['Ugrave']=217
latin1_refs['Uacute']=218
latin1_refs['Ucirc']=219
latin1_refs['Uuml']=220
latin1_refs['Yacute']=221
latin1_refs['THORN']=222
latin1_refs['szlig']=223
latin1_refs['agrave']=224
latin1_refs['aacute']=225
latin1_refs['acirc']=226
latin1_refs['atilde']=227
latin1_refs['auml']=228
latin1_refs['aring']=229
latin1_refs['aelig']=230
latin1_refs['ccedil']=231
latin1_refs['egrave']=232
latin1_refs['eacute']=233
latin1_refs['ecirc']=234
latin1_refs['euml']=235
latin1_refs['igrave']=236
latin1_refs['iacute']=237
latin1_refs['icirc']=238
latin1_refs['iuml']=239
latin1_refs['eth']=240
latin1_refs['ntilde']=241
latin1_refs['ograve']=242
latin1_refs['oacute']=243
latin1_refs['ocirc']=244
latin1_refs['otilde']=245
latin1_refs['ouml']=246
latin1_refs['divide']=247
latin1_refs['oslash']=248
latin1_refs['ugrave']=249
latin1_refs['uacute']=250
latin1_refs['ucirc']=251
latin1_refs['uuml']=252
latin1_refs['yacute']=253
latin1_refs['thorn']=254
latin1_refs['yuml']=255
latin1_refs['minus']=ord('-')
# approximate
latin1_refs['mdash']=151
latin1_refs['ndash']=150

greek_refs=dict()
greek_refs[913]='Alpha'
greek_refs[914]='Beta'
greek_refs[915]='Gamma'
greek_refs[916]='Delta'
greek_refs[917]='Epsilon'
greek_refs[918]='Zeta'
greek_refs[919]='Eta'
greek_refs[920]='Theta'
greek_refs[921]='Iota'
greek_refs[922]='Kappa'
greek_refs[923]='Lambda'
greek_refs[924]='Mu'
greek_refs[925]='Nu'
greek_refs[926]='Xi'
greek_refs[927]='Omicron'
greek_refs[928]='Pi'
greek_refs[929]='Ro'
greek_refs[931]='Sigma'
greek_refs[932]='Tau'
greek_refs[933]='Upsilon'
greek_refs[934]='Phi'
greek_refs[935]='Chi'
greek_refs[936]='Psi'
greek_refs[937]='Omega'
greek_refs[945]='alpha'
greek_refs[946]='beta'
greek_refs[947]='gamma'
greek_refs[948]='delta'
greek_refs[949]='epsilon'
greek_refs[950]='zeta'
greek_refs[951]='eta'
greek_refs[952]='theta'
greek_refs[953]='iota'
greek_refs[954]='kappa'
greek_refs[955]='lambda'
greek_refs[956]='mu'
greek_refs[957]='nu'
greek_refs[958]='xi'
greek_refs[959]='omicron'
greek_refs[960]='pi'
greek_refs[961]='rho'
greek_refs[962]='sigma'
greek_refs[963]='sigma'
greek_refs[964]='tau'
greek_refs[965]='upsilon'
greek_refs[966]='phi'
greek_refs[967]='chi'
greek_refs[968]='psi'
greek_refs[969]='omega'
greek_refs[977]='theta'
greek_refs[978]='upsilon'
greek_refs[982]='pi'

approx_refs=dict()
approx_refs[256]='A'
approx_refs[257]='a'
approx_refs[258]='A'
approx_refs[259]='a'
approx_refs[260]='A'
approx_refs[261]='a'
approx_refs[262]='C'
approx_refs[263]='c'
approx_refs[264]='C'
approx_refs[265]='c'
approx_refs[266]='C'
approx_refs[267]='c'
approx_refs[268]='C'
approx_refs[269]='c'
approx_refs[270]='D'
approx_refs[271]='d'
approx_refs[272]='D'
approx_refs[273]='d'
approx_refs[274]='E'
approx_refs[275]='e'
approx_refs[276]='E'
approx_refs[277]='e'
approx_refs[278]='E'
approx_refs[279]='e'
approx_refs[280]='E'
approx_refs[281]='e'
approx_refs[282]='E'
approx_refs[283]='e'
approx_refs[284]='G'
approx_refs[285]='g'
approx_refs[286]='G'
approx_refs[287]='g'
approx_refs[288]='G'
approx_refs[289]='g'
approx_refs[290]='G'
approx_refs[291]='g'
approx_refs[292]='H'
approx_refs[293]='h'
approx_refs[294]='H'
approx_refs[295]='h'
approx_refs[296]='I'
approx_refs[297]='i'
approx_refs[298]='I'
approx_refs[299]='i'
approx_refs[300]='I'
approx_refs[301]='i'
approx_refs[302]='I'
approx_refs[303]='i'
approx_refs[304]='I'
approx_refs[305]='i'
approx_refs[306]='IJ'
approx_refs[307]='ij'
approx_refs[308]='J'
approx_refs[309]='j'
approx_refs[310]='K'
approx_refs[311]='k'
approx_refs[312]='k'
approx_refs[313]='L'
approx_refs[314]='l'
approx_refs[315]='L'
approx_refs[316]='l'
approx_refs[317]='L'
approx_refs[318]='l'
approx_refs[319]='L'
approx_refs[320]='I'
approx_refs[321]='L'
approx_refs[322]='l'
approx_refs[323]='N'
approx_refs[324]='n'
approx_refs[325]='N'
approx_refs[326]='n'
approx_refs[327]='N'
approx_refs[328]='n'
approx_refs[329]='n'
approx_refs[330]='N'
approx_refs[331]='n'
approx_refs[332]='O'
approx_refs[333]='o'
approx_refs[334]='O'
approx_refs[335]='o'
approx_refs[336]='O'
approx_refs[337]='o'
approx_refs[338]='OE'
approx_refs[339]='oe'
approx_refs[340]='R'
approx_refs[341]='r'
approx_refs[342]='R'
approx_refs[343]='r'
approx_refs[344]='R'
approx_refs[345]='r'
approx_refs[346]='S'
approx_refs[347]='s'
approx_refs[348]='S'
approx_refs[349]='s'
approx_refs[350]='S'
approx_refs[351]='s'
approx_refs[352]='S'
approx_refs[353]='s'
approx_refs[354]='T'
approx_refs[355]='t'
approx_refs[356]='T'
approx_refs[357]='t'
approx_refs[358]='T'
approx_refs[359]='t'
approx_refs[360]='U'
approx_refs[361]='u'
approx_refs[362]='U'
approx_refs[363]='u'
approx_refs[364]='U'
approx_refs[365]='u'
approx_refs[366]='U'
approx_refs[367]='u'
approx_refs[368]='U'
approx_refs[369]='u'
approx_refs[370]='U'
approx_refs[371]='u'
approx_refs[372]='W'
approx_refs[373]='w'
approx_refs[374]='Y'
approx_refs[375]='y'
approx_refs[376]='Y'
approx_refs[377]='Z'
approx_refs[378]='z'
approx_refs[379]='Z'
approx_refs[380]='z'
approx_refs[381]='Z'
approx_refs[382]='z'
approx_refs[383]='I'
approx_refs[384]='b'
approx_refs[385]='B'
approx_refs[386]='b'
approx_refs[387]='b'
approx_refs[388]='b'
approx_refs[389]='b'
approx_refs[390]='C'
approx_refs[391]='C'
approx_refs[392]='c'
approx_refs[393]='D'
approx_refs[394]='D'
approx_refs[395]='d'
approx_refs[396]='d'
approx_refs[397]='d'
approx_refs[398]='E'
approx_refs[399]='e'
approx_refs[400]='e'
approx_refs[401]='F'
approx_refs[402]='f'
approx_refs[403]='G'
approx_refs[404]='Y'
approx_refs[405]='h'
approx_refs[406]='I'
approx_refs[407]='I'
approx_refs[408]='K'
approx_refs[409]='k'
approx_refs[410]='t'
approx_refs[411]='L'
approx_refs[412]='M'
approx_refs[413]='N'
approx_refs[414]='e'
approx_refs[415]='t'
approx_refs[416]='O'
approx_refs[417]='o'
approx_refs[418]='S'
approx_refs[419]='s'
approx_refs[420]='P'
approx_refs[421]='p'
approx_refs[422]='R'
approx_refs[423]='S'
approx_refs[424]='s'
approx_refs[425]='S'
approx_refs[426]='I'
approx_refs[427]='t'
approx_refs[428]='T'
approx_refs[429]='t'
approx_refs[430]='T'
approx_refs[431]='U'
approx_refs[432]='u'
approx_refs[433]='O'
approx_refs[434]='N'
approx_refs[435]='Y'
approx_refs[436]='y'
approx_refs[437]='Z'
approx_refs[438]='z'
approx_refs[439]='3'
approx_refs[440]='3'
approx_refs[441]='3'
approx_refs[442]='3'
approx_refs[443]='2'
approx_refs[444]='5'
approx_refs[445]='5'
approx_refs[446]='�'
approx_refs[447]='p'
approx_refs[448]='I'
approx_refs[449]='II'
approx_refs[450]='\#'
approx_refs[451]='!'
approx_refs[452]='DZ'
approx_refs[453]='Dz'
approx_refs[454]='dz'
approx_refs[455]='LJ'
approx_refs[456]='Lj'
approx_refs[457]='lj'
approx_refs[458]='NJ'
approx_refs[459]='Nj'
approx_refs[460]='nj'
approx_refs[461]='A'
approx_refs[462]='a'
approx_refs[463]='I'
approx_refs[464]='i'
approx_refs[465]='O'
approx_refs[466]='o'
approx_refs[467]='U'
approx_refs[468]='u'
approx_refs[469]='U'
approx_refs[470]='u'
approx_refs[471]='U'
approx_refs[472]='u'
approx_refs[473]='U'
approx_refs[474]='u'
approx_refs[475]='U'
approx_refs[476]='u'
approx_refs[477]='e'
approx_refs[478]='A'
approx_refs[479]='a'
approx_refs[480]='A'
approx_refs[481]='a'
approx_refs[482]='AE'
approx_refs[483]='ae'
approx_refs[484]='G'
approx_refs[485]='g'
approx_refs[486]='G'
approx_refs[487]='g'
approx_refs[488]='K'
approx_refs[489]='k'
approx_refs[490]='Q'
approx_refs[491]='q'
approx_refs[492]='Q'
approx_refs[493]='q'
approx_refs[494]='3'
approx_refs[495]='3'
approx_refs[496]='j'
approx_refs[497]='DZ'
approx_refs[498]='Dz'
approx_refs[499]='dz'
approx_refs[500]='G'
approx_refs[501]='g'
approx_refs[502]='?'
approx_refs[503]='?'
approx_refs[504]='?'
approx_refs[505]='?'
approx_refs[506]='A'
approx_refs[507]='a'
approx_refs[508]='AE'
approx_refs[509]='ae'
approx_refs[510]='O'
approx_refs[511]='o'
approx_refs[512]='A'
approx_refs[513]='a'
approx_refs[514]='A'
approx_refs[515]='a'
approx_refs[516]='E'
approx_refs[517]='e'
approx_refs[518]='E'
approx_refs[519]='e'
approx_refs[520]='I'
approx_refs[521]='i'
approx_refs[522]='i'
approx_refs[523]='i'
approx_refs[524]='O'
approx_refs[525]='o'
approx_refs[526]='O'
approx_refs[527]='o'
approx_refs[528]='R'
approx_refs[529]='r'
approx_refs[530]='R'
approx_refs[531]='r'
approx_refs[532]='U'
approx_refs[533]='u'
approx_refs[534]='U'
approx_refs[535]='u'
approx_refs[771]='�'
approx_refs[8211]=chr(150)
approx_refs[8212]=chr(151)
approx_refs[8217]='\''
approx_refs[8226]='�'
approx_refs[8230]='�'
approx_refs[8220]='"'
approx_refs[8221]='"'
#approx_refs[8242]='\''
#approx_refs[8243]='\'\''
approx_refs[8254]='-'
approx_refs[8260]='//'
approx_refs[16412]='"'
approx_refs[16413]='"'
approx_refs[16422]='...'

numEntityRe=re.compile(r'&#(\d+);')
entityRefRe=re.compile(r'&(\w+);')

def convertNamedEntities(text):
    matches=[]
    for iter in entityRefRe.finditer(text):
        matches.append(iter)
    matches.reverse()
    for match in matches:
        name=match.group(1)
        if latin1_refs.has_key(name):
            text=text[:match.start()]+chr(latin1_refs[name])+text[match.end():]
        else:
            text=text[:match.start()]+'/'+name+'/'+text[match.end():]
    return text;

def convertNumberedEntities(text):
    matches=[]
    for iter in numEntityRe.finditer(text):
        matches.append(iter)
    matches.reverse()
    for match in matches:
        num=int(match.group(1))
        if 160 == num: # nbsp i.e. ' '
            text = text[:match.start()] + " " + text[match.end():]
        elif num > 255:
            if approx_refs.has_key(num):
                text = text[:match.start()]+approx_refs[num]+text[match.end():]
            elif greek_refs.has_key(num):
                text = text[:match.start()]+'/'+greek_refs[num]+'/'+text[match.end():]
            else:
                # don't change the text
                pass
        else:
            text=text[:match.start()]+chr(num)+text[match.end():]
    return text

# This function uses .normalize function only available in python 2.3
# our converter needs to work on 2.2 so we use a simplified
# convertNumberedEntities version
def convertNumberedEntities23(text):
    matches=[]
    for iter in numEntityRe.finditer(text):
        matches.append(iter)
    matches.reverse()
    for match in matches:
        num=int(text[match.start(1):match.end(1)])
        if num>255:
            try:
                char=unichr(num)
                decomposed=unicodedata.normalize('NFKD', char)
                valid=''
                for char in decomposed:
                    if ord(char)<256:
                        valid+=chr(ord(char))
                if len(valid):
                    text=text[:match.start()]+valid+text[match.end():]
                else:
                    if approx_refs.has_key(num):
                        text=text[:match.start()]+approx_refs[num]+text[match.end():]
                    elif greek_refs.has_key(num):
                        text=text[:match.start()]+'/'+greek_refs[num]+'/'+text[match.end():]
            except ValueError:
                print "Wide unicode character (%d) in definition for text: %s." % (num, text)
        else:
            text=text[:match.start()]+chr(num)+text[match.end():]
    return text

def convertEntities(text):
    text = convertNamedEntities(text)
    text = convertNumberedEntities(text)
    return text

def convertEntities23(text):
    text = convertNamedEntities(text)
    text = convertNumberedEntities23(text)
    return text
