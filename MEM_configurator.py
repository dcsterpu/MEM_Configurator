from lxml import etree
import argparse
import logging
import os
import copy
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from xml.dom.minidom import parseString
import time
import psutil


def arg_parse(parser):
    parser.add_argument("-config", action="store_const", const="-config")
    parser.add_argument("input_configuration_file", help="configuration file location")


def validate_xml_with_xsd(path_xsd, path_xml, logger):
    # load xsd file
    xmlschema_xsd = etree.parse(path_xsd)
    xmlschema = etree.XMLSchema(xmlschema_xsd)
    # validate xml file
    xmldoc = etree.parse(path_xml)
    if xmlschema.validate(xmldoc) is not True:
        logger.warning('The file: ' + path_xml + ' is NOT valid with the provided xsd schema')
    else:
        logger.info('The file: ' + path_xml + ' is valid with the provided xsd schema')


def remove_duplicates(list_to_check):
    found = set()
    for item in list_to_check:
        if item['NAME'] not in found:
            yield item
            found.add(item['NAME'])


def check_if_xml_is_wellformed(file):
    parser = make_parser()
    parser.setContentHandler(ContentHandler())
    parser.parse(file)


def new_prettify(elem):
    rough_string = etree.tostring(elem, pretty_print=True)
    reparsed = parseString(rough_string)
    return '\n'.join([line for line in reparsed.toprettyxml(indent=' '*4).split('\n') if line.strip()])


def main():
    # parsing the command line arguments
    parser = argparse.ArgumentParser()
    arg_parse(parser)
    args = parser.parse_args()
    config_file = args.input_configuration_file
    config_file = config_file.replace("\\", "/")
    # get all configuration parameters
    recursive_path_arxml = []
    simple_path_arxml = []
    recursive_path_config = []
    simple_path_config = []
    output_path = ''
    report_path = ''
    tree = etree.parse(config_file)
    root = tree.getroot()
    directories = root.findall(".//DIR")
    for element in directories:
        if element.getparent().tag == "ARXML":
            if element.attrib['RECURSIVE'] == "true":
                recursive_path_arxml.append(element.text)
            else:
                simple_path_arxml.append(element.text)
        elif element.getparent().tag == "CONFIG":
            if element.attrib['RECURSIVE'] == "true":
                recursive_path_config.append(element.text)
            else:
                simple_path_config.append(element.text)
        elif element.getparent().tag == "EPC":
            output_path = element.text
        elif element.getparent().tag == "REPORT":
            report_path = element.text
    xsds = root.findall(".//XSD")
    xsd_arxml = ""
    xsd_config = ""
    for elem in xsds:
        if elem.getparent().tag == "ARXML":
            xsd_arxml = elem.text
        elif elem.getparent().tag == "CONFIG":
            xsd_config = elem.text
    # logger creation and setting
    logger = logging.getLogger('result')
    hdlr = logging.FileHandler(report_path + '/result.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    open(report_path + '/result.log', 'w').close()
    retrieve_data(recursive_path_arxml, simple_path_arxml, recursive_path_config, simple_path_config, xsd_arxml, xsd_config, output_path, logger)


def retrieve_data(recursive_arxml, simple_arxml, recursive_config, simple_config, xsd_arxml, xsd_config, output_path, logger):
    blocks = []
    subblocks = []
    profiles = []
    nvm_blocks = []
    arxml_interfaces = []
    arxml_data_types = []
    arxml_base_types = []
    NSMAP = {None: 'http://autosar.org/schema/r4.0', "xsi": 'http://www.w3.org/2001/XMLSchema-instance'}
    attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
    # parse the arxml files and get the necessary data
    for each_path in recursive_arxml:
        for directory, directories, files in os.walk(each_path):
            for file in files:
                if file.endswith('.arxml'):
                    fullname = os.path.join(directory, file)
                    try:
                        check_if_xml_is_wellformed(fullname)
                        logger.info('The file: ' + fullname + ' is well-formed')
                    except Exception as e:
                        logger.error('The file: ' + fullname + ' is not well-formed: ' + str(e))
                        return
                    validate_xml_with_xsd(xsd_arxml, fullname, logger)
                    tree = etree.parse(fullname)
                    root = tree.getroot()
                    sender_receiver_interface = root.findall(".//{http://autosar.org/schema/r4.0}SENDER-RECEIVER-INTERFACE")
                    for elem in sender_receiver_interface:
                        obj_elem = {}
                        variable_data_prototype = []
                        obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                        obj_elem['ROOT'] = elem.getparent().getparent().getchildren()[0].text
                        data_elements = elem.findall(".//{http://autosar.org/schema/r4.0}VARIABLE-DATA-PROTOTYPE")
                        for data_prototype in data_elements:
                            obj_variable = {}
                            obj_variable['NAME'] = data_prototype.find('.//{http://autosar.org/schema/r4.0}SHORT-NAME').text
                            obj_variable['TYPE'] = data_prototype.find('.//{http://autosar.org/schema/r4.0}TYPE-TREF').text
                            obj_variable['SW-BASE-TYPE'] = None
                            obj_variable['SIZE'] = None
                            variable_data_prototype.append(obj_variable)
                        obj_elem['DATA-ELEMENTS'] = variable_data_prototype
                        obj_elem['SIZE'] = None
                        arxml_interfaces.append(obj_elem)
                    implementation_data_types = root.findall(".//{http://autosar.org/schema/r4.0}IMPLEMENTATION-DATA-TYPE")
                    for elem in implementation_data_types:
                        obj_elem = {}
                        obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                        if elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-REF") is not None:
                            obj_elem['BASE-TYPE'] = elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-REF").text
                        else:
                            continue
                        arxml_data_types.append(obj_elem)
                    base_types = root.findall(".//{http://autosar.org/schema/r4.0}SW-BASE-TYPE")
                    for elem in base_types:
                        obj_elem = {}
                        obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                        obj_elem['PACKAGE'] = elem.getparent().getparent().getchildren()[0].text
                        obj_elem['SIZE'] = elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-SIZE").text
                        arxml_base_types.append(obj_elem)
    for each_path in simple_arxml:
        for file in os.listdir(each_path):
            if file.endswith('.arxml'):
                fullname = os.path.join(each_path, file)
                try:
                    check_if_xml_is_wellformed(fullname)
                    logger.info(' The file ' + fullname + ' is well-formed')
                except Exception as e:
                    logger.error(' The file ' + fullname + ' is not well-formed: ' + str(e))
                    return
                validate_xml_with_xsd(xsd_arxml, fullname, logger)
                tree = etree.parse(fullname)
                root = tree.getroot()
                sender_receiver_interface = root.findall(".//{http://autosar.org/schema/r4.0}SENDER-RECEIVER-INTERFACE")
                for elem in sender_receiver_interface:
                    obj_elem = {}
                    variable_data_prototype = []
                    obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                    obj_elem['ROOT'] = elem.getparent().getparent().getchildren()[0].text
                    data_elements = elem.findall(".//{http://autosar.org/schema/r4.0}VARIABLE-DATA-PROTOTYPE")
                    for data_prototype in data_elements:
                        obj_variable = {}
                        obj_variable['NAME'] = data_prototype.find('.//{http://autosar.org/schema/r4.0}SHORT-NAME').text
                        obj_variable['TYPE'] = data_prototype.find('.//{http://autosar.org/schema/r4.0}TYPE-TREF').text
                        obj_variable['SW-BASE-TYPE'] = None
                        obj_variable['SIZE'] = None
                        variable_data_prototype.append(obj_variable)
                    obj_elem['DATA-ELEMENTS'] = variable_data_prototype
                    obj_elem['SIZE'] = None
                    arxml_interfaces.append(obj_elem)
                implementation_data_types = root.findall(".//{http://autosar.org/schema/r4.0}IMPLEMENTATION-DATA-TYPE")
                for elem in implementation_data_types:
                    obj_elem = {}
                    obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                    if elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-REF") is not None:
                        obj_elem['BASE-TYPE'] = elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-REF").text
                    else:
                        continue
                    arxml_data_types.append(obj_elem)
                base_types = root.findall(".//{http://autosar.org/schema/r4.0}SW-BASE-TYPE")
                for elem in base_types:
                    obj_elem = {}
                    obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                    obj_elem['PACKAGE'] = elem.getparent().getparent().getchildren()[0].text
                    obj_elem['SIZE'] = elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-SIZE").text
                    arxml_base_types.append(obj_elem)
    # parse the config files and retrieve the necesary information
    for each_path in recursive_config:
        for directory, directories, files in os.walk(each_path):
            for file in files:
                if file.endswith('.xml'):
                    fullname = os.path.join(directory, file)
                    try:
                        check_if_xml_is_wellformed(fullname)
                        logger.info('The file: ' + fullname + ' is well-formed')
                    except Exception as e:
                        logger.error('The file: ' + fullname + ' is not well-formed: ' + str(e))
                        return
                    validate_xml_with_xsd(xsd_config, fullname, logger)
                    tree = etree.parse(fullname)
                    root = tree.getroot()
                    block = root.findall(".//BLOCK")
                    for elem in block:
                        obj_block = {}
                        interfaces = []
                        obj_block['NAME'] = elem.find('SHORT-NAME').text
                        obj_block['TYPE'] = elem.find('TYPE').text
                        # implementing requirement TRS.SYSDESC.CHECK.002
                        if elem.find('PROFIL-REF') is not None:
                            if elem.find('PROFIL-REF').text != '':
                                obj_block['PROFILE'] = elem.find('PROFIL-REF').text
                            else:
                                logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                                try:
                                    os.remove(output_path + '/NvM.epc')
                                    os.remove(output_path + '/NvDM.epc')
                                except OSError:
                                    pass
                                return
                        else:
                            logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                        if elem.find('WRITE-TIMEOUT') is not None:
                            obj_block['TIMEOUT'] = elem.find('WRITE-TIMEOUT').text
                        else:
                            obj_block['TIMEOUT'] = None
                        if elem.find('RESPECT-MAPPING') is not None:
                            obj_block['MAPPING'] = elem.find('RESPECT-MAPPING').text
                        else:
                            obj_block['MAPPING'] = None
                        if elem.find('SDF') is not None:
                            obj_block['SDF'] = elem.find('SDF').text
                        else:
                            obj_block['SDF'] = None
                        obj_block['DEVICE'] = None
                        sender_receiver_interfaces = elem.findall('.//SENDER-RECEIVER-INTERFACE-REF')
                        for element in sender_receiver_interfaces:
                            obj_interface = {}
                            obj_interface['NAME'] = element.text
                            obj_interface['SIZE'] = 0
                            obj_interface['SW-BASE-TYPE'] = None
                            obj_interface['DATA-PROTOTYPE'] = None
                            interfaces.append(obj_interface)
                        obj_block['INTERFACE'] = interfaces
                        obj_block['MAX-SIZE'] = None
                        blocks.append(obj_block)
                    profile = root.findall(".//PROFILE")
                    for elem in profile:
                        obj_profile = {}
                        params = []
                        obj_profile['NAME'] = elem.find('SHORT-NAME').text
                        obj_profile['MANAGEMENT'] = elem.find('MANAGEMENT').text
                        obj_profile['DURABILITY'] = elem.find('DURABILITY').text
                        obj_profile['MAX-SIZE'] = elem.find('BLOCK-SIZE-MAX').text
                        obj_profile['SAFETY'] = elem.find('SAFETY').text
                        obj_profile['DEVICE'] = elem.find('DEVICE').text
                        obj_profile['WRITING-NUMBER'] = elem.find('WRITING-NUMBER').text
                        param = elem.findall('.//PARAM')
                        for element in param:
                            obj = {}
                            obj['TYPE'] = element.attrib['DEST']
                            obj['VALUE'] = element.text
                            params.append(obj)
                        obj_profile['PARAM'] = params
                        profiles.append(obj_profile)
    for each_path in simple_config:
        for file in os.listdir(each_path):
            if file.endswith('.xml'):
                fullname = os.path.join(each_path, file)
                try:
                    check_if_xml_is_wellformed(fullname)
                    logger.info(' The file ' + fullname + ' is well-formed')
                except Exception as e:
                    logger.error(' The file ' + fullname + ' is not well-formed: ' + str(e))
                    return
                validate_xml_with_xsd(xsd_config, fullname, logger)
                tree = etree.parse(fullname)
                root = tree.getroot()
                block = root.findall(".//BLOCK")
                for elem in block:
                    obj_block = {}
                    interfaces = []
                    obj_block['NAME'] = elem.find('SHORT-NAME').text
                    obj_block['TYPE'] = elem.find('TYPE').text
                    # implementing requirement TRS.SYSDESC.CHECK.002
                    if elem.find('PROFIL-REF') is not None:
                        if elem.find('PROFIL-REF').text != '':
                            obj_block['PROFILE'] = elem.find('PROFIL-REF').text
                        else:
                            logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    else:
                        logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                        try:
                            os.remove(output_path + '/NvM.epc')
                            os.remove(output_path + '/NvDM.epc')
                        except OSError:
                            pass
                        return
                    if elem.find('WRITE-TIMEOUT') is not None:
                        obj_block['TIMEOUT'] = elem.find('WRITE-TIMEOUT').text
                    else:
                        obj_block['TIMEOUT'] = None
                    if elem.find('RESPECT-MAPPING') is not None:
                        obj_block['MAPPING'] = elem.find('RESPECT-MAPPING').text
                    else:
                        obj_block['MAPPING'] = None
                    if elem.find('SDF') is not None:
                        obj_block['SDF'] = elem.find('SDF').text
                    else:
                        obj_block['SDF'] = None
                    obj_block['DEVICE'] = None
                    sender_receiver_interfaces = elem.findall('.//SENDER-RECEIVER-INTERFACE-REF')
                    for element in sender_receiver_interfaces:
                        obj_interface = {}
                        obj_interface['NAME'] = element.text
                        obj_interface['SIZE'] = 0
                        obj_interface['SW-BASE-TYPE'] = None
                        obj_interface['DATA-PROTOTYPE'] = None
                        interfaces.append(obj_interface)
                    obj_block['INTERFACE'] = interfaces
                    obj_block['MAX-SIZE'] = None
                    blocks.append(obj_block)
                profile = root.findall(".//PROFILE")
                for elem in profile:
                    obj_profile = {}
                    params = []
                    obj_profile['NAME'] = elem.find('SHORT-NAME').text
                    obj_profile['MANAGEMENT'] = elem.find('MANAGEMENT').text
                    obj_profile['DURABILITY'] = elem.find('DURABILITY').text
                    obj_profile['MAX-SIZE'] = elem.find('BLOCK-SIZE-MAX').text
                    obj_profile['SAFETY'] = elem.find('SAFETY').text
                    obj_profile['DEVICE'] = elem.find('DEVICE').text
                    obj_profile['WRITING-NUMBER'] = elem.find('WRITING-NUMBER').text
                    param = elem.findall('.//PARAM')
                    for element in param:
                        obj = {}
                        obj['TYPE'] = element.attrib['DEST']
                        obj['VALUE'] = element.text
                        params.append(obj)
                    obj_profile['PARAM'] = params
                    profiles.append(obj_profile)
    # implement TRS.SYSDESC.CHECK.001
    for index1 in range(len(blocks)):
        for index2 in range(len(blocks)):
            if index1 != index2:
                if blocks[index1]['NAME'] == blocks[index2]['NAME']:
                    if blocks[index1]['PROFILE'] != blocks[index2]['PROFILE']:
                        logger.error('Different profiles defined for same block: ' + blocks[index1]['NAME'])
                        try:
                            os.remove(output_path + '/NvM.epc')
                            os.remove(output_path + '/NvDM.epc')
                        except OSError:
                            pass
                        return
                    elif blocks[index1]['TIMEOUT'] != blocks[index2]['TIMEOUT']:
                        logger.error('Different write timeout defined for same block: ' + blocks[index1]['NAME'])
                        try:
                            os.remove(output_path + '/NvM.epc')
                            os.remove(output_path + '/NvDM.epc')
                        except OSError:
                            pass
                        return
                    elif blocks[index1]['MAPPING'] != blocks[index2]['MAPPING']:
                        logger.error('Different mapping defined for same block: ' + blocks[index1]['NAME'])
                        try:
                            os.remove(output_path + '/NvM.epc')
                            os.remove(output_path + '/NvDM.epc')
                        except OSError:
                            pass
                        return
    # merge two block with the same name:
    for elem1 in blocks[:]:
        for elem2 in blocks[:]:
            if blocks.index(elem1) != blocks.index(elem2):
                if elem1['NAME'] == elem2['NAME']:
                    for interface in elem2['INTERFACE']:
                        elem1['INTERFACE'].append(interface)
    blocks = list(remove_duplicates(blocks))
    # compute size for each interface
    for interface in arxml_interfaces:
        interface_size = 0
        for data_element in interface['DATA-ELEMENTS']:
            # type = data_element.find(".//{http://autosar.org/schema/r4.0}TYPE-TREF").text.split("/")[-1]
            for data_type in arxml_data_types:
                if data_type['NAME'] == data_element['TYPE'].split("/")[-1]:
                    data_element['SW-BASE-TYPE'] = data_type['BASE-TYPE']
                    base = data_type['BASE-TYPE'].split("/")[-1]
                    package = data_type['BASE-TYPE'].split("/")[-2]
                    for base_type in arxml_base_types:
                        if base_type['NAME'] == base and base_type['PACKAGE'] == package:
                            interface_size = interface_size + int(base_type['SIZE'])
                            data_element['SIZE'] = int(base_type['SIZE'])
        interface['SIZE'] = int(interface_size / 8)
    # implement TRS.SYSDESC.CHECK.003
    all_interfaces = []
    for elem in blocks:
        for interface in elem['INTERFACE']:
            obj_temp = {}
            obj_temp['INTERFACE'] = interface
            obj_temp['BLOCK'] = elem['NAME']
            all_interfaces.append(obj_temp)
    for elem1 in all_interfaces:
        found = False
        for elem2 in arxml_interfaces:
            if elem1['INTERFACE']['NAME'] == "/" + elem2['ROOT'] + "/" + elem2['NAME']:
                elem1['INTERFACE']['SIZE'] = elem2['SIZE']
                elem1['INTERFACE']['DATA-PROTOTYPE'] = elem2['DATA-ELEMENTS']
                found = True
                break
        if not found:
            logger.error('Interface: ' + elem1['INTERFACE']['NAME'] + ' of block ' + elem1['BLOCK'] + ' is not present in the arxml files')
            try:
                os.remove(output_path + '/NvM.epc')
                os.remove(output_path + '/NvDM.epc')
            except OSError:
                pass
            return
    # implement TRS.SYSDESC.CHECK.004
    for index1 in range(len(all_interfaces)):
        for index2 in range(len(all_interfaces)):
            if index1 != index2:
                if all_interfaces[index1]['INTERFACE'] == all_interfaces[index2]['INTERFACE']:
                    if all_interfaces[index1]['BLOCK'] != all_interfaces[index2]['BLOCK']:
                        logger.error('Interface ' + all_interfaces[index1]['INTERFACE'] + ' is defined in multiple blocks: ' + all_interfaces[index1]['BLOCK'] + ' and ' + all_interfaces[index2]['BLOCK'])
                        try:
                            os.remove(output_path + '/NvM.epc')
                            os.remove(output_path + '/NvDM.epc')
                        except OSError:
                            pass
                        return
    # get the max-size information for each block from profile
    for block in blocks:
        found = False
        for profile in profiles:
            if block['PROFILE'] == profile['NAME']:
                block['MAX-SIZE'] = profile['MAX-SIZE']
                block['DEVICE'] = profile['DEVICE']
                if profile['SAFETY'] != 'true' and block['SDF'] is not None:
                    logger.error('The block ' + block['NAME'] + ' is not allowed to have SDF parameter set')
                    try:
                        os.remove(output_path + '/NvM.epc')
                        os.remove(output_path + '/NvDM.epc')
                    except OSError:
                        pass
                    return
                found = True
        if not found:
            logger.error('The profile ' + block['PROFILE'] + ' used in block ' + block['NAME'] + ' is not valid (not defined in the project)')
            try:
                os.remove(output_path + '/NvM.epc')
                os.remove(output_path + '/NvDM.epc')
            except OSError:
                pass
            return
    # implement TRS.SYSDESC.FUNC.002
    blocks = sorted(blocks, key=lambda x: x['PROFILE'])
    for block in blocks[:]:
        subblock_number = 1
        temp_size = 0
        temp_interfaces = []
        splitted = False
        obj_subblock = {}
        for interface in block['INTERFACE']:
            temp_size = temp_size + interface['SIZE']
            if temp_size <= int(block['MAX-SIZE']):
                temp_interfaces.append(interface)
                if splitted and block['INTERFACE'].index(interface) == len(block['INTERFACE'])-1:
                    obj_subblock['NAME'] = block['NAME'] + "_" + str(subblock_number)
                    obj_subblock['TYPE'] = block['TYPE']
                    obj_subblock['PROFILE'] = block['PROFILE']
                    obj_subblock['TIMEOUT'] = block['TIMEOUT']
                    obj_subblock['MAPPING'] = block['MAPPING']
                    obj_subblock['DEVICE'] = block['DEVICE']
                    obj_subblock['SDF'] = block['SDF']
                    obj_subblock['INTERFACE'] = temp_interfaces
                    new_dict = copy.deepcopy(obj_subblock)
                    subblocks.append(new_dict)
                    obj_subblock.clear()
            else:
                splitted = True
                obj_subblock['NAME'] = block['NAME'] + '_' + str(subblock_number)
                subblock_number = subblock_number + 1
                obj_subblock['TYPE'] = block['TYPE']
                obj_subblock['PROFILE'] = block['PROFILE']
                obj_subblock['TIMEOUT'] = block['TIMEOUT']
                obj_subblock['MAPPING'] = block['MAPPING']
                obj_subblock['DEVICE'] = block['DEVICE']
                obj_subblock['SDF'] = block['SDF']
                obj_subblock['INTERFACE'] = temp_interfaces
                new_dict = copy.deepcopy(obj_subblock)
                subblocks.append(new_dict)
                obj_subblock.clear()
                temp_size = 0
                temp_size = temp_size + interface['SIZE']
                del temp_interfaces[:]
                temp_interfaces.append(interface)
        if splitted:
            blocks.remove(block)

    # implement TRS.SYSDESC.FUNC.001
    final_blocks = []
    for subblock in subblocks:
        obj_block = {}
        data_elements = []
        obj_block['NAME'] = subblock['NAME']
        obj_block['MAPPING'] = subblock['MAPPING']
        obj_block['PROFILE'] = subblock['PROFILE']
        obj_block['DEVICE'] = subblock['DEVICE']
        obj_block['TIMEOUT'] = subblock['TIMEOUT']
        obj_block['SDF'] = subblock['SDF']
        for interface in subblock['INTERFACE']:
            for data in interface['DATA-PROTOTYPE']:
                obj_data_prototype = {}
                obj_data_prototype['NAME'] = interface['NAME'].split('/')[-1] + "_" + data['NAME']
                obj_data_prototype['DATA'] = interface['NAME'] + "/" + data['NAME']
                obj_data_prototype['SW-BASE-TYPE'] = data['SW-BASE-TYPE']
                obj_data_prototype['SIZE'] = data['SIZE']
                data_elements.append(obj_data_prototype)
        obj_block['DATA'] = data_elements
        final_blocks.append(obj_block)
    for block in blocks:
        obj_block = {}
        data_elements = []
        obj_block['NAME'] = block['NAME']
        obj_block['MAPPING'] = block['MAPPING']
        obj_block['PROFILE'] = block['PROFILE']
        obj_block['DEVICE'] = block['DEVICE']
        obj_block['TIMEOUT'] = block['TIMEOUT']
        obj_block['SDF'] = block['SDF']
        for interface in block['INTERFACE']:
            for data in interface['DATA-PROTOTYPE']:
                obj_data_prototype = {}
                obj_data_prototype['NAME'] = interface['NAME'].split('/')[-1] + "_" + data['NAME']
                obj_data_prototype['DATA'] = interface['NAME'] + "/" + data['NAME']
                obj_data_prototype['SW-BASE-TYPE'] = data['SW-BASE-TYPE']
                obj_data_prototype['SIZE'] = data['SIZE']
                data_elements.append(obj_data_prototype)
        obj_block['DATA'] = data_elements
        final_blocks.append(obj_block)
    for block in final_blocks:
        if block['MAPPING'] == 'false':
            block['DATA'] = sorted(block['DATA'], key=lambda x: x['SIZE'], reverse=True)
    index_name = 0
    for block in final_blocks:
        index_name = index_name + 1
        obj_nvm = {}
        obj_nvm['NAME'] = block['NAME']
        obj_nvm['DEVICE'] = block['DEVICE']
        obj_nvm['NvMRomBlockDataAddress'] = "&NvDM_RomBlock_" + str(index_name)
        obj_nvm['NvMRamBlockDataAddress'] = "&NvDM_RamBlock_" + str(index_name)
        obj_nvm['NvMSingleBlockCallback'] = None
        obj_nvm['NvMBlockUseAutoValidation'] = None
        obj_nvm['NvMStaticBlockIDCheck'] = None
        obj_nvm['NvMSelectBlockForWriteAll'] = None
        obj_nvm['NvMSelectBlockForReadAll'] = None
        obj_nvm['NvMResistantToChangedSw'] = None
        obj_nvm['NvMCalcRamBlockCrc'] = None
        obj_nvm['NvMBswMBlockStatusInformation'] = None
        obj_nvm['NvMRomBlockNum'] = None
        obj_nvm['NvMNvramDeviceId'] = "0"
        obj_nvm['NvMWriteVerification'] = None
        obj_nvm['NvMWriteBlockOnce'] = None
        obj_nvm['NvMMaxNumOfWriteRetries'] = None
        obj_nvm['NvMMaxNumOfReadRetries'] = None
        obj_nvm['NvMBlockManagementType'] = None
        obj_nvm['NvMBlockCrcType'] = None
        obj_nvm['NvMBlockJobPriority'] = None
        for profile in profiles:
            if profile['NAME'] == block['PROFILE']:
                for elem in profile['PARAM']:
                    if elem['TYPE'] == 'NvMBlockJobPriority':
                        if 0 <= int(elem['VALUE']) <= 255:
                            obj_nvm['NvMBlockJobPriority'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockJobPriority is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMBlockCrcType':
                        if elem['VALUE'] in ['NVM_CRC8', 'NVM_CRC16', 'NVM_CRC32']:
                            obj_nvm['NvMBlockCrcType'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockCrcType is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMBlockManagementType':
                        if elem['VALUE'] in ['NVM_BLOCK_REDUNDANT', 'NVM_BLOCK_NATIVE', 'NVM_BLOCK_DATASET']:
                            obj_nvm['NvMBlockManagementType'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockManagementType is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMMaxNumOfReadRetries':
                        if 0 <= int(elem['VALUE']) <= 7:
                            obj_nvm['NvMMaxNumOfReadRetries'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMMaxNumOfReadRetries is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMMaxNumOfWriteRetries':
                        if 0 <= int(elem['VALUE']) <= 7:
                            obj_nvm['NvMMaxNumOfWriteRetries'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMMaxNumOfWriteRetries is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMWriteBlockOnce':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMWriteBlockOnce'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteBlockOnce is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMWriteVerification':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMWriteVerification'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteVerification is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMNvBlockNum':
                        if 1 <= int(elem['VALUE']) <= 255:
                            obj_nvm['NvMNvBlockNum'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMNvBlockNum is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMRomBlockNum':
                        if 0 <= int(elem['VALUE']) <= 254:
                            obj_nvm['NvMRomBlockNum'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMRomBlockNum is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMBswMBlockStatusInformation':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMBswMBlockStatusInformation'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBswMBlockStatusInformation is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMCalcRamBlockCrc':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMCalcRamBlockCrc'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMCalcRamBlockCrc is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMResistantToChangedSw':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMResistantToChangedSw'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMResistantToChangedSw is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMSelectBlockForReadAll':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMSelectBlockForReadAll'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMSelectBlockForReadAll is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMSelectBlockForWriteAll':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMSelectBlockForWriteAll'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMSelectBlockForWriteAll is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMStaticBlockIDCheck':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMStaticBlockIDCheck'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMStaticBlockIDCheck is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    if elem['TYPE'] == 'NvMBlockUseAutoValidation':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMBlockUseAutoValidation'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockUseAutoValidation is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
                    # TODO: check the possible valid values of this parameter
                    if elem['TYPE'] == 'NvMSingleBlockCallback':
                        if elem['VALUE'] in ['Null', 'NULL']:
                            obj_nvm['NvMSingleBlockCallback'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMSingleBlockCallback is not correctly defined in profile ' + profile['NAME'])
                            try:
                                os.remove(output_path + '/NvM.epc')
                                os.remove(output_path + '/NvDM.epc')
                            except OSError:
                                pass
                            return
        for key, value in obj_nvm.items():
            if value is None:
                logger.error('Mandatory parameters are not configured for NvM block ' + obj_nvm['NAME'])
                try:
                    os.remove(output_path + '/NvM.epc')
                    os.remove(output_path + '/NvDM.epc')
                except OSError:
                    pass
                return
        nvm_blocks.append(obj_nvm)

    # generate NvM.epc
    rootNvM = etree.Element('AUTOSAR', {attr_qname: 'http://autosar.org/schema/r4.0 AUTOSAR_4-2-2_STRICT_COMPACT.xsd'}, nsmap=NSMAP)
    packages = etree.SubElement(rootNvM, 'AR-PACKAGES')
    package = etree.SubElement(packages, 'AR-PACKAGE')
    short_name = etree.SubElement(package, 'SHORT-NAME').text = "NvM"
    elements = etree.SubElement(package, 'ELEMENTS')
    ecuc_module = etree.SubElement(elements, 'ECUC-MODULE-CONFIGURATION-VALUES')
    short_name = etree.SubElement(ecuc_module, 'SHORT-NAME').text = "NvM"
    definition = etree.SubElement(ecuc_module, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-MODULE-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM"
    implementation = etree.SubElement(ecuc_module, 'IMPLEMENTATION-CONFIG-VARIANT').text = "VARIANT-PRE-COMPILE"
    containers = etree.SubElement(ecuc_module, 'CONTAINERS')
    # generic data
    ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
    short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "CommonPublishedInformation"
    definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation"
    parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
    ecuc_numerical_ArMajorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ArMajorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/ArMajorVersion"
    value = etree.SubElement(ecuc_numerical_ArMajorVersion, 'VALUE').text = "1"
    ecuc_numerical_ArMinorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ArMinorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/ArMinorVersion"
    value = etree.SubElement(ecuc_numerical_ArMinorVersion, 'VALUE').text = "0"
    ecuc_numerical_ArPatchVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ArPatchVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/ArPatchVersion"
    value = etree.SubElement(ecuc_numerical_ArPatchVersion, 'VALUE').text = "0"
    ecuc_numerical_ModuleId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ModuleId, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/ModuleId"
    value = etree.SubElement(ecuc_numerical_ModuleId, 'VALUE').text = "0"
    ecuc_numerical_ModuleId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ModuleId, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/ModuleId"
    value = etree.SubElement(ecuc_numerical_ModuleId, 'VALUE').text = "20"
    ecuc_textual_Release = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_textual_Release, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/Release"
    value = etree.SubElement(ecuc_textual_Release, 'VALUE').text = ""
    ecuc_numerical_SwMajorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_SwMajorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/SwMajorVersion"
    value = etree.SubElement(ecuc_numerical_SwMajorVersion, 'VALUE').text = "1"
    ecuc_numerical_SwMinorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_SwMinorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/SwMinorVersion"
    value = etree.SubElement(ecuc_numerical_SwMinorVersion, 'VALUE').text = "0"
    ecuc_numerical_SwPatchVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_SwPatchVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/SwPatchVersion"
    value = etree.SubElement(ecuc_numerical_SwPatchVersion, 'VALUE').text = "0"
    ecuc_numerical_VendorId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_VendorId, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_TxDxM6I16R0/NvM/CommonPublishedInformation/VendorId"
    value = etree.SubElement(ecuc_numerical_VendorId, 'VALUE').text = "1"
    for block in nvm_blocks:
        ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
        short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "NvM_" + block['NAME']
        definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor"
        parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
        # NvMRomBlockDataAddress
        ecuc_textual_NvMRomBlockDataAddress = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMRomBlockDataAddress, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMRomBlockDataAddress"
        value = etree.SubElement(ecuc_textual_NvMRomBlockDataAddress, 'VALUE').text = block['NvMRomBlockDataAddress']
        # NvMRamBlockDataAddress
        ecuc_textual_NvMRamBlockDataAddress = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMRamBlockDataAddress, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMRamBlockDataAddress"
        value = etree.SubElement(ecuc_textual_NvMRamBlockDataAddress, 'VALUE').text = block['NvMRamBlockDataAddress']
        # NvMSingleBlockCallback
        ecuc_textual_NvMSingleBlockCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMSingleBlockCallback, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMSingleBlockCallback"
        value = etree.SubElement(ecuc_textual_NvMSingleBlockCallback, 'VALUE').text = block['NvMSingleBlockCallback']
        # NvMBlockUseAutoValidation
        ecuc_numerical_NvMBlockUseAutoValidation= etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBlockUseAutoValidation, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMBlockUseAutoValidation"
        value = etree.SubElement(ecuc_numerical_NvMBlockUseAutoValidation, 'VALUE').text = block['NvMBlockUseAutoValidation']
        # NvMStaticBlockIDCheck
        ecuc_numerical_NvMStaticBlockIDCheck = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMStaticBlockIDCheck, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMStaticBlockIDCheck"
        value = etree.SubElement(ecuc_numerical_NvMStaticBlockIDCheck, 'VALUE').text = block['NvMStaticBlockIDCheck']
        # NvMSelectBlockForWriteAll
        ecuc_numerical_NvMSelectBlockForWriteAll = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMSelectBlockForWriteAll, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMSelectBlockForWriteAll"
        value = etree.SubElement(ecuc_numerical_NvMSelectBlockForWriteAll, 'VALUE').text = block['NvMSelectBlockForWriteAll']
        # NvMSelectBlockForReadAll
        ecuc_numerical_NvMSelectBlockForReadAll = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMSelectBlockForReadAll, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMSelectBlockForReadAll"
        value = etree.SubElement(ecuc_numerical_NvMSelectBlockForReadAll, 'VALUE').text = block['NvMSelectBlockForReadAll']
        # NvMResistantToChangedSw
        ecuc_numerical_NvMResistantToChangedSw = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMResistantToChangedSw, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMResistantToChangedSw"
        value = etree.SubElement(ecuc_numerical_NvMResistantToChangedSw, 'VALUE').text = block['NvMResistantToChangedSw']
        # NvMCalcRamBlockCrc
        ecuc_numerical_NvMCalcRamBlockCrc = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMCalcRamBlockCrc, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMCalcRamBlockCrc"
        value = etree.SubElement(ecuc_numerical_NvMCalcRamBlockCrc, 'VALUE').text = block['NvMCalcRamBlockCrc']
        # NvMBswMBlockStatusInformation
        ecuc_numerical_NvMBswMBlockStatusInformation = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBswMBlockStatusInformation, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMBswMBlockStatusInformation"
        value = etree.SubElement(ecuc_numerical_NvMBswMBlockStatusInformation, 'VALUE').text = block['NvMBswMBlockStatusInformation']
        # NvMRomBlockNum
        ecuc_numerical_NvMRomBlockNum = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMRomBlockNum, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMRomBlockNum"
        value = etree.SubElement(ecuc_numerical_NvMRomBlockNum, 'VALUE').text = block['NvMRomBlockNum']
        # NvMNvramDeviceId
        ecuc_numerical_NvMNvramDeviceId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMNvramDeviceId, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMNvramDeviceId"
        value = etree.SubElement(ecuc_numerical_NvMNvramDeviceId, 'VALUE').text = block['NvMNvramDeviceId']
        # NvMWriteVerification
        ecuc_numerical_NvMWriteVerification = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMWriteVerification, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMWriteVerification"
        value = etree.SubElement(ecuc_numerical_NvMWriteVerification, 'VALUE').text = block['NvMWriteVerification']
        # NvMWriteBlockOnce
        ecuc_numerical_NvMWriteBlockOnce = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMWriteBlockOnce, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMWriteBlockOnce"
        value = etree.SubElement(ecuc_numerical_NvMWriteBlockOnce, 'VALUE').text = block['NvMWriteBlockOnce']
        # NvMMaxNumOfWriteRetries
        ecuc_numerical_NvMMaxNumOfWriteRetries = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMMaxNumOfWriteRetries, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMMaxNumOfWriteRetries"
        value = etree.SubElement(ecuc_numerical_NvMMaxNumOfWriteRetries, 'VALUE').text = block['NvMMaxNumOfWriteRetries']
        # NvMMaxNumOfReadRetries
        ecuc_numerical_NvMMaxNumOfReadRetries = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMMaxNumOfReadRetries, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMMaxNumOfReadRetries"
        value = etree.SubElement(ecuc_numerical_NvMMaxNumOfReadRetries, 'VALUE').text = block['NvMMaxNumOfReadRetries']
        # NvMBlockJobPriority
        ecuc_numerical_NvMBlockJobPriority = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBlockJobPriority, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMBlockJobPriority"
        value = etree.SubElement(ecuc_numerical_NvMBlockJobPriority, 'VALUE').text = block['NvMBlockJobPriority']
        # NvMBlockManagementType
        ecuc_textual_NvMBlockManagementType = etree.SubElement(parameter, 'ECUC-ENUMERATION-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMBlockManagementType, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMBlockManagementType"
        value = etree.SubElement(ecuc_textual_NvMBlockManagementType, 'VALUE').text = block['NvMBlockManagementType']
        # NvMBlockCrcType
        ecuc_textual_NvMBlockCrcType = etree.SubElement(parameter, 'ECUC-ENUMERATION-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMBlockCrcType, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMBlockCrcType"
        value = etree.SubElement(ecuc_textual_NvMBlockCrcType, 'VALUE').text = block['NvMBlockCrcType']
        # FEE or EA reference
        subcontainers = etree.SubElement(ecuc_container, 'SUB-CONTAINERS')
        container = etree.SubElement(subcontainers, 'ECUC-CONTAINER-VALUE')
        short_name = etree.SubElement(container, 'SHORT-NAME').text = "NvMTargetBlockReference"
        definition = etree.SubElement(container, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-CHOICE-CONTAINER-DEF"
        definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMTargetBlockReference"
        subcontainer = etree.SubElement(container, 'SUB-CONTAINERS')
        container_value = etree.SubElement(subcontainer, 'ECUC-CONTAINER-VALUE')
        short_name = etree.SubElement(container_value, 'SHORT-NAME').text = "NvMTargetBlockReference"
        if block['DEVICE'] in ["FEE", "Fee", "fee"]:
            definition = etree.SubElement(container_value, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMFeeRef"
            reference_values = etree.SubElement(container_value, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-SYMBOLIC-NAME-REFERENCE-DEF"
            definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMFeeRef/NvMNameOfFeeBlock"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "ECUC-CONTAINER-VALUE"
            value.text = ""
        else:
            definition = etree.SubElement(container_value, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMEaRef"
            reference_values = etree.SubElement(container_value, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-SYMBOLIC-NAME-REFERENCE-DEF"
            definition.text = "/TS_TxDxM6I16R0/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMEaRef/NvMNameOfEaBlock"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "ECUC-CONTAINER-VALUE"
            value.text = ""
    pretty_xml = new_prettify(rootNvM)
    output = etree.ElementTree(etree.fromstring(pretty_xml))
    output.write(output_path + '/NvM.epc', encoding='UTF-8', xml_declaration=True, method="xml")
    # logger.info('=================Output file information=================')
    validate_xml_with_xsd(xsd_arxml, output_path + '/NvM.epc', logger)

    # generate NvDM.epc
    rootNvDM = etree.Element('AUTOSAR', {attr_qname: 'http://autosar.org/schema/r4.0 AUTOSAR_4-2-2_STRICT_COMPACT.xsd'}, nsmap=NSMAP)
    packages = etree.SubElement(rootNvDM, 'AR-PACKAGES')
    package = etree.SubElement(packages, 'AR-PACKAGE')
    short_name = etree.SubElement(package, 'SHORT-NAME').text = "NvDM"
    elements = etree.SubElement(package, 'ELEMENTS')
    ecuc_module = etree.SubElement(elements, 'ECUC-MODULE-CONFIGURATION-VALUES')
    short_name = etree.SubElement(ecuc_module, 'SHORT-NAME').text = "NvDM"
    definition = etree.SubElement(ecuc_module, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-MODULE-DEF"
    definition.text = "/TS_2018_01/NvDM"
    implementation = etree.SubElement(ecuc_module, 'IMPLEMENTATION-CONFIG-VARIANT').text = "VARIANT-PRE-COMPILE"
    containers = etree.SubElement(ecuc_module, 'CONTAINERS')
    # generic data
    ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
    short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "CommonPublishedInformation"
    definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation"
    parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
    ecuc_numerical_ArMajorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ArMajorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/ArMajorVersion"
    value = etree.SubElement(ecuc_numerical_ArMajorVersion, 'VALUE').text = "1"
    ecuc_numerical_ArMinorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ArMinorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/ArMinorVersion"
    value = etree.SubElement(ecuc_numerical_ArMinorVersion, 'VALUE').text = "0"
    ecuc_numerical_ArPatchVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ArPatchVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/ArPatchVersion"
    value = etree.SubElement(ecuc_numerical_ArPatchVersion, 'VALUE').text = "0"
    ecuc_numerical_ModuleId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ModuleId, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/ModuleId"
    value = etree.SubElement(ecuc_numerical_ModuleId, 'VALUE').text = "0"
    ecuc_numerical_ModuleId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_ModuleId, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/ModuleId"
    value = etree.SubElement(ecuc_numerical_ModuleId, 'VALUE').text = "20"
    ecuc_textual_Release = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_textual_Release, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/Release"
    value = etree.SubElement(ecuc_textual_Release, 'VALUE').text = ""
    ecuc_numerical_SwMajorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_SwMajorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/SwMajorVersion"
    value = etree.SubElement(ecuc_numerical_SwMajorVersion, 'VALUE').text = "1"
    ecuc_numerical_SwMinorVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_SwMinorVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/SwMinorVersion"
    value = etree.SubElement(ecuc_numerical_SwMinorVersion, 'VALUE').text = "0"
    ecuc_numerical_SwPatchVersion = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_SwPatchVersion, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/SwPatchVersion"
    value = etree.SubElement(ecuc_numerical_SwPatchVersion, 'VALUE').text = "0"
    ecuc_numerical_VendorId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_VendorId, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/TS_2018_01/NvDM/CommonPublishedInformation/VendorId"
    value = etree.SubElement(ecuc_numerical_VendorId, 'VALUE').text = "1"
    index = 0
    for block in final_blocks:
        ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
        short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "NvDM_" + block['NAME']
        definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
        definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor"
        parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
        for profile in profiles:
            if profile['NAME'] == block['PROFILE']:
                # NvDMDurability
                ecuc_textual_NvDMDurability = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvDMDurability, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMDurability"
                value = etree.SubElement(ecuc_textual_NvDMDurability, 'VALUE').text = profile['DURABILITY']
                # NvDMSafetyBlock
                ecuc_numerical_NvDMSafetyBlock = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMSafetyBlock, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMSafetyBlock"
                value = etree.SubElement(ecuc_numerical_NvDMSafetyBlock, 'VALUE')
                if block['SDF'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMWriteTimeout
                ecuc_numerical_NvDMWriteTimeout = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMWriteTimeout, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FLOAT-PARAM-DEF"
                definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMWriteTimeout"
                value = etree.SubElement(ecuc_numerical_NvDMWriteTimeout, 'VALUE').text = block['TIMEOUT']
                # NvDMWritingManagment
                ecuc_textual_NvDMWritingManagment = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvDMWritingManagment, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMWritingManagment"
                value = etree.SubElement(ecuc_textual_NvDMWritingManagment, 'VALUE').text = profile['MANAGEMENT']
        reference = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
        ecuc_reference = etree.SubElement(reference, 'ECUC-REFERENCE-VALUE')
        ecuc_reference.attrib['DEST'] = "ECUC-REFERENCE-DEF"
        ecuc_reference.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMNvMBlockDescriptorRef"
        value = etree.SubElement(reference, 'VALUE-REF')
        value.attrib['DEST'] = "ECUC-CONTAINER-VALUE"
        value.text = "/NvM/NvM/NvM_" + block['NAME']
        subcontainers = etree.SubElement(ecuc_container, 'SUB-CONTAINERS')
        index = 0
        for element in block['DATA']:
            ecuc_container = etree.SubElement(subcontainers, 'ECUC-CONTAINER-VALUE')
            short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = element['NAME']
            index = index + 1
            definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype"
            reference_values = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMBaseTypeRef"
            value = etree.SubElement(reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "SW-BASE-TYPE"
            value.text = element['SW-BASE-TYPE']
            reference_values = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/TS_2018_01/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMVariableDataPrototypeRef"
            value = etree.SubElement(reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "VARIABLE-DATA-PROTOTYPE"
            value.text = element['DATA']
    pretty_xml = new_prettify(rootNvDM)
    output = etree.ElementTree(etree.fromstring(pretty_xml))
    output.write(output_path + '/NvDM.epc', encoding='UTF-8', xml_declaration=True, method="xml")
    # logger.info('=================Output file information=================')
    validate_xml_with_xsd(xsd_arxml, output_path + '/NvDM.epc', logger)


if __name__ == "__main__":
    process = psutil.Process(os.getpid())
    start_time = time.clock()
    main()
    print(str(time.clock() - start_time) + " seconds")
    print(str(process.memory_info()[0]/float(2**20)) + " MB")
