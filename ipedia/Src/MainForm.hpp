#ifndef __MAINFORM_HPP__
#define __MAINFORM_HPP__

#include "iPediaForm.hpp"
#include "Definition.hpp"
#include "iPediaApplication.hpp"

class LookupHistory;
class RenderingPreferences;


class MainForm: public iPediaForm
{
    Definition article_;
    Definition about_;
    Definition register_;
    Definition tutorial_;
    Definition wikipedia_;
    GenericTextElement* articleCountElement_;
    bool forceAboutRecalculation_;    
    long articleCountSet_;
    int  penUpsToEat_;
    
    const LookupHistory& getHistory() const;
    
    const RenderingPreferences& renderingPreferences() const
    {return static_cast<const iPediaApplication&>(application()).renderingPreferences();}
    
    void handleScrollRepeat(const EventType& data);
    
    void handleControlSelect(const EventType& data);
    
    bool handleKeyPress(const EventType& event);
    
    void drawDefinition(ArsLexis::Graphics& graphics, const ArsLexis::Rectangle& bounds);
    
    void updateScrollBar();
 
    void randomArticle();
    
    void copySelectionToClipboard();

    void updateAfterLookup();
    
    void moveHistory(bool forward);
    
    void switchServer(const char* server);
    
    void setControlsState(bool enabled);
    
    void handleToggleStressMode();
    
    void search(bool fullText=false);
    
    void handlePenDown(const EventType& event);
    
    void handleLookupFinished(const EventType& event);
    
    void updateNavigationButtons();
    
    void handleExtendSelection(const EventType& event, bool endTracking=false);
    
    Err renderDefinition(Definition& def, ArsLexis::Graphics& graphics, const ArsLexis::Rectangle& rect);

    class RenderingProgressReporter: public Definition::RenderingProgressReporter
    {
        MainForm& form_;
        UInt32 ticksAtStart_;
        uint_t lastPercent_;
        bool showProgress_:1;
        bool afterTrigger_:1;
        ArsLexis::String waitText_;
        
    public:
        
        RenderingProgressReporter(MainForm& form);
        
        virtual void reportProgress(uint_t percent);

    };
    
    friend class RenderingProgressReporter;
    
    RenderingProgressReporter renderingProgressReporter_;
    
    Definition& currentDefinition();

    void prepareAbout();

    void updateArticleCountEl(long articleCount, ArsLexis::String& dbTime);

protected:

    void resize(const ArsLexis::Rectangle& screenBounds);
    
    void draw(UInt16 updateCode=frmRedrawUpdateCode);
    
    bool handleWindowEnter(const struct _WinEnterEventType& data);
    
    bool handleEvent(EventType& event);
    
    bool handleMenuCommand(UInt16 itemId);
    
    bool handleOpen();
    
public:

    enum ScrollUnit
    {
        scrollLine,
        scrollPage
    };
    
private:
    
    void scrollDefinition(int units, ScrollUnit unit, bool updateScrollbar);
    
public:
    
    MainForm(iPediaApplication& app);
    
    enum DisplayMode
    {
        showAbout,
        showTutorial,
        showRegister,
        showArticle,
        showWikipedia
    };
    
    DisplayMode displayMode() const
    {return displayMode_;}

    bool fCanScrollDef() const
    {return displayMode_==showAbout ? false : true; }

    void setDisplayMode(DisplayMode displayMode)
    {displayMode_=displayMode;}
    
    void setUpdateDefinitionOnEntry(bool val=true)
    {updateDefinitionOnEntry_=val;}

    void scrollDefinition(int units, ScrollUnit unit)
    {scrollDefinition(units, unit, true);}

    void prepareTutorial();    

    void prepareHowToRegister();

    void prepareWikipedia();

private:
    
    UInt32      lastPenDownTimestamp_;
    DisplayMode displayMode_:4;
    bool        updateDefinitionOnEntry_:1;
    bool        enableInputFieldAfterUpdate_:1;
    
};

#endif
