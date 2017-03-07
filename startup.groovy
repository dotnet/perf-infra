// Import the utility functionality.

import jobs.generation.*;

// The input project name (e.g. dotnet/corefx)
def project = GithubProject
// The input branch name (e.g. master)
def branch = GithubBranchName
// Folder that the project jobs reside in (project/branch)
def projectFolder = Utilities.getFolderName(project) + '/' + Utilities.getFolderName(branch)

// Globals

// Map of os -> osGroup.
def osGroupMap = ['Ubuntu14.04':'Linux',
                  'Ubuntu16.04':'Linux',
                  'Debian8.4':'Linux',
                  'Fedora23':'Linux',
                  'OSX':'OSX',
                  'Windows_NT':'Windows_NT',
                  'CentOS7.1': 'Linux',
                  'OpenSUSE13.2': 'Linux',
                  'RHEL7.2': 'Linux',
                  'LinuxARMEmulator': 'Linux']

// Map of os -> nuget runtime
def targetNugetRuntimeMap = ['OSX' : 'osx.10.10-x64',
                             'Ubuntu14.04' : 'ubuntu.14.04-x64',
                             'Ubuntu16.04' : 'ubuntu.16.04-x64',
                             'Fedora23' : 'fedora.23-x64',
                             'Debian8.4' : 'debian.8-x64',
                             'CentOS7.1' : 'centos.7-x64',
                             'OpenSUSE13.2' : 'opensuse.13.2-x64',
                             'RHEL7.2': 'rhel.7-x64']

def osShortName = ['Windows 10': 'win10',
                   'Windows 7' : 'win7',
                   'Windows_NT' : 'windows_nt',
                   'Ubuntu14.04' : 'ubuntu14.04',
                   'OSX' : 'osx',
                   'Windows Nano 2016' : 'winnano16',
                   'Ubuntu16.04' : 'ubuntu16.04',
                   'CentOS7.1' : 'centos7.1',
                   'Debian8.4' : 'debian8.4',
                   'OpenSUSE13.2' : 'opensuse13.2',
                   'Fedora23' : 'fedora23',
                   'RHEL7.2' : 'rhel7.2']


// **************************
// Define perf testing.  These tests should be run daily, and will run on Jenkins not in Helix
// **************************
[true, false].each { isPR ->
    ['Release'].each { configurationGroup ->
        ['Windows_NT'].each { os ->
        def osGroup = osGroupMap[os]
            def newJobName = "perf_JitBenchStart_${os.toLowerCase()}_${configurationGroup.toLowerCase()}"

            def newJob = job(Utilities.getFullJobName(project, newJobName, isPR)) {
            
                label('windows_clr_perf')
                wrappers {
                    credentialsBinding {
                        string('BV_UPLOAD_SAS_TOKEN', 'CoreCLR Perf BenchView Sas')
                    }
                }

                if (isPR)
                {
                    parameters
                    {
                        stringParam('BenchviewCommitName', '\${ghprbPullTitle}', 'The name that you will be used to build the full title of a run in Benchview.  The final name will be of the form <branch> private BenchviewCommitName')
                    }
                }
                
                def configuration = 'Release'
                def runType = isPR ? 'private' : 'rolling'
                def benchViewName = isPR ? 'JitBenchStart private %BenchviewCommitName%' : 'JitBenchStart rolling %GIT_BRANCH_WITHOUT_ORIGIN% %GIT_COMMIT%'

                steps {
                    batchFile("C:\\Tools\\nuget.exe install Microsoft.BenchView.JSONFormat -Source http://benchviewtestfeed.azurewebsites.net/nuget -OutputDirectory \"%WORKSPACE%\" -Prerelease -ExcludeVersion")
                    //Do this here to remove the origin but at the front of the branch name as this is a problem for BenchView
                    //we have to do it all as one statement because cmd is called each time and we lose the set environment variable
                    batchFile("if [%GIT_BRANCH:~0,7%] == [origin/] (set GIT_BRANCH_WITHOUT_ORIGIN=%GIT_BRANCH:origin/=%) else (set GIT_BRANCH_WITHOUT_ORIGIN=%GIT_BRANCH%)\n" +
                    "py \"%WORKSPACE%\\Microsoft.BenchView.JSONFormat\\tools\\submission-metadata.py\" --name \"${benchViewName}\" --user \"dotnet-bot@microsoft.com\"\n" +
                    "py \"%WORKSPACE%\\Microsoft.BenchView.JSONFormat\\tools\\build.py\" git --branch %GIT_BRANCH_WITHOUT_ORIGIN% --type ${runType}")
                    batchFile("py \"%WORKSPACE%\\Microsoft.BenchView.JSONFormat\\tools\\machinedata.py\"")
                    batchFile("pushd JitBench_Timing")
                    batchFile("py startup.py")
                    batchFile("popd")
                    batchFile("py C:\Tools\Microsoft.BenchView.JSONFormat\tools\measurement.py csv -m \"Duration\" -u \"ms\" --better desc --drop-first-value --append startup.txt")
                    batchFile("py C:\Tools\Microsoft.BenchView.JSONFormat\tools\measurement.py csv -m \"Duration\" -u \"ms\" --better desc --drop-first-value --append request.txt")
                    batchFile("py \"%BENCHVIEW_PATH%\submission.py\" measurement.json " +
                                    "--build build.json " +
                                    "--machine-data machinedata.json " +
                                    "--metadata submission-metadata.json " +
                                    "--group \"JitBenchStart\" " +
                                    "--type \"${runType}\" " +
                                    "--config-name \"${configuration}\" " +
                                    "--config Configuration \"${configuration}\" " +
                                    "--config OS \"Windows_NT\" " +
                                    "--arch \"x64\" " +
                                    "--machinepool \"PerfSnake\"")
                    batchFile("py \"%WORKSPACE%\\Microsoft.BenchView.JSONFormat\\tools\\upload.py\" submission.json --container coreclr")
  
                }
            }

            // Set the label.
            newJob.with {
                label('windows_clr_perf')
            }
            // Set up standard options.
            Utilities.standardJobSetup(newJob, project, isPR, "*/${branch}")

            // Set up triggers
            if (isPR) {
                TriggerBuilder builder = TriggerBuilder.triggerOnPullRequest()
                builder.setGithubContext("${os} Perf Tests")
                builder.triggerOnlyOnComment()
                builder.setCustomTriggerPhrase("(?i).*test\\W+${os}_JitBenchStart\\W+perf.*")
                builder.triggerForBranch(branch)
                builder.emitTrigger(newJob)
            }
            else {
                // Set a daily trigger
                Utilities.addPeriodicTrigger(newJob, '@daily')
            }
        }
    }
}