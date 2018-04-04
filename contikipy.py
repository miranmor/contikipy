#!/usr/bin/python
"""Contiki log parser."""
import argparse
import os
import shutil  # for copying files
import subprocess

import yaml

import cpconfig as config
import cplogparser as lp

# import yaml config
cfg = yaml.load(open("config.yaml", 'r'))


# ----------------------------------------------------------------------------#
def main():
    """Take in command line arguments and parses log accordingly."""
    # fetch arguments
    ap = argparse.ArgumentParser(prog='ContikiPy',
                                 description='Cooja simulation runner and '
                                             'Contiki log parser')
    ap.add_argument('--path', required=False, default=cfg['path'],
                    help='Absolute path to contiki')
    ap.add_argument('--target', required=False, default=cfg['target'],
                    help='Contiki platform TARGET')
    ap.add_argument('--log', required=False, default=cfg['log'],
                    help='Relative path to contiki log')
    ap.add_argument('--out', required=False, default=cfg['out'],
                    help='Absolute path to output folder')
    ap.add_argument('--wd', required=False, default=cfg['wd'],
                    help='(Relative) working directory for code + csc')
    ap.add_argument('--csc', required=False, default=cfg['csc'],
                    help='Cooja simulation file')
    ap.add_argument('--makeargs', required=False,
                    help='Makefile arguments')
    ap.add_argument('--runcooja', required=False, default=0,
                    help='Run the simulation')
    ap.add_argument('--parse', required=False, default=0,
                    help='Run the log parser')
    ap.add_argument('--comp', required=False, default=0,
                    help='Run the analyzer (compare sims)')
    args = ap.parse_args()

    if not args.makeargs:
        # get simulations configuration
        conf = config.Config()
        simulations = conf.simconfig()
        # get analysis configuration
        analysis = conf.analysisconfig()
    else:
        simulations = [{'desc': '', 'makeargs': str(args.makeargs)}]
        analysis = None

    simlog = None
    print '**** Run ' + str(len(simulations)) + ' simulations'
    for sim in simulations:
        # generate a simulation description
        desc = sim['desc']
        makeargs = sim['makeargs']
        plot_config = sim['plot']
        # Print some information about this simulation
        info = 'Running simulation: {0}'.format(desc)
        print '=' * len(info)
        print info
        print '=' * len(info)
        # HACK: replace remove list brackets
        makeargs = makeargs.replace('[', '').replace(']', '')
        print makeargs
        # make a note of our intended sim directory
        outdir = args.out + "/" + desc + "/"
        # run a cooja simulation with these sim settings
        if int(args.runcooja):
            if 'csc' in sim:
                csc = sim['csc']
            else:
                csc = args.csc
            print 'here'
            simlog = run(args.path,
                         args.target,
                         args.log,
                         args.wd,
                         csc,
                         outdir,
                         makeargs,
                         desc)
        # generate results by parsing the cooja log
        if int(args.parse) and desc is not None:
            parse(simlog, outdir, desc, 'cooja', plot_config)

    # analyze the generated results
    if int(args.comp) and analysis is not None:
        print '**** Analyzing (comparing) results...'
        lp.compare_results(args.out, analysis['sims'], analysis['plots'])


# ----------------------------------------------------------------------------#
def parse(log, dir, desc, fmt, plots):
    """Parse the main log to generate the data."""
    if log is None:
        log = dir + desc + ".log"
    print '**** Parse log and gererate results in: ' + dir
    print '> plots: ' + ' '.join(plots)
    logtype = (l for l in cfg['logtypes'] if l['type'] == fmt).next()
    df_dict = {}
    for d in cfg['data']['dictionary']:
        if 'pow' in d['type']:
            regex = logtype['fmt_re'] + d['regex']
        else:
            regex = logtype['fmt_re'] + logtype['log_re'] + d['regex']
        df = lp.parse_log(d['type'], log, dir, fmt, regex)
        if df is not None:
            df_dict.update({d['type']: df})
    lp.extract_data(df_dict)
    lp.pickle_data(dir, df_dict)
    lp.plot_data(dir, df_dict, plots)


# ----------------------------------------------------------------------------#
def run(contiki, target, log, wd, csc, outdir, args, desc):
    """Clean, make, and run cooja."""
    print '**** Clean and make: ' + contiki + wd + "/" + csc
    contikilog = contiki + log
    print '> Clean ' + contiki + wd
    clean(contiki + wd, target)
    # print '> Make ' + contiki + wd
    # make(contiki + wd, args)
    # Run the scenario in cooja with -nogui
    print '**** Create simulation directory'
    # Create a new folder for this scenario
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    print '**** Running simulation ' + desc
    run_cooja(contiki, contiki + wd + '/' + csc, args)
    print '**** Copy log into simulation directory'
    # Copy contiki ouput log file and prefix the desc
    simlog = outdir + "/" + desc + '.log'
    print simlog
    shutil.copyfile(contikilog, simlog)

    return simlog


# ----------------------------------------------------------------------------#
def run_cooja(contiki, sim, args):
    """Run cooja nogui."""
    # java = 'java -mx512m -jar'
    # cooja_jar = contiki + '/tools/cooja/dist/cooja.jar'
    # nogui = '-nogui=' + sim
    # contiki = '-contiki=' + contiki
    # cmd = args + ' ' + java + ' ' + cooja_jar + ' ' + nogui + ' ' + contiki
    ant = 'ant run_nogui'
    antbuild = '-file ' + contiki + '/tools/cooja/'
    antnogui = '-Dargs=' + sim
    cmd = args + ' ' + ant + ' ' + antbuild + ' ' + antnogui
    print '> ' + cmd
    subprocess.call(cmd, shell=True)


# ----------------------------------------------------------------------------#
def clean(path, target):
    """Run contiki make clean."""
    # make clean in case we have new cmd line arguments
    subprocess.call('make clean TARGET=' + target + ' ' +
                    ' -C ' + path + '/controller',
                    shell=True)
    subprocess.call('make clean TARGET=' + target + ' ' +
                    ' -C ' + path + '/node',
                    shell=True)


# ----------------------------------------------------------------------------#
def make(path, args, target):
    """Run contiki make."""
    print '> args: ' + args
    subprocess.call('make TARGET=' + target + ' ' + args +
                    ' -C ' + path + '/controller', shell=True)
    subprocess.call('make TARGET=' + target + ' ' + args +
                    ' -C ' + path + '/node',
                    shell=True)


# ----------------------------------------------------------------------------#
if __name__ == "__main__":
    # config = {}
    # execfile("mpy.conf", config)
    # print config["bitrate"]
    main()
