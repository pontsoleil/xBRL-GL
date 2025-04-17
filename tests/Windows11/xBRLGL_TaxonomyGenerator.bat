@echo off
REM Usage: .\xBRLGL_TaxonomyGenerator.bat case-c
REM -r Accntg Entrs for graphwalk LHM
REM -r AccntgEntrs for pased LHM
cd 
set INPUT=%1
python .\xBRLGL_TaxonomyGenerator.py ^
    LHM/xBRL_GL_%INPUT%_LHM.csv ^
    -b ../OIM-CSV/XBRL-GL-2025/gl-%INPUT%/ ^
    -r AccntgEntrs ^
	-l ja ^
	-c usd ^
	-e utf-8-sig ^
    -v
pause
