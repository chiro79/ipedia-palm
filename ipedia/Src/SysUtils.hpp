#ifndef __ARSLEXIS_SYSUTILS_HPP__
#define __ARSLEXIS_SYSUTILS_HPP__

#include <Debug.hpp>
#include <BaseTypes.hpp>

namespace ArsLexis
{

    bool isNotifyManager();
    
    void getScreenBounds(RectangleType& bounds);

    /** 
     * Generates a random long in the range 0..range-1. SysRandom() returns value
     * between 0..sysRandomMax which is 0x7FFF. We have to construct a long out of
     * that.
     * @note Shamelessly ripped from Noah's noah_pro_2nd_segment.c ;-)
     */
    std::uint32_t random(std::uint32_t range);
    
    Err numericValue(const char* begin, const char* end, std::int32_t& result, uint_t base=10);
    
    inline Err numericValue(const String& text, std::int32_t& result, uint_t base=10)
    {
        return numericValue(text.data(), text.data()+text.length(), result, base);
    }
    
    String hexBinEncode(const String& in);

    inline void hexBinEncodeInPlace(String& inOut)
    {
        inOut=hexBinEncode(inOut);
    }
    
    // detect a web browser app and return cardNo and dbID of its *.prc.
    // returns true if detected some viewer, false if none was found
    bool fDetectViewer(UInt16 *cardNoOut, LocalID *dbIDOut);
   
    Err getResource(UInt16 tableId, UInt16 index, String& out);
    
    Err getResource(UInt16 stringId, String& out);

	Err  ErrWebBrowserCommand(Boolean subLaunch, UInt16 launchFlags, UInt16 command, char *parameterP, UInt32 *resultP);

}

#endif
