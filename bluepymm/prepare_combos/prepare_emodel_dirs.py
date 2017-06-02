"""Python Model Management"""

# Copyright BBP/EPFL 2017; All rights reserved.
# Do not distribute without further notice.

# pylint: disable=C0325, W0223, R0914, E1121, E1123

import sys
import os
import sh
import shutil
import traceback
import multiprocessing
import tarfile

from bluepymm import tools


def check_emodels_in_repo(conf_dict):
    """Check whether input e-models are organized in branches of a repository.

    Args:
        conf_dict: A dict with either the key "emodels_repo" or the key
            "emodels_dir".

    Returns:
        True if the input e-models are organized in separate branches of a
        git repository, false if the e-models are organized into separate
        subdirectories.

    Raises:
        ValueError: if both or none of the keys "emodels_repo" and
            "emodels_dir" are present.

    TODO: replace "emodels_repo" and "emodels_dir" by "emodels_input_type" and
        "emodels_path" or similar.
    """
    if 'emodels_repo' in conf_dict and 'emodels_dir' in conf_dict:
        raise ValueError("Impossible to specify both 'emodels_repo' and"
                         " 'emodels_dir' in configuration file")
    elif 'emodels_repo' in conf_dict:
        emodels_in_repo = True
    elif 'emodels_dir' in conf_dict:
        emodels_in_repo = False
    else:
        raise ValueError("Need to specify either 'emodels_dir' or"
                         " 'emodels_repo' in configuration file")
    return emodels_in_repo


def convert_emodel_input(emodels_in_repo, conf_dict, continu):
    """Convert e-model input to BluePyMM file structure and return path to that
    structure.

    Args:
        emodels_in_repo: True if the input e-models are organized in separate
            branches of a git repository, false if the e-models are organized
            into separate subdirectories.
        conf_dict: A dict with e-model input configuration.

    Returns:
        Path to BluePyMM file structure.
    """
    tmp_emodels_dir = os.path.abspath(os.path.join(conf_dict['tmp_dir'],
                                                   'emodels_repo'))
    if not continu:
        if emodels_in_repo:
            print('Cloning input e-models repository in %s' % tmp_emodels_dir)
            sh.git('clone', conf_dict['emodels_repo'], tmp_emodels_dir)

            with tools.cd(tmp_emodels_dir):
                sh.git('checkout', conf_dict['emodels_githash'])
        else:
            shutil.copytree(conf_dict['emodels_dir'], tmp_emodels_dir)
    return tmp_emodels_dir


def get_emodel_dicts(emodels_dir, final_json_path, emodel_etype_map_path):
    """Read and return detailed e-model information.

    Args:
        emodels_dir: Path to BluePyMM file structure.
        final_json_path: Path to final e-model map, relative to
            `emodels_dir`.
        emodel_etype_map_path: Path to e-model e-type map, relative to
            `emodels_dir`.

    Returns:
        (string, dict, dict)-tuple with:
            - final e-model map,
            - e-model e-type map,
            - name of directory containing final e-model map.
    """
    final_dict_path = os.path.join(emodels_dir, final_json_path)
    final_dict = tools.load_json(final_dict_path)
    e_map_path = os.path.join(emodels_dir, emodel_etype_map_path)
    emodel_etype_map = tools.load_json(e_map_path)
    dict_dir = os.path.dirname(final_dict_path)
    return final_dict, emodel_etype_map, dict_dir


def create_and_write_hoc_file(emodel, emodel_dir, hoc_dir, emodel_params,
                              template, template_dir=None, morph_path=None,
                              model_name=None):
    """Create .hoc code for a given e-model based on code from
    '<emodel_dir>/setup', e-model parameters and a given template, and write
    out the result to a file named <hoc_dir>/<model_name or emodel>.hoc.

    Args:
        emodel: e-model name
        emodel_dir: the directory containing a module 'setup', which describes
            the e-model
        hoc_dir: the directory to which the resulting .hoc file will be written
                 out.
        emodel_params: a dict with e-model parameters
        template: template file used for the creation of the .hoc file
        template_dir: directory that contains the template. If None, a template
                      provided by BluePyOpt is used. Default is None.
        morph_path: path to morphology file, used to overwrite the original
                    morphology of an e-model. Default is None.
        model_name: used to name the .hoc file. If None, the e-model name is
                    used. Default is None.
    """
    setup = tools.load_module('setup', emodel_dir)

    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        try:
            sys.stdout = devnull
            evaluator = setup.evaluator.create(emodel)
            # set some template variables
            if morph_path is not None:
                evaluator.cell_model.morphology.morphology_path = morph_path
            if model_name is not None:
                evaluator.cell_model.name = model_name.replace("-", "_")
                evaluator.cell_model.check_name()
        finally:
            sys.stdout = old_stdout

    # create hoc code
    hoc = evaluator.cell_model.create_hoc(emodel_params, template=template,
                                          template_dir=template_dir)

    # write out result
    hoc_file_name = '{}.hoc'.format(model_name or emodel)
    emodel_hoc_path = os.path.join(hoc_dir, hoc_file_name)
    with open(emodel_hoc_path, 'w') as emodel_hoc_file:
        emodel_hoc_file.write(hoc)


def prepare_emodel_dir(input):
    """Prepare emodel dir"""

    original_emodel, emodel, emodel_dict, emodels_dir, \
        opt_dir, emodels_hoc_dir, emodels_in_repo, continu = input

    try:
        emodel_dirs = {}

        print('Preparing: %s' % emodel)
        emodel_dir = os.path.join(emodels_dir, emodel)
        emodel_dirs[emodel] = emodel_dir
        emodel_dirs[original_emodel] = emodel_dir

        if not continu:
            tar_filename = os.path.abspath(
                os.path.join(
                    emodels_dir,
                    '%s.tar' %
                    emodel))

            if 'main_path' in emodel_dict:
                main_path = emodel_dict['main_path']
            else:
                main_path = '.'

            if emodels_in_repo:
                with tools.cd(os.path.join(opt_dir, main_path)):
                    sh.git(
                        'archive',
                        '--format=tar',
                        '--prefix=%s/' % emodel,
                        'origin/%s' % emodel_dict['branch'],
                        _out=tar_filename)
            else:
                with tools.cd(os.path.join(opt_dir, main_path)):
                    with tarfile.open(tar_filename, 'w') as tar_file:
                        tar_file.add('.', arcname=emodel)

            with tools.cd(emodels_dir):
                sh.tar('xf', tar_filename)

                with tools.cd(emodel):
                    print('Compiling mechanisms ...')
                    sh.nrnivmodl('mechanisms')

                    create_and_write_hoc_file(
                        emodel, emodel_dir, emodels_hoc_dir,
                        emodel_dict['params'],
                        'cell_template.jinja2')

    except:
        raise Exception(
            "".join(traceback.format_exception(*sys.exc_info())))

    return emodel_dirs


def prepare_emodel_dirs(
        final_dict,
        emodel_etype_map,
        emodels_dir,
        opt_dir,
        emodels_hoc_dir,
        emodels_in_repo,
        continu=False):
    """Prepare the directories for the emodels"""

    tools.makedirs(emodels_dir)
    tools.makedirs(emodels_hoc_dir)

    emodel_dirs = {}

    arg_list = []
    for original_emodel in emodel_etype_map:
        emodel = emodel_etype_map[original_emodel]['mm_recipe']
        emodel_dict = final_dict[original_emodel]
        arg_list.append(
            (original_emodel,
             emodel,
             emodel_dict,
             emodels_dir,
             opt_dir,
             emodels_hoc_dir,
             emodels_in_repo,
             continu))

    print('Parallelising preparation of emodel dirs')
    pool = multiprocessing.Pool(maxtasksperchild=1)
    for emodel_dir_dict in pool.map(prepare_emodel_dir, arg_list, chunksize=1):
        for emodel, emodel_dir in emodel_dir_dict.items():
            emodel_dirs[emodel] = emodel_dir

    return emodel_dirs
