#include "Graphics.hpp"
#include <cassert>

namespace ArsLexis
{
    
    Graphics::~Graphics()
    {
    }

    typedef NativeColor_t (Graphics::* ColorSetterMethod_t)(NativeColor_t);
    static ColorSetterMethod_t colorSetters[]={&Graphics::setTextColor, &Graphics::setForegroundColor, &Graphics::setBackgroundColor};
    
    NativeColor_t Graphics::setColor(Graphics::ColorChoice choice, NativeColor_t color)
    {
        assert(choice<3);
        ColorSetterMethod_t setter=colorSetters[choice];
        return (this->*setter)(color);
    }
    
    void Graphics::drawCenteredText(const char_t* str, const Point& topLeft, uint_t width)
    {
        assert(str!=0);
        uint_t len=tstrlen(str);
        Coord_t charsWidth=textWidth(str, len);
        Point point(topLeft);
        point.x+=((Coord_t)width-charsWidth)/2;
        drawText(str, len, point);
    }
    
}