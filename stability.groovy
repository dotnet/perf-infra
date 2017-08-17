// Import the utility functionality.
import jobs.generation.*;

def project = GithubProject
def branch = GithubBranchName
def gitUrl = Utilities.calculateGitURL(project)

// Define the nightly workflows that measure the stability of performance machines
// Put these in a folder

def stabilityTestingFolderName = 'stability_testing'
folder('stability_testing') {}



// Defines stability testing for all linux OS's.  It might be possible to unify this into all unixes.
// Can't use pipeline here.  The postbuild step that is used to launch the subsequent builds doesn't work
// with the pipeline project type.  It might be possible to do this other ways.  For instance, evaluating all
// all eligible nodes based on an expression in a pipeline job and launching downstream jobs.

// We run two types:
// 1) Native testing of known binaries (a few parsec benchmarks) that are very stable.
// 2) Managed testing of known binaries that are stable

['windows', 'windows_server_2016'].each { osFamily ->
    def nativeStabilityJob = job(Utilities.getFullJobName("${osFamily}_native_stability_test", false, stabilityTestingFolderName)) {
        // Add a parameter to specify which nodes to run the stability job across
        parameters {
            labelParam('NODES_LABEL') {
                allNodes('allCases', 'AllNodeEligibility')
                defaultValue("${osFamily}_clr_perf")
                description('Nodes label expression to run the unix stability job across')
            }
        }
        wrappers {
					credentialsBinding {
						string('BV_UPLOAD_SAS_TOKEN', 'Stability Perf SAS Token')
					}
				}
        steps {
            if (osFamily != 'linux') {
                batchFile("C:\\Tools\\nuget.exe install Microsoft.BenchView.JSONFormat -Source http://benchviewtestfeed.azurewebsites.net/nuget -OutputDirectory \"%WORKSPACE%\" -Prerelease -ExcludeVersion")
                batchFile('stability\\runPythonOnWindows.bat')
            }
            else {
                shell("stability/linux_native-stability-test.py")
            }
        }
    }

    // Standard job setup, etc.
    Utilities.standardJobSetup(nativeStabilityJob, project, false, "*/${branch}")
    // Set the cron job here.  We run nightly on each flavor, regardless of code changes
    Utilities.addPeriodicTrigger(nativeStabilityJob, "@daily", true /*always run*/)
}
