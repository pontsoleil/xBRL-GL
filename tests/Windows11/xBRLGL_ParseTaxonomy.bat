@echo off
REM Usage: .\xBRLGL_ParseTaxonomy.bat Case-c

set INPUT=%1
python .\xBRLGL_ParseTaxonomy.py ^
    --base_dir ../XBRL-GL-PWD-2016-12-01 ^
    --palette %INPUT% ^
    --output ../OIM-CSV/XBRL-GL-2025/LHM/xBRL_GL_%INPUT%_LHM.csv ^
    --lang ja
pause