py %WORKSPACE%\stability\stability\windows_native-stability-test.py --stabilization --iterations=10
For /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\submission-metadata.py --name "%COMPUTERNAME% Stability Run %mydate%" --user-email "dotnet-bot@microsoft.com"
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\build.py git --type rolling --branch master
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\machinedata.py
py %WORKSPACE%\Microsoft.BenchView.JSONFormat\tools\measurement.py csv "stability.csv" --metric "Elapsed Time" --unit "Seconds" --better desc
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