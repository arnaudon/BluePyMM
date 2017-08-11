"""Test bluepymm/select_combos"""

from __future__ import print_function

"""
Copyright (c) 2017, EPFL/Blue Brain Project

 This file is part of BluePyMM <https://github.com/BlueBrain/BluePyMM>

 This library is free software; you can redistribute it and/or modify it under
 the terms of the GNU Lesser General Public License version 3.0 as published
 by the Free Software Foundation.

 This library is distributed in the hope that it will be useful, but WITHOUT
 ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
 details.

 You should have received a copy of the GNU Lesser General Public License
 along with this library; if not, write to the Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import os
import shutil
import filecmp

import nose.tools as nt

from bluepymm import tools, select_combos

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(BASE_DIR, 'examples/simple1')
TMP_DIR = os.path.join(BASE_DIR, 'tmp/select_combos')


def _verify_output(benchmark_dir, output_dir):
    """Helper function to verify output of combination selection"""
    files = ['extneurondb.dat', 'mecombo_emodel.tsv']
    matches = filecmp.cmpfiles(benchmark_dir, output_dir, files)
    if len(matches[0]) != len(files):
        print('Mismatch in files: {}'.format(matches[1]))
    nt.assert_equal(len(matches[0]), len(files))


def _config_select_combos(config_template_path, tmp_dir):
    """Helper function to prepare input data for select_combos"""
    # copy input data
    shutil.copy('output_expected/scores.sqlite', tmp_dir)

    # set configuration dict
    config = tools.load_json(config_template_path)

    # load, edit, and save run_combos config json
    run_config = tools.load_json(config['run_config'])
    run_config['scores_db'] = os.path.join(tmp_dir, 'scores.sqlite')
    run_config_filename = os.path.basename(config['run_config'])
    run_config_path = tools.write_json(tmp_dir, run_config_filename,
                                       run_config)

    # edit and save select_combos config json
    config['run_config'] = run_config_path
    config['report_dir'] = os.path.join(tmp_dir, 'report')
    config['output_dir'] = os.path.join(tmp_dir, 'output')
    return config


def _test_select_combos(test_data_dir, tmp_dir, config_template_path,
                        benchmark_dir):
    """Helper function to perform functional test of select_combos"""
    with tools.cd(test_data_dir):
        # prepare input data
        config = _config_select_combos(config_template_path, tmp_dir)

        # run combination selection
        select_combos.main.select_combos_from_conf(config)

        # verify output
        _verify_output(benchmark_dir, config['output_dir'])


def test_select_combos():
    """bluepymm.select_combos: test select_combos based on example simple1"""
    config_template_path = 'simple1_conf_select.json'
    benchmark_dir = 'output_megate_expected'
    tmp_dir = os.path.join(TMP_DIR, 'test_select_combos')
    tools.makedirs(tmp_dir)

    _test_select_combos(TEST_DATA_DIR, tmp_dir, config_template_path,
                        benchmark_dir)


def test_select_combos_2():
    """bluepymm.select_combos: test select_combos based on example simple1 bis
    """
    config_template_path = 'simple1_conf_select_2.json'
    benchmark_dir = 'output_megate_expected'
    tmp_dir = os.path.join(TMP_DIR, 'test_select_combos_2')
    tools.makedirs(tmp_dir)

    _test_select_combos(TEST_DATA_DIR, tmp_dir, config_template_path,
                        benchmark_dir)
