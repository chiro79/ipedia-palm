#include "RenderingPreferences.hpp"
#include <PrefsStore.hpp>

RenderingPreferences::RenderingPreferences():
    standardIndentation_(16),
    bulletIndentation_(2),
    backgroundColor_(0)
{
    styles_[styleHeader].font=largeFont;
    UInt32 screenDepths=0;
    Boolean color=false;
    Err error=WinScreenMode(winScreenModeGet, NULL, NULL, &screenDepths, &color);
    if (screenDepths>=8) // 16+ colors
    {
        hyperlinkDecorations_[hyperlinkTerm].textColor=57;
        hyperlinkDecorations_[hyperlinkExternal].textColor=35;
    }
    else if (screenDepths>=2) // 4 colors
    {
        hyperlinkDecorations_[hyperlinkTerm].textColor=2; // Dark gray
        hyperlinkDecorations_[hyperlinkExternal].textColor=1; // Light gray
    }
    if (screenDepths>=2)
    {
        for (uint_t i=0; i<stylesCount_; ++i)
            styles_[i].textColor=UIColorGetTableEntryIndex(UIObjectForeground);        
    }
    FontEffects fx;
    fx.setUnderline(FontEffects::underlineDotted);
    for (uint_t i=0; i<hyperlinkTypesCount_; ++i) 
        hyperlinkDecorations_[i].font.setEffects(fx);
    calculateIndentation();
}

void RenderingPreferences::calculateIndentation()
{
    const char* bullet="\x95";
    Graphics graphics;
    standardIndentation_=graphics.textWidth(bullet, 1)+bulletIndentation_;
}

Err RenderingPreferences::serializeOut(PrefsStoreWriter& writer, int uniqueId) const
{
    Err error;
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, backgroundColor_)))
        goto OnError;
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, bulletIndentation_)))
        goto OnError;
    for (uint_t i=0; i<hyperlinkTypesCount_; ++i)
    {
        if (errNone!=(error=hyperlinkDecorations_[i].serializeOut(writer, uniqueId)))
            goto OnError;
        uniqueId+=StyleFormatting::reservedPrefIdCount;
    }
    for (uint_t i=0; i<stylesCount_; ++i)
    {
        if (errNone!=(error=styles_[i].serializeOut(writer, uniqueId)))
            goto OnError;
        uniqueId+=StyleFormatting::reservedPrefIdCount;
    }
OnError:
    assert(errNone==error);
    return error;    
}

Err RenderingPreferences::serializeIn(PrefsStoreReader& reader, int uniqueId)
{
    Err                  error;
    RenderingPreferences tmp;
    UInt16               val;

    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &val)))
        goto OnError;
    tmp.setBackgroundColor(val);
    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &val)))
        goto OnError;
    tmp.setBulletIndentation(val);
    for (uint_t i=0; i<hyperlinkTypesCount_; ++i)
    {
        if (errNone!=(error=tmp.hyperlinkDecorations_[i].serializeIn(reader, uniqueId)))
            goto OnError;
        uniqueId += StyleFormatting::reservedPrefIdCount;
    }
    for (uint_t i=0; i<stylesCount_; ++i)
    {
        if (errNone!=(error=tmp.styles_[i].serializeIn(reader, uniqueId)))
            goto OnError;
        uniqueId += StyleFormatting::reservedPrefIdCount;
    }
OnError:
    (*this)=tmp;
    return error;    
}

Err RenderingPreferences::StyleFormatting::serializeOut(PrefsStoreWriter& writer, int uniqueId) const
{
    Err error;
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, font.fontId())))
        goto OnError;
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, font.effects().mask())))
        goto OnError;
    if (errNone!=(error=writer.ErrSetUInt16(uniqueId++, textColor)))
        goto OnError;
OnError:
    return error;
}

Err RenderingPreferences::StyleFormatting::serializeIn(PrefsStoreReader& reader, int uniqueId)
{
    Err             error;
    StyleFormatting tmp;
    UInt16          val;

    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &val)))
        goto OnError;
    tmp.font.setFontId(static_cast<FontID>(val));
    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &val)))
        goto OnError;
    tmp.font.setEffects(FontEffects(val));
    if (errNone!=(error=reader.ErrGetUInt16(uniqueId++, &val)))
        goto OnError;
    tmp.textColor=val;
OnError:    
    (*this)=tmp;
    return error;
}
