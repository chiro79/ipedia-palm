#!/usr/bin/python
# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk
#
# This script:
#  - downloads the main page of http://download.wikimedia.org
#  - parsers it to find the name of the current english, french and english
#    wikipedia cur database 
#    e.g.: http://download.wikimedia.org/archives/en/20040403_cur_table.sql.bz2
#  - downloads it if it hasn't been downloaded yet
#  - converts it if it hasn't been converted yet

# requires process module from
# http://starship.python.net/crew/tmick/index.html#process

import sys,string,re,time,urllib2,os,os.path,process,smtplib
import arsutils, wikipediasql, wikiToDbConvert

try:
    import psyco
    g_fPsycoAvailable = True
except:
    print "psyco not available. You should consider using it (http://psyco.sourceforge.net/)"
    g_fPsycoAvailable = False

# this is the whole text that was logged during this session
g_logTotal = ""

g_workingDir = "g:\\wikipedia\\"

# Which mail server to use when sending an e-mail
MAILHOST = None
# list of e-mail addresses to which send the e-mail
TO_LIST = ["krzysztofk@pobox.com", "kkowalczyk@gmail.com"]
FROM = None

g_machine = ""

g_latestDatabases = []

if sys.platform == "linux2":
    # this is our rackshack server
    g_workingDir = "/ipedia/wikipedia"
    MAILHOST = "localhost"
    FROM = "ipedia-dl-bot@ipedia.arslexis.com"
    g_machine = "ipedia.arslexis.com"
else:
    # this must be windows
    if "KJKLAP1"==os.getenv("COMPUTERNAME"):
        # this must be my laptop
        g_workingDir = "c:\\wikipedia\\"
        # this will only work when I'm connected to nwlink.com
        MAILHOST = "mail.nwlink.com"
        FROM = "kjk@nwlink.com"
        g_machine = "KJKLAP1"
    if "DVD"==os.getenv("COMPUTERNAME"):
        # this must be my desktop machine
        g_workingDir = "g:\\wikipedia\\"
        # this will only work when I'm connected to nwlink.com
        MAILHOST = "mail.nwlink.com"
        FROM = "kjk@nwlink.com"
        g_machine = "DVD"

#print "Working dir: %s" % g_workingDir

g_logFileName = os.path.join(g_workingDir,"log.txt")

g_reEnName = re.compile('archives/en/(\d+)_cur_table.sql.bz2', re.I)
g_reFrName = re.compile('archives/fr/(\d+)_cur_table.sql.bz2', re.I)
g_reDeName = re.compile('archives/de/(\d+)_cur_table.sql.bz2', re.I)

g_enUrlToDownload = None
g_deUrlToDownload = None
g_frUrlToDownload = None

g_foLog = None
def openLogFileIfNotOpen():
    global g_foLog, g_logFileName
    if None == g_foLog:
        g_foLog = open(g_logFileName, "ab+")
        curTime = time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() )
        g_foLog.write( "Activity on %s\n" % curTime)
    return g_foLog

def closeLogFile():
    global g_foLog
    if g_foLog:
        g_foLog.close()

def logEvent(txtToLog):
    global g_logTotal
    g_logTotal = "%s\n%s" % (g_logTotal,txtToLog)
    #print txtToLog
    fo = openLogFileIfNotOpen()
    fo.write("  " + txtToLog + "\n")
    fo.flush()

def matchUrlInTxt(txt, regExp):
    match=regExp.search(txt)
    if not match:
        return None

    fileName = txt[match.start():match.end()]
    fileUrl = 'http://download.wikimedia.org/' + fileName
    return fileUrl

def findEnFileUrlInStr(txt):
    global g_reEnName
    return matchUrlInTxt(txt, g_reEnName)

def findFrFileUrlInStr(txt):
    global g_reFrName
    return matchUrlInTxt(txt, g_reFrName)

def findDeFileUrlInStr(txt):
    global g_reDeName
    return matchUrlInTxt(txt, g_reDeName)

def getCurrentFileUrls():
    global g_enUrlToDownload, g_deUrlToDownload, g_frUrlToDownload
    try:
        f = urllib2.urlopen('http://download.wikimedia.org/')
        wikipediaHtml = f.read()
        f.close()
    except:
        logEvent("Failed to download http://download.wikimedia.org")
        raise
    #print wikipediaHtml
    logEvent("Downloaded http://download.wikimedia.org/index.html")
    g_enUrlToDownload = findEnFileUrlInStr(wikipediaHtml)
    if g_enUrlToDownload:
        logEvent("Found url for en cur database: " + g_enUrlToDownload )
    else:
        logEvent("Didn't find the url for en cur database in http://download.wikimedia.org/index.html")

    g_frUrlToDownload = findFrFileUrlInStr(wikipediaHtml)
    if g_frUrlToDownload:
        logEvent("Found url for fr cur database: " + g_frUrlToDownload )
    else:
        logEvent("Didn't find the url for fr cur database in http://download.wikimedia.org/index.html")

    g_deUrlToDownload = findDeFileUrlInStr(wikipediaHtml)
    if g_deUrlToDownload:
        logEvent("Found url for de cur database: " + g_deUrlToDownload )
    else:
        logEvent("Didn't find the url for de cur database in http://download.wikimedia.org/index.html")

def fFileExists(filePath):
    try:
        st = os.stat(filePath)
    except OSError:
        # TODO: should check that Errno is 2
        return False
    return True

# based on url of the form http://*/$lang/$fileName construct a file name of
# form "%s_%s" % ($lang, $fileName)
def fileNamesFromUrl(url):
    global g_workingDir
    fileName = url.split("/")[-1]
    lang = url.split("/")[-2]
    fileNameGzipped = "%s_%s" % (lang,fileName)
    filePathGzipped = os.path.join(g_workingDir,fileNameGzipped)

    # convert "foo.sql.bz2" to "foo.sql"
    parts = filePathGzipped.split(".")
    filePathUngzipped = string.join(parts[0:-1], ".")
    filePathUngzipped = os.path.join(g_workingDir,filePathUngzipped)

    #print filePathGzipped
    #print filePathUngzipped

    return (filePathGzipped, filePathUngzipped)

def fDbDownloaded(url):
    (fileGzipped, fileUngizpped) = fileNamesFromUrl(url)
    if fFileExists(fileGzipped):
        return True
    if fFileExists(fileUngizpped):
        return True
    return False

# I could try to use python's urllib2 module to do the downloading, but
# I prefer to outsorce that to wget
def downloadUrl(url):
    global g_workingDir

    if None == url:
        return
    os.chdir(g_workingDir)
    (fileNameGzipped, fileNameUngzipped) = fileNamesFromUrl(url)

    # don't remove '-q' option! if it's removed, the download hangs at 2.30 MB
    # (for whatever wicked reason)
    p = process.ProcessOpen(['wget', '-q', '-c', url, '--output-document', fileNameGzipped])

    res_stdout = p.stdout.read()                                     
    res_stderr = p.stderr.read()
    status = p.wait()   # .wait() returns the child's exit status

    #print "status = %d" % status

    if -1 != res_stderr.find("is not recognized"):
        logEvent("didn't launch wget properly")
        return
    
    if fDbDownloaded(url):
        logEvent("succesfully downloaded %s" % url)
    else:
        logEvent("failed to download %s" % url)

def downloadDb(url):
    global g_latestDatabases

    if fDbDownloaded(url):
        logEvent("%s has already been downloaded" % url)
    else:
        downloadUrl(url)

    if fDbDownloaded(url):
        (fileNameGzipped, fileNameUngzipped) = fileNamesFromUrl(url)
        if fFileExists(fileNameGzipped):
            g_latestDatabases.append(fileNameGzipped)

def convertDb(sqlDumpFileName):

    foLog = None
    try:
        logEvent("convertDb(%s) called" % sqlDumpFileName)
        connRoot = wikiToDbConvert.getRootConnection()

        dbName = wikiToDbConvert.getDbNameFromFileName(sqlDumpFileName)

        if dbName in wikiToDbConvert.getDbList():
            logEvent("db %s already exists" % dbName)
            return

        logEvent("started creating db %s" % dbName)
        wikiToDbConvert.createDb(connRoot,dbName)

        timer = arsutils.Timer(fStart=True)
        logFileName = wikipediasql.getLogFileName(sqlDumpFileName)
        # use small buffer so that we can observe changes with tail -w
        foLog = open(logFileName, "wb", 64)
        sys.stdout = foLog
        # sys.stderr = foLog
        wikiToDbConvert.convertArticles(sqlDumpFileName,articleLimit=None)
        wikiToDbConvert.calcReverseLinks(sqlDumpFileName)
        timer.stop()
        durInSecs = timer.getDurationInSecs()
        durTxt = arsutils.timeInSecsToTxt(durInSecs)
        logEvent("db %s created in %s" % (dbName, durTxt))

        timer = arsutils.Timer(fStart=True)
        wikiToDbConvert.createFtIndex()
        timer.stop()
        durInSecs = timer.getDurationInSecs()
        durTxt = arsutils.timeInSecsToTxt(durInSecs)
        logEvent("full-text index for db %s created in %s" % (dbName, durTxt))

        ARTICLE_COUNT_DELTA = 3000 # should be same as in iPediaServer.py
        articlesCount = wikiToDbConvert.getIpediaArticlesCount() - ARTICLE_COUNT_DELTA
        logEvent("%d articles in db %s" % (articlesCount, dbName))
    finally:
        wikiToDbConvert.deinitDatabase()
        if None != foLog:
            foLog.close()

def mailLog():
    global g_logTotal, MAILHOST, FROM, TO_LIST, g_machine
    if None == MAILHOST:
        return
    curDate = time.strftime( "%Y-%m-%d", time.localtime() )
    SUBJECT = "ipedia db download status %s (%s)" % (curDate,g_machine)
    BODY = g_logTotal
    body = string.join((
        "From: %s" % FROM,
        "To: %s" % string.join(TO_LIST,", "),
        "Subject: %s" % SUBJECT,
        "",
        BODY), "\r\n")
    #print body
    #print "SERVER: %s" % MAILHOST
    server = smtplib.SMTP(MAILHOST)
    server.sendmail(FROM, TO_LIST, body)
    server.quit()
 
if __name__=="__main__":
    if g_fPsycoAvailable:
        print "using psyco"
        psyco.full()
    try:
        getCurrentFileUrls()
        if None==g_frUrlToDownload and None==g_deUrlToDownload and None==g_enUrlToDownload:
            logEvent("didn't find any databses to download")
        else:
            downloadDb(g_frUrlToDownload)
            downloadDb(g_deUrlToDownload)
            downloadDb(g_enUrlToDownload)
            for sqlDumpFileName in g_latestDatabases:    
                    convertDb(sqlDumpFileName)
    finally:
        mailLog()