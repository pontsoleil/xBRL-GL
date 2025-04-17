@echo off
setlocal

echo === Running ParseTaxonomy for case-c ===
call .\xBRLGL_ParseTaxonomy.bat case-c

echo === Running ParseTaxonomy for case-c-b ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b

echo === Running ParseTaxonomy for case-c-b-m ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m

echo === Running ParseTaxonomy for case-c-b-m-u ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m-u

echo === Running ParseTaxonomy for case-c-b-m-u-e ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m-u-e

echo === Running ParseTaxonomy for case-c-b-m-u-e-t ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m-u-e-t

echo === Running ParseTaxonomy for case-c-b-m-u-e-t-s ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m-u-e-t-s

echo === Running ParseTaxonomy for case-c-b-m-u-t ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m-u-t

echo === Running ParseTaxonomy for case-c-b-m-u-t-s ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-m-u-t-s

echo === Running ParseTaxonomy for case-c-b-t ===
call .\xBRLGL_ParseTaxonomy.bat case-c-b-t

echo === Running ParseTaxonomy for case-c-t ===
call .\xBRLGL_ParseTaxonomy.bat case-c-t

echo === All taxonomy cases processed ===
endlocal
pause
