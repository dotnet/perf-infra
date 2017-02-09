#!/usr/bin/env python2.7

import os
import os.path
import platform
import sys
import argparse
import urllib
import tarfile
import shutil
import time
import subprocess
import re
import math

argParser = argparse.ArgumentParser()
argParser.add_argument('--stabilization', help="Run in stabilization mode.  Run until the standard deviation of the last N runs (stabilization-iterations) dips below a threshold", action="store_true")
argParser.add_argument('--stabilization-iterations', help="Number of successive iterations to measure in stabilization mode.", type=int, default=5)
argParser.add_argument('--std-dev', help='Target standard deviation in stabilization mode.  In %% points', type=float, default=1)
argParser.add_argument('--iterations', help="Number of iterations to run.  If in stabilization mode, this is the maximum number of iterations to run before giving up.  Otherwise this is the desired number of iterations.", type=int, default=1)
argParser.add_argument('--target-dir', help="Target directory for downloaded benchmarks", type=str, default=os.getcwd())
argParser.add_argument('--offline', help="Skip download of benchmarks", action="store_true")
argParser.add_argument('--no-unpack', help="Skip unpack of benchmarks (assumes already unpacked in target dir).  Implies offline", action="store_true")
args = None

# Downloads the benchmark to the target location
def downloadAndUnpack(sourceLocation, targetLocation):
    if (sourceLocation.find("http://") == 0) or (sourceLocation.find("https://") == 0):
        if ((not args.offline) and (not args.no_unpack)):
            print("Downloading from %s to %s" % (sourceLocation, targetLocation))
            # Download
            urllib.urlretrieve (sourceLocation, targetLocation)
    else:
        # Copy to target location
        print("Copying from %s to %s" % (sourceLocation, targetLocation))
        shutil.copy(sourceLocation, targetLocation)
    
    if (not args.no_unpack):
        print("Unpacking from %s" % (targetLocation))
        # Unpack. Check extension Assumed to be zip
        benchmarkTar = tarfile.open(targetLocation)
        benchmarkTar.extractall()
        benchmarkTar.close()
    return 0

def writeBenchviewCSV(results):
    csvFile = open("stability.csv", 'w')
    for value in results:
        csvFile.write("blackscholes,stability,{0}\r\n".format(value))
    return 0

def runAndProcess(commandLine, processFunc):
    # Current results
    results = []
    
    # Loop over the maximum number of iterations
    maxIter = args.iterations
    for i in range(1, maxIter + 1):
        sys.stdout.write('Running iteration %d of %d - ' % (i, maxIter))
        sys.stdout.flush()
        # Execute the benchmark
        result = subprocess.check_output(commandLine, shell=True)
        # Process the results
        timing = processFunc(result)
        results.append(timing)
        print ("%fs" % (timing))
        # If in stabilization mode and we're over the target number of iterations, compute the standard
        # deviation over the target number of stabilization iterations.  If below the stabilization target, exit.
        # If we haven't hit the stabilization target, continue
        if (args.stabilization and i >= args.stabilization_iterations):
            median, percentOfMedian = computeStats (results, args.stabilization_iterations)
            print ("Standard deviation was %.2f%% of median %.3f over the last %d iterations" % (percentOfMedian, median, args.stabilization_iterations))
            if (percentOfMedian <= args.std_dev):
                print ("Hit target of < %.2f%%, stopping" % (args.std_dev))
                writeBenchviewCSV(results)
                return 0
            else:
                print ("Haven't hit target of < %.2f%%, continuing" % (args.std_dev))
    
    # If in stabilization mode and we haven't hit the target, then exit with a non-zero exit code to indicate that
    # Something is wrong here.
    if (args.stabilization):
        print ("Failed to hit standard deviation target of %.2f%%, exiting" % (args.std_dev))
        writeBenchviewCSV(results)
        return 1
    else:
        # Compute and print the standard deviation
        median, percentOfMedian = computeStats (results, len(results))
        print ("Standard deviation was %.2f%% of median %.3f." % (percentOfMedian, median))
        if (percentOfMedian <= args.std_dev):
            print ("Hit target of < %.2f%%" % (args.std_dev))
            writeBenchviewCSV(results)
            return 0
        else:
            print ("Did not hit target of < %.2f%%, failing" % (args.std_dev))
            writeBenchviewCSV(results)
            return 1

# Computes the median and standard deviatio.  There isn't a standard library
# for this so we do it manually.
def computeStats(results, lastNValues):
    resultsLen = len(results)
    # Grab the sub array
    subArray = results[resultsLen-lastNValues:resultsLen]
    # Sort and remove the top and bottom values
    subArray = sorted(subArray)[1:(len(subArray)-1)]
	# Adjust lastNValues to new number
    lastNValues = lastNValues - 2
    # Find the median
    median = None
    medianValueIndex = (lastNValues - 1) / 2
    if (lastNValues % 2 == 1):
        median = float(subArray[medianValueIndex])
    else:
        median = float(subArray[medianValueIndex] + subArray[medianValueIndex + 1]/2.0)
    
    # Find the mean
    mean = sum(subArray) / float(lastNValues)
    # percent of median is the standard deviation computed as a % of the median.
    sqdiff = map(lambda x: (x - mean) ** 2, subArray)
    meanSqdif = sum(sqdiff) / float(lastNValues)
    sqrtmeanSqdif = math.sqrt(meanSqdif)
    
    # Compute percentage of the median
    percentOfMedian = (sqrtmeanSqdif / median) * 100.0
    return (median, percentOfMedian)
    
# Given output from a command line, process the result and return the ET.
def parsecProcessResults(result):
    # Match the data in the 
    for line in iter(result.splitlines()):
        m = re.search('\[HOOKS\] Total time spent in ROI: (\d+\.?\d+)*s', line)
        if (m == None):
            continue
        timing = m.group(1)
        return float(timing)
        
def runParsec():
    # Table of parsec build locations, indexed by platform
    blackScholesLocations = {'Windows' : 'https://dciperfdata.blob.core.windows.net/stability/Windows-blackscholes.tar.gz',
                             'Linux' : 'https://dciperfdata.blob.core.windows.net/stability/Linux-blackscholes.tar.gz'}
    
    # Download blackscholes
    benchmarkLocation = blackScholesLocations[platformSystemName]
    targetDir = os.path.join(args.target_dir, 'blackscholes')
    if not os.path.exists(targetDir):
        os.makedirs(targetDir)
    targetFile = os.path.join(targetDir, 'blackscholes.tar.gz')
    downloadAndUnpack(benchmarkLocation, targetFile)
    
    return runAndProcess("%WORKSPACE%\\blackscholes_cpp_serial 1 in_10M.txt prices.txt", parsecProcessResults)
    
# List of benchmarks to run
benchmarkRunners = {'Parsec': runParsec}
    
if __name__ == '__main__':
    args = argParser.parse_args()
    # Check the arguments
    
    platformSystemName = platform.system()
    print("Running native stability tests on %s. Aiming for standard deviation of %.2f%% from median" % (platformSystemName, args.std_dev))
    
    for benchmarkName, benchmarkFunction, in benchmarkRunners.iteritems():
        print("Running %s" % (benchmarkName))
        if (benchmarkFunction() != 0):
            print ("Benchmark failed to reach desired standard deviation, exiting")
            sys.exit(1)
    sys.exit(0)
    
