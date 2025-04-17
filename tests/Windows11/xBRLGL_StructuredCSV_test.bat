@echo off
setlocal

echo === Generating 1-GL-Generic-simple-context ===
call .\xBRLGL_StructuredCSV.bat 1-GL-Generic-simple-context

echo === Generating 2-GL-Generic-tuple ===
call .\xBRLGL_StructuredCSV.bat  2-GL-Generic-tuple

echo === Generating 3-GL-Generic-tuple-Dimension ===
call .\xBRLGL_StructuredCSV.bat  3-GL-Generic-tuple-Dimension

echo === Generating BP_FixedAssetList ===
call .\xBRLGL_StructuredCSV.bat  BP_FixedAssetList

echo === Generating BP_TrialBalance ===
call .\xBRLGL_StructuredCSV.bat  BP_TrialBalance

echo === Generating Customer_Invoices ===
call .\xBRLGL_StructuredCSV.bat  Customer_Invoices

echo === Generating Employee_Timesheets ===
call .\xBRLGL_StructuredCSV.bat  Employee_Timesheets

echo === Generating Job-budget-v-actual ===
call .\xBRLGL_StructuredCSV.bat  Job-budget-v-actual

echo === Generating JournalEntry_Annotated_Book-Tax ===
call .\xBRLGL_StructuredCSV.bat  JournalEntry_Annotated_Book-Tax

echo === Generating Vendor_Invoices_Normalized ===
call .\xBRLGL_StructuredCSV.bat  Vendor_Invoices_Normalized

echo === Generating Vendor_Invoices ===
call .\xBRLGL_StructuredCSV.bat  Vendor_Invoices

echo === All structured CSV generation steps completed ===
endlocal
pause