
#include "iPediaApplication.hpp"
#include <SysUtils.hpp>
#include <DeviceInfo.hpp>

//#include <StringListForm.hpp>

#include "MainForm.hpp"
#include "RegistrationForm.hpp"
#include "SearchResultsForm.hpp"
#include "LookupManager.hpp"
#include "LookupHistory.hpp"

#include <PrefsStore.hpp>

#define SERVER_DICT_PC       "dict-pc.arslexis.com:9000"
#define SERVER_LOCALHOST_2   "192.168.0.1:9000"

//#define SERVER_TO_USE SERVER_LOCALHOST
#define SERVER_TO_USE SERVER_OFFICIAL

IMPLEMENT_APPLICATION_CREATOR(appFileCreator)

#ifndef NDEBUG
#pragma inline_depth 0
#endif

iPediaApplication::iPediaApplication():
    history_(0),
    lookupManager_(0),
    stressMode_(false),
    fArticleCountChecked(false),
    strList(NULL),
    strListSize(0),
    hyperlinkHandler_(NULL)
{
#ifdef INTERNAL_BUILD
# ifndef NDEBUG    
    //log().addSink(new MemoLogSink(), Logger::logError);
    //log().addSink(new MemoLogSink(), Logger::logDebug);
    //log().addSink(new HostFileLogSink("\\var\\log\\iPedia.log"), Logger::logEverything);
    //log().addSink(new DebuggerLogSink(), Logger::logWarning);
# else
    //log().addSink(new MemoLogSink(), Logger::logError);
# endif
#endif
}

#ifndef NDEBUG
#pragma inline_depth 2
#endif

inline void iPediaApplication::detectViewer()
{
    UInt16  cardNo;
    LocalID dbID;

    if (fDetectViewer(&cardNo,&dbID))
    {
        assert(dbID != 0);
        assert(NULL != hyperlinkHandler_);
        hyperlinkHandler_->setViewerLocation(cardNo, dbID);
    }
}

Err iPediaApplication::initialize()
{
    Err error=RichApplication::initialize();
    return error;
}

//#pragma inline_depth(2)

iPediaApplication::~iPediaApplication()
{
    // Don't remove if or expect crash on non-global launch. I really KNOW that you can delete NULL. But not here.
    if (NULL != lookupManager_)
        delete lookupManager_;
    if (NULL != history_)
        delete history_;
    
    if (NULL != hyperlinkHandler_)
        delete hyperlinkHandler_;
        
    if (NULL != strList)
        FreeStringList(strList, strListSize);
}

Err iPediaApplication::normalLaunch()
{
    serverAddress = SERVER_TO_USE;
    preferences_.currentLang = _T("en");
    hyperlinkHandler_ = new iPediaHyperlinkHandler();
    detectViewer();
    history_ = new LookupHistory();
    loadPreferences();
#ifdef INTERNAL_BUILD
    // make it easier for me to run the app
    // if running on Treo 600 set the default server to my server
    if (runningOnTreo600() && !underSimulator())
    {
        //server_ = SERVER_OFFICIAL;
    }
#endif

    gotoForm(mainForm);
    runEventLoop();
    savePreferences();
    return errNone;
}

bool iPediaApplication::fLookupInProgress() const
{
    if (NULL==lookupManager_)
        return false;
    return lookupManager_->lookupInProgress();
}

LookupManager* iPediaApplication::getLookupManager(bool create)
{
    if (!lookupManager_ && create)
    {
        assert(0!=history_);
        lookupManager_=new LookupManager(*history_);
    }
    return lookupManager_;
}

void iPediaApplication::waitForEvent(EventType& event)
{
    SocketConnectionManager* manager=0;
    if (lookupManager_)
        manager=&lookupManager_->connectionManager();
    if (manager && manager->active())
    {
#ifdef ARSLEXIS_USE_SELECT_EVENTS
        if (!underSimulator())
            manager->waitForEvent(event, evtWaitForever);
        else 
        {
#else
        {
#endif        
        setEventTimeout(0);
        RichApplication::waitForEvent(event);
        if (nilEvent==event.eType)
            manager->manageConnectionEvents(ticksPerSecond()/20);
        }
    }
    else
    {
        setEventTimeout(evtWaitForever);
        RichApplication::waitForEvent(event);
    }        
}

Form* iPediaApplication::createForm(UInt16 formId)
{
    Form* form;
//    StringListForm *strListForm;

    switch (formId)
    {
        case mainForm:
            form = new PediaMainForm(*this);
            break;
            
        case registrationForm:
            form = new RegistrationForm(*this);
            break;

        case searchResultsForm:
            form = new SearchResultsForm(*this);
            break;

/*

        case stringListSelectDbId:
            strListForm = new StringListForm(*this, (uint_t)stringListForm, (uint_t)stringList, (uint_t)selectButton, (uint_t)cancelButton);
            strListForm->SetStringList(strListSize, strList, appDbnameStringSelected);
            form = strListForm;
            break;

        case stringListHistoryId:
            strListForm = new StringListForm(*this, (uint_t)stringListForm, (uint_t)stringList, (uint_t)selectButton, (uint_t)cancelButton);
            strListForm->SetStringList(strListSize, strList, appHistoryStringSelected);
            form = strListForm;
            break;

        case stringListLinkedArticlesId:
            strListForm = new StringListForm(*this, (uint_t)stringListForm, (uint_t)stringList, (uint_t)selectButton, (uint_t)cancelButton);
            strListForm->SetStringList(strListSize, strList, appLinkedArticlesStringSelected);
            form = strListForm;
            break;

        case stringListLinkingArticlesId:
            strListForm = new StringListForm(*this, (uint_t)stringListForm, (uint_t)stringList, (uint_t)selectButton, (uint_t)cancelButton);
            strListForm->SetStringList(strListSize, strList, appLinkingArticlesStringSelected);
            form = strListForm;
            break;

*/

        default:
            assert(false);
    }
    return form;            
}

bool iPediaApplication::handleApplicationEvent(EventType& event)
{
    bool handled=false;
    if (lookupManager_ && appLookupEventFirst<=event.eType && appLookupEventLast>=event.eType)
        lookupManager_->handleLookupEvent(event);
    else
        handled=RichApplication::handleApplicationEvent(event);
    return handled;
}

// backward-compat
#define reservedRenderingPrefIdCount 17
    
enum PreferenceId 
{
    cookiePrefId,
    regCodePrefId,
    serialNumberRegFlagPrefId, // unused
    lastArticleCountPrefId,
    databaseTimePrefId,
    lookupHistoryFirstPrefId,
    renderingPrefsFirstPrefId=lookupHistoryFirstPrefId+LookupHistory::reservedPrefIdCount,
    
    //availableLangsPrefId = renderingPrefsFirstPrefId+RenderingPreferences::reservedPrefIdCount+1,
    availableLangsPrefId = renderingPrefsFirstPrefId+reservedRenderingPrefIdCount+1,
    currentLangPrefId,
    next = currentLangPrefId+1
};

// These globals will be removed by dead code elimination.
StaticAssert<(sizeof(uint_t) == sizeof(UInt16))> uint_t_the_same_size_as_UInt16;
StaticAssert<(sizeof(bool) == sizeof(Boolean))> bool_the_same_size_as_Boolean;

void iPediaApplication::loadPreferences()
{
    Preferences prefs;
    // PrefsStoreXXXX seem to be rather heavyweight objects (writer is >480kB), so it might be a good idea not to allocate them on stack.
    std::auto_ptr<PrefsStoreReader> reader(new PrefsStoreReader(appPrefDatabase, appFileCreator, sysFileTPreferences));

    Err         error;
    const char* text;

    // we siliently ignore all the errors since they might happen during upgrade
    // i.e. if version n+1 reads prefs of version n, in which case some of the
    // prefs might be missing
    if (errNone==(error=reader->ErrGetStr(cookiePrefId, &text)))
    {
        prefs.cookie = text;
    }

    if (errNone==(error=reader->ErrGetStr(regCodePrefId, &text)))
    {
        prefs.regCode = text;
    }

    prefs.articleCount = -1;
    error = reader->ErrGetLong(lastArticleCountPrefId, &prefs.articleCount);

    if (errNone==(error=reader->ErrGetStr(databaseTimePrefId, &text))) 
    {
        prefs.databaseTime = text;
    }

    // error = prefs.renderingPreferences.serializeIn(*reader, renderingPrefsFirstPrefId);

    if (errNone==(error=reader->ErrGetStr(availableLangsPrefId, &text)))
    {
        prefs.availableLangs = text;
    }

    if (errNone==(error=reader->ErrGetStr(currentLangPrefId, &text)))
    {
        prefs.currentLang = text;
    }

    preferences_ = prefs;

    assert(0!=history_);
    error = history_->serializeIn(*reader, lookupHistoryFirstPrefId);

    return;        
}

void iPediaApplication::savePreferences()
{
    Err   error;
    std::auto_ptr<PrefsStoreWriter> writer(new PrefsStoreWriter(appPrefDatabase, appFileCreator, sysFileTPreferences));

    if (errNone!=(error=writer->ErrSetStr(cookiePrefId, preferences_.cookie.c_str())))
        goto OnError;
    if (errNone!=(error=writer->ErrSetStr(regCodePrefId, preferences_.regCode.c_str())))
        goto OnError;
    if (errNone!=(error=writer->ErrSetLong(lastArticleCountPrefId, preferences_.articleCount))) 
        goto OnError;
    if (errNone!=(error=writer->ErrSetStr(databaseTimePrefId, preferences_.databaseTime.c_str())))
        goto OnError;
    //if (errNone!=(error=preferences_.renderingPreferences.serializeOut(*writer, renderingPrefsFirstPrefId)))
    //    goto OnError;
    assert(0!=history_);
    if (errNone!=(error=history_->serializeOut(*writer, lookupHistoryFirstPrefId)))
        goto OnError;

    if (errNone!=(error=writer->ErrSetStr(availableLangsPrefId, preferences_.availableLangs.c_str())))
        goto OnError;
    if (errNone!=(error=writer->ErrSetStr(currentLangPrefId, preferences_.currentLang.c_str())))
        goto OnError;

    if (errNone!=(error=writer->ErrSavePreferences()))
        goto OnError;
    return;        
OnError:
    //! @todo Diplay alert that saving failed?
    return;
}
