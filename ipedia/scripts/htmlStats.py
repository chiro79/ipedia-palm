# Author: Krzysztof Kowalczyk
# Purpose: an easy way to view ipedia usage statistics via web browser
# Usage: launch htmlStats.py via htmlStats.bat and visit
#        http://localhost:PORT/ in your favourite web browser
import sys, random, string, cgi, random, BaseHTTPServer
import arsutils, ServerErrors
from downloadStats import *

# TODO:
# - daily stats
# - in users:
#  * multi-column
#  * separate stats for registered users
#  * for registered users: number of days between trying the app and registering the app
#  * hyperlink to user id
# - fix recognition of devices
# - stats for a given user (all his requests, sorted by date, newest at the top)
# - in home:
#  * multi-column
#  * add random/search/full-text search stats

PORT = 1974

# True if we should ignore lookupLimitReached errors
g_filterLookupLimitErrors = True

g_lookupLimitErrors = 0

g_users = None
g_requests = None

# g_userStats has summary statistics about each user. It's a hash table
# where the key is user id and the value is UserStats class with summary
# info abou this user
g_userStats = None

# g_deviceStats keeps info about each device type registered with
# InfoMan. It's an array of 2-element tuples. First element is the
# count of devices, second is 
g_deviceStats = None

# g_registrationData is a hash table where a key is date and the value is a list
# of users that registered at that day
g_registrationData = None

# g_requestsPerDay has info about number of requests per day.
g_requestsPerDay = None

# g_failedReqs is cached info about failed requests, basically, filtered
# g_requests
g_failedReqs = None

def getUsersData():
    global g_users
    if None != g_users:
        return g_users
    g_users = getTableUsersData()
    return g_users

def getRequestsData():
    global g_requests
    if None != g_requests:
        return g_requests
    g_requests = getTableRequestLogData()
    return g_requests

def sortPred(el1, el2):
    return cmp(el1[1], el2[1])

def isUserRegistered(userId):
    users = getUsersData()
    regCode = users[userId-1][USERS_REG_CODE]
    if None == regCode:
        return False
    return True

class UserStats:
    def __init__(self, userId):
        self.userId = userId
        self.reqCount = 0
        self.failedReqCount = 0
        self.randomReqCount = 0
        self.searchReqCount = 0
        self.extendedReqCount = 0
        self.uniqueDays = 0
        self.fRegistered = isUserRegistered(userId)

    def getTotalReqCount(self): 
        return self.reqCount

# Creates statistics about number of requests per user. Returns
# a hash where the key is user id and the value is UserStats object.
# It's cached in g_userStats object
def getUserStats():
    global g_userStats
    if None != g_userStats:
        return g_userStats
    userStats = {}
    for req in getRequestsData():
        userId = int(req[RL_USER_ID])
        if not userStats.has_key(userId):
            userStats[userId] = UserStats(userId)
        user = userStats[userId]

        user.reqCount += 1
        if None != req[RL_ERROR]:
            user.failedReqCount += 1

        reqType = req[RL_REQUEST_TYPE]
        if "r" == reqType:
            user.randomReqCount += 1
        elif "s" == reqType:
            user.searchReqCount += 1
        elif "e" == reqType:
            user.extendedReqCount += 1
        else:
            print "unknown req type '%s'" % reqType
            assert False

    g_userStats = userStats
    return g_userStats

# given an array of UserStats objects, returns a tuple:
# - number of registered users
# - number of requests per registered user
def getRegisteredInfo(userStats):
    registered = [user for user in userStats.values() if user.fRegistered]
    registeredCount = len(registered)
    totalCount = 0
    for user in registered:
        totalCount += user.getTotalReqCount()
    return (registeredCount, totalCount / registeredCount)

def usersStatsHtml():
    userStats = getUserStats()

    (registeredCount, reqsPerRegistered) = getRegisteredInfo(userStats)

    userCount = len(userStats)
    reqCount = len(getRequestsData())
    reqPerUser = float(reqCount) / float(userCount)
    res = ["Users: %d, registered: %d, requests: %d, Requests/user: %.2f, Requests/registered: %.2f<br>" % (userCount, registeredCount, reqCount, reqPerUser, reqsPerRegistered)]

    userIds = userStats.keys()
    userIds.sort()

    res.append("<table>")
    res.append(htmlRow(["<b>user id<b>", "<b>total<b>", "<b>failed<b>"]))
    for userId in userIds:
        user = userStats[userId]
        if user.fRegistered:
            #userIdTxt = "<b><font color=red>%d</font></b>" % userId
            userIdTxt = "<b>%d</b>" % userId
        else:
            userIdTxt = str(userId)
        res.append(htmlRow((userIdTxt, str(user.getTotalReqCount()), str(user.failedReqCount))))
    res.append("</table>")
    return string.join(res, "\n")

def htmlRow(columns):
    res = ["<tr>"]
    for c in columns:
        if type(c) is tuple or type(c) is list:
            assert 2 == len(c)
            res.append("<td class=\"%s\">" % c[1])
            c = c[0]
        else:
            res.append("<td>")
        res.append(c)
        res.append("</td>")
    res.append("</tr>")
    return string.join(res, "\n")

def sortDeviceStatsPred(el1, el2):
    return cmp(el2[1], el1[1])

# Keeps info about stats about a given device. total is the number of
# users who registered with this device. recent is the number of users
# who registered recently with this device (recent are the last 100 registrations)
class DeviceStat:
    def __init__(self):
        self.total = 0
        self.recent = 0

# creates stats about devices used. Returns a hash table where the
# key is a device name and the value is number of such devices registered
def getDeviceStats():
    global g_deviceStats
    if None != g_deviceStats:
        return g_deviceStats
    deviceStats = {}
    # we rely on the fact, that this data is sorted by the 'registration' time,
    # and we use last 100 'registrations' to calculate 'recent' stats
    users = getUsersData()
    usersCount = len(users)
    for userNo in range(usersCount):
        user = users[userNo]
        deviceInfo = user[USERS_DEVICE_INFO]
        di = arsutils.decodeDi(deviceInfo)
        deviceName = di['device_name']
        if deviceStats.has_key(deviceName):
            deviceStats[deviceName].total +=1
        else:
            deviceStats[deviceName] = DeviceStat()
        if userNo > usersCount - 100:
            deviceStats[deviceName].recent += 1
    g_deviceStats = deviceStats
    return deviceStats

MIN_DEVICES_COUNT = 4

def deviceStatsHtml():
    deviceStats = getDeviceStats()
    deviceStatsArr = [[item[0], item[1].total, item[1].recent] for item in deviceStats.items() if item[1].total >= MIN_DEVICES_COUNT]
    deviceStatsArr.sort(sortDeviceStatsPred)
    res = ["<table>"]
    res.append(htmlRow(["<b>device<b>", "<b>total<b>", "<b>recent<b>"]))
    for (deviceName, total, recent) in deviceStatsArr:
        res.append(htmlRow((deviceName, str(total), str(recent))))
    res.append("</table>")
    return string.join(res, "\n")

# keeps stats about a given day
class ReqDailyStats:
    def __init__(self):
        self.total = 0
        self.failed = 0
        self.uniqueUsers = []

def sortDailyStatsPred(el1, el2):
    return cmp(el2[0], el1[0])

# hash which has a day in format "yyyy-mm-dd" as a key and the number of
# new registered users on this day as a value
g_newUsersData = None

# for a given day (in format "yyyy-mm-dd") return number of new user
# (users who started using the program on that day)
def getNewUsersForDay(dayTxt):
    global g_newUsersData
    if None == g_newUsersData:
        g_newUsersData = {}
        for user in getUsersData():
            userRegDay = user[USERS_COOKIE_ISSUE_DATE]
            if None == userRegDay:
                continue
            userRegDayTxt = "%04d-%02d-%02d" % (userRegDay.year, userRegDay.month, userRegDay.day)
            if g_newUsersData.has_key(userRegDayTxt):
                g_newUsersData[userRegDayTxt] = g_newUsersData[userRegDayTxt] + 1
            else:
                g_newUsersData[userRegDayTxt] = 1
    if g_newUsersData.has_key(dayTxt):
        return g_newUsersData[dayTxt]
    else:
        return 0

# creates stats about requests per day. Returns a hash where the key
# is the data and the value is ReqDailyStats object with stats for this
# date
def getDailyStats():
    global g_requestsPerDay
    if None != g_requestsPerDay:
        return g_requestsPerDay
    requestsPerDay = {}
    for req in getRequestsData():
        userId = req[RL_USER_ID]
        reqDate = req[RL_LOG_DATE]
        reqError = req[RL_ERROR]
        fFailed = False
        if None != reqError:
            fFailed = True
        reqDateTxt = "%04d-%02d-%02d" % (reqDate.year, reqDate.month, reqDate.day)
        if requestsPerDay.has_key(reqDateTxt):
            stats = requestsPerDay[reqDateTxt]
        else:
            stats = ReqDailyStats()
            requestsPerDay[reqDateTxt] = stats
        stats.total = stats.total + 1
        if fFailed:
            stats.failed += 1
        if not userId in stats.uniqueUsers:
            stats.uniqueUsers.append(userId)
    g_requestsPerDay = requestsPerDay
    return requestsPerDay

def dailyStatsHtml():
    requestsPerDay = getDailyStats()
    dailyStats = requestsPerDay.items()
    dailyStats.sort(sortDailyStatsPred)
    res = []
    res.append("<table>")
    res.append(htmlRow(("<b>date</b>", "<b>total</b>", "<b>failed</b>", "<b>users</b>", "<b>new users</b>")))
    for stat in dailyStats:
        dateTxt = stat[0]
        dateLinkTxt = link("day/%s" % dateTxt, dateTxt)
        totalTxt = str(stat[1].total)
        failedTxt = str(stat[1].failed)
        uniqueUsersCount = len(stat[1].uniqueUsers)
        newUsers = getNewUsersForDay(dateTxt)
        res.append(htmlRow((dateLinkTxt, totalTxt, failedTxt, str(uniqueUsersCount), str(newUsers))))
    res.append("</table>")
    return string.join(res, "\n")

def dayStatsHtml(day):
    return genEmpty()

# those must be in sync with \server\ServerErrors.py
g_errorCodeToName = ["errorUnknown", 
    "serverFailure",
    "unsupportedDevice",
    "invalidRegCode",
    "malformedRequest",
    "lookupLimitReached",
    "invalidRequest",
    "unexpectedRequestArgument",
    "requestArgumentMissing",
    "invalidProtocolVersion",
    "invalidCookie",
    "userDisabled",
    "forceUpgrade",
    "langNotAvailable"
   ]

def getErrorCodeName(errorCode):
    global g_errorCodeToName
    return g_errorCodeToName[errorCode]

# creates stats about all failed requests. Returns a tuple:
# creates stats about all failed requests. Returns a list of failed requests
# - a list of failed requests
# - number of requests failed because of lookupLimitReachedError 
def getFailedRequestsStats(filterLookupLimitErrors):
    global g_failedReqs, g_lookupLimitErrors
    if None != g_failedReqs:
        return (g_failedReqs, g_lookupLimitErrors)
    totalErrors = 0 # not including lookupLimitReached
    failedReqs = []
    for req in getRequestsData():
        errorCode = req[RL_ERROR]
        if None == errorCode:
            continue
        if ServerErrors.lookupLimitReached == int(errorCode):
            g_lookupLimitErrors += 1
            continue
        failedReqs.append(req)
    # since requests are already sorted by id/date, the reverse order
    # makes the most recent ones at the top
    failedReqs.reverse()
    g_failedReqs = failedReqs
    return (g_failedReqs, g_lookupLimitErrors)

    for req in failedReqs:
        reqDate = req[RL_LOG_DATE]
        reqDateTxt = "%04d-%02d-%02d" % (reqDate.year, reqDate.month, reqDate.day)
        errorCode = req[RL_ERROR]
        errorCode = int(str(errorCode))
        reqTxt = req[RL_SEARCH_DATA]
        res.append( "%s %2d %s " % (reqDateTxt, errorCode, reqTxt))
    return string.join(res, "<br>\n")

def failedStatsHtml():
    global g_filterLookupLimitErrors
    (failedReqs, lookupLimitErrors) = getFailedRequestsStats(g_filterLookupLimitErrors)
    totalErrors = len(failedReqs)

    res = ["Total errors: %d, Lookup limit errors: %d" % (totalErrors, lookupLimitErrors)]
    res.append("<table>")
    res.append(htmlRow(("<b>date</b>", "<b>error</b>", "<b>query<b>")))
    for req in failedReqs:
        reqDate = req[RL_LOG_DATE]
        reqDateTxt = "%04d-%02d-%02d" % (reqDate.year, reqDate.month, reqDate.day)
        errorCode = int(str(req[RL_ERROR]))
        errorCodeTxt = getErrorCodeName(errorCode)
        reqTxt = req[RL_SEARCH_DATA]
        res.append(htmlRow((reqDateTxt, "%d (%s)" % (errorCode, errorCodeTxt), (reqTxt, "left"))))
    res.append("</table>")
    return string.join(res, "\n")

HOME_LINK    = "home"
USERS_LINK   = "users"
FAILED_LINK  = "failed"
DEVICES_LINK = "devices"

TOP_LINKS = [HOME_LINK, USERS_LINK, FAILED_LINK, DEVICES_LINK]

def link(linkUrl, linkName, fJustName=False):
    if fJustName: return linkName
    return "<a href=\"/%s\">%s</a>" % (linkUrl, linkName)

def pageStart(): return """
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <title>Statsw</title>
    <link rel="stylesheet" href="main.css" type="text/css"/>
</head>
<body>"""

def pageEnd():
    return """
</body>
</html>"""

def topLinksHtml(disabledLinks=[]):
    ret = [link(l,l, l in disabledLinks) for l in TOP_LINKS]
    return string.join(ret, "&nbsp;&nbsp;") + "</p>"

def topLinksHtml2(disabledLinks=[]):
    ret = []
    for l in TOP_LINKS:
        if l in disabledLinks:
            ret.append(l)
        else:
            ret.append(link(l,l))
    return string.join(ret, "&nbsp;&nbsp;") + "</p>"

def genInsideBody(disabledLink, htmlInside):
    res = [pageStart(), topLinksHtml([disabledLink]), htmlInside, pageEnd()]
    return string.join(res)

def genEmpty(): return "This is an empty page, not yet implemented"

def homeHtml():
    return genInsideBody(HOME_LINK, dailyStatsHtml())

def failedHtml():
    return genInsideBody(FAILED_LINK, failedStatsHtml())

def devicesHtml():
    return genInsideBody(DEVICES_LINK, deviceStatsHtml())

def dayHtml(day):
    return genInsideBody(HOME_LINK, dayStatsHtml(day))

def usersHtml():
    return genInsideBody(USERS_LINK, usersStatsHtml())

def mainCssHtml():
    return """
body {
    background: #F5F5F5;
    font: 11px/18px lucida grande, verdana, sans-serif;
}

table {
    font: 11px/18px lucida grande, verdana, sans-serif;
    background: #c5c5c5;
    text-align: right;
}

tr {
    background: #a5a5a5;
}

td.left {
    text-align: left;
}

"""

# REQ_MAP maps a request path to a function that returns HTML for a 
# given request
REQ_NAME = 0
REQ_PROC = 1
REQ_MAP = {
    "" : homeHtml,
    HOME_LINK : homeHtml,
    USERS_LINK : usersHtml,
    FAILED_LINK : failedHtml,
    DEVICES_LINK : devicesHtml,
    "day" : dayHtml,
    "main.css" : mainCssHtml,
}

def htmlFromRequest(req):
    # first look for an exact match
    if REQ_MAP.has_key(req):
        proc = REQ_MAP[req]
        return proc()
    # now look for /foo/bar/goo request, where foo is the dispatch
    # and (bar, goo) are arguments. Could also use /foo?var1=val1 syntax.
    reqList = string.split(req, "/")
    if 1 == len(reqList):
        return None
    req = reqList[0]
    args = reqList[1:]
    # for now only support one argument, because I'm too lazy to figure out
    # the python calling syntax for > 1 arg    
    if 1 != len(args):
        return None
    arg = args[0]
    if REQ_MAP.has_key(req):
        proc = REQ_MAP[req]
        return proc(arg)
    return None

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        # strip "/" from the beginning
        assert '/' == self.path[0]
        req = self.path[1:]
        print "req: '%s'" % req
        html = htmlFromRequest(req)

        if None == html:
            self.send_error(404, "File not found")
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html)

def main():
    loadData()
    httpd = BaseHTTPServer.HTTPServer(("", PORT), Handler)
    print "go to http://localhost:%d/" % PORT
    httpd.serve_forever()

if __name__ == "__main__":
    main()
