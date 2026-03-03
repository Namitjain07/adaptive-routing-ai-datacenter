#!/usr/bin/env python3
"""
Batch Experiment Runner
Runs multiple routing experiments sequentially with comprehensive logging,
progress tracking, and automatic cleanup between runs.
"""

import sys
import os
import time
import json
import argparse
import subprocess
import signal
import logging
from datetime import datetime, timedelta

sys.path.append('/home/namitjain07/Desktop/NAI')
from utils.logger import setup_logger, get_logger

# ──────────────────────────────────────────────────────────────────────────────
# Experiment suite definitions
# ──────────────────────────────────────────────────────────────────────────────

EXPERIMENT_SUITES = {
    'quick': [
        {'name': 'ECMP_AllToAll',      'routing': 'ecmp',     'traffic': 'all_to_all', 'duration': 5},
        {'name': 'Adaptive_AllToAll',  'routing': 'adaptive', 'traffic': 'all_to_all', 'duration': 5},
    ],
    'basic': [
        {'name': 'ECMP_AllToAll',      'routing': 'ecmp',     'traffic': 'all_to_all', 'duration': 10},
        {'name': 'Adaptive_AllToAll',  'routing': 'adaptive', 'traffic': 'all_to_all', 'duration': 10},
        {'name': 'ECMP_Bursty',        'routing': 'ecmp',     'traffic': 'bursty',     'duration': 10},
        {'name': 'Adaptive_Bursty',    'routing': 'adaptive', 'traffic': 'bursty',     'duration': 10},
    ],
    'comprehensive': [
        {'name': 'ECMP_AllToAll_10s',      'routing': 'ecmp',     'traffic': 'all_to_all', 'duration': 10},
        {'name': 'Adaptive_AllToAll_10s',  'routing': 'adaptive', 'traffic': 'all_to_all', 'duration': 10},
        {'name': 'ECMP_AllToAll_15s',      'routing': 'ecmp',     'traffic': 'all_to_all', 'duration': 15},
        {'name': 'Adaptive_AllToAll_15s',  'routing': 'adaptive', 'traffic': 'all_to_all', 'duration': 15},
        {'name': 'ECMP_AllReduce_10s',     'routing': 'ecmp',     'traffic': 'allreduce',  'duration': 10},
        {'name': 'Adaptive_AllReduce_10s', 'routing': 'adaptive', 'traffic': 'allreduce',  'duration': 10},
        {'name': 'ECMP_AllReduce_15s',     'routing': 'ecmp',     'traffic': 'allreduce',  'duration': 15},
        {'name': 'Adaptive_AllReduce_15s', 'routing': 'adaptive', 'traffic': 'allreduce',  'duration': 15},
        {'name': 'ECMP_Bursty_10s',        'routing': 'ecmp',     'traffic': 'bursty',     'duration': 10},
        {'name': 'Adaptive_Bursty_10s',    'routing': 'adaptive', 'traffic': 'bursty',     'duration': 10},
        {'name': 'ECMP_Bursty_15s',        'routing': 'ecmp',     'traffic': 'bursty',     'duration': 15},
        {'name': 'Adaptive_Bursty_15s',    'routing': 'adaptive', 'traffic': 'bursty',     'duration': 15},
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Batch Runner
# ──────────────────────────────────────────────────────────────────────────────

class BatchRunner:
    """
    Runs a list of experiments sequentially, logging progress and results.
    """

    def __init__(self, experiments, output_dir='results', wait_between=15,
                 cleanup=True, num_spines=4, num_leaves=4, hosts_per_leaf=4):
        self.experiments  = experiments
        self.output_dir   = output_dir
        self.wait_between = wait_between
        self.cleanup      = cleanup
        self.num_spines   = num_spines
        self.num_leaves   = num_leaves
        self.hosts_per_leaf = hosts_per_leaf

        # Per-batch log file so `tail -f` can follow a single file
        self.batch_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.logger = setup_logger(
            name='batch_runner',
            level=logging.INFO,
            log_dir='logs',
            log_file=f'batch_runner_{self.batch_ts}.log'
        )

        # Summary accumulator
        self.summary = {
            'batch_info': {
                'total_experiments': len(experiments),
                'completed': 0,
                'failed': 0,
                'skipped': 0,
                'total_time': 0,
                'start_time': None,
                'end_time': None,
                'log_file': f'logs/batch_runner_{self.batch_ts}.log',
            },
            'experiments': []
        }

        self._stop_requested = False
        signal.signal(signal.SIGINT,  self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    # ── signal handling ────────────────────────────────────────────────────────

    def _handle_signal(self, sig, frame):
        self.logger.warning("Interrupt received — finishing current experiment then stopping.")
        self._stop_requested = True

    # ── helpers ────────────────────────────────────────────────────────────────

    def _hr(self, char='=', width=70):
        self.logger.info(char * width)

    def _mininet_cleanup(self):
        """Best-effort Mininet cleanup between runs."""
        self.logger.info("Running Mininet cleanup (mn -c)...")
        proc = subprocess.run(
            ['sudo', 'mn', '-c'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if proc.returncode == 0:
            self.logger.info("Mininet cleanup OK")
        else:
            self.logger.warning("mn -c returned non-zero — continuing anyway")

        # Kill stale iperf3 processes
        subprocess.run(['sudo', 'pkill', '-9', 'iperf3'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def _fmt_duration(seconds):
        """Format seconds as 'Xm Ys'."""
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s:02d}s" if m else f"{s}s"

    def _estimate_eta(self, elapsed, done, total):
        if done == 0:
            return "unknown"
        avg = elapsed / done
        remaining = (total - done) * avg
        return self._fmt_duration(remaining)

    # ── core ───────────────────────────────────────────────────────────────────

    def run_single(self, exp, index, total):
        """
        Invoke run_experiment.py for one experiment entry.
        Returns a result dict.
        """
        name     = exp['name']
        routing  = exp['routing']
        traffic  = exp['traffic']
        duration = exp['duration']

        self._hr()
        self.logger.info(
            f"EXPERIMENT {index}/{total}: {name}  "
            f"[{routing.upper()} | {traffic} | {duration}s]"
        )
        self._hr()
        self.logger.info(f"Config: routing={routing}, traffic={traffic}, duration={duration}s, "
                         f"spines={self.num_spines}, leaves={self.num_leaves}, "
                         f"hosts/leaf={self.hosts_per_leaf}")

        cmd = [
            'sudo', 'python3', 'run_experiment.py',
            '--mode',    'single',
            '--routing', routing,
            '--traffic', traffic,
            '--duration', str(duration),
            '--spines',  str(self.num_spines),
            '--leaves',  str(self.num_leaves),
            '--hosts',   str(self.hosts_per_leaf),
            '--output',  self.output_dir,
        ]

        start = time.time()
        timeout = duration * 60 + 300   # generous upper bound

        record = {
            'index':       index,
            'name':        name,
            'routing':     routing,
            'traffic':     traffic,
            'duration':    duration,
            'status':      'unknown',
            'elapsed':     0,
            'output_file': None,
            'error':       None,
            'start_time':  datetime.now().isoformat(),
        }

        try:
            self.logger.info(f"Launching subprocess: {' '.join(cmd[2:])}")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd='/home/namitjain07/Desktop/NAI'
            )

            # Stream subprocess output to the batch log in real time
            for line in iter(proc.stdout.readline, ''):
                stripped = line.rstrip()
                if stripped:
                    self.logger.info(f"  [subprocess] {stripped}")

            proc.wait(timeout=timeout)
            elapsed = time.time() - start

            if proc.returncode == 0:
                record['status']  = 'completed'
                record['elapsed'] = round(elapsed, 1)
                self.logger.info(
                    f"[OK] {name} completed in {self._fmt_duration(elapsed)}"
                )
            else:
                record['status']  = 'failed'
                record['elapsed'] = round(elapsed, 1)
                record['error']   = f"exit code {proc.returncode}"
                self.logger.error(
                    f"[FAIL] {name} failed (exit {proc.returncode}) "
                    f"after {self._fmt_duration(elapsed)}"
                )

        except subprocess.TimeoutExpired:
            proc.kill()
            elapsed = time.time() - start
            record['status']  = 'timeout'
            record['elapsed'] = round(elapsed, 1)
            record['error']   = f"timed out after {self._fmt_duration(elapsed)}"
            self.logger.error(f"[TIMEOUT] {name} timed out after {self._fmt_duration(elapsed)}")

        except Exception as exc:
            elapsed = time.time() - start
            record['status']  = 'error'
            record['elapsed'] = round(elapsed, 1)
            record['error']   = str(exc)
            self.logger.error(f"[ERROR] {name}: {exc}", exc_info=True)

        record['end_time'] = datetime.now().isoformat()
        return record

    # ── main batch loop ────────────────────────────────────────────────────────

    def run(self):
        total      = len(self.experiments)
        batch_start = time.time()

        self.summary['batch_info']['start_time'] = datetime.now().isoformat()
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)

        self._hr('=')
        self.logger.info("BATCH EXPERIMENT RUNNER")
        self.logger.info(f"Total experiments : {total}")
        self.logger.info(f"Output directory  : {self.output_dir}/")
        self.logger.info(f"Log file          : logs/batch_runner_{self.batch_ts}.log")
        self.logger.info(f"Topology          : {self.num_spines} spines / "
                         f"{self.num_leaves} leaves / "
                         f"{self.hosts_per_leaf} hosts per leaf")
        self.logger.info(f"Wait between runs : {self.wait_between}s")
        self._hr('=')

        for idx, exp in enumerate(self.experiments, start=1):
            if self._stop_requested:
                self.logger.warning(f"Stop requested — skipping remaining {total - idx + 1} experiment(s).")
                for remaining in self.experiments[idx - 1:]:
                    self.summary['experiments'].append({
                        'index': idx, 'name': remaining['name'],
                        'status': 'skipped', 'elapsed': 0
                    })
                    self.summary['batch_info']['skipped'] += 1
                    idx += 1
                break

            # Pre-run cleanup
            if self.cleanup:
                self._mininet_cleanup()
                time.sleep(3)

            # Run
            record = self.run_single(exp, idx, total)
            self.summary['experiments'].append(record)

            if record['status'] == 'completed':
                self.summary['batch_info']['completed'] += 1
            else:
                self.summary['batch_info']['failed'] += 1

            # Progress report
            elapsed_batch = time.time() - batch_start
            done = idx
            pct  = done / total * 100
            eta  = self._estimate_eta(elapsed_batch, done, total)
            self.logger.info(
                f"Progress: {done}/{total} ({pct:.0f}%)  |  "
                f"Elapsed: {self._fmt_duration(elapsed_batch)}  |  "
                f"ETA: {eta}  |  "
                f"Completed: {self.summary['batch_info']['completed']}  "
                f"Failed: {self.summary['batch_info']['failed']}"
            )

            # Wait between runs (skip after last)
            if idx < total and not self._stop_requested:
                self.logger.info(f"Waiting {self.wait_between}s before next experiment...")
                for remaining in range(self.wait_between, 0, -5):
                    time.sleep(min(5, remaining))
                    self.logger.debug(f"  Next experiment in {remaining - min(5, remaining)}s...")

        # Finalise summary
        total_time = time.time() - batch_start
        self.summary['batch_info']['total_time']   = round(total_time, 1)
        self.summary['batch_info']['end_time']     = datetime.now().isoformat()
        self.summary['batch_info']['avg_time_per'] = (
            round(total_time / self.summary['batch_info']['completed'], 1)
            if self.summary['batch_info']['completed'] else 0
        )

        self._save_summary()
        self._print_final_summary(total_time)

        return self.summary

    # ── reporting ──────────────────────────────────────────────────────────────

    def _save_summary(self):
        summary_file = f"{self.output_dir}/batch_summary_{self.batch_ts}.json"
        with open(summary_file, 'w') as f:
            json.dump(self.summary, f, indent=2)
        self.logger.info(f"Batch summary saved to {summary_file}")

    def _print_final_summary(self, total_time):
        bi = self.summary['batch_info']
        self._hr('=')
        self.logger.info("BATCH COMPLETE — FINAL SUMMARY")
        self._hr('-')
        self.logger.info(f"  Total experiments : {bi['total_experiments']}")
        self.logger.info(f"  Completed         : {bi['completed']}")
        self.logger.info(f"  Failed / Timeout  : {bi['failed']}")
        self.logger.info(f"  Skipped           : {bi['skipped']}")
        self.logger.info(f"  Total time        : {self._fmt_duration(total_time)}")
        self.logger.info(f"  Avg per experiment: {self._fmt_duration(bi.get('avg_time_per', 0))}")
        self._hr('-')
        self.logger.info("  Per-experiment breakdown:")
        for r in self.summary['experiments']:
            status_tag = {
                'completed': '[OK]     ',
                'failed':    '[FAIL]   ',
                'timeout':   '[TIMEOUT]',
                'skipped':   '[SKIP]   ',
                'error':     '[ERROR]  ',
            }.get(r['status'], '[?]      ')
            err_str = f"  <- {r['error']}" if r.get('error') else ''
            self.logger.info(
                f"  {status_tag} {r['name']:<35} "
                f"{self._fmt_duration(r['elapsed']):<10}{err_str}"
            )
        self._hr('=')


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Batch Experiment Runner for Adaptive vs ECMP Routing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python3 run_batch_experiments.py --type quick
  sudo python3 run_batch_experiments.py --type basic --wait 20
  sudo python3 run_batch_experiments.py --type comprehensive --output results/run1
  sudo python3 run_batch_experiments.py --type custom --experiments ecmp:all_to_all:10 adaptive:bursty:15
        """
    )

    parser.add_argument('--type',
                        choices=['quick', 'basic', 'comprehensive', 'custom'],
                        default='quick',
                        help='Experiment suite to run (default: quick)')

    parser.add_argument('--experiments', nargs='+', metavar='ROUTING:TRAFFIC:DURATION',
                        help='Custom experiments in "routing:traffic:duration" format '
                             '(used with --type custom)')

    parser.add_argument('--output', default='results',
                        help='Output directory for result JSON files (default: results)')

    parser.add_argument('--wait', type=int, default=15,
                        help='Seconds to wait between experiments (default: 15)')

    parser.add_argument('--no-cleanup', action='store_true',
                        help='Skip mn -c cleanup between experiments')

    parser.add_argument('--spines',  type=int, default=4,  help='Number of spine switches (default: 4)')
    parser.add_argument('--leaves',  type=int, default=4,  help='Number of leaf switches (default: 4)')
    parser.add_argument('--hosts',   type=int, default=4,  help='Hosts per leaf switch (default: 4)')

    parser.add_argument('--verbose', action='store_true',
                        help='Enable DEBUG-level logging')

    args = parser.parse_args()

    # ── build experiment list ──────────────────────────────────────────────────
    if args.type == 'custom':
        if not args.experiments:
            parser.error("--type custom requires --experiments ROUTING:TRAFFIC:DURATION [...]")
        experiments = []
        for i, spec in enumerate(args.experiments, start=1):
            try:
                routing, traffic, duration = spec.split(':')
                experiments.append({
                    'name':     f"Custom_{i}_{routing}_{traffic}",
                    'routing':  routing,
                    'traffic':  traffic,
                    'duration': int(duration),
                })
            except ValueError:
                parser.error(f"Invalid experiment spec '{spec}' — expected routing:traffic:duration")
    else:
        experiments = EXPERIMENT_SUITES[args.type]

    # ── run ────────────────────────────────────────────────────────────────────
    runner = BatchRunner(
        experiments=experiments,
        output_dir=args.output,
        wait_between=args.wait,
        cleanup=not args.no_cleanup,
        num_spines=args.spines,
        num_leaves=args.leaves,
        hosts_per_leaf=args.hosts,
    )

    summary = runner.run()

    # Exit with non-zero if any experiment failed
    failed = summary['batch_info']['failed']
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
