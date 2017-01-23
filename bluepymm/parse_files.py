"""Create sqlite database"""

from __future__ import print_function

"""Some Code based on BrainBuilder and morph repair code"""

import os
import json
import collections
import pandas
import sh
import re

import xml.etree.ElementTree

import bluepymm


def get_emodel_dicts(
        emodels_repo,
        emodels_githash,
        final_json_path,
        emodel_etype_map_path,
        tmp_opt_repo,
        continu=False):
    """Get dictionary with final emodels"""

    if not continu:
        print('Cloning emodels repo in %s' % tmp_opt_repo)
        sh.git(  # pylint: disable=E1121
            'clone',
            '%s' %
            emodels_repo,
            tmp_opt_repo)

        with bluepymm.tools.cd(tmp_opt_repo):
            sh.git('checkout', '%s' % emodels_githash)  # pylint: disable=E1121

    final_dict = json.loads(
        open(
            os.path.join(
                tmp_opt_repo,
                final_json_path)).read())

    emodel_etype_map = json.loads(
        open(
            os.path.join(
                tmp_opt_repo,
                emodel_etype_map_path)).read())

    opt_dir = os.path.dirname(os.path.join(tmp_opt_repo, final_json_path))
    return final_dict, emodel_etype_map, opt_dir


def _parse_recipe(recipe_filename):
    """parse a BBP recipe and return the corresponding etree"""

    parser = xml.etree.ElementTree.XMLParser()
    parser.entity = collections.defaultdict(lambda: '')
    return xml.etree.ElementTree.parse(recipe_filename, parser=parser)


def read_mm_recipe(recipe_filename):
    """Take a BBP builder recipe and return possible me combinations"""
    recipe_tree = _parse_recipe(recipe_filename)

    def read_records():
        '''parse each neuron posibility in the recipe'''

        for layer in recipe_tree.findall('NeuronTypes')[0].getchildren():

            for structural_type in layer.getchildren():
                if structural_type.tag == 'StructuralType':

                    for electro_type in structural_type.getchildren():
                        if electro_type.tag == 'ElectroType':

                            percentage = (
                                float(
                                    structural_type.attrib['percentage']) /
                                100 *
                                float(
                                    electro_type.attrib['percentage']) /
                                100 *
                                float(
                                    layer.attrib['percentage']) /
                                100)

                            if percentage == 0.0:
                                raise Exception(
                                    'Found a percentage of 0.0 '
                                    'in recipe, script cant to '
                                    'handle this case')

                            yield (int(layer.attrib['id']),
                                   structural_type.attrib['id'],
                                   electro_type.attrib['id'])

    return pandas.DataFrame(
        read_records(),
        columns=[
            'layer',
            'fullmtype',
            'etype'])


def xmlmorphinfo_from_xml(xml_morph):
    '''extracts properties from a neurondb.xml <morphology> stanza'''
    name = xml_morph.findtext('name')
    mtype = xml_morph.findtext('mtype')
    msubtype = xml_morph.findtext('msubtype')
    fullmtype = '%s:%s' % (mtype, msubtype) if msubtype != '' else mtype
    layer = int(xml_morph.findtext('layer'))
    return (name, fullmtype, mtype, msubtype, layer)


def extract_morphinfo_from_xml(root, wanted=None):
    '''returns a generator that contains all the morphologies from `root`'''
    for morph in root.findall('.//morphology'):
        morph = xmlmorphinfo_from_xml(morph)
        yield morph


def read_mtype_morph_map(neurondb_xml_filename):
    """Read neurondb.xml"""

    xml_tree = _parse_recipe(neurondb_xml_filename)

    mtype_morph_map = pandas.DataFrame(
        extract_morphinfo_from_xml(xml_tree.getroot()), columns=[
            'morph_name', 'fullmtype', 'mtype', 'submtype', 'layer'])

    return mtype_morph_map


def extract_emodel_etype_json(json_filename):
    """Read emodel etype json"""

    with open(json_filename) as json_file:
        emodel_etype_dict = json.loads(json_file.read())

    for emodel, etype_dict in emodel_etype_dict.items():
        for etype, layers in etype_dict.items():
            for layer in layers:
                yield (emodel, etype, layer)


def convert_emodel_etype_map(emodel_etype_map, fullmtypes, etypes):
    """Resolve regex's in emodel etype map"""

    return_df = pandas.DataFrame()
    morph_name_regexs = {}
    for original_emodel in emodel_etype_map:
        emodel = emodel_etype_map[original_emodel]['mm_recipe']
        layers = emodel_etype_map[original_emodel]['layer']

        if 'etype' in emodel_etype_map[original_emodel]:
            etype_regex = re.compile(emodel_etype_map[original_emodel]['etype'])
        else:
            etype_regex = re.compile('.*')

        if 'mtype' in emodel_etype_map[original_emodel]:
            mtype_regex = re.compile(
                emodel_etype_map[original_emodel]['mtype'])
        else:
            mtype_regex = re.compile('.*')

        if 'morph_name' in emodel_etype_map[original_emodel]:
            morph_name_regex = emodel_etype_map[original_emodel]['morph_name']
        else:
            morph_name_regex = '.*'

        if morph_name_regex not in morph_name_regexs:
            morph_name_regexs[morph_name_regex] = re.compile(morph_name_regex)

        for layer in layers:
            for fullmtype in fullmtypes:
                if mtype_regex.match(fullmtype):
                    for etype in etypes:
                        if etype_regex.match(etype):
                            return_df = return_df.append(
                                {'emodel': emodel,
                                 'layer': layer,
                                 'fullmtype': fullmtype,
                                 'etype': etype,
                                 'morph_regex':
                                    morph_name_regexs[morph_name_regex],
                                 'original_emodel':
                                 original_emodel},
                                ignore_index=True)

    return return_df
