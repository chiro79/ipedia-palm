#include "FormObject.hpp"

namespace ArsLexis
{
    
    FormObject::~FormObject()
    {
    }
    
    void FormObject::attach(UInt16 id)
    {
        assert(frmInvalidObjectId!=id);
        index_=FrmGetObjectIndex(*form_, id_=id);
        assert(frmInvalidObjectId!=index_);
        object_=FrmGetObjectPtr(*form_, index_);
        assert(0!=object_);
    }
    
    void FormObject::bounds(Rectangle& out) const
    {
        RectangleType rect;
        FrmGetObjectBounds(*form_, index(), &rect);
        out=rect;
    }
    
    void FormObject::setBounds(const Rectangle& bounds)
    {
        assert(valid());
        RectangleType rect=toNative(bounds);
        FrmSetObjectBounds(*form_, index(), &rect);
    }

    void FormObject::attachByIndex(UInt16 index)
    {
        assert(frmInvalidObjectId!=index);
        id_=FrmGetObjectId(*form_, index_=index);
        assert(frmInvalidObjectId!=id_);
        object_=FrmGetObjectPtr(*form_, index_);
        assert(0!=object_);
    }
    
    
}    