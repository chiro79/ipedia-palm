#include <Socket.hpp>
#include <SocketAddress.hpp>
#include <NetLibrary.hpp>

namespace ArsLexis
{

#pragma mark -
#pragma mark SocketBase

    SocketBase::SocketBase(NetLibrary& netLib):
        log_("SocketBase"),
        netLib_(netLib),
        socket_(0)
    {
        assert(netLib_.refNum());
    }
    
    SocketBase::~SocketBase()
    {
        if (socket_!=0)
        {
            Err error=NetLibSocketClose(netLib_, socket_, evtWaitForever, &error);
            if (error)
                log().error()<<"~SocketBase(): NetLibSocketClose() returned error, "<<error;
        }
    }
    
    Err SocketBase::open(NetSocketAddrEnum domain, NetSocketTypeEnum type, Int16 protocol, Int32 timeout)
    {
        assert(!socket_);
        Err error=errNone;
        socket_=NetLibSocketOpen(netLib_, domain, type, protocol, timeout, &error);
        assert(error || (socket_!=0));
        return error;
    }
    
    Err SocketBase::shutdown(Int16 direction, Int32 timeout)
    {
        assert(socket_!=0);
        Err error=errNone;
        Int16 result=NetLibSocketShutdown(netLib_, socket_, direction, timeout, &error);
        if (-1==result)
            assert(error);
        else
            assert(!error);
        if (error)
            log()<<"shutdown(): NetLibSocketShutdown() returned error, "<<error;
        return error;
    }
    
    Err SocketBase::send(UInt16& sent, const void* buffer, UInt16 bufferLength, Int32 timeout, UInt16 flags, const SocketAddress* address)
    {
        assert(socket_!=0);
        Err error=errNone;
        const NetSocketAddrType* addr=0;
        UInt16 addrLen=0;
        if (address)
        {
            addr=*address;
            addrLen=address->size();
        }
        Int16 result=NetLibSend(netLib_, socket_, const_cast<void*>(buffer), bufferLength, flags, 
            const_cast<NetSocketAddrType*>(addr), addrLen, timeout, &error);
        if (result>0)
        {
            assert(!error);
            sent+=result;
        }
        else if (0==result)
            assert(netErrSocketClosedByRemote==error);
        else
            assert(error);
        return error;
    }
    
    Err SocketBase::receive(UInt16& received, void* buffer, UInt16 bufferLength, Int32 timeout, UInt16 flags)
    {
        assert(socket_!=0);
        Err error=errNone;
        
        Int16 result=NetLibReceive(netLib_, socket_, buffer, bufferLength, flags, 0, 0, timeout, &error);
        if (result>=0)
        {
            assert(!error);
            received+=result;
        }
        else
            assert(error);
        return error;
    }

    Err SocketBase::setNonBlocking(bool value)
    {
        Boolean flag=value;
        Err error=setOption(netSocketOptLevelSocket, netSocketOptSockNonBlocking, &flag, sizeof(flag));
        return error;
    } 

    Err SocketBase::setOption(UInt16 level, UInt16 option, void* optionValue, UInt16 valueLength, Int32 timeout)
    {
        assert(socket_!=0);
        Err error=errNone;
        Int16 result=NetLibSocketOptionSet(netLib_, socket_, level, option, optionValue, valueLength, timeout, &error);
        if (-1==result)
            assert(error);
        else
            assert(!error);
        if (error)            
            log()<<"setOption(): NetLibSocketOptionSet() returned error, "<<error;
        return error;
    }
    
    Err SocketBase::getOption(UInt16 level, UInt16 option, void* optionValue, UInt16& valueLength, Int32 timeout) const
    {
        assert(socket_!=0);
        Err error=errNone;
        Int16 result=NetLibSocketOptionGet(netLib_, socket_, level, option, optionValue, &valueLength, timeout, &error);
        if (-1==result)
            assert(error);
        else
            assert(!error);
        if (error)            
            log().warning()<<"getOption(): NetLibSocketOptionGet() returned error, "<<error;
        return error;
    }
        
    Err Socket::connect(const SocketAddress& address, Int32 timeout)
    {
        assert(socket_!=0);
        Err error=errNone;
        const NetSocketAddrType* addr=address;
        UInt16 addrLen=address.size();
        Int16 result=NetLibSocketConnect(netLib_, socket_, const_cast<NetSocketAddrType*>(addr), addrLen, timeout, &error);
        if (-1==result)
            assert(error);
        else
            assert(!error);
        return error;
    }

    Err SocketBase::setLinger(const NetSocketLingerType& linger)
    {
        assert(socket_!=0);
        Err error=setOption(netSocketOptLevelSocket, netSocketOptSockLinger, const_cast<NetSocketLingerType*>(&linger), sizeof(linger));
        return error;
    }
    
/*    
    Err SocketBase::getLinger(NetSocketLingerType& linger) const
    {
        assert(socket_!=0);
        Err error=getOption(netSocketOptLevelSocket, netSocketOptSockLinger, &linger, sizeof(linger);
        return error;
    }
*/    
    
#pragma mark -
#pragma mark SocketSelector

    SocketSelector::SocketSelector(NetLibrary& netLib, bool catchStandardEvents):
        netLib_(netLib),
        width_(0),
        eventsCount_(0)
    {
        for (UInt16 i=0; i<eventTypesCount_; ++i)
        {
            netFDZero(&inputFDs_[i]);
            netFDZero(&outputFDs_[i]);
        }
        if (catchStandardEvents)
            netFDSet(sysFileDescStdIn, &inputFDs_[eventRead]);
        recalculateWidth();
    }
    
    Err SocketSelector::select(Int32 timeout)
    {
        for (UInt16 i=0; i<eventTypesCount_; ++i)
            outputFDs_[i]=inputFDs_[i];

        Err error=errNone;
        // Seems NetLibSelect() is really badly screwed in PalmOS - see strange error behaviour in the following if-else...
        Int16 eventsCount=NetLibSelect(netLib_, width_+1, &outputFDs_[eventRead], &outputFDs_[eventWrite], &outputFDs_[eventException], timeout, &error);
        if (-1==eventsCount)
        {
            if (!error)
                error=netErrTimeout;
            eventsCount_=0;
        }
        else
        {
            assert(!error);
            eventsCount_=eventsCount;
            if (0==eventsCount_)
                error=netErrTimeout;
        }            
        return error;
    }
    
    void SocketSelector::recalculateWidth()
    {
        width_=1;
        for (UInt16 i=sizeof(NetFDSetType)*8-1; i>0; --i)
            if (netFDIsSet(i, &inputFDs_[eventRead]) ||
                netFDIsSet(i, &inputFDs_[eventWrite]) ||
                netFDIsSet(i, &inputFDs_[eventException]))
            {
                width_=i+1;
                break;
            }                
    }
    
}