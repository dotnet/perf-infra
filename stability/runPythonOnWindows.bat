py %WORKSPACE%\stability\stability\windows_native-stability-test.py --iterations=11
For /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
For /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a:%%b)
set timestamp=%mydate%T%mytime%:00Z
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\submission-metadata.py --name "%COMPUTERNAME% Stability Run %mydate%-%mytime%" --user-email "dotnet-bot@microsoft.com"
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\build.py git --type rolling --branch master --number %mydate%-%mytime% --source-timestamp "%timestamp%"
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\machinedata.py
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\measurement.py csv "stability.csv" --metric "Elapsed Time" --unit "Seconds" --better desc --drop-first-value
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\submission.py measurement.json ^
                                                               --build build.json ^
                                                               --machine-data machinedata.json ^
                                                               --metadata submission-metadata.json ^
                                                               --group "Windows Stability Tests" ^
                                                               --type "rolling" ^
                                                               --config-name "%COMPUTERNAME%" ^
                                                               --config Computer "%COMPUTERNAME%" ^
                                                               --architecture x64 ^
                                                               --machinepool "perfsnake"
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\upload.py submission.json --container stability