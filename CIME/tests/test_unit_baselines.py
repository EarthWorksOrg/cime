#!/usr/bin/env python3

import gzip
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from CIME import baselines
from CIME.tests.test_unit_system_tests import CPLLOG

def create_mock_case(tempdir, get_latest_cpl_logs):
    caseroot = Path(tempdir, "0", "caseroot")
    rundir = caseroot / "run"

    get_latest_cpl_logs.return_value = (
        str(rundir / "cpl.log.gz"),
    )

    baseline_root = Path(tempdir, "baselines")

    case = mock.MagicMock()

    return case, caseroot, rundir, baseline_root

class TestUnitBaseline(unittest.TestCase):
    def test_get_throughput_no_file(self):
        throughput = baselines.get_throughput("/tmp/cpl.log")

        assert throughput is None

    def test_get_throughput(self):
        with tempfile.TemporaryDirectory() as tempdir:
            cpl_log_path = Path(tempdir, "cpl.log.gz")

            with gzip.open(cpl_log_path, "w") as fd:
                fd.write(CPLLOG.encode("utf-8"))

            throughput = baselines.get_throughput(str(cpl_log_path))

        assert throughput == 719.635

    def test_get_mem_usage_gz(self):
        with tempfile.TemporaryDirectory() as tempdir:
            cpl_log_path = Path(tempdir, "cpl.log.gz")

            with gzip.open(cpl_log_path, "w") as fd:
                fd.write(CPLLOG.encode("utf-8"))

            mem_usage = baselines.get_mem_usage(str(cpl_log_path))

        assert mem_usage == [(10102.0, 1673.89), (10103.0, 1673.89), (10104.0, 1673.89), (10105.0, 1673.89)]

    @mock.patch("CIME.baselines.os.path.isfile")
    def test_get_mem_usage(self, isfile):
        isfile.return_value = True

        with mock.patch("builtins.open", mock.mock_open(read_data=CPLLOG.encode("utf-8"))) as mock_file:
            mem_usage = baselines.get_mem_usage("/tmp/cpl.log")

        assert mem_usage == [(10102.0, 1673.89), (10103.0, 1673.89), (10104.0, 1673.89), (10105.0, 1673.89)]

    def test_read_baseline_mem_empty(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="")) as mock_file:
            baseline = baselines.read_baseline_mem("/tmp/cpl-mem.log")

        assert baseline is 0

    def test_read_baseline_mem_none(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="-1")) as mock_file:
            baseline = baselines.read_baseline_mem("/tmp/cpl-mem.log")

        assert baseline is 0

    def test_read_baseline_mem(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="200")) as mock_file:
            baseline = baselines.read_baseline_mem("/tmp/cpl-mem.log")

        assert baseline == 200

    def test_read_baseline_tput_empty(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="")) as mock_file:
            baseline = baselines.read_baseline_tput("/tmp/cpl-tput.log")

        assert baseline is None

    def test_read_baseline_tput_none(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="-1")) as mock_file:
            baseline = baselines.read_baseline_tput("/tmp/cpl-tput.log")

        assert baseline is None

    def test_read_baseline_tput(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="200")) as mock_file:
            baseline = baselines.read_baseline_tput("/tmp/cpl-tput.log")

        assert baseline == 200

    @mock.patch("CIME.baselines.get_mem_usage")
    def test_write_baseline_mem_no_value(self, get_mem_usage):
        get_mem_usage.return_value = []

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            baselines.write_baseline_mem("/tmp", "/tmp/cpl.log")

        mock_file.assert_called_with("/tmp/cpl-mem.log", "w")
        mock_file.return_value.write.assert_called_with("-1")

    @mock.patch("CIME.baselines.get_mem_usage")
    def test_write_baseline_mem(self, get_mem_usage):
        get_mem_usage.return_value = [(1, 200)]

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            baselines.write_baseline_mem("/tmp", "/tmp/cpl.log")

        mock_file.assert_called_with("/tmp/cpl-mem.log", "w")
        mock_file.return_value.write.assert_called_with("200")

    @mock.patch("CIME.baselines.get_throughput")
    def test_write_baseline_tput_no_value(self, get_throughput):
        get_throughput.return_value = None

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            baselines.write_baseline_tput("/tmp", "/tmp/cpl.log")

        mock_file.assert_called_with("/tmp/cpl-tput.log", "w")
        mock_file.return_value.write.assert_called_with("-1")

    @mock.patch("CIME.baselines.get_throughput")
    def test_write_baseline_tput(self, get_throughput):
        get_throughput.return_value = 200

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            baselines.write_baseline_tput("/tmp", "/tmp/cpl.log")

        mock_file.assert_called_with("/tmp/cpl-tput.log", "w")
        mock_file.return_value.write.assert_called_with("200")

    @mock.patch("CIME.baselines.get_throughput")
    @mock.patch("CIME.baselines.read_baseline_tput")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_throughput_no_baseline_file(self, get_latest_cpl_logs, read_baseline_tput, get_throughput):
        read_baseline_tput.side_effect = FileNotFoundError

        get_throughput.return_value = 504

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_throughput(case)

        assert below_tolerance is None
        assert diff == None
        assert tolerance == 0.05
        assert baseline == None
        assert current == None

    @mock.patch("CIME.baselines.get_throughput")
    @mock.patch("CIME.baselines.read_baseline_tput")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_throughput_no_baseline(self, get_latest_cpl_logs, read_baseline_tput, get_throughput):
        read_baseline_tput.return_value = None

        get_throughput.return_value = 504

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_throughput(case)

        assert below_tolerance is None
        assert diff == None
        assert tolerance == 0.05
        assert baseline == None
        assert current == 504

    @mock.patch("CIME.baselines.get_throughput")
    @mock.patch("CIME.baselines.read_baseline_tput")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_throughput_no_tolerance(self, get_latest_cpl_logs, read_baseline_tput, get_throughput):
        read_baseline_tput.return_value = 500

        get_throughput.return_value = 504

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                None
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_throughput(case)

        assert below_tolerance
        assert diff == -0.008
        assert tolerance == 0.1
        assert baseline == 500
        assert current == 504

    @mock.patch("CIME.baselines.get_throughput")
    @mock.patch("CIME.baselines.read_baseline_tput")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_throughput(self, get_latest_cpl_logs, read_baseline_tput, get_throughput):
        read_baseline_tput.return_value = 500

        get_throughput.return_value = 504

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_throughput(case)

        assert below_tolerance
        assert diff == -0.008
        assert tolerance == 0.05
        assert baseline == 500
        assert current == 504

    @mock.patch("CIME.baselines.get_mem_usage")
    @mock.patch("CIME.baselines.read_baseline_mem")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_memory_no_baseline(self, get_latest_cpl_logs, read_baseline_mem, get_mem_usage):
        read_baseline_mem.return_value = None

        get_mem_usage.return_value = [
            (1, 1000.0),
            (2, 1001.0),
            (3, 1002.0),
            (4, 1003.0),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_memory(case)

        assert below_tolerance
        assert diff == 0.0
        assert tolerance == 0.05
        assert baseline == 0.0
        assert current == 1003.0

    @mock.patch("CIME.baselines.get_mem_usage")
    @mock.patch("CIME.baselines.read_baseline_mem")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_memory_not_enough_samples(self, get_latest_cpl_logs, read_baseline_mem, get_mem_usage):
        read_baseline_mem.return_value = 1000.0

        get_mem_usage.return_value = [
            (1, 1000.0),
            (2, 1001.0),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_memory(case)

        assert below_tolerance is None
        assert diff == None
        assert tolerance == 0.05
        assert baseline == 1000.0
        assert current == None

    @mock.patch("CIME.baselines.get_mem_usage")
    @mock.patch("CIME.baselines.read_baseline_mem")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_memory_no_baseline_file(self, get_latest_cpl_logs, read_baseline_mem, get_mem_usage):
        read_baseline_mem.side_effect = FileNotFoundError

        get_mem_usage.return_value = [
            (1, 1000.0),
            (2, 1001.0),
            (3, 1002.0),
            (4, 1003.0),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance,  baseline, current = baselines.compare_memory(case)

        assert below_tolerance is None
        assert diff == None
        assert tolerance == 0.05
        assert baseline == None
        assert current == None

    @mock.patch("CIME.baselines.get_mem_usage")
    @mock.patch("CIME.baselines.read_baseline_mem")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_memory_no_tolerance(self, get_latest_cpl_logs, read_baseline_mem, get_mem_usage):
        read_baseline_mem.return_value = 1000.0

        get_mem_usage.return_value = [
            (1, 1000.0),
            (2, 1001.0),
            (3, 1002.0),
            (4, 1003.0),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                None,
            )

            below_tolerance, diff, tolerance, baseline, current = baselines.compare_memory(case)

        assert below_tolerance
        assert diff == 0.003
        assert tolerance == 0.1
        assert baseline == 1000.0
        assert current == 1003.0

    @mock.patch("CIME.baselines.get_mem_usage")
    @mock.patch("CIME.baselines.read_baseline_mem")
    @mock.patch("CIME.baselines.get_latest_cpl_logs")
    def test_compare_memory(self, get_latest_cpl_logs, read_baseline_mem, get_mem_usage):
        read_baseline_mem.return_value = 1000.0

        get_mem_usage.return_value = [
            (1, 1000.0),
            (2, 1001.0),
            (3, 1002.0),
            (4, 1003.0),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            case, _, _, baseline_root = create_mock_case(tempdir, get_latest_cpl_logs)

            case.get_value.side_effect = (
                str(baseline_root),
                "master/ERIO.ne30_g16_rx1.A.docker_gnu",
                0.05,
            )

            below_tolerance, diff, tolerance, baseline, current = baselines.compare_memory(case)

        assert below_tolerance
        assert diff == 0.003
        assert tolerance == 0.05
        assert baseline == 1000.0
        assert current == 1003.0

    def test_get_latest_cpl_logs_found_multiple(self):
        with tempfile.TemporaryDirectory() as tempdir:
            run_dir = Path(tempdir) / "run"
            run_dir.mkdir(parents=True, exist_ok=False)

            cpl_log_path = run_dir / "cpl.log.gz"
            cpl_log_path.touch()

            cpl_log_2_path = run_dir / "cpl-2023-01-01.log.gz"
            cpl_log_2_path.touch()

            case = mock.MagicMock()
            case.get_value.side_effect = (
                str(run_dir),
                "mct",
            )

            latest_cpl_logs = baselines.get_latest_cpl_logs(case)

        assert len(latest_cpl_logs) == 2
        assert sorted(latest_cpl_logs) == sorted([str(cpl_log_path), str(cpl_log_2_path)])

    def test_get_latest_cpl_logs_found_single(self):
        with tempfile.TemporaryDirectory() as tempdir:
            run_dir = Path(tempdir) / "run"
            run_dir.mkdir(parents=True, exist_ok=False)

            cpl_log_path = run_dir / "cpl.log.gz"
            cpl_log_path.touch()

            case = mock.MagicMock()
            case.get_value.side_effect = (
                str(run_dir),
                "mct",
            )

            latest_cpl_logs = baselines.get_latest_cpl_logs(case)

        assert len(latest_cpl_logs) == 1
        assert latest_cpl_logs[0] == str(cpl_log_path)

    def test_get_latest_cpl_logs(self):
        case = mock.MagicMock()
        case.get_value.side_effect = (
            f"/tmp/run",
            "mct",
        )

        latest_cpl_logs = baselines.get_latest_cpl_logs(case)

        assert len(latest_cpl_logs) == 0
