#include <Text.hpp>
#include <DynStr.hpp>

#include <FormObject.hpp>

#include "LookupManager.hpp"
#include "LookupHistory.hpp"

#include "SearchResultsForm.hpp"
#include "MainForm.hpp"

using ArsLexis::String;

void SearchResultsForm::updateSearchResults()
{
    DynStr *title = NULL;

    iPediaApplication& app = static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager = app.getLookupManager();


    if (lookupManager)
    {
        listPositionsString_=lookupManager->lastExtendedSearchResults();    
        listPositions_.clear();
        String::iterator end(listPositionsString_.end());
        String::iterator lastStart=listPositionsString_.begin();
        for (String::iterator it=listPositionsString_.begin(); it!=end; ++it)
        {
            if ('\n'==*it)
            {
                const char* start=&(*lastStart);
                lastStart=it;
                ++lastStart;
                *it=chrNull;
                listPositions_.push_back(start);
            }
        }
        if (!lookupManager->lastExtendedSearchTerm().empty())
        {
            title = DynStrFromCharP(lookupManager->lastExtendedSearchTerm().c_str(), 32);
            if (NULL == title)
                goto Exit;
            size_t resultsCount = listPositions_.size();
            char buffer[32] = {0};
            int len = formatNumber(resultsCount, buffer, sizeof(buffer));
            assert(len != -1 );
            DynStrAppendCharP(title, _T(" ("));
            DynStrAppendCharP(title, buffer);
            DynStrAppendCharP(title, _T(" results"));
            setTitle(DynStrGetCStr(title));
        }

    }
    {
        List list(*this, searchResultsList);
        list.setChoices(&listPositions_[0], listPositions_.size());
    }
    {
        Field field(*this, refineSearchInputField);
        field.erase();
    }                
Exit:
    update();
    if (NULL != title)
        DynStrDelete(title);
}

SearchResultsForm::SearchResultsForm(iPediaApplication& app):
    iPediaForm(app, searchResultsForm)
{
}

SearchResultsForm::~SearchResultsForm()
{
}

void SearchResultsForm::draw(UInt16 updateCode)
{
    Graphics graphics;
    ArsRectangle rect(bounds());
    ArsRectangle progressArea(rect.x(), rect.height()-16, rect.width(), 16);
    if (redrawAll==updateCode)
    {   
        if (visible())
            graphics.erase(progressArea);
        iPediaForm::draw(updateCode);
    }
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager();
    if (lookupManager && lookupManager->lookupInProgress())
        lookupManager->showProgress(graphics, progressArea);
}

bool SearchResultsForm::handleOpen()
{
    bool handled=iPediaForm::handleOpen();
    updateSearchResults();
    return handled;
}

void SearchResultsForm::resize(const ArsRectangle& screenBounds)
{
    ArsRectangle rect(bounds());
    if (screenBounds!=rect)
    {
        setBounds(screenBounds);
        
        {
            List list(*this, searchResultsList);
            list.bounds(rect);
            rect.height()=screenBounds.height()-34;
            rect.width()=screenBounds.width()-4;
            list.setBounds(rect);
            list.adjustVisibleItems();
        }
        {
            FormObject object(*this, refineSearchInputField);
            object.bounds(rect);
            rect.y()=screenBounds.height()-14;
            rect.width()=screenBounds.width()-74;
            object.setBounds(rect);

            object.attach(cancelButton);
            object.bounds(rect);
            rect.y()=screenBounds.height()-14;
            rect.x()=screenBounds.width()-34;
            object.setBounds(rect);

            object.attach(refineSearchButton);
            object.bounds(rect);
            rect.y()=screenBounds.height()-14;
            rect.x()=screenBounds.width()-69;
            object.setBounds(rect);
        }        
        update();
    }
}

void SearchResultsForm::refineSearch()
{
    Field field(*this, refineSearchInputField);
    const char* text=field.text();
    uint_t textLen;
    if (0==text || 0==(textLen=StrLen(text)))
        return;
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager();
    if (0==lookupManager)
        return;
    
    String expression(lookupManager->lastExtendedSearchTerm());
    expression.reserve(expression.length()+textLen+1);
    expression.append(1, ' ').append(text, textLen);
    lookupManager->search(expression);
}

void SearchResultsForm::handleControlSelect(const EventType& event)
{
    switch (event.data.ctlSelect.controlID)
    {
        case refineSearchButton:
            refineSearch();
            break;
        
        case cancelButton:
            {
                PediaMainForm* form=static_cast<PediaMainForm*>(application().getOpenForm(mainForm));
                assert(form);
                form->update();
                closePopup();
            }
            break;
        
        default:
            assert(false);            
    }
}

void SearchResultsForm::setControlsState(bool enabled)
{
    {
        Control control(*this, refineSearchButton);
        control.setEnabled(enabled);
        control.attach(cancelButton);
        control.setEnabled(enabled);
    }
    {        
        Field field(*this, refineSearchInputField);
        if (enabled)
        {
            field.show();
            field.focus();
        }
        else
        {
            releaseFocus();
            field.hide();
        }
    }            
}

void SearchResultsForm::handleListSelect(const EventType& event)
{
    assert(searchResultsList==event.data.lstSelect.listID);
    assert(listPositions_.size()>event.data.lstSelect.selection);
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager();
    if (lookupManager)
    {
        const String& term=listPositions_[event.data.lstSelect.selection];
        const LookupHistory& history=app.history();
        if (history.hasCurrentTerm() && history.currentTerm()==term)
            closePopup();
        else
            lookupManager->lookupTerm(term, app.preferences().currentLang);
    }        
}

bool SearchResultsForm::handleKeyPress(const EventType& event)
{
    bool handled=false;
    List list(*this, searchResultsList);

    if (fiveWayLeftPressed(&event))
    {
        list.setSelectionDelta(-list.visibleItemsCount());
        handled = true;
    } 
    else if (fiveWayRightPressed(&event))
    {
        list.setSelectionDelta(list.visibleItemsCount());
        handled = true;
    } 
    else if (fiveWayUpPressed(&event))
    {
        list.setSelectionDelta(-1);
        handled = true;
    } 
    else if (fiveWayDownPressed(&event))
    {
        list.setSelectionDelta(1);
        handled = true;
    }
    else
    {
        switch (event.data.keyDown.chr)
        {
            case chrPageDown:
                list.setSelectionDelta(list.visibleItemsCount());
                handled=true;
                break;
                
            case chrPageUp:
                list.setSelectionDelta(-list.visibleItemsCount());
                handled=true;
                break;
            
            case chrDownArrow:
                list.scroll(winDown, 1);
                handled=true;
                break;

            case chrUpArrow:
                list.scroll(winUp, 1);
                handled=true;
                break;

            // if there is no text in the text field, select
            // the article
            case vchrRockerCenter:
            {
                Field fld(*this, refineSearchInputField);
                if (0==fld.textLength())
                {
                    iPediaApplication& app=static_cast<iPediaApplication&>(application());
                    LookupManager* lookupManager=app.getLookupManager();
                    if (lookupManager)
                    {
                        const String& title=listPositions_[list.selection()];
                        const LookupHistory& history=app.history();
                        if (history.hasCurrentTerm() && history.currentTerm()==title)
                            closePopup();
                        else
                            lookupManager->lookupTerm(title, app.preferences().currentLang);
                    }
                }
                handled = true;
            }
            break;
    
            case chrLineFeed:
            case chrCarriageReturn:
                {
                    Control control(*this, refineSearchButton);
                    control.hit();
                }                
                handled=true;
                break;
        }
    }
    return handled;
}

void SearchResultsForm::handleLookupFinished(const EventType& event)
{
    setControlsState(true);
    const LookupFinishedEventData& data=reinterpret_cast<const LookupFinishedEventData&>(event.data);
    if (data.outcomeArticleBody==data.outcome)
    {
        PediaMainForm* form=static_cast<PediaMainForm*>(application().getOpenForm(mainForm));
        assert(form);
        if (form)
            form->setUpdateDefinitionOnEntry();
        closePopup();
        return;
    }
    else if (data.outcomeList==data.outcome)
        updateSearchResults();
    else
        update();
    LookupManager* lookupManager=static_cast<iPediaApplication&>(application()).getLookupManager();
    assert(lookupManager);
    lookupManager->handleLookupFinishedInForm(data);
}


bool SearchResultsForm::handleEvent(EventType& event)
{
    bool handled=false;
    switch (event.eType)
    {
        case ctlSelectEvent:
            handleControlSelect(event);
            handled=true;
            break;
            
        case lstSelectEvent:
            handleListSelect(event);
            handled=true;
            break;

        case LookupManager::lookupFinishedEvent:
            handleLookupFinished(event);
            handled=true;
            break;     
            
        case LookupManager::lookupStartedEvent:
            setControlsState(false);            // No break is intentional.
            
        case LookupManager::lookupProgressEvent:
            update(redrawProgressIndicator);
            break;
    
        case keyDownEvent:
            handled=handleKeyPress(event);
            break;        
    
        default:
            handled=iPediaForm::handleEvent(event);
    }
    return handled;
}

bool SearchResultsForm::handleMenuCommand(UInt16 menuItem)
{
    bool handled=false;
    Control control(*this);
    switch (menuItem)
    {
        case refineSearchMenuItem:
            control.attach(refineSearchButton);
            break;
       
        case cancelSearchMenuItem:
            control.attach(cancelButton);
            break;
        
        default:
            assert(false);            
    }
    if (control.valid())
    {
        control.hit();
        handled=true;
    }
    return handled;
}

bool SearchResultsForm::handleWindowEnter(const struct _WinEnterEventType& data)
{
    const FormType* form=*this;
    if (data.enterWindow==static_cast<const void*>(form))
    {
        FormObject object(*this, refineSearchInputField);
        object.focus();
    }
    iPediaApplication& app=static_cast<iPediaApplication&>(application());
    LookupManager* lookupManager=app.getLookupManager();
    if (lookupManager)
        setControlsState(!lookupManager->lookupInProgress());

    return iPediaForm::handleWindowEnter(data);
}
