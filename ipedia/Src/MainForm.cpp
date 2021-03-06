#include "MainForm.hpp"
#include <FormObject.hpp>
#include "iPediaApplication.hpp"
#include "LookupManager.hpp"
#include "LookupHistory.hpp"
#include <SysUtils.hpp>
#include <Text.hpp>
#include <StringListForm.hpp>

#include <TextElement.hpp>
#include <LineBreakElement.hpp>
#include <ParagraphElement.hpp>

#include <LangNames.hpp>

static char_t** ExtractLinksFromDefinition(const TextRenderer& renderer, int& strListSize)
{
    int       strCount;
    char_t ** strList;
    for (int phase=0; phase<=1; phase++)
    {
        if (1 == phase)
        {
            strListSize = strCount;
            strList = new char_t *[strCount];
        }
        strCount = 0;

        TextRenderer::const_iterator end = renderer.end();
        for (TextRenderer::const_iterator it = renderer.begin(); it != end; ++it)
        {
            if ((*it)->isTextElement())
            {
                TextElement* txtEl = static_cast<TextElement*>(*it);
                if ((txtEl->isHyperlink()) &&
                    ((txtEl->hyperlinkProperties()->type==hyperlinkTerm) ||
                     (txtEl->hyperlinkProperties()->type==hyperlinkExternal)))
                {
                    if (1==phase)
                    {
                        strList[strCount] = StringCopy(txtEl->hyperlinkProperties()->resource);
                        replaceCharInString(strList[strCount], _T('_'), _T(' '));
                    }
                    strCount += 1;
                }
            }
        }
    }
    return strList;
}

PediaMainForm::PediaMainForm(iPediaApplication& app):
    iPediaForm(app, mainForm),
    renderingProgressReporter_(*this),
    displayMode_(showAbout),
    lastPenDownTimestamp_(0),
    updateDefinitionOnEntry_(false),
    enableInputFieldAfterUpdate_(false),
    penUpsToEat_(0),
    ignoreEvents_(false),
    graffiti_(*this),
    termInputField_(*this),
    scrollBar_(*this),
    backButton_(*this),
    forwardButton_(*this),
    searchButton_(*this),
    articleRenderer_(*this, &scrollBar_),
    infoRenderer_(*this, &scrollBar_)
    //articleRenderer_(*this, app.preferences().renderingPreferences, &scrollBar_),
    //infoRenderer_(*this, app.preferences().renderingPreferences, &scrollBar_)
{
    articleRenderer_.setRenderingProgressReporter(&renderingProgressReporter_);
    articleRenderer_.setHyperlinkHandler(&app.hyperlinkHandler());

    articleRenderer_.setInteractionBehavior(  
        TextRenderer::behavMouseSelection 
      | TextRenderer::behavDoubleClickSelection
      | TextRenderer::behavUpDownScroll 
      | TextRenderer::behavHyperlinkNavigation  
    );

    infoRenderer_.setHyperlinkHandler(&app.hyperlinkHandler());
    setFocusControlId(termInputField);
}

void PediaMainForm::attachControls() 
{
    iPediaForm::attachControls();
    
    graffiti_.attachByIndex(getGraffitiStateIndex());
    termInputField_.attach(termInputField);
    scrollBar_.attach(definitionScrollBar);
    backButton_.attach(backButton);
    forwardButton_.attach(forwardButton);
    searchButton_.attach(searchButton);
    articleRenderer_.attach(articleRenderer);
    infoRenderer_.attach(infoRenderer);
    infoRenderer_.setNavOrderOptions(TextRenderer::navOrderFirst);
}

bool PediaMainForm::handleOpen()
{
    bool fOk=iPediaForm::handleOpen();
    updateNavigationButtons();
    // to prevent accidental selection of links in main About page
    penUpsToEat_ = 1;
    setDisplayMode(displayMode_);
    return fOk;
}

inline const LookupHistory& PediaMainForm::getHistory() const
{
    return static_cast<const iPediaApplication&>(application()).history();
}

void PediaMainForm::resize(const ArsRectangle& screenBounds)
{
    ArsRectangle bounds(this->bounds());
    if (screenBounds==bounds)
        return;

    setBounds(screenBounds);

    infoRenderer_.anchor(screenBounds, anchorRightEdge, 8, anchorBottomEdge, 36);
    articleRenderer_.anchor(screenBounds, anchorRightEdge, 8, anchorBottomEdge, 36);
    scrollBar_.anchor(screenBounds, anchorLeftEdge, 7, anchorBottomEdge, 36);
    termInputField_.anchor(screenBounds, anchorRightEdge, 72, anchorTopEdge, 14);

    searchButton_.anchor(screenBounds, anchorLeftEdge, 34, anchorTopEdge, 14);
    backButton_.anchor(screenBounds, anchorNot, 0, anchorTopEdge, 14);
    forwardButton_.anchor(screenBounds, anchorNot, 0, anchorTopEdge, 14);
    graffiti_.anchor(screenBounds, anchorLeftEdge, 46, anchorTopEdge, 16);
            
    update();    
}

void PediaMainForm::draw(UInt16 updateCode)
{
    Graphics graphics(windowHandle());
    ArsRectangle rect(bounds());
    ArsRectangle progressArea(rect.x(), rect.height()-17, rect.width(), 17);
    if (redrawAll == updateCode)
    {
        if (visible())
            graphics.erase(progressArea);
        iPediaForm::draw(updateCode);
        graphics.drawLine(rect.x(), rect.height()-18, rect.width(), rect.height()-18);
    }

    if (app().fLookupInProgress())
        app().getLookupManager()->showProgress(graphics, progressArea);

    if (enableInputFieldAfterUpdate_)
    {
        enableInputFieldAfterUpdate_ = false;
        termInputField_.show();
        //termInputField_.focus();
    }
}


void PediaMainForm::moveHistory(bool forward)
{
    LookupManager* lookupManager=app().getLookupManager(true);
    if (NULL != lookupManager && !lookupManager->lookupInProgress())
        lookupManager->moveHistory(forward);
}

void PediaMainForm::handleControlSelect(const EventType& event)
{
    LookupManager* lookupManager = app().getLookupManager();
    if (NULL != lookupManager && lookupManager->lookupInProgress())
        return;
        
    bool fFullText = false;
    switch (event.data.ctlSelect.controlID)
    {
        case searchButton:
            // If button held for more than ~300msec, perform full text search.
            if (TimGetTicks() - lastPenDownTimestamp_ > app().ticksPerSecond()/3)
                fFullText = true;
            search(fFullText);
            break;
            
        case backButton:
            moveHistory(false);
            break;
        
        case forwardButton:
            moveHistory(true);
            break;
        
        default:
            assert(false);
    }
}

void PediaMainForm::setControlsState(bool enabled)
{
//    backButton_.setEnabled(enabled);
//    forwardButton_.setEnabled(enabled);
    searchButton_.setEnabled(enabled);
    if (enabled)
        enableInputFieldAfterUpdate_  = true;
    else
    {
        releaseFocus();
        termInputField_.hide();
    }
}

void PediaMainForm::handleLookupFinished(const EventType& event)
{
    setControlsState(true);
    const LookupFinishedEventData& data=reinterpret_cast<const LookupFinishedEventData&>(event.data);
    switch (data.outcome)
    {
        case data.outcomeArticleBody:
            updateAfterLookup();
            break;

        case data.outcomeList:
            Application::popupForm(searchResultsForm);
            break;

        case data.outcomeDatabaseSwitched:
            // recalc about info and show about screen
            setDisplayMode(showAbout);            
            termInputField_.replace("");
            update();
            break;

        case data.outcomeAvailableLangs:
            assert(!app().preferences().availableLangs.empty());
            if (app().preferences().availableLangs.empty())
            {
                // this shouldn't happen but if it does, we want to break
                // to avoid infinite loop (changeDatabase() will issue request
                // to get available langs whose result we handle here
                break;
            }
            changeDatabase();
            break;

        case data.outcomeNotFound:
            termInputField_.select();
            // No break is intentional.

        default:
            update();
    }

    LookupManager* lookupManager=app().getLookupManager();
    assert(lookupManager);
    lookupManager->handleLookupFinishedInForm(data);

    if (app().inStressMode())
    {
        EvtResetAutoOffTimer();
        randomArticle();
    }        
}

bool PediaMainForm::handleEvent(EventType& event)
{
    if (showArticle == displayMode_ && articleRenderer_.handleEventInForm(event))
        return true;
    if (showArticle != displayMode_ && infoRenderer_.visible() && infoRenderer_.handleEventInForm(event))
        return true;
        
    bool handled=false;
    if (ignoreEvents_)
        return false;
    switch (event.eType)
    {
        case keyDownEvent:
            handled=handleKeyPress(event);
            break;
            
        case ctlSelectEvent:
            handleControlSelect(event);
            break;
        
        case penUpEvent:
            if (penUpsToEat_ > 0)
            {
                --penUpsToEat_;
                handled = true;
            }
            break;
    
        case LookupManager::lookupFinishedEvent:
            handleLookupFinished(event);
            handled = true;
            break;     
            
        case LookupManager::lookupStartedEvent:
            setControlsState(false);            // No break is intentional.
            
        case LookupManager::lookupProgressEvent:
            update(redrawProgressIndicator);
            handled = true;
            break;

        case iPediaApplication::appRegisterEvent:
            Application::popupForm(registrationForm);
            handled = true;
            break;

        case iPediaApplication::appRegistrationFinished:
            if (showAbout == displayMode_)
                prepareAbout();
            update();
            handled = true;
            break;

        case iPediaApplication::appLangNotAvailable:
            // for whatever reason server told us that the language
            // we were using is not available. That shouldn't happen
            // because we only use langauges that server gives us, but
            // it might becaues e.g. we might disable a given language on the
            // server and the client might have outdated list of available
            // languages. In this case we switch to "en" (English) which
            // should always be available
            FrmAlert(langNotAvailableAlert);
            LookupManager* lookupManager = app().getLookupManager(true);
            if (lookupManager && !lookupManager->lookupInProgress())
                lookupManager->switchDatabase("en");
            handled = true;
            break;

        case iPediaApplication::appForceUpgrade:
            {
                UInt16 buttonId = FrmAlert(forceUpgradeAlert);
                if (0==buttonId)
                {
                    // this is "Update" button so take them to a web page
                    if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, updateCheckURL ,NULL) )
                        FrmAlert(noWebBrowserAlert);
                }
                handled = true;
            }
            break;

        case iPediaApplication::appRandomWord:
            randomArticle();
            handled = true;
            break;

        case penDownEvent:
            lastPenDownTimestamp_=TimGetTicks();
            break;
    
        default:
            handled = iPediaForm::handleEvent(event);
    }
    return handled;
}

void PediaMainForm::updateNavigationButtons()
{
    const LookupHistory& history=getHistory();

    bool enabled = history.hasPrevious();
    if (enabled)
        backButton_.setGraphics(backBitmap);
    else
        backButton_.setGraphics(backDisabledBitmap);
        
    enabled = history.hasNext();
    if (enabled)
        forwardButton_.setGraphics(forwardBitmap);
    else
        forwardButton_.setGraphics(forwardDisabledBitmap);
}

void PediaMainForm::updateAfterLookup()
{
    LookupManager* lookupManager = app().getLookupManager();
    assert(lookupManager!=0);
    if (lookupManager)
    {
        articleRenderer_.setModel(lookupManager->lastDefinitionModel, Definition::ownModelNot);
        setDisplayMode(showArticle);
        
        termInputField_.replace(lookupManager->lastSearchTerm());
        termInputField_.select();                    
        articleRenderer_.focus();
        update();
    }
    updateNavigationButtons();
}

bool PediaMainForm::handleKeyPress(const EventType& event)
{
    bool handled = false;
    if (fiveWayCenterPressed(&event))
        lastPenDownTimestamp_ = TimGetTicks();

    switch (event.data.keyDown.chr)
    {
        case chrLineFeed:
        case chrCarriageReturn:
            lastPenDownTimestamp_ = TimGetTicks();
            searchButton_.hit();
            handled = true;
            break;
            
    }
    return handled;
}

void PediaMainForm::switchServer(char_t * server)
{
    app().serverAddress = server;    
}

bool PediaMainForm::handleMenuCommand(UInt16 itemId)
{
    bool handled = false;

    switch (itemId)
    {
#ifdef  INTERNAL_BUILD    
        case useDictPcMenuItem:
            switchServer(SERVER_OFFICIAL);
            handled = true;
            break;
            
        case useLocalhostMenuItem:
            switchServer(SERVER_LOCALHOST);
            handled = true;
            break;

        case toggleStressModeMenuItem:
            handleToggleStressMode();
            handled = true;
            break;
#endif
            
        case registerMenuItem:
#ifdef UNLOCKED
            FrmAlert(alreadyRegisteredAlert);
#else
            Application::popupForm(registrationForm);
#endif
            handled = true;
            break;
            
        case copyMenuItem:
            copySelectionOrAllToClipboard();
            handled = true;
            break;
            
        case searchResultsMenuItem:
            Application::popupForm(searchResultsForm);
            handled = true;
            break;

        case randomMenuItem:
            randomArticle();
            handled = true;
            break;

        case changeDatabaseMenuItem:
            changeDatabase();
            handled = true;
            break;

        case arslexisWebsiteMenuItem:
            if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, "http://www.arslexis.com/pda/palm.html",NULL) )
                FrmAlert(noWebBrowserAlert);
            handled = true;
            break;

        case checkUpdatesMenuItem:
            if ( errNone != WebBrowserCommand(false, 0, sysAppLaunchCmdGoToURL, updateCheckURL ,NULL) )
                FrmAlert(noWebBrowserAlert);
            handled = true;
            break;

        case aboutMenuItem:
            if (showAbout != displayMode_)
            {
                setDisplayMode(showAbout);
                update();
            }
            handled = true;
            break;

        case tutorialMenuItem:
            if (showTutorial != displayMode_)
            {
                setDisplayMode(showTutorial);
                update();
            }
            handled = true;
            break;

        case searchMenuItem:
            search();
            handled = true;
            break;

        case extendedSearchMenuItem:
            search(true);
            handled = true;
            break;
            
        case forwardMenuItem:
            if (forwardButton_.enabled())
                forwardButton_.hit();
            break;
            
        case backMenuItem:
            if (backButton_.enabled())
                backButton_.hit();
            break;

        case historyMenuItem:
            doHistory();
            handled = true;
            break;

        case linkedArticlesMenuItem:
            doLinkedArticles();
            handled = true;
            break;

        case linkingArticlesMenuItem:
            doLinkingArticles();
            handled = true;
            break;

        default:
            handled = iPediaForm::handleMenuCommand(itemId);
    }
    // to prevent accidental selection of links in main About page
    penUpsToEat_ = 1;
    return handled;
}

void PediaMainForm::doHistory()
{
    LookupManager* lookupManager=app().getLookupManager(true);
    if (NULL==lookupManager)
        return;
    LookupHistory& lookupHistory = lookupManager->getHistory();
    if (lookupHistory.empty())
        return;
    const StringList_t& history = lookupHistory.getHistory();
    app().strList = StringListFromStringList(history, app().strListSize);
    ReverseStringList(app().strList, app().strListSize);
    int sel = showStringListForm(app().strList, app().strListSize);
    doLookupSelectedTerm(sel);    
}

void PediaMainForm::doLookupSelectedTerm(int selectedStr)
{
    if (NOT_SELECTED==selectedStr)
        goto Exit;

    const char_t* term = app().strList[selectedStr];

    LookupManager* lookupManager=app().getLookupManager(true);
    if (lookupManager && !lookupManager->lookupInProgress())
        lookupManager->lookupIfDifferent(term, app().preferences().currentLang);

Exit:

    FreeStringList(app().strList, app().strListSize);
    app().strList = NULL;
}

void PediaMainForm::doLinkedArticles()
{
    // this only applies to articles, not about etc.
    if (showArticle != displayMode_)
        return;

    TextRenderer* renderer = &articleRenderer_;
    
    app().strList = ExtractLinksFromDefinition(*renderer, app().strListSize);
    int sel = showStringListForm(app().strList, app().strListSize);
    doLookupSelectedTerm(sel);    
}

void PediaMainForm::doLinkingArticles()
{
    // this only applies to articles, not about etc.
    if (showArticle != displayMode_)
        return;

    LookupManager* lookupManager = app().getLookupManager(true);
    if (NULL==lookupManager)
        return;

    const String& reverseLinks = lookupManager->lastReverseLinks();
    app().strList = StringListFromString(reverseLinks, "\n", app().strListSize);
    for (int i=0; i<app().strListSize; i++)
    {
        replaceCharInString(app().strList[i], _T('_'), _T(' '));
    }
    int sel = showStringListForm(app().strList, app().strListSize);
    doLookupSelectedTerm(sel);    
}

// this will be called either as a result of invoking menu item
// or getAvailableLangs() query to the server (which we issue ourselves,
// so it's kind of a recursion)
void PediaMainForm::changeDatabase()
{
    String availableLangs = app().preferences().availableLangs;
    if (availableLangs.empty())
    {
        // if we don't have available langs, issue a request asking for it
        LookupManager* lookupManager=app().getLookupManager(true);
        if (lookupManager && !lookupManager->lookupInProgress())
            lookupManager->getAvailableLangs();
        return;
    }

    char_t **strList = StringListFromString(availableLangs, " ", app().strListSize);
    const char_t* fullName;
    String nameToDisplay;

    for (int i=0; i<app().strListSize; i++)
    {
        fullName = GetLangNameByLangCode(strList[i], tstrlen(strList[i]));
        if (NULL != fullName)
            nameToDisplay.assign(fullName);
        else
            nameToDisplay.assign(_T("Unknown"));

        nameToDisplay.append(_T(" ("));
        nameToDisplay.append(strList[i]);
        nameToDisplay.append(_T(")"));

        delete [] strList[i];
        strList[i] = StringCopy(nameToDisplay);
    }

    app().strList = strList;
    int sel = showStringListForm(app().strList, app().strListSize);
    doDbSelected(sel);
}

int PediaMainForm::showStringListForm(char_t* strList[], int strListSize)
{
    StringListForm* form = new StringListForm(app(), stringListForm, stringList, selectButton, cancelButton);
    form->initialize();
    form->SetStringList(app().strListSize, app().strList);
    ignoreEvents_ = true; // Strange things happen here and if we don't prevent MainForm from processing events we'll overflow the stack :-(
    int sel = form->showModalAndGetSelection();
    ignoreEvents_ = false;
    update();
    delete form;
    return sel;    
}

void PediaMainForm::doDbSelected(int selectedStr)
{
    if (NOT_SELECTED == selectedStr)
        goto Exit;

    char_t *fullName = app().strList[selectedStr];
    // a hack: lang is what is inside "(" and ")"
    while (*fullName && (*fullName!='('))
        ++fullName;
    assert(*fullName);
    char_t *langName = fullName+1;
    langName[2] = '\0';

    LookupManager* lookupManager=app().getLookupManager(true);
    assert(NULL != lookupManager);

    if (lookupManager && !lookupManager->lookupInProgress())
    {
        lookupManager->switchDatabase(langName);
    }

Exit:
    FreeStringList(app().strList, app().strListSize);
    app().strList = NULL;
}

void PediaMainForm::randomArticle()
{
    LookupManager* lookupManager=app().getLookupManager(true);
    if (lookupManager && !lookupManager->lookupInProgress())
        lookupManager->lookupRandomTerm();
}

void PediaMainForm::copySelectionOrAllToClipboard()
{
    TextRenderer* renderer = &infoRenderer_;
    if (showArticle == displayMode_)
        renderer = &articleRenderer_;
     
    if (renderer->empty())
        return;
    String text;
    renderer->copySelectionOrAll();
}

bool PediaMainForm::handleWindowEnter(const struct _WinEnterEventType& data)
{
    const FormType* form = *this;
    if (data.enterWindow==static_cast<const void*>(form))
    {
        LookupManager* lookupManager = app().getLookupManager();
        if (lookupManager)
        {
            if (updateDefinitionOnEntry_)
            {
                updateDefinitionOnEntry_ = false;
                updateAfterLookup();
            }
            setControlsState(!lookupManager->lookupInProgress());
        }
    }
    return iPediaForm::handleWindowEnter(data);
}

void PediaMainForm::handleToggleStressMode()
{
    if (app().inStressMode())
        app().toggleStressMode(false);
    else
    {
        app().toggleStressMode(true);
        randomArticle();
    }        
}

void PediaMainForm::search(bool fullText)
{
    const char* text = termInputField_.text();
    uint_t textLen;
    if (0==text || 0==(textLen=StrLen(text)))
        return;
        
    LookupManager* lookupManager=app().getLookupManager(true);
    if (!lookupManager || lookupManager->lookupInProgress())
        return;

    String term(text, textLen);
    if (!fullText)
    {
        if (!lookupManager->lookupIfDifferent(term, app().preferences().currentLang) && showArticle!=displayMode())
            updateAfterLookup();
    }
    else
        lookupManager->search(term);
}

static void wikipediaActionCallback(void *data)
{
    assert(NULL!=data);
    PediaMainForm * mf = static_cast<PediaMainForm*>(data);
    assert(PediaMainForm::showWikipedia != mf->displayMode());
    mf->setDisplayMode(PediaMainForm::showWikipedia);
    mf->update();
}

static void tutorialActionCallback(void *data)
{
    assert(NULL!=data);
    PediaMainForm * mf = static_cast<PediaMainForm*>(data);
    assert(PediaMainForm::showTutorial != mf->displayMode());
    mf->setDisplayMode(PediaMainForm::showTutorial);
    mf->update();
}

static void unregisteredActionCallback(void *data)
{
    assert(NULL!=data);
    PediaMainForm * mf = static_cast<PediaMainForm*>(data);
    assert(PediaMainForm::showRegister!=mf->displayMode());
    mf->setDisplayMode(PediaMainForm::showRegister);
    mf->update();
}

static void aboutActionCallback(void *data)
{
    assert(NULL!=data);
    PediaMainForm * mf = static_cast<PediaMainForm*>(data);
    assert(PediaMainForm::showAbout != mf->displayMode());
    mf->setDisplayMode(PediaMainForm::showAbout);
    mf->update();
}

static void randomArticleActionCallback(void *data)
{
    assert(NULL!=data);
    PediaMainForm * mf = static_cast<PediaMainForm*>(data);
    assert(PediaMainForm::showTutorial == mf->displayMode());
    sendEvent(iPediaApplication::appRandomWord);
}

static void prepareArticleCountEl(TextElement *articleCountElement, long articleCount, const String& dbTime)
{
    assert(NULL!=articleCountElement);

    assert(-1 != articleCount);
    assert(8 == dbTime.length());
    char buffer[32];
    int len = formatNumber(articleCount, buffer, sizeof(buffer));
    assert(len != -1 );
    String articleCountText;
    articleCountText.append(buffer, len);
    articleCountText.append(" articles. ");

    iPediaApplication& app = iPediaApplication::instance();
    const String& langCode = app.preferences().currentLang;
    const char_t* langName = GetLangNameByLangCode(langCode.c_str(), langCode.length());
    if (NULL == langName)
        langName = _T("Unknown");
        
    articleCountText.append(langName);

    articleCountText.append(" encyclopedia last updated on ");
    articleCountText.append(dbTime, 0, 4);
    articleCountText.append(1, '-');
    articleCountText.append(dbTime, 4, 2);
    articleCountText.append(1, '-');
    articleCountText.append(dbTime, 6, 2);
    articleCountElement->setText(articleCountText);

}


TextElement *    articleCountElement;

void PediaMainForm::prepareAbout()
{
    DefinitionModel* model = new_nt DefinitionModel();   
    if (NULL == model)   
    {   
       //application().alert(notEnoughMemoryAlert);   
       return;   
    }   
     
    Definition::Elements_t& elems = model->elements; 

    TextElement *  text;
    TextElement *  articleCountElement;
    setTitle("iPedia");

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(new LineBreakElement(1,10));

    elems.push_back(text=new TextElement("ArsLexis iPedia"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setStyle(StyleGetStaticStyle(styleNameHeader));

    elems.push_back(new LineBreakElement(1,3));

    const char* version="Ver " appVersion
#ifdef INTERNAL_BUILD
    " (internal)"
#endif
/*
#ifdef DEBUG
        " (debug)"
#endif*/
    ;
    elems.push_back(text=new TextElement(version));
    text->setJustification(DefinitionElement::justifyCenter);
    elems.push_back(new LineBreakElement(1,4));

#ifdef UNLOCKED
    elems.push_back(text=new TextElement("Registered PalmSource version"));
    text->setJustification(DefinitionElement::justifyCenter);
    elems.push_back(new LineBreakElement(1,2));
#else
    if (app().preferences().regCode.empty())
    {
        elems.push_back(text=new TextElement("Unregistered ("));
        text->setJustification(DefinitionElement::justifyCenter);
        elems.push_back(text=new TextElement("how to register"));
        text->setJustification(DefinitionElement::justifyCenter);
        // url doesn't really matter, it's only to establish a hotspot
        text->setHyperlink("", hyperlinkTerm);
        text->setActionCallback( unregisteredActionCallback, static_cast<void*>(this) );
        elems.push_back(text=new TextElement(")"));
        text->setJustification(DefinitionElement::justifyCenter);
        elems.push_back(new LineBreakElement(1,2));
    }
    else
    {
        elems.push_back(text=new TextElement("Registered"));
        text->setJustification(DefinitionElement::justifyCenter);
        elems.push_back(new LineBreakElement(1,2));
    }
#endif

    elems.push_back(text=new TextElement("Software \251 "));
    text->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(text=new TextElement("ArsLexis"));
    text->setJustification(DefinitionElement::justifyCenter);
    text->setHyperlink("http://www.arslexis.com/pda/palm.html", hyperlinkExternal);

    elems.push_back(new LineBreakElement(1,4));
    elems.push_back(text=new TextElement("Data \251 "));
    text->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(text=new TextElement("WikiPedia"));
    text->setJustification(DefinitionElement::justifyCenter);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback(wikipediaActionCallback, static_cast<void*>(this) );

    elems.push_back(new LineBreakElement(1,2));

    articleCountElement = new TextElement(" ");

    if (-1 != app().preferences().articleCount)    
    {
        prepareArticleCountEl(articleCountElement, app().preferences().articleCount, app().preferences().databaseTime);
    }

    elems.push_back(articleCountElement);
    articleCountElement->setJustification(DefinitionElement::justifyCenter);

    elems.push_back(new LineBreakElement(1, 2));
    elems.push_back(text=new TextElement("Using iPedia: "));
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new TextElement("tutorial"));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback(tutorialActionCallback, this);

    //infoRenderer_.replaceElements(elems);
    infoRenderer_.setModel(model, Definition::ownModel);
}

// TODO: make those on-demand only to save memory
void PediaMainForm::prepareTutorial()
{
    DefinitionModel* model = new_nt DefinitionModel();   
    if (NULL == model)   
    {   
       //application().alert(notEnoughMemoryAlert);   
       return;   
    }
    Definition::Elements_t& elems = model->elements; 
    setTitle("iPedia - Tutorial");
    TextElement* text;

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(text=new TextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( aboutActionCallback, static_cast<void*>(this) );
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("iPedia is a wireless encyclopedia. Use it to get information and facts on just about anything."));
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("Finding an encyclopedia article."));
//    text->setEffects(fxBold);
    elems.push_back(text=new TextElement(" Let's assume you want to read an encyclopedia article on Seattle. Enter 'Seattle' in the text field at the bottom of the screen and press 'Search' (or center button on Treo's 5-way navigator)."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("Finding all articles with a given word."));
//    text->setEffects(fxBold);
    elems.push_back(text=new TextElement(" Let's assume you want to find all articles that mention Seattle. Enter 'Seattle' in the text field and use 'Main/Extended search' menu item. In response you'll receive a list of articles that contain word 'Seattle'."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("Refining the search."));
//    text->setEffects(fxBold);
    elems.push_back(text=new TextElement(" If there are too many results, you can refine (narrow) the search results by adding additional terms e.g. type 'museum' and press 'Refine' button. You'll get a smaller list of articles that contain both 'Seattle' and 'museum'."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("Results of last extended search."));
//    text->setEffects(fxBold);
    elems.push_back(text=new TextElement(" At any time you can get a list of results from last extended search by using menu item 'Main/Extended search results'."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("Random article."));
//    text->setEffects(fxBold);
    elems.push_back(text=new TextElement(" You can use menu 'Main/Random article' (or "));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(text=new TextElement("click here"));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( randomArticleActionCallback, static_cast<void*>(this) );
    elems.push_back(text=new TextElement(") to get a random article."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("More information."));
//    text->setEffects(fxBold);
    elems.push_back(text=new TextElement(" Please visit our website "));
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new TextElement("arslexis.com"));
    text->setHyperlink("http://www.arslexis.com/pda/palm.html", hyperlinkExternal);
    text->setJustification(DefinitionElement::justifyLeft);

    elems.push_back(text=new TextElement(" for more information about iPedia."));
    text->setJustification(DefinitionElement::justifyLeft);
    elems.push_back(new LineBreakElement(4,3));

    elems.push_back(text=new TextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback(aboutActionCallback, this);

    //infoRenderer_.replaceElements(elems);
    infoRenderer_.setModel(model, Definition::ownModel);
}

static void registerActionCallback(void *data)
{
    assert(NULL!=data);
    PediaMainForm * mf = static_cast<PediaMainForm*>(data);   
    sendEvent(iPediaApplication::appRegisterEvent);
}

// TODO: make those on-demand only to save memory
void PediaMainForm::prepareHowToRegister()
{
    DefinitionModel* model = new_nt DefinitionModel();   
    if (NULL == model)   
    {   
       //application().alert(notEnoughMemoryAlert);   
       return;   
    }
    Definition::Elements_t& elems = model->elements; 
    setTitle("iPedia - How to register");
    TextElement* text;

    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(text=new TextElement("Unregistered version of iPedia limits how many articles can be viewed in one day (there are no limits on random articles.)"));
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new TextElement("In order to register iPedia you need to purchase registration code at "));

// those 3 #defines should be mutually exclusive
#ifdef PALMGEAR
    elems.push_back(text=new TextElement("palmgear.com?67708"));
#endif

#ifdef HANDANGO
    elems.push_back(text=new TextElement("handango.com/purchase, product id: 128991"));
#endif

#ifdef ARSLEXIS_VERSION
    elems.push_back(text=new TextElement("our website "));
    elems.push_back(text=new TextElement("http://www.arslexis.com"));
    text->setHyperlink("http://www.arslexis.com/pda/palm.html", hyperlinkExternal);
#endif
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new TextElement("After obtaining registration code use menu item 'Options/Register' (or "));
    elems.push_back(text=new TextElement("click here"));
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback( registerActionCallback, static_cast<void*>(this) );
    elems.push_back(text=new TextElement(") to enter registration code. "));

    elems.push_back(text=new TextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback(aboutActionCallback, this);

    //infoRenderer_.replaceElements(elems);
    infoRenderer_.setModel(model, Definition::ownModel);
}

void PediaMainForm::prepareWikipedia()
{
    DefinitionModel* model = new_nt DefinitionModel();   
    if (NULL == model)   
    {   
       //application().alert(notEnoughMemoryAlert);   
       return;   
    }
    Definition::Elements_t& elems = model->elements; 
    setTitle("iPedia - Wikipedia");
    TextElement* text;
    FontEffects fxBold;
    fxBold.setWeight(FontEffects::weightBold);

    elems.push_back(text=new TextElement("All the articles in iPedia come from WikiPedia project and are licensed under "));
    elems.push_back(text=new TextElement("GNU Free Documentation License"));
    text->setHyperlink("http://www.gnu.org/copyleft/fdl.html", hyperlinkExternal);
    elems.push_back(text=new TextElement("."));
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new TextElement("To find out more about WikiPedia project, visit "));
    elems.push_back(text=new TextElement("wikipedia.org"));
    text->setHyperlink("http://www.wikipedia.org", hyperlinkExternal);
    elems.push_back(text=new TextElement(" website. "));
    elems.push_back(new LineBreakElement());

    elems.push_back(text=new TextElement("Go back to main screen."));
    text->setJustification(DefinitionElement::justifyLeft);
    // url doesn't really matter, it's only to establish a hotspot
    text->setHyperlink("", hyperlinkTerm);
    text->setActionCallback(aboutActionCallback, this);

    //infoRenderer_.replaceElements(elems);
    infoRenderer_.setModel(model, Definition::ownModel);
}    

void PediaMainForm::setDisplayMode(PediaMainForm::DisplayMode mode) 
{
    
    switch (mode) 
    {
        case showAbout:
            articleRenderer_.hide();
            prepareAbout();
            infoRenderer_.show();
            break;
            
        case showArticle: 
        {
            infoRenderer_.hide();
            const LookupHistory& history = getHistory();
            if (history.hasCurrentTerm())
                setTitle(history.currentTerm().c_str());
            else
                setTitle("iPedia");
            articleRenderer_.show();
            break;
        }
        
        case showRegister:
            articleRenderer_.hide();
            prepareHowToRegister();
            infoRenderer_.show();
            break;
            
        case showTutorial:
            articleRenderer_.hide();
            prepareTutorial();
            infoRenderer_.show();
            break;
            
        case showWikipedia:
            articleRenderer_.hide();
            prepareWikipedia();
            infoRenderer_.show();
            break;
 
        default:
            assert(false);          
    }
    displayMode_ = mode;

}
