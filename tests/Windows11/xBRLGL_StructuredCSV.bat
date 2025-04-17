@echo off
REM Usage: .\xBRLGL_StructuredCSV.bat Customer_Invoices

set INPUT=%1
python .\xBRLGL_StructuredCSV.py ^
    -i ids/%INPUT%.xml ^
    -n 2025-12-01 ^
    -s LHM/xBRL_GL_case-c-b-m-u-e-t-s_LHM.csv ^
    -o OIM/%INPUT%.csv ^
    -e utf-8-sig 
pause
