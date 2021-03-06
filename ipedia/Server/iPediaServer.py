#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

# Copyright: Krzysztof Kowalczyk
# Owner: Andrzej Ciarkowski
#
# Purpose: server component for iPedia
#
# Usage:
#   -verbose : print debugging info
#   -usepsyco : will use psyco, if available
#   -db name  : use database name
#   -listdbs  : list all available ipedia databases
#   -demon    : start in deamon mode

import sys, string, re, random, time, MySQLdb, _mysql_exceptions

import iPediaFields, ServerErrors, arsutils
from ThreadedServer import *

try:
    import psyco
    g_fPsycoAvailable = True
except:
    print "psyco not available. You should consider using it (http://psyco.sourceforge.net/)"
    g_fPsycoAvailable = False

DB_HOST        = 'localhost'
DB_USER        = 'ipedia'
DB_PWD         = 'ipedia'
MANAGEMENT_DB  = 'ipedia_manage'

g_fDisableRegistrationCheck     = False
g_unregisteredLookupsLimit      = 30
g_unregisteredLookupsDailyLimit = 2

g_fDumpPayload = False

DEFINITION_FORMAT_VERSION = "1"
PROTOCOL_VERSION = "1"

# list of supported languages. also defines the order in which we return
# languages in Available-Languages
g_supportedLangs = ["en", "de", "fr"]

# for some reason we count more things as articles than WikiPedia. In order
# to not look like we have more than them, we substract ARTICLE_COUNT_DELTA
# to the number of articles we show to people. This is just a guess - we want
# to report less than wikipedia but not much less.
ARTICLE_COUNT_DELTA = 3000

# this is a special reg code used for testing. Clients should never sent
# such reg code (a reg code format we use for real clients is a 12-digit number)
testValidRegCode    = "7432"
testDisabledRegCode = "2347"

# testing only
g_fForceUpgrade = False

# contains info about all available databases. databse name is the key, value
# is a DbInfo class describing given database
g_allDbsInfo = None

# list of all database names
g_allDbNames = None

class DbInfo:
    def __init__(self,dbName, lang, articlesCount, dbDate, redirectsCount, minDefId, maxDefId):
        self.dbName = dbName
        self.lang = lang
        self.articlesCount = articlesCount
        self.dbDate = dbDate
        self.redirectsCount = redirectsCount
        self.minDefId = minDefId
        self.maxDefId = maxDefId

# severity of the log message
# SEV_NONE is used to indicate that we don't do any logging at all
# SEV_HI is for messages of high severity (e.g. exception) that usually should always be logged
# SEV_MED is for messages of medium severity, use for debugging info that is often of interest
# SEV_LOW is for messages of low severity, use for extra debugging info that is only rarely of interest
(SEV_NONE, SEV_HI,SEV_MED,SEV_LOW) = (0,1,2,3)

# what is the highest severity that we'll log. if SEV_NONE => nothing,
# if SEV_HI => only SEV_HI messages, if SEV_MED => SEV_HI and SEV_MED messages etc.
g_acceptedLogSeverity = SEV_NONE

def log(sev,txt):
    global g_acceptedLogSeverity
    assert sev in [SEV_HI,SEV_MED,SEV_LOW] # client isn't supposed to pass SEV_NONE
    if sev <= g_acceptedLogSeverity:
        sys.stdout.write(txt)

g_dbInfoPerLang = {}

def setCurrDbForLang(lang,dbInfo):
    global g_dbInfoPerLang
    g_dbInfoPerLang[lang] = dbInfo

def getCurrDbForLang(lang):
    global g_dbInfoPerLang
    if g_dbInfoPerLang.has_key(lang):
        return g_dbInfoPerLang[lang]
    else:
        return None

def getAllLangs():
    global g_dbInfoPerLang, g_supportedLangs
    langs = [lang for lang in g_supportedLangs if g_dbInfoPerLang.has_key(lang)]
    return string.join(langs," ")

def createManagementConnection():
    #log(SEV_LOW,"creating management connection\n")
    # TODO: should we reuse the connection?
    return MySQLdb.Connect(host=DB_HOST, user=DB_USER, passwd=DB_PWD, db=MANAGEMENT_DB)

def createArticlesConnection(dbName):
    #log(SEV_LOW,"creating connection for db %s\n" % dbName)
    # TODO: should we reuse the connection?
    return MySQLdb.Connect(host=DB_HOST, user=DB_USER, passwd=DB_PWD, db=dbName)

lineSeparator =     "\n"

# A format of a request accepted by a server is very strict:
# validClientRequest = validClientField ":" fieldValue? "\n"
# fieldValue = " " string
# validClientField = "Get-Cookie" | "Protocol-Version" etc.
# In other words:
#  - if request has no parameters, then it must be a requestField immediately
#    followed by a colon (":") and a newline ("\n")
#  - if request has parameters, then it must be a requestField immediately
#    followed by a colon (":"), space (" "), arbitrary string which is an argument and newline ("\n")
#
# This function parses the request line from the server and returns a tuple
# (field,value). If request has no parameters, value is None
# If there was an error parsing the line (it doesn't correspond to our strict
# format), field is None
def parseRequestLine(line):
    parts = line.split(":", 1)
    if 1==len(parts):
        # there was no ":" so this is invalid request
        return (None,None)
    field = parts[0]
    value = parts[1]
    if ""==value:
        # the second part is an empty line which means that this is a request
        # without an argument
        return (field, None)
    # this is a request with an argument, so it should begin with a space
    if ' '!=value[0]:
        # it doesn't begin with a space, so invalid
        return (None,None)
    value = value[1:]
    return (field,value)

# given a device info as a string in our encoded form, return a dictionary
# whose keys are tags (e.g. "PL", "SN", "PN") and value is a tuple:
# (value as decoded hex string, value as original hex-encoded string)
# Return None if device info is not in a (syntactically) correct format.
# Here we don't check if tags are valid (known), just the syntax
def decodeDeviceInfo(deviceInfo):
    result = {}
    parts = deviceInfo.split(":")
    for part in parts:
        # each part has to be in the format: 2-letter tag followed by
        # hex-encoded value of that tag
        if len(part)<4:
            # 4 characters are: 2 for the tag, 2 for at least one byte of value
            return None
        tag = part[0:2]
        tagValueHex = part[2:]
        if len(tagValueHex) % 2 != 0:
            return None
        rest = tagValueHex
        tagValueDecoded = ""
        while len(rest)>0:
            curByteHex = rest[0:2]
            rest = rest[2:]
            try:
                curByte = int(curByteHex,16)
                tagValueDecoded += chr(curByte)
            except:
                return False
        result[tag] = (tagValueDecoded,tagValueHex)
    return result

# TODO: add Smartphone/Pocket PC tags
validTags = ["PL", "PN", "SN", "HN", "OC", "OD", "HS", "IM"]
def fValidDeviceInfo(deviceInfo):
    deviceInfoDecoded = decodeDeviceInfo(deviceInfo)
    if None == deviceInfoDecoded:
        log(SEV_HI,"couldn't decode device info '%s'\n" % deviceInfo)
        return False
    tagsPresent = deviceInfoDecoded.keys()
    for tag in tagsPresent:
        if tag not in validTags:
            log(SEV_HI,"tag '%s' is not valid\n" % tag)
            return False
    # "PL" (Platform) is a required tag - must be sent by all clients
    if "PL" not in tagsPresent:
        return False
    return True

# If we know for sure that device id was unique, we issue previously assigned
# cookie. This prevents using program indefinitely by just reinstalling it
# after a limit for unregistered version has been reached.
# Unique tags are:
#   PN (phone number)
#   SN (serial number)
#   HN (handspring serial number)
#   IM (Treo IMEI number)
def fDeviceInfoUnique(deviceInfo):
    deviceInfoDecoded = decodeDeviceInfo(deviceInfo)
    if None == deviceInfoDecoded:
        return False
    tags = deviceInfoDecoded.keys()
    if ("PN" in tags) or ("SN" in tags) or ("HN" in tags) or ("IM" in tags):
        return True
    return False

def getUniqueCookie(cursor):
    randMax=2**16-1
    while True:
        cookie = ""
        for i in range(8):
            val = random.randint(0, randMax)
            hexVal = hex(val)[2:]
            cookie += hexVal
        cursor.execute("""SELECT user_id FROM users WHERE cookie='%s'""" % cookie)
        row = cursor.fetchone()
        if not row:
            break
    return cookie

# return a blob which is a '\n'-separated list of all article titles that link
# to a given article. Returns None if we don't have this information.
def getReverseLinks(db,cursor,articleTitle):
    articleTitleEscaped = db.escape_string(articleTitle)
    cursor.execute("SELECT links_to_it FROM reverse_links WHERE title='%s';" % articleTitleEscaped)
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        return None

# return a tuple (articleId,articleTitle,articleBody) for a random
# article from the datbase
def getRandomArticle(cursor):
    iterationsLeft = 10
    retVal = None
    while iterationsLeft>0:
        cursor.execute("""SELECT min(id), max(id) FROM articles""")
        row = cursor.fetchone()
        (minId, maxId) = row[0], row[1]
        termId = random.randint(minId, maxId)
        query = """SELECT id, title, body FROM articles WHERE id=%d;""" % termId
        cursor.execute(query)
        row = cursor.fetchone()
        if row:
            retVal = (row[0], row[1], row[2])
            break
        iterationsLeft -= 1
    return retVal


# return a tuple (articleId,articleTitle,articleBody) for an article with a
# given title (or None if article with such title doesn't exists)
def findArticle(db, cursor, title):
    # ifninite cycles shouldn't happen, but just in case we're limiting number of re-directs
    redirectsLeft = 10
    retVal = None
    while redirectsLeft>0:
        titleEscaped = db.escape_string(title)
        query = """SELECT id, title, body FROM articles WHERE title='%s';""" % titleEscaped
        cursor.execute(query)
        row = cursor.fetchone()
        if row:
            retVal = (row[0], row[1], row[2])
            break
        query = """SELECT redirect FROM redirects WHERE title='%s';""" % titleEscaped
        cursor.execute(query)
        row = cursor.fetchone()
        if not row:
            break
        title=row[0]
        redirectsLeft -= 1
    return retVal

listLengthLimit = 200

# given a search term, return a list of articles matching this term.
# list can be empty (no matches)
def findFullTextMatches(db, cursor, searchTerm, startOffset = None):
    words = searchTerm.split()
    queryStr = string.join(words, " +")
    queryStrEscaped = db.escape_string(queryStr)
    searchTermEscaped = db.escape_string(searchTerm)
    log(SEV_LOW,"Performing full text search for '%s'\n" % queryStr)

    limitStr = " LIMIT %d " % listLengthLimit
    if startOffset is not None:
        limitStr = " LIMIT 100 OFFSET %d " % startOffset

    query = """SELECT id, title, match(title, body) AGAINST('%s') AS relevance FROM articles WHERE match(title, body) against('%s' in boolean mode) ORDER BY relevance DESC %s""" % (searchTermEscaped, queryStrEscaped, limitStr)
    cursor.execute(query)
    row = cursor.fetchone()
    if not row:
        log (SEV_LOW,"Performing non-boolean mode search for '%s'" % queryStr)
        query = """SELECT id, title, match(title, body) AGAINST('%s') AS relevance FROM articles WHERE match(title, body) against('%s') ORDER BY relevance DESC %s""" % (searchTermEscaped, queryStrEscaped, limitStr)
        cursor.execute(query)

    titleList=[]
    while row:
        titleList.append(row[1])
        row=cursor.fetchone()
    return titleList

# differen types of requests to log (request_type column in request_log table)
SEARCH_TYPE_STANDARD = 's'
SEARCH_TYPE_EXTENDED = 'e'
SEARCH_TYPE_RANDOM   = 'r'

class iPediaProtocol(LineReceiver):

    def __init__(self):
        self.delimiter = '\n'

        # info about the database we use for this client
        # must be set before we create articles connection (self.dbArticles)
        self.dbInfo = None

        self.dbManagement = None
        self.dbArticles = None

        # dictionary to keep values of client request fields parsed so far
        self.fields = {}

        self.userId = None
        self.fRegisteredUser = False

        # used in logging, must be set when we handle search requests
        self.searchResult = None

    # return true if current request has a given field
    def fHasField(self,fieldName):
        assert iPediaFields.fClientField(fieldName)
        if self.fields.has_key(fieldName):
            return True
        return False

    # return value of a given field or None if:
    #  - field was no present
    #  - field had no value (no argument) (so use fHasField() to tell those cases apart)
    def getFieldValue(self,fieldName):
        assert iPediaFields.fClientField(fieldName)
        if self.fHasField(fieldName):
            return self.fields[fieldName]
        return None

    def setFieldValue(self,fieldName,value):
        assert iPediaFields.fClientField(fieldName)
        # shouldn't be called more than once per value
        assert not self.fHasField(fieldName)
        self.fields[fieldName] = value

    def getManagementDatabase(self):
        if not self.dbManagement:
            self.dbManagement = createManagementConnection()
        return self.dbManagement

    def getArticlesDatabase(self):
        if not self.dbArticles:
            assert self.dbInfo != None
            self.dbArticles = createArticlesConnection(self.dbInfo.dbName)
        return self.dbArticles

    def outputField(self, name, value=None):
        if value:
            field = "%s: %s%s" % (name, value, lineSeparator)
        else:
            field = "%s:%s" % (name, lineSeparator)
        self.transport.write(field)
        log(SEV_MED,field)

    def outputPayloadField(self, name, payload):
        global g_fDumpPayload
        self.outputField(name, str(len(payload)))
        self.transport.write(payload)
        self.transport.write(lineSeparator)
        if g_fDumpPayload:
            log(SEV_HI,payload)

    # return client's (peer connection's) ip address as a string
    def getClientIp(self):
        peerInfo = self.transport.getPeer()
        clientIp = peerInfo.host
        return clientIp

    def logRequestGeneric(self,userId,requestType,searchData,searchResult,error):
        assert SEARCH_TYPE_STANDARD  == requestType or \
               SEARCH_TYPE_EXTENDED  == requestType or \
               SEARCH_TYPE_RANDOM    == requestType

        if SEARCH_TYPE_STANDARD == requestType:
            assert None != searchData

        if SEARCH_TYPE_EXTENDED == requestType:
            assert None != searchData

        if SEARCH_TYPE_RANDOM == requestType:
            assert None == searchData

        cursor = None
        try:
            db = self.getManagementDatabase()
            clientIp = self.getClientIp()
            clientIpEscaped = db.escape_string(clientIp)

            if None == searchData:
                assert SEARCH_TYPE_RANDOM == requestType
                searchDataTxt = "NULL"
            else:
                searchDataTxt = "'%s'" % db.escape_string(searchData)

            if None == searchResult:
                # a standard search might turn into full-text search if term
                # is not found.
                assert (SEARCH_TYPE_EXTENDED == requestType) or (SEARCH_TYPE_STANDARD == requestType) or (None != error)
                searchResultTxt = "NULL"
            else:
                searchResultTxt = "'%s'" % db.escape_string(searchResult)

            if None == error:
                errorTxt = "NULL"
            else:
                errorTxt = "'%d'" % error

            sql = "INSERT INTO request_log (user_id,client_ip,log_date,request_type,search_data,search_result,error) VALUES (%d,'%s',now(),'%s', %s, %s, %s);" % (userId, clientIpEscaped, requestType, searchDataTxt,searchResultTxt,errorTxt)
            cursor = db.cursor()
            cursor.execute(sql)
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            log(SEV_HI, arsutils.exceptionAsStr(ex))


    def logSearchRequest(self,userId,searchTerm,articleTitle,error):
        self.logRequestGeneric(userId,SEARCH_TYPE_STANDARD,searchTerm,articleTitle,error)

    def logExtendedSearchRequest(self,userId,searchTerm,error):
        self.logRequestGeneric(userId,SEARCH_TYPE_EXTENDED,searchTerm,None,error)

    def logRandomSearchRequest(self,userId,articleTitle,error):
        self.logRequestGeneric(userId,SEARCH_TYPE_RANDOM,None,articleTitle,error)

    # TODO: in order to improve performance, we should do buffered logging i.e.
    # we just cache N requests to log in memory. When we reach N (and/or some time
    # has passed), we INSERT them in one go. This should be faster.
    # Ideally we would also be able to flush cached logs via remote interface
    def logRequest(self, error):
        # sometimes we have errors before we can establish userId
        if None == self.userId:
            return

        if self.fHasField(iPediaFields.getArticle):
            self.logSearchRequest(self.userId,self.getFieldValue(iPediaFields.getArticle),self.searchResult,error)
        elif self.fHasField(iPediaFields.getArticleU):
            self.logSearchRequest(self.userId,self.getFieldValue(iPediaFields.getArticleU),self.searchResult,error)
        elif self.fHasField(iPediaFields.search):
            self.logExtendedSearchRequest(self.userId,self.getFieldValue(iPediaFields.search),error)
        elif self.fHasField(iPediaFields.getRandom):
            self.logRandomSearchRequest(self.userId,self.searchResult,error)

    # the last stage of processing a request: if there was an error, append
    # iPediaFields.error to the response, send the response to the client and
    # log the request
    def finish(self, error):
        if None != error:
            self.outputField(iPediaFields.error, str(error))
        self.transport.loseConnection()

        self.logRequest(error)
        if self.dbManagement:
            self.dbManagement.close()
            self.dbManagement=None

        if self.dbArticles:
            self.dbArticles.close()
            self.dbArticles=None

        log(SEV_MED, "--------------------------------------------------------------------------------\n")

    # return True if regCode exists in a list of valid registration codes
    def fRegCodeExists(self,regCode):
        cursor = None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            regCodeEscaped = db.escape_string(regCode)
            cursor.execute("""SELECT reg_code, disabled_p FROM reg_codes WHERE reg_code='%s'""" % regCodeEscaped)
            row = cursor.fetchone()
            cursor.close()
            if row and 'f'==row[1]:
                return True
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise
        return False

    # Log all Get-Cookie requests
    def logGetCookie(self,userId,deviceInfo,cookie):
        cursor=None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            clientIpEscaped = db.escape_string(self.getClientIp())
            deviceInfoEscaped = db.escape_string(deviceInfo)
            cookieEscaped = db.escape_string(cookie)
            cursor.execute("""INSERT INTO get_cookie_log (user_id, client_ip, log_date, device_info, cookie) VALUES (%d, '%s', now(), '%s', '%s');""" % (userId, clientIpEscaped, deviceInfoEscaped, cookieEscaped))
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            log(SEV_HI, arsutils.exceptionAsStr(ex))

    # Log all attempts to verify registration code. We ignore all errors from here
    def logRegCodeToVerify(self,userId,regCode,fRegCodeValid):
        reg_code_valid_p = 'f'
        if fRegCodeValid:
            reg_code_valid_p = 't'

        cursor=None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            clientIpEscaped = db.escape_string(self.getClientIp())
            regCodeEscaped = db.escape_string(regCode)
            cursor.execute("""INSERT INTO verify_reg_code_log (user_id, client_ip, log_date, reg_code, reg_code_valid_p) VALUES (%d, '%s', now(), '%s', '%s');""" % (userId, clientIpEscaped,regCodeEscaped, reg_code_valid_p))
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            log(SEV_HI, arsutils.exceptionAsStr(ex))

    def outputArticle(self, title, body, reverseLinks):
        self.outputField(iPediaFields.formatVersion, DEFINITION_FORMAT_VERSION)
        self.outputField(iPediaFields.articleTitle, title)
        self.searchResult = title # for loggin
        self.outputPayloadField(iPediaFields.articleBody, body)
        if None != reverseLinks:
            self.outputPayloadField(iPediaFields.reverseLinks, reverseLinks)

    def preprocessArticleBody(self, body):
        # those macros are actually removed during conversion phase, so this
        # code is disabled. I'll leave it for now if we decide to revive it
        return body
        # perf: we could improve this by marking articles that need this conversion
        # in the database and only do this if it's marked as such. but maybe
        # the overhead of storing/retrieving this info will be bigger than code

        # perf: maybe we should ignore {{NUMBEROFARTICLES}} or replace it during conversion
        body=body.replace("{{NUMBEROFARTICLES}}", str(self.dbInfo.articlesCount))
        # speed up trick: don't do the conversion if there can't possibly anything to convert
        if -1 == body.find("{{CURRENT"):
            return body
        body=body.replace("{{CURRENTMONTH}}",       str(int(time.strftime('%m'))));
        body=body.replace("{{CURRENTMONTHNAME}}",   time.strftime('%B'))
        body=body.replace("{{CURRENTMONTHNAMEGEN}}",time.strftime("%B"))
        body=body.replace("{{CURRENTDAY}}",         str(int(time.strftime("%d"))))
        body=body.replace("{{CURRENTDAYNAME}}",     time.strftime("%A"))
        body=body.replace("{{CURRENTYEAR}}",        time.strftime("%Y"))
        body=body.replace("{{CURRENTTIME}}",        time.strftime("%X"))
        return body

    def handleGetArticleURequest(self):
        assert self.fHasField(iPediaFields.getArticleU)
        title = self.getFieldValue(iPediaFields.getArticleU)
        return self.handleGetArticleRequestGeneric(title,False)

    def handleGetArticleRequest(self, fCheckLookupLimit=True):
        assert self.fHasField(iPediaFields.getArticle)
        title = self.getFieldValue(iPediaFields.getArticle)
        return self.handleGetArticleRequestGeneric(title,True)

    def handleGetArticleRequestGeneric(self, title, fCheckLookupLimit):
        if self.fHasField(iPediaFields.search) or self.fHasField(iPediaFields.getRandom):
            # those shouldn't be in the same request
            return ServerErrors.malformedRequest

        if not self.fRegisteredUser and fCheckLookupLimit:
            if self.fOverUnregisteredLookupsLimit(self.userId):
                return ServerErrors.lookupLimitReached

        cursor = None
        try:
            db = self.getArticlesDatabase()
            cursor = db.cursor()
            articleTuple = findArticle(db, cursor, title)
            if articleTuple:
                (articleId, title, body) = articleTuple
                reverseLinks = getReverseLinks(db,cursor,title)
                # self.preprocessArticleBody(body)
                self.outputArticle(title,body,reverseLinks)
            else:
                termList = findFullTextMatches(db, cursor, title)
                if 0==len(termList):
                    self.outputField(iPediaFields.notFound)
                else:
                    self.outputField(iPediaFields.articleTitle, title)
                    self.outputPayloadField(iPediaFields.searchResults, string.join(termList, "\n"))
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise
        return None

    def handleGetAvailableLangs(self):
        assert self.fHasField(iPediaFields.getAvailableLangs)
        langs = getAllLangs()
        self.outputField(iPediaFields.availableLangs, langs)

    def handleSearchRequest(self):
        assert self.fHasField(iPediaFields.search)

        if self.fHasField(iPediaFields.getArticle) or self.fHasField(iPediaFields.getRandom):
            # those shouldn't be in the same request
            return ServerErrors.malformedRequest

        searchTerm = self.getFieldValue(iPediaFields.search)
        cursor = None
        try:
            db = self.getArticlesDatabase()
            cursor = db.cursor()
            termList = findFullTextMatches(db, cursor, searchTerm)
            if 0==len(termList):
                self.outputField(iPediaFields.notFound)
            else:
                self.outputField(iPediaFields.articleTitle, searchTerm)
                self.outputPayloadField(iPediaFields.searchResults, string.join(termList, "\n"))
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
        return None

    def handleGetRandomRequest(self):
        assert self.fHasField(iPediaFields.getRandom)

        if self.fHasField(iPediaFields.getArticle) or self.fHasField(iPediaFields.search):
            # those shouldn't be in the same request
            return ServerErrors.malformedRequest

        cursor = None
        try:
            db = self.getArticlesDatabase()
            cursor = db.cursor()
            (articleId, title, body) = getRandomArticle(cursor)
            reverseLinks = getReverseLinks(db,cursor,title)
            # body = self.preprocessArticleBody(body)
            self.outputArticle(title,body,reverseLinks)
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
        return None

    # Return True if a user identified by userId is over unregistered lookup
    # limits. False if not. Assumes that we don't call this if a user is registered
    def fOverUnregisteredLookupsLimit(self,userId):
        global g_unregisteredLookupsDailyLimit, g_unregisteredLookupsLimit, g_fDisableRegistrationCheck
        assert not self.fRegisteredUser
        cursor = None
        fOverLimit = False
        try:
            db=self.getManagementDatabase()
            cursor=db.cursor()
            query="SELECT COUNT(*) FROM request_log WHERE NOT (request_type='r') AND user_id=%d" % userId
            cursor.execute(query)
            row=cursor.fetchone()
            assert None!=row
            totalLookups = row[0]
            if totalLookups >= g_unregisteredLookupsLimit:
                query="SELECT COUNT(*) FROM request_log WHERE user_id=%d AND NOT (request_type='r') AND log_date>DATE_SUB(CURDATE(), INTERVAL 1 DAY)" % self.userId
                cursor.execute(query)
                row=cursor.fetchone()
                assert None != row
                todayLookups = row[0]
                if todayLookups >= g_unregisteredLookupsDailyLimit:
                    fOverLimit=True
            cursor.close()
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise
        if g_fDisableRegistrationCheck:
            fOverLimit = False
        return fOverLimit

    # handle iPediaFields.verifyRegCode. If reg code is invalid append iPediaFields.regCodeValid
    # with value "0". If reg code is invalid, append iPediaFields.regCodeValid with value
    # "1" and update users table to mark this as a registration
    # Return error if there was an error that requires aborting connection
    # Return None if all was ok
    def handleVerifyRegistrationCodeRequest(self):
        # by now we have to have it (from handling iPediaFields.getCookie, iPediaFields.cookie or iPediaFields.regCode)
        assert self.userId
        assert self.fHasField(iPediaFields.verifyRegCode)
        # those are the only fields that can come with iPediaFields.verifyRegCode
        allowedFields = [iPediaFields.transactionId, iPediaFields.clientInfo, iPediaFields.protocolVersion, iPediaFields.cookie, iPediaFields.getCookie, iPediaFields.verifyRegCode, iPediaFields.getArticleCount, iPediaFields.getDatabaseTime, iPediaFields.getAvailableLangs]
        for field in self.fields.keys():
            if field not in allowedFields:
                return ServerErrors.malformedRequest

        regCode = self.getFieldValue(iPediaFields.verifyRegCode)

        fRegCodeExists = self.fRegCodeExists(regCode)

        self.logRegCodeToVerify(self.userId,regCode,fRegCodeExists)

        if not fRegCodeExists:
            self.outputField(iPediaFields.regCodeValid, "0")
            return None

        # update users table to reflect the fact, that this user has registered
        cursor=None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            regCodeEscaped = db.escape_string(regCode)

            # TODO: should we check if a given user is already registered? It's
            # possible scenario, but not making much sense
            cursor.execute("""UPDATE users SET reg_code='%s', registration_date=now() WHERE user_id=%d""" % (regCodeEscaped, self.userId))
            cursor.close()

            self.outputField(iPediaFields.regCodeValid, "1")
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise
        return None

    # Set self.userId based on reg code given by client
    # Return error if there was a problem that requires aborting the connection
    # Return None if all was ok
    def handleRegistrationCodeRequest(self):
        assert self.fHasField(iPediaFields.regCode)

        if self.fHasField(iPediaFields.getCookie) or self.fHasField(iPediaFields.cookie):
            # those shouldn't be in the same request
            return ServerErrors.malformedRequest

        regCode = self.getFieldValue(iPediaFields.regCode)
        cursor = None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            regCodeEscaped = db.escape_string(regCode)

            cursor.execute("SELECT user_id,disabled_p FROM users WHERE reg_code='%s';" % regCodeEscaped)
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return ServerErrors.invalidRegCode

            if 't'==row[1]:
                return ServerErrors.userDisabled

            self.userId = int(row[0])
            self.fRegisteredUser = True
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise
        return None

    # Set self.userId based on cookie given by client
    # Return error if there was a problem that requires aborting the connection
    # Return None if all was ok
    def handleCookieRequest(self):
        assert self.fHasField(iPediaFields.cookie)

        if self.fHasField(iPediaFields.getCookie) or self.fHasField(iPediaFields.regCode):
            # those shouldn't be in the same request
            return ServerErrors.malformedRequest

        cookie = self.getFieldValue(iPediaFields.cookie)
        cursor = None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            cookieEscaped = db.escape_string(cookie)

            cursor.execute("SELECT user_id,disabled_p FROM users WHERE cookie='%s';" % cookieEscaped)
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return ServerErrors.invalidCookie

            if 't'==row[1]:
                return ServerErrors.userDisabled

            self.userId = int(row[0])
        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise
        return None

    # Assign a cookie to the user. Try to re-use cookie based on deviceInfo
    # or create a new entry in users table. Set self.userId
    # Return error if there was a problem that requires aborting the connection
    # Return None if all was ok
    def handleGetCookieRequest(self):
        assert self.fHasField(iPediaFields.getCookie)

        if self.fHasField(iPediaFields.regCode) or self.fHasField(iPediaFields.cookie):
            # those shouldn't be in the same request
            return ServerErrors.malformedRequest

        deviceInfo = self.getFieldValue(iPediaFields.getCookie)
        if not fValidDeviceInfo(deviceInfo):
            return ServerErrors.unsupportedDevice

        cursor=None
        try:
            db = self.getManagementDatabase()
            cursor = db.cursor()
            deviceInfoEscaped = db.escape_string(deviceInfo)

            fNeedsCookie = True
            if fDeviceInfoUnique(deviceInfo):
                cursor.execute("SELECT user_id,cookie,reg_code FROM users WHERE device_info='%s';" % deviceInfoEscaped)
                row = cursor.fetchone()
                if row:
                    self.userId = int(row[0])
                    cookie = row[1]
                    fNeedsCookie = False
                    # TODO: what to do if reg_code exists for this row?
                    # This can happen in the scenario:
                    #  - Get-Cookie
                    #  - register
                    #  - delete the app, re-install
                    #  - Get-Cookie - we reget the cookie

            if fNeedsCookie:
                # generate new entry in users table
                cookie = getUniqueCookie(cursor)
                # it's probably still possible (but very unlikely) to have a duplicate
                # cookie, in which case we'll just abort
                query = """INSERT INTO users (cookie, device_info, cookie_issue_date, reg_code, registration_date, disabled_p) VALUES ('%s', '%s', now(), NULL, NULL, 'f');""" % (cookie, deviceInfoEscaped)
                cursor.execute(query)
                self.userId=cursor.lastrowid

            self.outputField(iPediaFields.cookie, cookie)
            cursor.close()

        except _mysql_exceptions.Error, ex:
            if cursor:
                cursor.close()
            raise

        self.logGetCookie(self.userId,deviceInfo,cookie)
        return None

    # figure out user id and set self.userId
    # Possible cases:
    # a) we get registration code
    #     - user_id is "select user_id from users where reg_code = $reg_code"
    #     - cookie should not be present
    # b) we get cookie
    #     - user_id is "select user_id from users where cookie = $cookie", reg_code column should be empty
    #     - reg code should not be present
    # c) we have Get-Cookie request
    #     - we try to re-issue cookie based on device_info i.e. if deviceInfoUnique($deviceInfo)
    #       select cookie from users where device_info = $deviceInfo. if present go to b)
    #       if not present, we create a new entry in users table, and use the new user_id
    # return error if for any reson we failed and need to terminate, None if all is ok
    def computeUserId(self):

        # case a)
        if self.fHasField(iPediaFields.regCode):
            return self.handleRegistrationCodeRequest()

        # case b)
        if self.fHasField(iPediaFields.cookie):
            return self.handleCookieRequest()

        # case c)
        if self.fHasField(iPediaFields.getCookie):
            return self.handleGetCookieRequest()

    # called after we parse the whole client request (or if there's an error
    # during request parsing) so that we can process the request and return
    # apropriate response to the client.
    # If error is != None, this is the server errro code to return to the client
    def answer(self,error):
        global g_fForceUpgrade, g_supportedLangs

        try:
            log(SEV_MED, "--------------------------------------------------------------------------------\n")

            # try to return iPediaFields.transactionId at all costs
            if self.fHasField(iPediaFields.transactionId):
                self.outputField(iPediaFields.transactionId, self.getFieldValue(iPediaFields.transactionId))

            # exit if there was an error during request parsing
            if None != error:
                return self.finish(error)

            if g_fForceUpgrade:
                return self.finish(ServerErrors.forceUpgrade)

            if not self.fHasField(iPediaFields.transactionId):
                return self.finish(ServerErrors.malformedRequest)

            # protocolVersion and clientInfo must exist
            if not self.fHasField(iPediaFields.protocolVersion):
                return self.finish(ServerErrors.malformedRequest)

            if not self.fHasField(iPediaFields.clientInfo):
                return self.finish(ServerErrors.malformedRequest)

            if PROTOCOL_VERSION != self.getFieldValue(iPediaFields.protocolVersion):
                return self.finish(ServerErrors.invalidProtocolVersion)

            error = self.computeUserId()
            if None != error:
                return self.finish(error)

            assert self.userId

            # determine which database to use. Must be set before any other
            # request is performed
            if not self.fHasField(iPediaFields.useLang):
                lang = "en"
            else:
                lang = self.getFieldValue(iPediaFields.useLang)
            # TODO: calculate valid languages list dynamically from the database
            # so that it's easier to add new languages
            if lang not in g_supportedLangs:
                return self.finish(ServerErrors.langNotAvailable)

            self.dbInfo = getCurrDbForLang(lang)
            if self.dbInfo == None:
                return self.finish(ServerErrors.langNotAvailable)

            # dispatch a function handling a given request field
            for fieldName in self.fields.keys():
                fieldHandleProc = getFieldHandler(fieldName)
                if None != fieldHandleProc:
                    error = fieldHandleProc(self)
                    if None != error:
                        return self.finish(error)

            # too simple to warrant functions
            if self.fHasField(iPediaFields.getArticleCount):
                self.outputField(iPediaFields.articleCount, str(self.dbInfo.articlesCount))

            if self.fHasField(iPediaFields.getDatabaseTime):
                self.outputField(iPediaFields.databaseTime, self.dbInfo.dbDate)

        except Exception, ex:
            log(SEV_HI, arsutils.exceptionAsStr(ex))
            return self.finish(ServerErrors.serverFailure)

        self.finish(None)

    def lineReceived(self, request):
        try:
            # empty line marks end of request
            if request == "":
                return self.answer(None)

            log(SEV_MED, "%s\n" % request)

            (fieldName,value) = parseRequestLine(request)
            if None == fieldName:
                return self.answer(ServerErrors.malformedRequest)

            if not iPediaFields.fClientField(fieldName):
                return self.answer(ServerErrors.invalidRequest)

            if iPediaFields.fFieldHasArguments(fieldName):
                if None == value:
                    # expected arguments for this request, but didn't get it
                    return self.answer(ServerErrors.requestArgumentMissing)
            else:
                if None != value:
                    # got arguments even though the function doesn't expect it
                    return self.answer(ServerErrors.unexpectedRequestArgument)

            if self.fHasField(fieldName):
                # duplicate field
                return self.answer(ServerErrors.malformedRequest)

            self.setFieldValue(fieldName,value)

        except Exception, ex:
            log(SEV_HI, arsutils.exceptionAsStr(ex))
            return self.answer(ServerErrors.serverFailure)

# matches client request to a handler function (function to be called for
# handling this request. None means there is no handler function for a given field.
clientFieldsHandlers = {
    iPediaFields.protocolVersion   : None,
    iPediaFields.clientInfo        : None,
    iPediaFields.transactionId     : None,
    iPediaFields.cookie            : None,
    iPediaFields.getCookie         : None,
    iPediaFields.regCode           : None,
    iPediaFields.verifyRegCode     : iPediaProtocol.handleVerifyRegistrationCodeRequest,

    iPediaFields.getArticle        : iPediaProtocol.handleGetArticleRequest,
    iPediaFields.getArticleU       : iPediaProtocol.handleGetArticleURequest,
    iPediaFields.getRandom         : iPediaProtocol.handleGetRandomRequest,
    iPediaFields.search            : iPediaProtocol.handleSearchRequest,
    iPediaFields.getArticleCount   : None,
    iPediaFields.getDatabaseTime   : None,

    iPediaFields.getAvailableLangs : iPediaProtocol.handleGetAvailableLangs,
    iPediaFields.useLang           : None,
}

def getFieldHandler(fieldName):
    global clientFieldsHandlers
    return clientFieldsHandlers[fieldName]

def getDbInfo(dbName):
    assert fIpediaDb(dbName)

    lang = getLangFromDbName(dbName)
    dbDate = getDateFromDbName(dbName)

    db = createArticlesConnection(dbName)
    cursor = db.cursor()
    cursor.execute("""SELECT COUNT(*), min(id), max(id) FROM articles""")
    row = cursor.fetchone()
    articlesCount = row[0]-ARTICLE_COUNT_DELTA
    minDefinitionId = row[1]
    maxDefinitionId = row[2]
    cursor.execute("""SELECT COUNT(*) FROM redirects""")
    row = cursor.fetchone()
    redirectsCount = row[0]
    cursor.close()
    db.close()

    dbInfo = DbInfo(dbName,lang, articlesCount, dbDate, redirectsCount, minDefinitionId, maxDefinitionId)
    return dbInfo

dbDateRe = re.compile("[0-9]{8}", re.I)
def fDbDate(dbDate):
    if not dbDateRe.match(dbDate):
        return False
    return True

def fIpediaDb(dbName):
    """Return True if a given database name is a name of the database with Wikipedia
    articles"""
    global g_supportedLangs

    if 0 != dbName.find("ipedia_"):
        return False
    parts = dbName.split("_")

    if 2 == len(parts):
        lang = "en"
        dbDate = parts[1]
    elif 3 == len(parts):
        lang = parts[1]
        dbDate = parts[2]
    else:
        return False

    if lang not in g_supportedLangs:
        return False

    if not fDbDate(dbDate):
        return False

    return True

# returns a dictionary describing all iPedia databases
# dictionary key is database name, the value is number of articles in that database
def getIpediaDbs():
    conn = MySQLdb.Connect(host=DB_HOST, user=DB_USER, passwd=DB_PWD, db='')
    cur = conn.cursor()
    cur.execute("SHOW DATABASES;")
    dbsInfo = {}
    for row in cur.fetchall():
        dbName = row[0]
        if fIpediaDb(dbName):
            dbsInfo[dbName] = getDbInfo(dbName)
    cur.close()
    conn.close()
    return dbsInfo

def getDbByName(dbName):
    global g_allDbsInfo
    for dbInfo in g_allDbsInfo.values():
            if dbInfo.dbName == dbName:
                return dbInfo
    return None

class iPediaTelnetProtocol(LineReceiver):

    listRe=re.compile(r'\s*list\s*', re.I)
    useDbRe=re.compile(r'\s*use\s+(\w+)\s*', re.I)

    def __init__(self):
        self.delimiter='\n'

    # lists available databases. The format is:
    # fr:
    # dbOne
    # *dbTwo
    # dbThree
    # en:
    # *dbOne
    # etc.
    def listDatabases(self):
        global g_supportedLangs
        try:
            dbInfos = getAllDbInfos(True)
            for lang in g_supportedLangs:
                currDbForLang = getCurrDbForLang(lang)
                if None != currDbForLang:
                    self.transport.write("%s:\n" % lang)
                    for dbInfo in dbInfos.values():
                        if dbInfo.lang == lang:
                            if dbInfo.dbName == currDbForLang.dbName:
                                self.transport.write("*%s %d\n" % (dbInfo.dbName, dbInfo.articlesCount))
                            else:
                                self.transport.write("%s %d\n" % (dbInfo.dbName, dbInfo.articlesCount))
        except _mysql_exceptions.Error, ex:
            txt = arsutils.exceptionAsStr(ex)
            log(SEV_HI, txt)
            self.transport.write("exception: %s \r\n" % txt)

    def useDatabase(self, dbName):
        dbsInfo = None
        try:
            dbInfos = getAllDbInfos(True)

            dbInfo = getDbByName(dbName)
            if None == dbInfo:
                self.transport.write("Database '%s' doesn't exist\n" % dbName)
                self.transport.write("Available databases:\n")
                self.listDatabases()
                return

            dbForLang = getCurrDbForLang(dbInfo.lang)
            assert dbInfo.lang == dbForLang.lang
            if dbInfo.dbName == dbForLang.dbName:
                self.transport.write("This is already current database\n");
                return

            if "en" == dbInfo.lang:
                requiredCount = 300000
            elif "fr" == dbInfo.lang:
                requiredCount = 40000
            elif "de" == dbInfo.lang:
                requiredCount = 120000
            else:
                assert False

            if dbInfo.articlesCount < requiredCount:
                self.transport.write("Database '%s' doesn't have enough articles ('%d', at least %d required)\r\n" % (dbInfo.dbName, dbInfo.articlesCount, requiredCount))
                return
            setCurrDbForLang(dbInfo.lang, dbInfo)
            self.transport.write("Switching to database %s, lang=%s\n" % (dbInfo.dbName, dbInfo.lang))
            self.transport.write("Number of Wikipedia articles: %d\n" % dbInfo.articlesCount)
            self.transport.write("Number of redirects: %d\n" % dbInfo.redirectsCount)
            self.transport.write("Databse date: %s\n" % dbInfo.dbDate)

        except _mysql_exceptions.Error, ex:
            txt = arsutils.exceptionAsStr(ex)
            log(SEV_HI, txt)
            self.transport.write("exception: %s \r\n" % txt)
            return

    def lineReceived(self, request):
        # print "telnet: '%s'" % request
        if iPediaTelnetProtocol.listRe.match(request):
            self.listDatabases()
            return

        match = iPediaTelnetProtocol.useDbRe.match(request)
        if match:
            self.useDatabase(match.group(1))
            return

        self.transport.loseConnection()

def usageAndExit():
    print "iPediaServer.py [-demon] [-verbose] [-usepsyco] [-listdbs] [-db name]"
    sys.exit(0)

def getLangFromDbName(dbName):
    # database names are in 2 styles:
    # old english db: ipedia_$date (e.g. ipedia_20040829)
    # new multi-lang db: ipedia_$lang_$data (e.g. ipedia_fr_20040829)
    parts = dbName.split("_")
    if 2==len(parts):
        # old style
        lang = "en"
    else:
        assert 3 == len(parts)
        lang = parts[1]

    return lang

def getDateFromDbName(dbName):
    parts = dbName.split("_")
    if 2==len(parts):
        dbDate = parts[1]
    else:
        assert 3 == len(parts)
        dbDate = parts[2]
    return dbDate

# read a list of databases in MySQL and set g_allDbsInfo, g_allDbNames
def getAllDbInfos(fRecreate=False):
    global g_allDbsInfo, g_allDbNames

    if None != g_allDbsInfo and not fRecreate:
        return g_allDbsInfo

    g_allDbsInfo = getIpediaDbs()
    g_allDbNames = g_allDbsInfo.keys()
    if 0 == len(g_allDbNames):
        return g_allDbsInfo
    g_allDbNames.sort()
    return g_allDbsInfo

def getAllDbNames(fRecreate=False):
    global g_allDbsInfo
    if fRecreate:
       getAllDbInfos(True)
       return g_allDbNames
    else:
        if None == g_allDbNames:
            getAllDbInfos(True)
        return g_allDbNames

def getLatestDbForLang(lang):
    dbInfosDict = getAllDbInfos()
    dbInfos = dbInfosDict.values()
    latestDb = None
    for dbInfo in dbInfos:
        if dbInfo.lang == lang:
            if None == latestDb:
                latestDb = dbInfo
            else:
                if dbInfo.dbDate > latestDb.dbDate:
                    # those are string but they also sort correctly by date
                    latestDb = dbInfo
    return latestDb

def main():
    global g_fPsycoAvailable, g_acceptedLogSeverity, g_supportedLangs, g_fDisableRegistrationCheck

    fDemon = arsutils.fDetectRemoveCmdFlag("-demon")
    if not fDemon:
        fDemon = arsutils.fDetectRemoveCmdFlag("-daemon")

    fNoCheck = arsutils.fDetectRemoveCmdFlag("-nolimits")

    if not fNoCheck:
        fNoCheck = arsutils.fDetectRemoveCmdFlag("-disableregcheck")

    if fNoCheck:
        g_fDisableRegistrationCheck = True

    g_acceptedLogSeverity = SEV_NONE
    if None != arsutils.fDetectRemoveCmdFlag( "-verbose" ):
        g_acceptedLogSeverity = SEV_MED

    fUsePsyco = arsutils.fDetectRemoveCmdFlag("-usepsyco")
    if g_fPsycoAvailable and fUsePsyco:
        print "using psyco"
        psyco.full()

    dbInfos = getAllDbInfos()
    if 0==len(dbInfos):
        print "No databases available"
        sys.exit(0)

    fListDbs = arsutils.fDetectRemoveCmdFlag("-listdbs")
    if fListDbs:
        for name in getAllDbNames():
            print name
        sys.exit(0)

    enDb = arsutils.getRemoveCmdArg("-en")
    frDb = arsutils.getRemoveCmdArg("-fr")
    deDb = arsutils.getRemoveCmdArg("-de")

    if len(sys.argv) != 1:
        usageAndExit()

    for lang in g_supportedLangs:
        dbInfo = getLatestDbForLang(lang)
        if None != dbInfo:
            setCurrDbForLang(lang,dbInfo)

    allDbNames = getAllDbNames()

    for lang in g_supportedLangs:
        dbInfo = getCurrDbForLang(lang)
        if None == dbInfo:
            print "No database for lang '%s'" % lang
        else:
            print "Using db '%s' for lang '%s', %d articles" % (dbInfo.dbName, lang, int(dbInfo.articlesCount))

    if None != enDb:
        # TODO: add selecting the db
        pass

    if fDemon:
        arsutils.daemonize('/dev/null','/ipedia/ipedia.log','/ipedia/ipedia.log')

    telnetPort = 9303 # a random number
    runTelnetServer(telnetPort, iPediaTelnetProtocol)
    port = 9000
    runServer(port, iPediaProtocol)
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()

