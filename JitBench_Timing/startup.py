import sys
import os
import shutil 
import argparse

def error(message, exitCode = 1):
    print(message)
    sys.exit(exitCode)

def run_command(cmd, outputFile=None):
    print('running command \'{}\''.format(cmd))
    if outputFile is None:
        return os.system(cmd)
    else:
        return os.system(cmd + ' >> ' + outputFile)

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

def parse_output (inFileName):
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
    
    if len(startups) == 0 or \
            len(requests) != len(startups) or \
            len(minSteadyState) != len(startups) or \
            len(maxSteadyState) != len(startups) or \
            len(avgSteadyState) != len(startups):
        error('Error parsing data, missing data detected') 

    create_csv_file(startups, 'startup.txt', 'JitBenchStartupTime')
    create_csv_file(requests, 'request.txt', 'JitBenchRequestTime')
    create_csv_file(minSteadyState, 'minSteadyState.txt', 'JitBenchRequestMinimumSteadyStateTime')
    create_csv_file(maxSteadyState, 'maxSteadyState.txt', 'JitBenchRequestMaximumSteadyStateTime')
    create_csv_file(avgSteadyState, 'avgSteadyState.txt', 'JitBenchRequestAverageSteadyStateTime')

def copy_file(curName, newName):
    print('copying {} to {}'.format(curName, newName))
    if os.path.isfile(newName):
        os.remove(newName)
    
    shutil.copyfile(curName, newName)

def copy_folder(curPath, newParent):
    print ('copying folder {} inside target folder {}'.format(curPath, newParent))
    shutil.move(curPath, newParent)

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
        run_command('/bin/bash -c build.sh release {} skiptests'.format(archStr))

    productIdentifier = '{}.{}.Release'.format(osStr, archStr)
    coreClrOutPath = os.path.join('bin', 'Product', productIdentifier)
    if not os.path.isdir(coreClrOutPath):
        error('coreclr build output path {} does not exist'.format(coreClrOutPath))

    os.chdir(startDir)


def prepare_jitbench(config):
    startDir = os.getcwd()
    jitBenchDir = os.path.join(startDir, 'JitBench')
    
    if os.path.isdir(jitBenchDir):
        os.chdir(jitBenchDir)
        run_command('git pull')
        os.chdir(startDir)
    else:
        run_command('git clone -b dev https://github.com/davmason/JitBench')

    if not os.path.isdir(jitBenchDir):
        error('JitBench folder does not exist')

    os.chdir(jitBenchDir)

    # Get the latest shared runtime and SDK
    # TODO: ability to change architecture
    archStr = config['Arch']
    run_command('powershell .\\Dotnet-Install.ps1 -SharedRuntime -InstallDir .dotnet -Channel master -Architecture {}'.format(archStr))
    run_command('powershell .\\Dotnet-Install.ps1 -InstallDir .dotnet -Channel master -Architecture {}'.format(archStr))
    
    # Add new dotnet to path
    os.environ['PATH'] = os.path.join(os.getcwd(), '.dotnet') + os.pathsep + os.environ['PATH']
    
    run_command('dotnet --info')

    os.chdir(os.path.join('src', 'MusicStore'))

    # Restore the MusicStore project
    run_command('dotnet restore')

    # Modify shared runtime with local built copy
    sharedRuntimeDir = os.path.join(jitBenchDir, '.dotnet', 'shared', 'Microsoft.NETCore.App')
    patched = False
    crossgenPath = ''
    for item in os.listdir(sharedRuntimeDir):
        targetRuntimeDir = os.path.join(sharedRuntimeDir, item)
        print('considering item {}'.format(targetRuntimeDir))
        if os.path.isdir(targetRuntimeDir) and item.startswith('2.0'):
            print('patching shared runtime dir {} with {}'.format(targetRuntimeDir, config['CoreCLRBinPath']))
            patch_coreclr_files(config['CoreCLRBinPath'], targetRuntimeDir)
            patched = True
            crossgenPath = os.path.join(targetRuntimeDir, 'crossgen.exe')

    if not patched:
        error('did not find a dotnet version to patch')

    # publish the App
    run_command('dotnet publish -c Release -f netcoreapp20')

    publishPath = os.path.join('bin', 'Release', 'netcoreapp20', 'publish')
    
    # There is an issue with the lab machines where we were going over the 260 character
    # path limit. We can avoid that by moving the publish folder to the root of the
    # workspace
    copy_folder(publishPath, startDir)
    os.chdir(os.path.join(startDir, 'publish'))

    # Crossgen all the framework assemblies
    run_command('powershell .\\Invoke-Crossgen.ps1 -crossgen_path {}'.format(crossgenPath))
    
    os.chdir(startDir)


def run_jitbench(config):
    startDir = os.getcwd()

    targetDir = os.path.join(startDir, 'publish')
    os.chdir(targetDir)

    targetCommand = 'dotnet MusicStore.dll' 

    # Warmup the scenario
    if run_command(targetCommand) != 0:
        error('Running MusicStore failed')

    for i in range(0, 100):
        if run_command(targetCommand, 'output.txt') != 0:
            error('Running MusicStore failed')

    curName = os.path.join(os.getcwd(), 'output.txt')
    newName = os.path.join(startDir, 'output.txt')
    copy_file(curName, newName)

    os.chdir(startDir)
    return newName

def parse_config():
    workingDir = os.environ['WORKSPACE']
    config = { 'Arch': 'x64', 'OS': 'Windows_NT', 'CoreCLRBinPath': '', 'Workspace': workingDir, 'LocalRun': False}
    
    parser = argparse.ArgumentParser(description='Patches JitBench with a local CLR and runs basic timings')
    parser.add_argument('--os', help='Operating system to target (Windows or Linux)')
    parser.add_argument('--arch', help='Architecture to target (x86 or x64)')
    parser.add_argument('--coreclrbinpath', help='path to coreclr binaries to run JitBench (e.g. D:\\coreclr\\bin\\product\\Windows_NT.x64.Release\\)')
    parser.add_argument('--workspace', help='Local directory to clone JitBench in to')
    
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
        os.mkdir(workingDir)

    os.chdir(workingDir)

    coreClrBinPath = config['CoreCLRBinPath'];
    if not coreClrBinPath or coreClrBinPath.isspace():
        prepare_coreclr(config)
        productIdentifier = '{}.{}.Release'.format(config['OS'], config['Arch'])
        coreClrBinPath = os.path.join(workingDir, 'coreclr', 'bin', 'Product', productIdentifier)
        config['CoreCLRBinPath'] = coreClrBinPath
    
    if not os.path.isdir(coreClrBinPath):
        error('CoreCLR bin path {} does not exist'.format(coreClrBinPath))

    prepare_jitbench(config)
    fileName = run_jitbench(config)
    parse_output(fileName)
    sys.exit(0)
