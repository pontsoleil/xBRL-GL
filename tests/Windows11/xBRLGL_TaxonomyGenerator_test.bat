@echo off
setlocal

echo === Generating Taxonomy for case-c ===
call .\xBRLGL_TaxonomyGenerator.bat case-c

echo === Generating Taxonomy for case-c-b ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b

echo === Generating Taxonomy for case-c-b-m ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m

echo === Generating Taxonomy for case-c-b-m-u ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m-u

echo === Generating Taxonomy for case-c-b-m-u-e ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m-u-e

echo === Generating Taxonomy for case-c-b-m-u-e-t ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m-u-e-t

echo === Generating Taxonomy for case-c-b-m-u-e-t-s ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m-u-e-t-s

echo === Generating Taxonomy for case-c-b-m-u-t ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m-u-t

echo === Generating Taxonomy for case-c-b-m-u-t-s ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-m-u-t-s

echo === Generating Taxonomy for case-c-b-t ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-b-t

echo === Generating Taxonomy for case-c-t ===
call .\xBRLGL_TaxonomyGenerator.bat case-c-t

echo === All taxonomy generation steps completed ===
endlocal
pause
