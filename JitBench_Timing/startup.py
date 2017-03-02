import sys
import os

def error(message, exitCode = 1):
    print(message)
    sys.exit(exitCode)

def create_csv_file(data, name, benchmarkTitle):
    if os.path.isfile(name):
        os.remove(name)
    
    f = open(name, "w")

    for item in data:
        f.write("{},{}".format(benchmarkTitle, item))
        f.write("\n")

def parse_num_from_string (str):
    # Numbers in the output have a trailing 'ms' we need to strip.
    # There are also a lot of non-number outputs.
    for s in str.split():
        if s[0].isdigit():
            numString = s[:-2]
            if not numString.isdigit():
                error("expected number, found non-numeric string")

            return numString
    
    return -1

def parse_output (inFileName):
    startups = []
    requests = []

    for line in open(inFileName, "r"):
        if line.startswith("Server started in"):
            startupTime = parse_num_from_string(line)
            startups.append(startupTime)
        elif line.startswith("Request took"):
            requestTime = parse_num_from_string(line)
            requests.append(requestTime)
    
    if len(startups) == 0 or len(requests) != len(startups):
        error("Error parsing data, missing data detected") 

    create_csv_file(startups, "startup.txt", "JitBenchStartupTime")
    create_csv_file(requests, "request.txt", "JitBenchRequestTime")

def copy_file(curName, newName):
    print("moving {} to {}".format(curName, newName))
    if os.path.isfile(newName):
        os.remove(newName)
    
    os.rename(curName, newName)

def patch_coreclr_files(coreClrBinPath, sharedRuntime):
    for item in os.listdir(coreClrBinPath):
        fullPath = os.path.join(coreClrBinPath, item)
        if os.path.isfile(fullPath):
            copy_file(fullPath, os.path.join(sharedRuntime, item))

def prepare_coreclr():
    startDir = os.getcwd()

    coreClrDir = "coreclr"
    
    if os.path.isdir(coreClrDir):
        os.chdir(coreClrDir)
        os.system("git pull")
        os.chdir(startDir)
    else:
        os.system("git clone https://github.com/dotnet/coreclr")

    os.chdir(coreClrDir)

    os.system("cmd.exe /c build.cmd release x64 skiptests")

    if not os.path.isdir("bin\\Product\\Windows_NT.x64.Release"):
        error("coreclr build output does not exist")

    os.chdir(startDir)


def prepare_jitbench(coreClrBinPath):
    startDir = os.getcwd()
    jitBenchDir = os.path.join(startDir, "JitBench")
    
    if os.path.isdir(jitBenchDir):
        os.chdir(jitBenchDir)
        os.system("git pull")
        os.chdir(startDir)
    else:
        os.system("git clone -b dev https://github.com/davmason/JitBench")

    if not os.path.isdir(jitBenchDir):
        error("JitBench folder does not exist")

    os.chdir(jitBenchDir)

    # Get the latest shared runtime and SDK
    os.system("powershell Set-ExecutionPolicy RemoteSigned")
    os.system("powershell .\\Dotnet-Install.ps1 -SharedRuntime -InstallDir .dotnet -Channel master -Architecture x64")
    os.system("powershell .\\Dotnet-Install.ps1 -InstallDir .dotnet -Architecture x64")
    
    # Add new dotnet to path
    os.environ["PATH"] = os.path.join(os.getcwd(), ".dotnet") + os.pathsep + os.environ["PATH"]
    
    os.system("dotnet --info")

    os.chdir("src\\MusicStore")

    # Restore the MusicStore project
    os.system("dotnet restore")

    # Modify shared runtime with local built copy
    sharedRuntimeDir = os.path.join(jitBenchDir, ".dotnet\\shared\\Microsoft.NETCore.App\\")
    patched = False
    for item in os.listdir(sharedRuntimeDir):
        targetRuntimeDir = sharedRuntimeDir + "\\" + item
        print("considering item {}".format(targetRuntimeDir))
        if os.path.isdir(targetRuntimeDir) and item.startswith("2.0"):
            print("patching shared runtime dir {} with {}".format(targetRuntimeDir, coreClrBinPath))
            patch_coreclr_files(coreClrBinPath, targetRuntimeDir)
            patched = True

    if not patched:
        error("did not find a dotnet version to patch")

    # publish the App
    os.system("dotnet publish -c Release -f netcoreapp20")

    os.chdir("bin\\Release\\netcoreapp20\\publish")

    # Crossgen all the framework assemblies
    os.system("powershell .\\Invoke-Crossgen.ps1")
    
    os.chdir(startDir)


def run_jitbench():
    startDir = os.getcwd()

    targetDir = "JitBench\\src\\MusicStore\\bin\\Release\\netcoreapp20\\publish"
    os.chdir(targetDir)

    targetCommand = "dotnet MusicStore.dll" 

    # Warmup the scenario
    if os.system(targetCommand) != 0:
        error("Running MusicStore failed")

    for i in range(0, 100):
        if os.system("{} >> {}".format(targetCommand, "output.txt")) != 0:
            error("Running MusicStore failed")

    curName = os.path.join(os.getcwd(), "output.txt")
    newName = os.path.join(startDir, "output.txt")
    copy_file(curName, newName)

    os.chdir(startDir)
    return newName

if __name__ == "__main__":
    workingDir = os.environ["WORKSPACE"]
    os.chdir(workingDir)
    prepare_coreclr()
    coreClrBinPath = os.path.join(workingDir, "coreclr\\bin\\Product\\Windows_NT.x64.Release")
    prepare_jitbench(coreClrBinPath)
    fileName = run_jitbench()
    parse_output(fileName)
    sys.exit(0)
