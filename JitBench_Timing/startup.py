import sys
import os
import shutil 
import argparse
import subprocess

def error(message, exitCode = 1):
    print(message)
    run_command('subst X: /D')
    sys.exit(exitCode)

def run_command(cmd, outputFilePath = None, append = True):
    expandedCmd = os.path.expandvars(cmd)
    print('running command \'{}\' in directory \'{}\''.format(expandedCmd, os.getcwd()))
    if outputFilePath is None:
        return os.system(expandedCmd)
    else:
        # Write to file and Console
        if append:
            outputFile = open(outputFilePath, 'a')
        else:
            outputFile = open(outputFilePath, 'w')
        outProc = subprocess.Popen(expandedCmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        for line in outProc.stdout:
            sys.stdout.write(line)
            outputFile.write(line)
        outProc.wait()
        return outProc.returncode

def create_csv_file(data, name, benchmarkTitle):
    if os.path.isfile(name):
        os.remove(name)
    
    f = open(name, 'w')

    for item in data:
        f.write('{},{}'.format(benchmarkTitle, item))
        f.write('\n')

def parse_num_from_string (str):
    # Numbers in the output have a trailing 'ms' we need to strip.
    # There are also a lot of non-number outputs.
    for s in str.split():
        if s[0].isdigit():
            numString = s[:-2]
            if not numString.isdigit():
                error('expected number, found non-numeric string')

            return numString
    
    return -1

def parse_output (inFileName, iters, suffix):
    startups = []
    requests = []
    minSteadyState = []
    maxSteadyState = []
    avgSteadyState = []

    for line in open(inFileName, 'r'):
        if line.startswith('Server started in'):
            startupTime = parse_num_from_string(line)
            startups.append(startupTime)
        elif line.startswith('Request took'):
            requestTime = parse_num_from_string(line)
            requests.append(requestTime)
        elif line.startswith('Steadystate min response time'):
            minTime = parse_num_from_string(line)
            minSteadyState.append(minTime)
        elif line.startswith('Steadystate max response time'):
            maxTime = parse_num_from_string(line)
            maxSteadyState.append(maxTime)
        elif line.startswith('Steadystate average response time'):
            avgTime = parse_num_from_string(line)
            avgSteadyState.append(avgTime)
        elif line.startswith('ASP.NET loaded from bin. This is a bug if you wanted crossgen'):
            error(line)
    
    if len(startups) == 0:
        error('No data detected, startups count = 0')
    if len(startups) != iters:
        error('startups count = {}, expected {}'.format(len(startups), iters))
    if len(requests) != len(startups):
        error('requests count = {}, expected {}'.format(len(requests), len(startups)))
    if len(minSteadyState) != len(startups):
        error('minSteadyState count = {}, expected {}'.format(len(minSteadyState), len(startups)))
    if len(maxSteadyState) != len(startups):
        error('maxSteadyState count = {}, expected {}'.format(len(maxSteadyState), len(startups)))
    if len(avgSteadyState) != len(startups):
        error('avgSteadyState count = {}, expected {}'.format(len(avgSteadyState), len(startups))) 

    create_csv_file(startups, 'startup' + suffix + '.txt', 'JitBenchStartupTime' + suffix)
    create_csv_file(requests, 'request' + suffix + '.txt', 'JitBenchRequestTime' + suffix)
    create_csv_file(minSteadyState, 'minSteadyState' + suffix + '.txt', 'JitBenchRequestMinimumSteadyStateTime' + suffix)
    create_csv_file(maxSteadyState, 'maxSteadyState' + suffix + '.txt', 'JitBenchRequestMaximumSteadyStateTime' + suffix)
    create_csv_file(avgSteadyState, 'avgSteadyState' + suffix + '.txt', 'JitBenchRequestAverageSteadyStateTime' + suffix)

def copy_file(curName, newName):
    print('copying {} to {}'.format(curName, newName))
    if os.path.isfile(newName):
        os.remove(newName)
    
    shutil.copyfile(curName, newName)

def patch_coreclr_files(coreClrBinPath, sharedRuntime):
    for item in os.listdir(coreClrBinPath):
        fullPath = os.path.join(coreClrBinPath, item)
        if os.path.isfile(fullPath):
            copy_file(fullPath, os.path.join(sharedRuntime, item))

def prepare_coreclr(config):
    startDir = os.getcwd()

    coreClrDir = 'coreclr'
    
    if os.path.isdir(coreClrDir):
        os.chdir(coreClrDir)
        run_command('git pull')
        os.chdir(startDir)
    else:
        run_command('git clone https://github.com/dotnet/coreclr')

    os.chdir(coreClrDir)

    # TODO: ability to change architecture
    archStr = config['Arch']
    osStr = config['OS']
    if osStr == 'Windows_NT':
        run_command('cmd.exe /c build.cmd release {} skiptests'.format(archStr))
    else:
        run_command('./build.sh release {} skiptests'.format(archStr))

    productIdentifier = '{}.{}.Release'.format(osStr, archStr)
    coreClrOutPath = os.path.join('bin', 'Product', productIdentifier)
    if not os.path.isdir(coreClrOutPath):
        error('coreclr build output path {} does not exist'.format(coreClrOutPath))

    os.chdir(startDir)


def prepare_jitbench(config):
    startDir = os.getcwd()
    jitBenchDir = os.path.join(startDir, 'JitBench')

    if config['SetupJitBench']:
        if os.path.isdir(jitBenchDir):
            os.chdir(jitBenchDir)
            run_command('git pull')
            os.chdir(startDir)
        else:
            run_command('git clone -b dev https://github.com/davmason/JitBench')

    if not os.path.isdir(jitBenchDir):
        error('JitBench folder does not exist')

    os.chdir(jitBenchDir)

    if config['SetupJitBench']:
        # Get the latest shared runtime and SDK
        # TODO: ability to change architecture
        archStr = config['Arch']
        osStr = config['OS']
    
        if osStr == 'Windows_NT':
            run_command('powershell .\\Dotnet-Install.ps1 -SharedRuntime -InstallDir .dotnet -Channel master -Architecture {}'.format(archStr))
            run_command('powershell .\\Dotnet-Install.ps1 -InstallDir .dotnet -Channel master -Architecture {}'.format(archStr))
        else:
            run_command('./dotnet-install.sh -sharedruntime -installdir .dotnet -channel master -architecture {}'.format(archStr))
            run_command('source ./dotnet-install.sh -installdir .dotnet -channel master -architecture {}'.format(archStr))
      
    # Add new dotnet to path
    os.environ['PATH'] = os.path.join(os.getcwd(), '.dotnet') + os.pathsep + os.environ['PATH']
    
    run_command('dotnet --info')

    if config['SetupJitBench']:
        # Modify shared runtime with local built copy
        sharedRuntimeDir = os.path.join(jitBenchDir, '.dotnet', 'shared', 'Microsoft.NETCore.App')
        patched = False
        for item in os.listdir(sharedRuntimeDir):
            targetRuntimeDir = os.path.join(sharedRuntimeDir, item)
            print('considering item {}'.format(targetRuntimeDir))
            if os.path.isdir(targetRuntimeDir) and item.startswith('2.0'):
                print('patching shared runtime dir {} with {}'.format(targetRuntimeDir, config['CoreCLRBinPath']))
                patch_coreclr_files(config['CoreCLRBinPath'], targetRuntimeDir)
                patched = True

        if not patched:
            error('did not find a dotnet version to patch')

        # Install crossgened assemblies
        # TODO: right now the runtime param is built in. Need to fix that.
        if osStr == 'Windows_NT':
            outFileName = 'aspnetinstall.txt'
            run_command('powershell .\AspNet-GenerateStore.ps1 -InstallDir .store -Architecture {} -Runtime win7-x64'.format(archStr), outFileName)

            aspnetVersion = ''
            frameworkVersion = ''
            aspnetManifest = ''
            sharedStore = ''
            # In the usual case these would be set by the script, but we need to 
            # set them manually since sub scripts don't impact our environment like
            # it would in powershell
            for line in open(outFileName, 'r'):
                if line.startswith('Setting JITBENCH_ASPNET_VERSION to '):
                    aspnetVersion = line[35:].rstrip()
                    os.environ['JITBENCH_ASPNET_VERSION'] = aspnetVersion
                elif line.startswith('Setting JITBENCH_FRAMEWORK_VERSION to '):
                    frameworkVersion = line[38:].rstrip()
                    os.environ['JITBENCH_FRAMEWORK_VERSION'] = frameworkVersion
                elif line.startswith('Setting JITBENCH_ASPNET_MANIFEST to '):
                    aspnetManifest = line[36:].rstrip()
                    os.environ['JITBENCH_ASPNET_MANIFEST'] = aspnetManifest
                elif line.startswith('Setting DOTNET_SHARED_STORE to '):
                    sharedStore = line[31:].rstrip()
                    os.environ['DOTNET_SHARED_STORE'] = sharedStore
            
            if aspnetVersion is None or aspnetVersion.isspace():
                error('Missing asp.net version from script output')
            if frameworkVersion is None or frameworkVersion.isspace():
                error('Missing framework version from script output')
            if aspnetManifest is None or aspnetManifest.isspace():
                error('Missing asp.net manifest from script output')
            if sharedStore is None or sharedStore.isspace():
                error('Missing shared store from script output')

            print('aspnet version = {}'.format(aspnetVersion))
            print('framework version = {}'.format(frameworkVersion))
            print('aspnet manifest = {}'.format(aspnetManifest))
            print('shared store = {}'.format(sharedStore))
            
        else:
            run_command('source ./aspnet-generatestore.sh -i .store --arch {} -r {}'.format(archStr, 'ubuntu.14.04-x64'))

        os.chdir(os.path.join('src', 'MusicStore'))

        # Restore the MusicStore project
        run_command('dotnet restore')

        # publish the App
        if osStr == 'Windows_NT':
            run_command('dotnet publish -c Release -f netcoreapp2.0 --manifest %JITBENCH_ASPNET_MANIFEST%')
        else:
            run_command('dotnet publish -c Release -f netcoreapp2.0 --manifest $JITBENCH_ASPNET_MANIFEST')

        publishPath = os.path.join('bin', 'Release', 'netcoreapp2.0', 'publish')
    
    os.chdir(startDir)


def run_jitbench(config, tiered):
    startDir = os.getcwd()

    targetDir = os.path.join('JitBench', 'src', 'MusicStore', 'bin', 'Release', 'netcoreapp2.0', 'publish')
    os.chdir(targetDir)

    targetCommand = 'dotnet MusicStore.dll' 

    if tiered:
        os.environ['COMPLUS_EXPERIMENTAL_TieredCompilation']='1'
    else:
        os.environ['COMPLUS_EXPERIMENTAL_TieredCompilation']='0'

    # Warmup the scenario
    if run_command(targetCommand) != 0:
        error('Running MusicStore failed')

    # Delete existing results if there are any
    outputFilePath = 'output_tiered.txt' if tiered else 'output.txt'
    if os.path.isfile(outputFilePath):
        os.remove(outputFilePath)

    iterations = 100
    for i in range(0, iterations):
        if run_command(targetCommand, outputFilePath) != 0:
            error('Running MusicStore failed')

    curName = os.path.join(os.getcwd(), outputFilePath)
    newName = os.path.join(startDir, outputFilePath)
    copy_file(curName, newName)

    os.chdir(startDir)
    return newName, iterations

def parse_config():
    workingDir = os.environ['WORKSPACE']
    config = { 'Arch': 'x64', 'OS': 'Windows_NT', 'CoreCLRBinPath': '', 'Workspace': workingDir, 'LocalRun': False, 'SetupJitBench': True}
    
    parser = argparse.ArgumentParser(description='Patches JitBench with a local CLR and runs basic timings')
    parser.add_argument('--os', help='Operating system to target (Windows or Linux)')
    parser.add_argument('--arch', help='Architecture to target (x86 or x64)')
    parser.add_argument('--coreclrbinpath', help='path to coreclr binaries to run JitBench (e.g. D:\\coreclr\\bin\\product\\Windows_NT.x64.Release\\)')
    parser.add_argument('--workspace', help='Local directory to clone JitBench in to')
    parser.add_argument('--setupjitbench', help='Set to false if you want to skip enlisting\building\crossgening JitBench')

    args = parser.parse_args()

    if args.os != None:
        lowerOs = args.os.lower()
        if lowerOs == 'windows' or lowerOs == 'windows_nt':
            config['OS'] = 'Windows_NT'
        elif lowerOs == 'linux':
            config['OS'] = 'Linux'
    if args.arch != None:
        archLower = args.arch.lower()
        if archLower == 'x64':
            config['Arch'] = 'x64'
        elif archLower == 'x86':
            config['Arch'] = 'x86'
    if args.coreclrbinpath != None:
        config['CoreCLRBinPath'] = args.coreclrbinpath
        config['LocalRun'] = True
    if args.setupjitbench != None:
        config['SetupJitBench'] = False
    if args.workspace != None:
        config['Workspace'] = args.workspace

    workingDir = config['Workspace']
    if workingDir is None or workingDir.isspace():
        error("No workspace defined, must define through either environment variable WORKSPACE or --workspace command line option")

    return config

if __name__ == '__main__':
    config = parse_config()
    print('Running with OS={} Arch={} Workspace={}'.format(config['OS'], config['Arch'], config['Workspace']))
    workingDir = config['Workspace']

    if not os.path.isdir(workingDir):
        os.makedirs(workingDir)

    absolutePath = os.path.abspath(workingDir)
    run_command('subst X: {}'.format(absolutePath))
    remappedDir = 'X:\\'
    os.chdir(remappedDir)

    coreClrBinPath = config['CoreCLRBinPath'];
    if not coreClrBinPath or coreClrBinPath.isspace():
        prepare_coreclr(config)
        productIdentifier = '{}.{}.Release'.format(config['OS'], config['Arch'])
        coreClrBinPath = os.path.join(remappedDir, 'coreclr', 'bin', 'Product', productIdentifier)
        config['CoreCLRBinPath'] = coreClrBinPath
    
    if not os.path.isdir(coreClrBinPath):
        error('CoreCLR bin path {} does not exist'.format(coreClrBinPath))

    prepare_jitbench(config)
    tieredFileName, iters = run_jitbench(config, True)
    parse_output(tieredFileName, iters, '_TieredCompiliation')
    fileName, iters = run_jitbench(config, False)
    parse_output(fileName, iters, '')

    run_command("subst X: /D")
    sys.exit(0)
