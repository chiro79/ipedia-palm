@rem scripts that copies ipedia server files to the server
@rem kills currently running server and starts a new one
@rem could be vastly improved by copying only files that have
@rem changed (a good approximation of this would be checked out
@rem files which can be quickly determined with svn status)
@rem another way to speed it up would be to copy to a local directory,
@rem zip it, copy the zip file to the server and unzip it there

@rem set your Unix user, password and where do you keep the sources
@rem (note that ipedia sources must be at the same level as moriarty_palm)
@rem e.g.:

@rem set settings based on computer name
@if %computername%==DVD goto SetDVD
@if %computername%==DVD2 goto SetDVD

@echo "Don't know the setup for computer %computername%"
@goto EOF

:SetDVD
@SET USER=ipedia
@rem this relates to what createlocal.bat uses for DSTDIR
@SET DIR=c:\kjk\ipedia
@goto SetupDone

:SetupDone

@rem provide password as the first argument
@SET PWD=%1

@IF NOT DEFINED USER echo "need to define USER" & goto :EOF
@IF NOT DEFINED PWD echo 'need to define PWD' & goto :EOF

@SET SEC_P=%2
@IF DEFINED SEC_P goto SetupOfficial
@goto NotOfficial

:SetupOfficial
@IF %SEC_P%==official goto ReallySetupOfficial
@echo if second param given, it should be "official" and not %SEC_P%
@goto EOF

:ReallySetupOfficial
@rem TODO: check that the computer is DVD2 or KJKLAP1
@rem echo setting up for official server
@SET USER=ipedia

:NotOfficial

@call createlocal.bat

pushd %DIR%

del ipedia-src.zip
zip -r ipedia-src.zip src
pscp -r -pw %PWD% ipedia-src.zip %USER%@ipedia.arslexis.com:/home/%USER%/
plink -pw %PWD% %USER%@ipedia.arslexis.com cd /home/%USER%; rm -rf src-prev; mv src src-prev; unzip ipedia-src.zip

@IF DEFINED SEC_P goto RunOfficial
plink -pw %PWD% %USER%@ipedia.arslexis.com cd /home/%USER%/src; python2.4 killipedia.py; sleep 10; python2.4 iPediaServer.py -demon -verbose -disableregcheck
@goto PopDir

:RunOfficial
plink -pw %PWD% %USER%@ipedia.arslexis.com cd /home/%USER%/src; python2.4 killipedia.py; sleep 10; python2.4 iPediaServer.py -demon -verbose

:PopDir
@popd

:EOF
