from lxml import etree, objectify                   # pragma: no cover
import argparse                                     # pragma: no cover
import logging                                      # pragma: no cover
import os                                           # pragma: no cover
import sys                                          # pragma: no cover
import copy                                         # pragma: no cover
from xml.sax import make_parser                     # pragma: no cover
from xml.sax.handler import ContentHandler          # pragma: no cover
from xml.dom.minidom import parseString             # pragma: no cover
# from coverage import Coverage                       # pragma: no cover


def arg_parse(parser):
    parser.add_argument('-in', '--inp', nargs='*', help="input path or file", required=True, default="")
    parser.add_argument('-in_resizing', '--resizing', nargs='*',  help="input path or file for block resizing", required=False, default="")
    parser.add_argument('-out', '--out', help="output path", required=False, default="")
    parser.add_argument('-out_epc', '--out_epc', help="output path for configuration file(s)", required=False, default="")
    parser.add_argument('-out_log', '--out_log', help="output path for log file", required=False, default="")
    parser.add_argument('-alignment', '--alignment', help="data mode alignment in memory blocks (in bytes)", required=True, choices=['2', '4', '8'])


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


def set_logger(path):
    # logger creation and setting
    logger = logging.getLogger('result')
    hdlr = logging.FileHandler(path + '/result_MEM.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    open(path + '/result_MEM.log', 'w').close()
    return logger


def check_ordered(block_list):
    total = 0
    max = float('-inf')
    min = float('+inf')
    IDs = []

    # extract IDs for each block into an array
    for block in block_list:
        for key, value in block.items():
            if key == 'NvMNvramBlockIdentifier':
                IDs.append(value)
                break
    # create a set for quick order
    seen = set()
    for elem in IDs:
        if elem in seen:
            return False
        seen.add(elem)
        if elem > max:
            max = elem
        if elem < min:
            min = elem
        total += elem
    # sum of n consecutive numbers
    if 2*total != max*(max+1) - min*(min-1):
        return False

    return True


def main():
    # parsing the command line arguments
    parser = argparse.ArgumentParser()
    arg_parse(parser)
    args = parser.parse_args()
    input_path = args.inp
    resizing_path = args.resizing
    error = False
    path_list = []
    file_list = []
    entry_list = []
    for path in input_path:
        if path.startswith('@'):
            file = open(path[1:])
            line_file = file.readline()
            while line_file != "":
                line_file = line_file.rstrip()
                line_file = line_file.lstrip()
                if "#" not in line_file:
                    if os.path.isdir(line_file):
                        path_list.append(line_file)
                    elif os.path.isfile(line_file):
                        file_list.append(line_file)
                    else:
                        print("\nError defining the input path: " + line_file + "\n")
                        error = True
                    line_file = file.readline()
                else:
                    line_file = file.readline()
            file.close()
        else:
            if os.path.isdir(path):
                path_list.append(path)
            elif os.path.isfile(path):
                file_list.append(path)
            else:
                print("\nError defining the input path: " + path + "\n")
                error = True
    for path in path_list:
        for (dirpath, dirnames, filenames) in os.walk(path):
            for file in filenames:
                fullname = dirpath + '\\' + file
                file_list.append(fullname)
    [entry_list.append(elem) for elem in file_list if elem not in entry_list]
    priority_list = []
    path_list = []
    file_list = []
    for path in resizing_path:
        if os.path.isdir(path):
            path_list.append(path)
        elif os.path.isfile(path):
            file_list.append(path)
        else:
            print("\nError defining the input path: " + path + "\n")
            error = True
    for path in path_list:
        for (dirpath, dirnames, filenames) in os.walk(path):
            for file in filenames:
                fullname = dirpath + '\\' + file
                file_list.append(fullname)
    [priority_list.append(elem) for elem in file_list if elem not in priority_list]
    if error:
        sys.exit(1)
    output_path = args.out
    alignment = args.alignment
    output_epc = args.out_epc
    output_log = args.out_log
    if output_path:
        if not os.path.isdir(output_path):
            print("\nError defining the output path!\n")
            sys.exit(1)
        if output_log:
            if not os.path.isdir(output_log):
                print("\nError defining the output log path!\n")
                sys.exit(1)
            logger = set_logger(output_log)
            create_MEM_config(entry_list, priority_list, output_path, logger, alignment)
        else:
            logger = set_logger(output_path)
            create_MEM_config(entry_list, priority_list, output_path, logger, alignment)
    elif not output_path:
        if output_epc:
            if not os.path.isdir(output_epc):
                print("\nError defining the output configuration path!\n")
                sys.exit(1)
            if output_log:
                if not os.path.isdir(output_log):
                    print("\nError defining the output log path!\n")
                    sys.exit(1)
                logger = set_logger(output_log)
                create_MEM_config(entry_list, priority_list, output_epc, logger, alignment)
            else:
                logger = set_logger(output_epc)
                create_MEM_config(entry_list, priority_list, output_epc, logger, alignment)
    else:
        print("\nNo output path defined!\n")
        sys.exit(1)


def create_MEM_config(files_list, priority_list, output_path, logger, alignment):
    error_no = 0
    warning_no = 0
    info_no = 0
    blocks = []
    subblocks = []
    profiles = []
    mappings = []
    config_ids = []
    nvm_blocks = []
    extern_blocks = []
    final_fixed_blocks = []
    arxml_interfaces = []
    arxml_data_types = []
    arxml_base_types = []
    priority_blocks = []
    ports = []
    NSMAP = {None: 'http://autosar.org/schema/r4.0', "xsi": 'http://www.w3.org/2001/XMLSchema-instance'}
    attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
    # try:
        # parse the arxml files and get the necessary data
    for file in files_list:
        if file.endswith('.epc'):
            try:
                check_if_xml_is_wellformed(file)
                logger.info(' The file ' + file + ' is well-formed')
                info_no = info_no + 1
            except Exception as e:
                logger.error(' The file ' + file + ' is not well-formed: ' + str(e))
                print('ERROR: The file ' + file + ' is not well-formed: ' + str(e))
                error_no = error_no + 1
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            container = root.find(".//{http://autosar.org/schema/r4.0}CONTAINERS")
            for block in container.findall("{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE"):
                if block.find("./{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1] != "NvMBlockDescriptor":
                    continue
                obj_block = {}
                obj_block['NAME'] = block.find("./{http://autosar.org/schema/r4.0}SHORT-NAME").text
                obj_block['SOURCE'] = 'Extern'
                numeric = block.findall(".//{http://autosar.org/schema/r4.0}ECUC-NUMERICAL-PARAM-VALUE")
                for elem in numeric:
                    if elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1] == "NvMNvramBlockIdentifier":
                        obj_block[elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]] = 0
                    else:
                        if elem.find(".//{http://autosar.org/schema/r4.0}VALUE") is not None:
                            obj_block[elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]] = elem.find(".//{http://autosar.org/schema/r4.0}VALUE").text
                        else:
                            obj_block[elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]] = None
                textual = block.findall(".//{http://autosar.org/schema/r4.0}ECUC-TEXTUAL-PARAM-VALUE")
                for elem in textual:
                    if elem.find(".//{http://autosar.org/schema/r4.0}VALUE") is not None:
                        obj_block[elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]] = elem.find(".//{http://autosar.org/schema/r4.0}VALUE").text
                    else:
                        obj_block[elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]] = None
                reference = block.findall(".//{http://autosar.org/schema/r4.0}ECUC-REFERENCE-VALUE")
                for elem in reference:
                    obj_block[elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]] = ""
                    if "Fee" in elem.find(".//{http://autosar.org/schema/r4.0}DEFINITION-REF").text.split("/")[-1]:
                        obj_block['DEVICE'] = "FEE"
                    else:
                        obj_block['DEVICE'] = "EA"
                extern_blocks.append(obj_block)
        if file.endswith('.arxml'):
            try:
                check_if_xml_is_wellformed(file)
                logger.info('The file: ' + file + ' is well-formed')
                info_no = info_no + 1
            except Exception as e:
                logger.error('The file: ' + file + ' is not well-formed: ' + str(e))
                print('ERROR: The file: ' + file + ' is not well-formed: ' + str(e))
                error_no = error_no + 1
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
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
                    if data_prototype.find('.//{http://autosar.org/schema/r4.0}VALUE') is not None:
                        obj_variable['INIT'] = data_prototype.find('.//{http://autosar.org/schema/r4.0}VALUE').text
                    else:
                        obj_variable['INIT'] = 0
                        logger.warning(str(obj_variable['NAME']) + " doesn't have an initial value defined")
                        warning_no = warning_no + 1
                    obj_variable['SW-BASE-TYPE'] = None
                    obj_variable['SIZE'] = None
                    obj_variable['REAL-TYPE'] = None
                    obj_variable['BASE-SIZE'] = 0
                    variable_data_prototype.append(obj_variable)
                obj_elem['DATA-ELEMENTS'] = variable_data_prototype
                obj_elem['SIZE'] = None
                arxml_interfaces.append(obj_elem)
            implementation_data_types = root.findall(".//{http://autosar.org/schema/r4.0}IMPLEMENTATION-DATA-TYPE")
            for elem in implementation_data_types:
                obj_elem = {}
                obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                obj_elem['TYPE'] = elem.find(".//{http://autosar.org/schema/r4.0}CATEGORY").text
                if elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-REF") is not None:
                    obj_elem['BASE-TYPE'] = elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-REF").text
                else:
                    pass
                if elem.find(".//{http://autosar.org/schema/r4.0}IMPLEMENTATION-DATA-TYPE-REF") is not None:
                    obj_elem['ID-TYPE'] = elem.find(".//{http://autosar.org/schema/r4.0}IMPLEMENTATION-DATA-TYPE-REF").text
                else:
                    pass
                result = 1
                if elem.find(".//{http://autosar.org/schema/r4.0}ARRAY-SIZE") is not None:
                    arrays = elem.findall(".//{http://autosar.org/schema/r4.0}ARRAY-SIZE")
                    for array in arrays:
                        result *= int(array.text)
                        obj_elem['ARRAY-SIZE'] = str(result)
                else:
                    pass
                arxml_data_types.append(obj_elem)
            base_types = root.findall(".//{http://autosar.org/schema/r4.0}SW-BASE-TYPE")
            for elem in base_types:
                obj_elem = {}
                obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                obj_elem['PACKAGE'] = elem.getparent().getparent().getchildren()[0].text
                obj_elem['SIZE'] = elem.find(".//{http://autosar.org/schema/r4.0}BASE-TYPE-SIZE").text
                arxml_base_types.append(obj_elem)
            pr_ports = root.findall(".//{http://autosar.org/schema/r4.0}PR-PORT-PROTOTYPE")
            for elem in pr_ports:
                obj_elem = {}
                obj_elem['NAME'] = elem.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                obj_elem['ASWC'] = elem.getparent().getparent().getchildren()[0].text
                obj_elem['ROOT'] = elem.getparent().getparent().getparent().getparent().getchildren()[0].text
                obj_elem['INTERFACE'] = elem.find(".//{http://autosar.org/schema/r4.0}PROVIDED-REQUIRED-INTERFACE-TREF").text
                obj_elem['SIZE'] = None
                obj_elem['DATA-ELEMENTS'] = None
                obj_elem['REAL-TYPE'] = None
                obj_elem['BASE-SIZE'] = 0
                ports.append(obj_elem)
        if file.endswith('.xml'):
            try:
                check_if_xml_is_wellformed(file)
                logger.info(' The file ' + file + ' is well-formed')
                info_no = info_no + 1
            except Exception as e:
                logger.error(' The file ' + file + ' is not well-formed: ' + str(e))
                print('ERROR: The file ' + file + ' is not well-formed: ' + str(e))
                error_no = error_no + 1
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            block = root.findall(".//BLOCK")
            for elem in block:
                obj_block = {}
                block_ports = []
                obj_block['NAME'] = elem.find('SHORT-NAME').text
                obj_block['TYPE'] = elem.find('TYPE').text
                # implementing requirement TRS.SYSDESC.CHECK.002
                if elem.find('PROFIL-REF') is not None:
                    if elem.find('PROFIL-REF').text != '' or elem.find('PROFILE-REF') is None:
                        obj_block['PROFILE'] = elem.find('PROFIL-REF').text
                    else:
                        logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                        print('ERROR: No profile defined for block ' + elem.find('SHORT-NAME').text)
                        error_no = error_no + 1
                else:
                    logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                    print('ERROR: No profile defined for block ' + elem.find('SHORT-NAME').text)
                    error_no = error_no + 1
                if elem.find('SINGLE-BLOCK-CALL-BACK-FUNCTION') is not None:
                    obj_block['CALLBACK'] = elem.find('SINGLE-BLOCK-CALL-BACK-FUNCTION').text
                else:
                    obj_block['CALLBACK'] = None
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
                obj_block['RESISTENT'] = None
                obj_block['POSITION'] = None
                obj_block['CONSISTENCY'] = None
                obj_block['CRC'] = None
                obj_block['ID'] = None
                pr_ports = elem.findall('.//PR-PORT-PROTOTYPE-REF')
                for element in pr_ports:
                    obj_interface = {}
                    obj_interface['NAME'] = element.text
                    obj_interface['ASWC'] = None
                    obj_interface['SIZE'] = 0
                    obj_interface['SW-BASE-TYPE'] = None
                    obj_interface['DATA-PROTOTYPE'] = None
                    block_ports.append(obj_interface)
                obj_block['PORT'] = block_ports
                obj_block['MAX-SIZE'] = None
                blocks.append(obj_block)
            profile = root.findall(".//PROFILE")
            for elem in profile:
                obj_profile = {}
                params = []
                obj_profile['NAME'] = elem.find('SHORT-NAME').text
                # obj_profile['MANAGEMENT'] = elem.find('MANAGEMENT').text
                obj_profile['DURABILITY'] = elem.find('DURABILITY').text
                obj_profile['MAX-SIZE'] = elem.find('BLOCK-SIZE-MAX').text
                if elem.find('SAFETY') is not None:
                    obj_profile['SAFETY'] = elem.find('SAFETY').text
                else:
                    obj_profile['SAFETY'] = 'false'
                if elem.find('CONSISTENCY') is not None:
                    obj_profile['CONSISTENCY'] = elem.find('CONSISTENCY').text
                else:
                    obj_profile['CONSISTENCY'] = 'false'
                if elem.find('CRC') is not None:
                    obj_profile['CRC'] = elem.find('CRC').text
                else:
                    obj_profile['CRC'] = 'false'
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
            mapping = root.findall(".//MAPPING")
            for elem in mapping:
                obj_mapping = {}
                obj_mapping['BLOCK'] = elem.find('BLOCK-REF').text
                obj_mapping['POSITION'] = int(elem.find('POSITION').text)
                mappings.append(obj_mapping)
            ids = root.findall(".//NVM_COMPILED_CONFIG_ID")
            for elem in ids:
                config_ids.append(elem.text)
    # parse the xml block data overloading (if any)
    for file in priority_list:
        if file.endswith('.xml'):
            try:
                check_if_xml_is_wellformed(file)
                logger.info(' The file ' + file + ' is well-formed')
                info_no = info_no + 1
            except Exception as e:
                logger.error(' The file ' + file + ' is not well-formed: ' + str(e))
                print('ERROR: The file ' + file + ' is not well-formed: ' + str(e))
                error_no = error_no + 1
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            block = root.findall(".//BLOCK")
            for elem in block:
                obj_block = {}
                block_ports = []
                obj_block['NAME'] = elem.find('SHORT-NAME').text
                obj_block['TYPE'] = elem.find('TYPE').text
                # implementing requirement TRS.SYSDESC.CHECK.002
                if elem.find('PROFIL-REF') is not None:
                    if elem.find('PROFIL-REF').text != '' or elem.find('PROFILE-REF') is None:
                        obj_block['PROFILE'] = elem.find('PROFIL-REF').text
                    else:
                        logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                        print('ERROR: No profile defined for block ' + elem.find('SHORT-NAME').text)
                        error_no = error_no + 1
                else:
                    logger.error('No profile defined for block ' + elem.find('SHORT-NAME').text)
                    print('ERROR: No profile defined for block ' + elem.find('SHORT-NAME').text)
                    error_no = error_no + 1
                if elem.find('SINGLE-BLOCK-CALL-BACK-FUNCTION') is not None:
                    obj_block['CALLBACK'] = elem.find('SINGLE-BLOCK-CALL-BACK-FUNCTION').text
                else:
                    obj_block['CALLBACK'] = None
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
                obj_block['RESISTENT'] = None
                obj_block['POSITION'] = None
                obj_block['CONSISTENCY'] = None
                obj_block['CRC'] = None
                obj_block['ID'] = None
                pr_ports = elem.findall('.//PR-PORT-PROTOTYPE-REF')
                for element in pr_ports:
                    obj_interface = {}
                    obj_interface['NAME'] = element.text
                    obj_interface['ASWC'] = None
                    obj_interface['SIZE'] = 0
                    obj_interface['SW-BASE-TYPE'] = None
                    obj_interface['DATA-PROTOTYPE'] = None
                    block_ports.append(obj_interface)
                obj_block['PORT'] = block_ports
                obj_block['MAX-SIZE'] = None
                priority_blocks.append(obj_block)

    ############ external blocks check############
    # add Tresos-generated default parameters with their default value
    tresos_parameters = {'NvMNvBlockBaseNumber': '0', 'NvMNvBlockNum': "1", 'NvMAdvancedRecovery': "False", 'NvMBlockUseSyncMechanism': "False",
                         'NvMBlockWriteProt': "False", 'NvMExtraBlockChecks': "False", 'NvMProvideRteAdminPort': "False", 'NvMProvideRteInitBlockPort': "False",
                         'NvMProvideRteJobFinishedPort': "False", 'NvMProvideRteMirrorPort': "False", 'NvMProvideRteServicePort': "False", 'NvMUserProvidesSpaceForBlockAndCrc': "False"}
    for block in extern_blocks:
        for key in tresos_parameters.keys():
            if key not in block.keys():
                block[key] = tresos_parameters[key]


    # check if mandatory parameters are not present in test
    mandatory_parameters = ['NvMNvramBlockIdentifier', 'NvMNvBlockNum', 'NvMNvBlockLength', 'NvMStaticBlockIDCheck', 'NvMResistantToChangedSw', 'NvMMaxNumOfReadRetries', 'NvMNvBlockBaseNumber',
                            'NvMBlockUseCrc', 'NvMBswMBlockStatusInformation', 'NvMRomBlockNum', 'NvMNvramDeviceId', 'NvMWriteVerification', 'NvMWriteBlockOnce', 'NvMMaxNumOfWriteRetries',
                            'NvMBlockJobPriority', 'NvMBlockManagementType', 'NvMAdvancedRecovery', 'NvMBlockUseSyncMechanism', 'NvMBlockWriteProt', 'NvMExtraBlockChecks', 'NvMProvideRteAdminPort',
                            'NvMProvideRteInitBlockPort', 'NvMProvideRteJobFinishedPort', 'NvMProvideRteMirrorPort', 'NvMProvideRteServicePort', 'NvMUserProvidesSpaceForBlockAndCrc']
    for block in extern_blocks:
        for parameter in mandatory_parameters:
            found = False
            for key in block.keys():
                if key == parameter:
                    found = True
                    break
            if not found:
                logger.error('Mandatory parameters are not present for external NvM block ' + block['NAME'] + ": " + parameter)
                print('ERROR: Mandatory parameters are not present for external NvM block ' + block['NAME'] + ": " + parameter)
                error_no = error_no + 1

    # check if mapping position 1 is set
    for mapping in mappings:
        if mapping['POSITION'] == 1:
            logger.error('It is forbidden to map a block on position 1; this position is reserved')
            print('ERROR: It is forbidden to map a block on position 1; this position is reserved')
            error_no = error_no + 1
#################################NvMInitBlockCallback
    if error_no != 0:
        print("There is at least one blocking error! Check the generated log.")
        print("\n stopped with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
        try:
            os.remove(output_path + '/NvM.epc')
            os.remove(output_path + '/NvDM.epc')
        except OSError:
            pass
        sys.exit(1)
    # check that there is only one CompiledConfigID
    if len(config_ids) > 1 or len(config_ids) == 0:
        logger.error('None or multiple CompiledConfigID parameters defined')
        print('ERROR: None or multiple CompiledConfigID parameters defined')
        error_no = error_no + 1
    # implement TRS.SYSDESC.CHECK.001
    for index1 in range(len(blocks)):
        for index2 in range(len(blocks)):
            if index1 != index2:
                if blocks[index1]['NAME'] == blocks[index2]['NAME']:
                    if blocks[index1]['PROFILE'] != blocks[index2]['PROFILE']:
                        logger.error('Different profiles defined for same block: ' + blocks[index1]['NAME'])
                        print('ERROR: Different profiles defined for same block: ' + blocks[index1]['NAME'])
                        error_no = error_no + 1
                    elif blocks[index1]['TIMEOUT'] != blocks[index2]['TIMEOUT']:
                        logger.error('Different write timeout defined for same block: ' + blocks[index1]['NAME'])
                        print('ERROR: Different write timeout defined for same block: ' + blocks[index1]['NAME'])
                        error_no = error_no + 1
                    elif blocks[index1]['MAPPING'] != blocks[index2]['MAPPING']:
                        logger.error('Different mapping defined for same block: ' + blocks[index1]['NAME'])
                        print('ERROR: Different mapping defined for same block: ' + blocks[index1]['NAME'])
                        error_no = error_no + 1
    # one block with SDF = true cannot be present in multiple files
    for elem1 in blocks[:]:
        for elem2 in blocks[:]:
            if blocks.index(elem1) != blocks.index(elem2):
                if elem1['NAME'] == elem2['NAME']:
                    if elem1['SDF'] == 'true':
                        logger.error('The block ' + elem1['NAME'] + ' cannot be defined in multiple ASWC because SDF = true')
                        print('ERROR: The block ' + elem1['NAME'] + ' cannot be defined in multiple ASWC because SDF = true')
                        error_no = error_no + 1
    # merge two block with the same name
    # TRS.MEMCFG.CHECK.013(0) : if the same block has different callbacks defined --> error
    block_list = []
    block_names = []
    for index1 in range(len(blocks)):
        if blocks[index1]['NAME'] not in block_names:
            block_list.append(blocks[index1])
            block_names.append(blocks[index1]['NAME'])
        else:
            for index2 in range(len(blocks)):
                if index1 != index2 and blocks[index1]['NAME'] == blocks[index2]['NAME']:
                    block_index = block_list.index(blocks[index2])
                    if blocks[index1]['CALLBACK'] is not None and block_list[block_index]['CALLBACK'] is not None and blocks[index1]['CALLBACK'] != block_list[block_index]['CALLBACK']:
                        logger.error('The block ' + blocks[index1]['NAME'] + ' is defined in multiple files with different callbacks')
                        print('ERROR: The block ' + blocks[index1]['NAME'] + ' is defined in multiple files with different callbacks')
                        error_no = error_no + 1
                        break
                    for port in blocks[index1]['PORT']:
                        if port in block_list[block_index]['PORT']:
                            logger.error('The data element ' + port['NAME'] + ' is already defined in the block ' + blocks[index1]['NAME'])
                            print('ERROR: The data element ' + port['NAME'] + ' is already defined in the block ' + blocks[index1]['NAME'])
                            error_no = error_no + 1
                            break
                        else:
                            block_list[block_index]['PORT'].append(port)
    blocks = block_list

    # overwrite data blocks with data from the priority blocks
    # TRS.MEMCFG.GEN.015
    if priority_blocks:
        for overloaded in priority_blocks:
            for block in blocks:
                if block['NAME'] == overloaded['NAME']:
                    block['TYPE'] = overloaded['TYPE']
                    block['PROFILE'] = overloaded['PROFILE']
                    block['CALLBACK'] = overloaded['CALLBACK']
                    block['TIMEOUT'] = overloaded['TIMEOUT']
                    block['MAPPING'] = overloaded['MAPPING']
                    block['SDF'] = overloaded['SDF']
                    block['DEVICE'] = overloaded['DEVICE']
                    block['RESISTENT'] = overloaded['RESISTENT']
                    block['POSITION'] = overloaded['TYPE']
                    block['CONSISTENCY'] = overloaded['CONSISTENCY']
                    block['CRC'] = overloaded['CRC']
                    block['ID'] = overloaded['ID']
                    block['MAX-SIZE'] = overloaded['MAX-SIZE']
                    block['PORT'] = overloaded['PORT']

    # get the max-size information for each block from profile
    for block in blocks:
        found = False
        for profile in profiles:
            if block['PROFILE'] == profile['NAME']:
                block['MAX-SIZE'] = profile['MAX-SIZE']
                block['DEVICE'] = profile['DEVICE']
                block['CONSISTENCY'] = profile['CONSISTENCY']
                block['CRC'] = profile['CRC']
                if profile['SAFETY'] != 'true':
                    block['SDF'] = 'false'
                for param in profile['PARAM']:
                    if param['TYPE'] == 'NvMResistantToChangedSw':
                        block['RESISTENT'] = param['VALUE']
                found = True
        if not found:
            logger.error('The profile ' + str(block['PROFILE']) + ' used in block ' + str(block['NAME']) + ' is not valid (not defined in the project)')
            print('ERROR: The profile ' + str(block['PROFILE']) + ' used in block ' + str(block['NAME']) + ' is not valid (not defined in the project)')
            error_no = error_no + 1

    # compute size for each interface
    for interface in arxml_interfaces:
        interface_size = 0
        for data_element in interface['DATA-ELEMENTS']:
            found = False
            for data_type in arxml_data_types:
                if not found:
                    if data_type['NAME'] == data_element['TYPE'].split("/")[-1]:
                        if data_type['TYPE'] == "VALUE":
                            data_element['SW-BASE-TYPE'] = data_type['BASE-TYPE']
                            base = data_type['BASE-TYPE'].split("/")[-1]
                            package = data_type['BASE-TYPE'].split("/")[-2]
                            for base_type in arxml_base_types:
                                if base_type['NAME'] == base and base_type['PACKAGE'] == package:
                                    interface_size = interface_size + int(base_type['SIZE'])
                                    data_element['SIZE'] = int(base_type['SIZE'])
                                    found = True
                                    data_element['REAL-TYPE'] = data_type['TYPE']
                                    data_element['BASE-SIZE'] = base_type['SIZE']
                                    break
                        elif data_type['TYPE'] == "ARRAY":
                            for idt in arxml_data_types:
                                if idt['NAME'] == data_type['ID-TYPE'].split("/")[-1]:
                                    data_element['SW-BASE-TYPE'] = idt['BASE-TYPE']
                                    base = idt['BASE-TYPE'].split("/")[-1]
                                    package = idt['BASE-TYPE'].split("/")[-2]
                                    for base_type in arxml_base_types:
                                        if base_type['NAME'] == base and base_type['PACKAGE'] == package:
                                            interface_size += (int(data_type['ARRAY-SIZE']) * int(base_type['SIZE']))
                                            data_element['SIZE'] = int(data_type['ARRAY-SIZE']) * int(base_type['SIZE'])
                                            found = True
                                            data_element['REAL-TYPE'] = data_type['TYPE']
                                            data_element['BASE-SIZE'] = base_type['SIZE']
                                            break
                                    break
                else:
                    break
        interface['SIZE'] = int(interface_size / 8)
    # find size for each port
    for port in ports:
        for interface in arxml_interfaces:
            if port['INTERFACE'].split("/")[-1] == interface['NAME']:
                port['SIZE'] = interface['SIZE']
                port['DATA-ELEMENTS'] = interface['DATA-ELEMENTS']
                break
    for port in ports:
        if port['SIZE'] is None:
            logger.error('The port ' + port['NAME'] + " doesn't have an interface defined in the project: " + port['INTERFACE'])
            print('The port ' + port['NAME'] + " doesn't have an interface defined in the project: " + port['INTERFACE'])
            error_no = error_no + 1
    # implement TRS.SYSDESC.CHECK.003
    all_ports = []
    for elem in blocks:
        for port in elem['PORT']:
            obj_temp = {}
            obj_temp['PORT'] = port
            obj_temp['BLOCK'] = elem['NAME']
            all_ports.append(obj_temp)
    for elem1 in all_ports:
        found = False
        for elem2 in ports:
            if elem2['ROOT'] == elem1['PORT']['NAME'].split("/")[1] and elem2['NAME'] == elem1['PORT']['NAME'].split("/")[-1]:
                elem1['PORT']['SIZE'] = elem2['SIZE']
                elem1['PORT']['ASWC'] = elem2['ASWC']
                elem1['PORT']['DATA-PROTOTYPE'] = elem2['DATA-ELEMENTS']
                elem1['PORT']['REAL-TYPE'] = elem2['REAL-TYPE']
                elem1['PORT']['BASE-SIZE'] = elem2['BASE-SIZE']
                found = True
                break
        if not found:
            logger.error('Port: ' + elem1['PORT']['NAME'] + ' of block ' + elem1['BLOCK'] + ' is not present in the arxml files')
            print('ERROR: Port: ' + elem1['PORT']['NAME'] + ' of block ' + elem1['BLOCK'] + ' is not present in the arxml files')
            error_no = error_no + 1
    # implement TRS.SYSDESC.CHECK.004
    for index1 in range(len(all_ports)):
        for index2 in range(len(all_ports)):
            if index1 != index2:
                if all_ports[index1]['PORT'] == all_ports[index2]['PORT']:
                    if all_ports[index1]['BLOCK'] != all_ports[index2]['BLOCK']:
                        logger.error('Port ' + all_ports[index1]['PORT']['NAME'] + ' is defined in multiple blocks: ' + all_ports[index1]['BLOCK'] + ' and ' + all_ports[index2]['BLOCK'])
                        print('ERROR: Port ' + all_ports[index1]['PORT']['NAME'] + ' is defined in multiple blocks: ' + all_ports[index1]['BLOCK'] + ' and ' + all_ports[index2]['BLOCK'])
                        error_no = error_no + 1

    if error_no != 0:
        print("There is at least one blocking error! Check the generated log.")
        print("\nExecution stopped with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
        try:
            os.remove(output_path + '/NvM.epc')
            os.remove(output_path + '/NvDM.epc')
        except OSError:
            pass
        sys.exit(1)

    # implement TRS.MEMCFG.FUNC.004
    count = 0
    for block in blocks:
        line_size = 0
        for port in block['PORT']:
            if port['DATA-PROTOTYPE']:
                for indexD in range(len(port['DATA-PROTOTYPE'])):
                    if port['DATA-PROTOTYPE'][indexD]['SIZE']/8 > int(alignment):
                        if port['DATA-PROTOTYPE'][indexD]['REAL-TYPE'] != 'ARRAY':
                            logger.error('The port ' + port['NAME'] + ' has a referenced data element greater than the alignment: ' + port['DATA-PROTOTYPE'][indexD]['NAME'])
                            print('ERROR: The port ' + port['NAME'] + ' has a referenced data element greater than the alignment: ' + port['DATA-PROTOTYPE'][indexD]['NAME'])
                            sys.exit(1)
                        else:
                            line_size += port['DATA-PROTOTYPE'][indexD]['SIZE'] / 8
                            if line_size % int(alignment) > 0:
                                stuff_needed = line_size % int(alignment)
                                line_size -= port['DATA-PROTOTYPE'][indexD]['SIZE'] / 8
                                for cnt in range(0, int(int(alignment) - stuff_needed)):
                                    port['SIZE'] = port['SIZE'] + 1
                                    new_dict = {}
                                    new_dict['NAME'] = "Stuffing_" + str(count)
                                    count += 1
                                    new_dict['TYPE'] = "/Pack_sw_Types/tBYTE"
                                    new_dict['SIZE'] = 8
                                    new_dict['SW-BASE-TYPE'] = "/AUTOSAR_Platform/BaseTypes/uint8"
                                    new_dict['INIT'] = "0"
                                    new_dict['REAL-TYPE'] = "VALUE"
                                    port['DATA-PROTOTYPE'].insert(port['DATA-PROTOTYPE'].index(port['DATA-PROTOTYPE'][indexD]), new_dict)
                                    indexD += 1
                                line_size = 0
                                line_size += port['DATA-PROTOTYPE'][indexD]['SIZE'] / 8
                                continue
                            elif int(alignment) - line_size == 0:
                                line_size = 0
                    else:
                        line_size += port['DATA-PROTOTYPE'][indexD]['SIZE'] / 8
                        if int(alignment) - line_size < 0:
                            line_size -= port['DATA-PROTOTYPE'][indexD]['SIZE'] / 8
                            for cnt in range(0, int(int(alignment) - line_size)):
                                port['SIZE'] = port['SIZE'] + 1
                                new_dict = {}
                                new_dict['NAME'] = "Stuffing_" + str(count)
                                count += 1
                                new_dict['TYPE'] = "/Pack_sw_Types/tBYTE"
                                new_dict['SIZE'] = 8
                                new_dict['SW-BASE-TYPE'] = "/AUTOSAR_Platform/BaseTypes/uint8"
                                new_dict['INIT'] = "0"
                                new_dict['REAL-TYPE'] = "VALUE"
                                port['DATA-PROTOTYPE'].insert(port['DATA-PROTOTYPE'].index(port['DATA-PROTOTYPE'][indexD]), new_dict)
                                indexD += 1
                            line_size = 0
                            line_size += port['DATA-PROTOTYPE'][indexD]['SIZE']/8
                            continue
                        elif int(alignment) - line_size == 0:
                            line_size = 0

    # for internal blocks, if block['TYPE']=Specific, check that the total size does not surpass the profile max-size
    for block in blocks:
        if block['TYPE'] == 'Specific':
            block_size = 0
            for port in block['PORT']:
                block_size += port['SIZE']
            if block_size > int(block['MAX-SIZE']):
                logger.error('The block ' + block['NAME'] + ' is specific, but the total size is greater than the profile max-size')
                print('ERROR: The block ' + block['NAME'] + ' is specific, but the total size is greater than the profile max-size')
                error_no = error_no + 1
    # treat NvMResistantToChangedSw blocks separately
    fixed_blocks = []
    for block in blocks[:]:
        if block['RESISTENT'] == "True":
            fixed_blocks.append(block)
            blocks.remove(block)
    #fixed_blocks = sorted(fixed_blocks, key=lambda x: x['POSITION'])
    index = 0
    for block in fixed_blocks:
        block['ID'] = index
        index = index + 1
    for block in blocks:
        block['ID'] = index
        index = index + 1
    #############################
    if error_no != 0:
        print("There is at least one blocking error! Check the generated log.")
        print("\nExecution stopped with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
        try:
            os.remove(output_path + '/NvM.epc')
            os.remove(output_path + '/NvDM.epc')
        except OSError:
            pass
        sys.exit(1)
    # implement TRS.SYSDESC.FUNC.002
    blocks = sorted(blocks, key=lambda x: x['PROFILE'])
    for block in blocks[:]:
        subblock_number = 1
        temp_size = 0
        temp_ports = []
        splitted = False
        overhead = False
        obj_subblock = {}
        for port in block['PORT']:
            old_size = temp_size
            temp_size = temp_size + port['SIZE']
            if temp_size <= int(block['MAX-SIZE']):
                temp_ports.append(port)
                if splitted and block['PORT'].index(port) == len(block['PORT'])-1:
                    obj_subblock['NAME'] = block['NAME'] + "_" + str(subblock_number)
                    obj_subblock['TYPE'] = block['TYPE']
                    obj_subblock['PROFILE'] = block['PROFILE']
                    obj_subblock['TIMEOUT'] = block['TIMEOUT']
                    obj_subblock['MAPPING'] = block['MAPPING']
                    obj_subblock['DEVICE'] = block['DEVICE']
                    obj_subblock['CALLBACK'] = block['CALLBACK']
                    obj_subblock['CONSISTENCY'] = block['CONSISTENCY']
                    obj_subblock['CRC'] = block['CRC']
                    obj_subblock['SDF'] = block['SDF']
                    obj_subblock['ID'] = block['ID']
                    obj_subblock['SIZE'] = old_size
                    obj_subblock['PORT'] = temp_ports
                    new_dict = copy.deepcopy(obj_subblock)
                    subblocks.append(new_dict)
                    overhead = False
                    obj_subblock.clear()
            else:
                splitted = True
                overhead = True
                obj_subblock['NAME'] = block['NAME'] + '_' + str(subblock_number)
                subblock_number = subblock_number + 1
                obj_subblock['TYPE'] = block['TYPE']
                obj_subblock['PROFILE'] = block['PROFILE']
                obj_subblock['TIMEOUT'] = block['TIMEOUT']
                obj_subblock['MAPPING'] = block['MAPPING']
                obj_subblock['DEVICE'] = block['DEVICE']
                obj_subblock['CALLBACK'] = block['CALLBACK']
                obj_subblock['CONSISTENCY'] = block['CONSISTENCY']
                obj_subblock['CRC'] = block['CRC']
                obj_subblock['SDF'] = block['SDF']
                obj_subblock['ID'] = block['ID']
                obj_subblock['SIZE'] = old_size
                obj_subblock['PORT'] = temp_ports
                new_dict = copy.deepcopy(obj_subblock)
                subblocks.append(new_dict)
                obj_subblock.clear()
                temp_size = 0
                temp_size = temp_size + port['SIZE']
                del temp_ports[:]
                temp_ports.append(port)
        # create subblock with last elements
        if overhead:
            obj_subblock['NAME'] = block['NAME'] + '_' + str(subblock_number)
            subblock_number = subblock_number + 1
            obj_subblock['TYPE'] = block['TYPE']
            obj_subblock['PROFILE'] = block['PROFILE']
            obj_subblock['TIMEOUT'] = block['TIMEOUT']
            obj_subblock['MAPPING'] = block['MAPPING']
            obj_subblock['DEVICE'] = block['DEVICE']
            obj_subblock['CALLBACK'] = block['CALLBACK']
            obj_subblock['CONSISTENCY'] = block['CONSISTENCY']
            obj_subblock['CRC'] = block['CRC']
            obj_subblock['SDF'] = block['SDF']
            obj_subblock['ID'] = block['ID']
            obj_subblock['SIZE'] = old_size
            obj_subblock['PORT'] = temp_ports
            new_dict = copy.deepcopy(obj_subblock)
            subblocks.append(new_dict)
        # delete splitted blocks
        if splitted:
            blocks.remove(block)

    # implement TRS.SYSDESC.FUNC.001
    for block in fixed_blocks:
        obj_block = {}
        block_size = 0
        data_elements = []
        obj_block['NAME'] = block['NAME']
        obj_block['ID'] = block['ID']
        index = index + 1
        obj_block['MAPPING'] = block['MAPPING']
        obj_block['PROFILE'] = block['PROFILE']
        obj_block['DEVICE'] = block['DEVICE']
        obj_block['CALLBACK'] = block['CALLBACK']
        obj_block['TIMEOUT'] = block['TIMEOUT']
        obj_block['CONSISTENCY'] = block['CONSISTENCY']
        obj_block['CRC'] = block['CRC']
        obj_block['SDF'] = block['SDF']
        obj_block['POSITION'] = block['POSITION']
        for port in block['PORT']:
            for data in port['DATA-PROTOTYPE']:
                obj_data_prototype = {}
                obj_data_prototype['NAME'] = port['ASWC'] + "_" + port['NAME'].split('/')[-1] + "_" + data['NAME']
                obj_data_prototype['DATA'] = port['NAME'] + "/" + data['NAME']
                obj_data_prototype['SW-BASE-TYPE'] = data['SW-BASE-TYPE']
                obj_data_prototype['TYPE'] = data['TYPE']
                obj_data_prototype['INIT'] = data['INIT']
                obj_data_prototype['SIZE'] = data['SIZE']
                obj_data_prototype['REAL-TYPE'] = data['REAL-TYPE']
                block_size = block_size + int(data['SIZE'])
                data_elements.append(obj_data_prototype)
        obj_block['SIZE'] = int(block_size/8)
        obj_block['DATA'] = data_elements
        final_fixed_blocks.append(obj_block)
    final_blocks = []
    for subblock in subblocks:
        obj_block = {}
        block_size = 0
        data_elements = []
        obj_block['NAME'] = subblock['NAME']
        obj_block['ID'] = subblock['ID']
        index = index + 1
        obj_block['MAPPING'] = subblock['MAPPING']
        obj_block['PROFILE'] = subblock['PROFILE']
        obj_block['DEVICE'] = subblock['DEVICE']
        obj_block['CALLBACK'] = subblock['CALLBACK']
        obj_block['TIMEOUT'] = subblock['TIMEOUT']
        obj_block['CONSISTENCY'] = subblock['CONSISTENCY']
        obj_block['CRC'] = subblock['CRC']
        obj_block['SDF'] = subblock['SDF']
        obj_block['SIZE'] = subblock['SIZE']
        for port in subblock['PORT']:
            for data in port['DATA-PROTOTYPE']:
                obj_data_prototype = {}
                obj_data_prototype['NAME'] = port['ASWC'] + "_" + port['NAME'].split('/')[-1] + "_" + data['NAME']
                obj_data_prototype['DATA'] = port['NAME'] + "/" + data['NAME']
                obj_data_prototype['SW-BASE-TYPE'] = data['SW-BASE-TYPE']
                obj_data_prototype['TYPE'] = data['TYPE']
                obj_data_prototype['INIT'] = data['INIT']
                obj_data_prototype['SIZE'] = data['SIZE']
                obj_data_prototype['REAL-TYPE'] = data['REAL-TYPE']
                block_size = block_size + int(data['SIZE'])
                data_elements.append(obj_data_prototype)
        obj_block['SIZE'] = int(block_size/8)
        obj_block['DATA'] = data_elements
        final_blocks.append(obj_block)
    for block in blocks:
        obj_block = {}
        block_size = 0
        data_elements = []
        obj_block['NAME'] = block['NAME']
        obj_block['ID'] = block['ID']
        index = index + 1
        obj_block['MAPPING'] = block['MAPPING']
        obj_block['PROFILE'] = block['PROFILE']
        obj_block['DEVICE'] = block['DEVICE']
        obj_block['CALLBACK'] = block['CALLBACK']
        obj_block['TIMEOUT'] = block['TIMEOUT']
        obj_block['CONSISTENCY'] = block['CONSISTENCY']
        obj_block['CRC'] = block['CRC']
        obj_block['SDF'] = block['SDF']
        for port in block['PORT']:
            for data in port['DATA-PROTOTYPE']:
                obj_data_prototype = {}
                obj_data_prototype['NAME'] = port['ASWC'] + "_" + port['NAME'].split('/')[-1] + "_" + data['NAME']
                obj_data_prototype['DATA'] = port['NAME'] + "/" + data['NAME']
                obj_data_prototype['SW-BASE-TYPE'] = data['SW-BASE-TYPE']
                obj_data_prototype['TYPE'] = data['TYPE']
                obj_data_prototype['INIT'] = data['INIT']
                obj_data_prototype['SIZE'] = data['SIZE']
                obj_data_prototype['REAL-TYPE'] = data['REAL-TYPE']
                block_size = block_size + int(data['SIZE'])
                data_elements.append(obj_data_prototype)
        obj_block['SIZE'] = int(block_size/8)
        obj_block['DATA'] = data_elements
        final_blocks.append(obj_block)
    for block in final_blocks:
        if block['MAPPING'] == 'false':
            block['DATA'] = sorted(block['DATA'], key=lambda x: x['SIZE'], reverse=True)
    # determine the starting ID of the generated blocks
    #index = 4
    for block in final_fixed_blocks:
        obj_nvm = {}
        obj_nvm['NAME'] = block['NAME']
        obj_nvm['SOURCE'] = 'Intern'
        obj_nvm['DEVICE'] = block['DEVICE']
        obj_nvm['NvMNvramBlockIdentifier'] = 0
        obj_nvm['NvMRomBlockDataAddress'] = "&NvDM_RomBlock_" + block['NAME']
        obj_nvm['NvMNvBlockLength'] = block['SIZE']
        obj_nvm['NvMSingleBlockCallback'] = None
        obj_nvm['NvMNvBlockBaseNumber'] = 0
        obj_nvm['NvMNvBlockNum'] = 1
        obj_nvm['NvMWriteVerificationDataSize'] = None
        obj_nvm['NvMAdvancedRecovery'] = 'False'
        obj_nvm['NvMBlockUseSyncMechanism'] = 'False'
        obj_nvm['NvMBlockWriteProt'] = 'False'
        obj_nvm['NvMExtraBlockChecks'] = 'False'
        obj_nvm['NvMProvideRteAdminPort'] = 'False'
        obj_nvm['NvMProvideRteInitBlockPort'] = 'False'
        obj_nvm['NvMProvideRteJobFinishedPort'] = 'False'
        obj_nvm['NvMProvideRteMirrorPort'] = 'False'
        obj_nvm['NvMProvideRteServicePort'] = 'False'
        obj_nvm['NvMUserProvidesSpaceForBlockAndCrc'] = 'False'
        obj_nvm['NvMRPortInterfacesASRVersion'] = None
        obj_nvm['NvMInitBlockCallback'] = None
        obj_nvm['NvMReadRamBlockFromNvCallback'] = None
        obj_nvm['NvMWriteRamBlockToNvCallback'] = None
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
        obj_nvm['NvMBlockUseCrc'] = "False"
        obj_nvm['NvMNameOfFeeBlock'] = ""
        obj_nvm['NvMNameOfEaBlock'] = ""
        for profile in profiles:
            if profile['NAME'] == block['PROFILE']:
                for elem in profile['PARAM']:
                    if elem['TYPE'] == 'NvMNvBlockBaseNumber':
                        if 1 <= int(elem['VALUE']) <= 65534:
                            obj_nvm['NvMNvBlockBaseNumber'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMNvBlockBaseNumber is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMNvBlockBaseNumber is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMWriteVerificationDataSize':
                        if 1 <= int(elem['VALUE']) <= 65534:
                            obj_nvm['NvMWriteVerificationDataSize'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteVerificationDataSize is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMWriteVerificationDataSize is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBlockUseSyncMechanism':
                        if elem['VALUE'] in ['False', 'True', '0', '1']:
                            obj_nvm['NvMBlockUseSyncMechanism'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockUseSyncMechanism is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockUseSyncMechanism is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMInitBlockCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMInitBlockCallback'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMReadRamBlockFromNvCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMReadRamBlockFromNvCallback'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMWriteRamBlockToNvCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMWriteRamBlockToNvCallback'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMBlockWriteProt':
                        if elem['VALUE'] in ['False', 'True', '0', '1']:
                            obj_nvm['NvMBlockWriteProt'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockWriteProt is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockWriteProt is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMAdvancedRecovery':
                        obj_nvm['NvMAdvancedRecovery'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMNvramDeviceId':
                        obj_nvm['NvMNvramDeviceId'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMExtraBlockChecks':
                        obj_nvm['NvMExtraBlockChecks'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteAdminPort':
                        obj_nvm['NvMProvideRteAdminPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteInitBlockPort':
                        obj_nvm['NvMProvideRteInitBlockPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteJobFinishedPort':
                        obj_nvm['NvMProvideRteJobFinishedPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteMirrorPort':
                        obj_nvm['NvMProvideRteMirrorPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteServicePort':
                        obj_nvm['NvMProvideRteServicePort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMUserProvidesSpaceForBlockAndCrc':
                        obj_nvm['NvMUserProvidesSpaceForBlockAndCrc'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMRPortInterfacesASRVersion':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMRPortInterfacesASRVersion'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMBlockJobPriority':
                        if 0 <= int(elem['VALUE']) <= 255:
                            obj_nvm['NvMBlockJobPriority'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockJobPriority is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockJobPriority is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBlockCrcType':
                        if elem['VALUE'] in ['NVM_CRC8', 'NVM_CRC16', 'NVM_CRC32']:
                            obj_nvm['NvMBlockCrcType'] = elem['VALUE']
                            obj_nvm['NvMBlockUseCrc'] = "True"
                    if elem['TYPE'] == 'NvMBlockManagementType':
                        if elem['VALUE'] in ['NVM_BLOCK_REDUNDANT', 'NVM_BLOCK_NATIVE', 'NVM_BLOCK_DATASET']:
                            obj_nvm['NvMBlockManagementType'] = elem['VALUE']
                            obj_nvm['NvMBlockUseCrc'] = "True"
                        else:
                            logger.error('The parameter NvMBlockManagementType is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockManagementType is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMMaxNumOfReadRetries':
                        if 0 <= int(elem['VALUE']) <= 7:
                            obj_nvm['NvMMaxNumOfReadRetries'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMMaxNumOfReadRetries is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMMaxNumOfReadRetries is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMMaxNumOfWriteRetries':
                        if 0 <= int(elem['VALUE']) <= 7:
                            obj_nvm['NvMMaxNumOfWriteRetries'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMMaxNumOfWriteRetries is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMMaxNumOfWriteRetries is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMWriteBlockOnce':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMWriteBlockOnce'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteBlockOnce is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMWriteBlockOnce is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMWriteVerification':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMWriteVerification'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteVerification is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMWriteVerification is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMNvBlockNum':
                        if 1 <= int(elem['VALUE']) <= 255:
                            obj_nvm['NvMNvBlockNum'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMNvBlockNum is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMNvBlockNum is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMRomBlockNum':
                        if 0 <= int(elem['VALUE']) <= 254:
                            obj_nvm['NvMRomBlockNum'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMRomBlockNum is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMRomBlockNum is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBswMBlockStatusInformation':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMBswMBlockStatusInformation'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBswMBlockStatusInformation is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBswMBlockStatusInformation is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMCalcRamBlockCrc':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMCalcRamBlockCrc'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMResistantToChangedSw':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMResistantToChangedSw'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMResistantToChangedSw is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMResistantToChangedSw is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMSelectBlockForReadAll':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMSelectBlockForReadAll'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMSelectBlockForWriteAll':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMSelectBlockForWriteAll'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMStaticBlockIDCheck':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMStaticBlockIDCheck'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMStaticBlockIDCheck is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMStaticBlockIDCheck is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBlockUseAutoValidation':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMBlockUseAutoValidation'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockUseAutoValidation is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockUseAutoValidation is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMSingleBlockCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMSingleBlockCallback'] = elem['VALUE']
        if block['CALLBACK'] is not None:
            obj_nvm['NvMSingleBlockCallback'] = block['CALLBACK']
        for key, value in obj_nvm.items():
            if value is None:
                if key not in ['NvMRomBlockDataAddress', 'NvMBlockUseAutoValidation', 'NvMSingleBlockCallback', 'NvMSelectBlockForWriteAll', 'NvMSelectBlockForReadAll', 'NvMCalcRamBlockCrc', 'NvMBlockCrcType', 'NvMWriteRamBlockToNvCallback', 'NvMReadRamBlockFromNvCallback', 'NvMInitBlockCallback', 'NvMRPortInterfacesASRVersion', 'NvMWriteVerificationDataSize']:
                    logger.error('Mandatory parameters are not configured for NvM block ' + obj_nvm['NAME'] + ": " + key)
                    print('ERROR: Mandatory parameters are not configured for NvM block ' + obj_nvm['NAME'] + ": " + key)
                    error_no = error_no + 1
        nvm_blocks.append(obj_nvm)
    for block in final_blocks:
        obj_nvm = {}
        obj_nvm['NAME'] = block['NAME']
        obj_nvm['SOURCE'] = 'Intern'
        obj_nvm['DEVICE'] = block['DEVICE']
        obj_nvm['NvMNvramBlockIdentifier'] = 0
        obj_nvm['NvMRomBlockDataAddress'] = "&NvDM_RomBlock_" + block['NAME']
        obj_nvm['NvMNvBlockLength'] = block['SIZE']
        obj_nvm['NvMSingleBlockCallback'] = None
        obj_nvm['NvMNvBlockBaseNumber'] = 0
        obj_nvm['NvMNvBlockNum'] = 1
        obj_nvm['NvMWriteVerificationDataSize'] = None
        obj_nvm['NvMAdvancedRecovery'] = 'False'
        obj_nvm['NvMBlockUseSyncMechanism'] = 'False'
        obj_nvm['NvMBlockWriteProt'] = 'False'
        obj_nvm['NvMExtraBlockChecks'] = 'False'
        obj_nvm['NvMProvideRteAdminPort'] = 'False'
        obj_nvm['NvMProvideRteInitBlockPort'] = 'False'
        obj_nvm['NvMProvideRteJobFinishedPort'] = 'False'
        obj_nvm['NvMProvideRteMirrorPort'] = 'False'
        obj_nvm['NvMProvideRteServicePort'] = 'False'
        obj_nvm['NvMUserProvidesSpaceForBlockAndCrc'] = 'False'
        obj_nvm['NvMRPortInterfacesASRVersion'] = None
        obj_nvm['NvMInitBlockCallback'] = None
        obj_nvm['NvMReadRamBlockFromNvCallback'] = None
        obj_nvm['NvMWriteRamBlockToNvCallback'] = None
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
        obj_nvm['NvMBlockUseCrc'] = "False"
        obj_nvm['NvMNameOfFeeBlock'] = ""
        obj_nvm['NvMNameOfEaBlock'] = ""
        for profile in profiles:
            if profile['NAME'] == block['PROFILE']:
                for elem in profile['PARAM']:
                    if elem['TYPE'] == 'NvMNvBlockBaseNumber':
                        if 1 <= int(elem['VALUE']) <= 65534:
                            obj_nvm['NvMNvBlockBaseNumber'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMNvBlockBaseNumber is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMNvBlockBaseNumber is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMWriteVerificationDataSize':
                        if 1 <= int(elem['VALUE']) <= 65534:
                            obj_nvm['NvMWriteVerificationDataSize'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteVerificationDataSize is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMWriteVerificationDataSize is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBlockUseSyncMechanism':
                        if elem['VALUE'] in ['False', 'True', '0', '1']:
                            obj_nvm['NvMBlockUseSyncMechanism'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockUseSyncMechanism is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockUseSyncMechanism is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMInitBlockCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMInitBlockCallback'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMReadRamBlockFromNvCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMReadRamBlockFromNvCallback'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMWriteRamBlockToNvCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMWriteRamBlockToNvCallback'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMBlockWriteProt':
                        if elem['VALUE'] in ['False', 'True', '0', '1']:
                            obj_nvm['NvMBlockWriteProt'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockWriteProt is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockWriteProt is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMAdvancedRecovery':
                        obj_nvm['NvMAdvancedRecovery'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMNvramDeviceId':
                        obj_nvm['NvMNvramDeviceId'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMExtraBlockChecks':
                        obj_nvm['NvMExtraBlockChecks'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteAdminPort':
                        obj_nvm['NvMProvideRteAdminPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteInitBlockPort':
                        obj_nvm['NvMProvideRteInitBlockPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteJobFinishedPort':
                        obj_nvm['NvMProvideRteJobFinishedPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteMirrorPort':
                        obj_nvm['NvMProvideRteMirrorPort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMProvideRteServicePort':
                        obj_nvm['NvMProvideRteServicePort'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMUserProvidesSpaceForBlockAndCrc':
                        obj_nvm['NvMUserProvidesSpaceForBlockAndCrc'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMRPortInterfacesASRVersion':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMRPortInterfacesASRVersion'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMBlockJobPriority':
                        if 0 <= int(elem['VALUE']) <= 255:
                            obj_nvm['NvMBlockJobPriority'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockJobPriority is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockJobPriority is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBlockCrcType':
                        if elem['VALUE'] in ['NVM_CRC8', 'NVM_CRC16', 'NVM_CRC32']:
                            obj_nvm['NvMBlockCrcType'] = elem['VALUE']
                            obj_nvm['NvMBlockUseCrc'] = "True"
                    if elem['TYPE'] == 'NvMBlockManagementType':
                        if elem['VALUE'] in ['NVM_BLOCK_REDUNDANT', 'NVM_BLOCK_NATIVE', 'NVM_BLOCK_DATASET']:
                            obj_nvm['NvMBlockManagementType'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockManagementType is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockManagementType is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMMaxNumOfReadRetries':
                        if 0 <= int(elem['VALUE']) <= 7:
                            obj_nvm['NvMMaxNumOfReadRetries'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMMaxNumOfReadRetries is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMMaxNumOfReadRetries is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMMaxNumOfWriteRetries':
                        if 0 <= int(elem['VALUE']) <= 7:
                            obj_nvm['NvMMaxNumOfWriteRetries'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMMaxNumOfWriteRetries is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMMaxNumOfWriteRetries is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMWriteBlockOnce':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMWriteBlockOnce'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteBlockOnce is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMWriteBlockOnce is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMWriteVerification':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMWriteVerification'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMWriteVerification is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMWriteVerification is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMNvBlockNum':
                        if 1 <= int(elem['VALUE']) <= 255:
                            obj_nvm['NvMNvBlockNum'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMNvBlockNum is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMNvBlockNum is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMRomBlockNum':
                        if 0 <= int(elem['VALUE']) <= 254:
                            obj_nvm['NvMRomBlockNum'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMRomBlockNum is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMRomBlockNum is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBswMBlockStatusInformation':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMBswMBlockStatusInformation'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBswMBlockStatusInformation is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBswMBlockStatusInformation is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMCalcRamBlockCrc':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMCalcRamBlockCrc'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMResistantToChangedSw':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMResistantToChangedSw'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMResistantToChangedSw is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMResistantToChangedSw is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMSelectBlockForReadAll':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMSelectBlockForReadAll'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMSelectBlockForWriteAll':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMSelectBlockForWriteAll'] = elem['VALUE']
                    if elem['TYPE'] == 'NvMStaticBlockIDCheck':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMStaticBlockIDCheck'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMStaticBlockIDCheck is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMStaticBlockIDCheck is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMBlockUseAutoValidation':
                        if elem['VALUE'] in ['False', 'True']:
                            obj_nvm['NvMBlockUseAutoValidation'] = elem['VALUE']
                        else:
                            logger.error('The parameter NvMBlockUseAutoValidation is not correctly defined in profile ' + profile['NAME'])
                            print('ERROR: The parameter NvMBlockUseAutoValidation is not correctly defined in profile ' + profile['NAME'])
                            error_no = error_no + 1
                    if elem['TYPE'] == 'NvMSingleBlockCallback':
                        if elem['VALUE'] != "":
                            obj_nvm['NvMSingleBlockCallback'] = elem['VALUE']
        if block['CALLBACK'] is not None:
            obj_nvm['NvMSingleBlockCallback'] = block['CALLBACK']
        for key, value in obj_nvm.items():
            if value is None:
                if key not in ['NvMRomBlockDataAddress', 'NvMBlockUseAutoValidation', 'NvMSingleBlockCallback', 'NvMSelectBlockForWriteAll', 'NvMSelectBlockForReadAll', 'NvMCalcRamBlockCrc', 'NvMBlockCrcType', 'NvMWriteRamBlockToNvCallback', 'NvMReadRamBlockFromNvCallback', 'NvMInitBlockCallback', 'NvMRPortInterfacesASRVersion', 'NvMWriteVerificationDataSize']:
                    logger.error('Mandatory parameters are not configured for NvM block ' + obj_nvm['NAME'] + ": " + key)
                    print('ERROR: Mandatory parameters are not configured for NvM block ' + obj_nvm['NAME'] + ": " + key)
                    error_no = error_no + 1
        nvm_blocks.append(obj_nvm)
    # add extern blocks to the start of the list
    nvm_blocks = extern_blocks + nvm_blocks
    # check if there are NvMResistantToChangedSw blocks
    last_id = 0
    for block in nvm_blocks:
        if block['NvMResistantToChangedSw'] == "True" or block['NvMResistantToChangedSw'] == "1":
            found = False
            for mapping in mappings:
                if mapping['BLOCK'] == block['NAME']:
                    block['NvMNvramBlockIdentifier'] = int(mapping['POSITION'])
                    if int(mapping['POSITION']) > last_id:
                        last_id = int(mapping['POSITION'])
                    found = True
            if not found:
                logger.error('No mapping defined for block ' + block['NAME'])
                print('ERROR: No mapping defined for block ' + block['NAME'])
                error_no = error_no + 1
    # check if there are predefined blocks in the mapping file that are not in the input data
    for mapping in mappings:
        mapping_existent = False
        for block in nvm_blocks:
            if mapping['BLOCK'] == block['NAME']:
                if block['NvMResistantToChangedSw'] == 'True' or block['NvMResistantToChangedSw'] == '1':
                    mapping_existent = True
                else:
                    logger.error('Forbidden mapping for not ResistantToChangedSw block:' + mapping['BLOCK'])
                    print('ERROR: Forbidden mapping for not ResistantToChangedSw block:' + mapping['BLOCK'])
                    error_no = error_no + 1
        if not mapping_existent:
            logger.error('The mapped block ' + mapping['BLOCK'] + ' is not present in the input data')
            print('ERROR: The mapped block ' + mapping['BLOCK'] + ' is not present in the input data')
            error_no = error_no + 1
    # compute NvMNvramBlockIdentifier and the sort the blocks based on this parameter
    for block in nvm_blocks:
        if block['NvMNvramBlockIdentifier'] == 0:
            last_id = last_id + 1
            block['NvMNvramBlockIdentifier'] = last_id
    nvm_blocks = sorted(nvm_blocks, key=lambda x: x['NvMNvramBlockIdentifier'])
    # check that NvMNvramBlockIdentifier starts from 1 and is continuously
    if check_ordered(nvm_blocks):
        pass
    else:
        logger.error('The mapping index of all resistant-to-change blocks are not consecutive and continously: Start form 2 (1 is reserved)')
        print('ERROR: The mapping index of all resistant-to-change blocks are not consecutive and continously: Start form 2 (1 is reserved)')
        error_no = error_no + 1

    ##
    total_nb_nvm_blocks = 0
    immediate_nb_nvm_blocks = 0
    for block in nvm_blocks:
        total_nb_nvm_blocks = total_nb_nvm_blocks + 1
        if block['NvMBlockJobPriority'] == '0':
            immediate_nb_nvm_blocks = immediate_nb_nvm_blocks + 1
    ##############################
    if error_no != 0:
        print("There is at least one blocking error! Check the generated log.")
        print("\nExecution stopped with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
        try:
            os.remove(output_path + '/NvM.epc')
            os.remove(output_path + '/NvDM.epc')
        except OSError:
            pass
        sys.exit(1)
    # stuff blocks with padding bytes
    for block in nvm_blocks:
        if (8 * int(alignment)) - int(block['NvMNvBlockLength']) < 0:
            pass


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
    definition.text = "/AUTOSAR/EcuDefs/NvM"
    implementation = etree.SubElement(ecuc_module, 'IMPLEMENTATION-CONFIG-VARIANT').text = "VARIANT-PRE-COMPILE"
    containers = etree.SubElement(ecuc_module, 'CONTAINERS')
    # common data
    ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
    short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "NvMCommon"
    definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMCommon"
    parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
    ecuc_numerical_CompiledConfigID = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_CompiledConfigID, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMCommon/NvMCompiledConfigId"
    value = etree.SubElement(ecuc_numerical_CompiledConfigID, 'VALUE').text = config_ids[0]
    ecuc_numerical_StandardJob = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
    definition = etree.SubElement(ecuc_numerical_StandardJob, 'DEFINITION-REF')
    definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMCommon/NvMSizeStandardJobQueue"
    value = etree.SubElement(ecuc_numerical_StandardJob, 'VALUE').text = str(total_nb_nvm_blocks)
    if immediate_nb_nvm_blocks > 0:
        ecuc_numerical_ImmediateJob = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_ImmediateJob, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMCommon/NvMSizeImmediateJobQueue"
        value = etree.SubElement(ecuc_numerical_ImmediateJob, 'VALUE').text = str(immediate_nb_nvm_blocks)
    for block in nvm_blocks:
        if block['SOURCE'] == 'Extern':
            ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
            short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = block['NAME']
            definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor"
            parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
        else:
            ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
            short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "NvM_" + block['NAME']
            definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor"
            parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
        # NvMNvramBlockIdentifier
        ecuc_numerical_NvMNvramBlockIdentifier = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMNvramBlockIdentifier, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMNvramBlockIdentifier"
        value = etree.SubElement(ecuc_numerical_NvMNvramBlockIdentifier, 'VALUE').text = str(block['NvMNvramBlockIdentifier'])
        # NvMNvBlockBaseNumber
        ecuc_numerical_NvMNvBlockBaseNumber = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMNvBlockBaseNumber, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMNvBlockBaseNumber"
        value = etree.SubElement(ecuc_numerical_NvMNvBlockBaseNumber, 'VALUE').text = str(block['NvMNvBlockBaseNumber'])
        # NvMNvBlockNum
        ecuc_numerical_NvMNvBlockNum = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMNvBlockNum, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMNvBlockNum"
        value = etree.SubElement(ecuc_numerical_NvMNvBlockNum, 'VALUE').text = str(block['NvMNvBlockNum'])
        # NvMWriteVerificationDataSize
        if 'NvMWriteVerificationDataSize' in block.keys():
            if block['NvMWriteVerificationDataSize'] is not None:
                ecuc_numerical_NvMWriteVerificationDataSize = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvMWriteVerificationDataSize, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMWriteVerificationDataSize"
                value = etree.SubElement(ecuc_numerical_NvMWriteVerificationDataSize, 'VALUE').text = str(block['NvMWriteVerificationDataSize'])
        # NvMBlockUseSyncMechanism
        ecuc_numerical_NvMBlockUseSyncMechanism = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBlockUseSyncMechanism, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockUseSyncMechanism"
        value = etree.SubElement(ecuc_numerical_NvMBlockUseSyncMechanism, 'VALUE').text = str(block['NvMBlockUseSyncMechanism'])
        # NvMBlockWriteProt
        ecuc_numerical_NvMBlockWriteProt = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBlockWriteProt, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockWriteProt"
        value = etree.SubElement(ecuc_numerical_NvMBlockWriteProt, 'VALUE').text = str(block['NvMBlockWriteProt'])
        # NvMInitBlockCallback
        if 'NvMInitBlockCallback' in block.keys():
            if block['SOURCE'] == 'Extern':
                if block['NvMInitBlockCallback'] is not None:
                    ecuc_numerical_NvMInitBlockCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                    definition = etree.SubElement(ecuc_numerical_NvMInitBlockCallback, 'DEFINITION-REF')
                    definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMInitBlockCallback"
                    value = etree.SubElement(ecuc_numerical_NvMInitBlockCallback, 'VALUE').text = block['NvMInitBlockCallback']
            else:
                if block['NvMInitBlockCallback'] == 'True' or block['NvMInitBlockCallback'] == '1':
                    ecuc_numerical_NvMInitBlockCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                    definition = etree.SubElement(ecuc_numerical_NvMInitBlockCallback, 'DEFINITION-REF')
                    definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMInitBlockCallback"
                    value = etree.SubElement(ecuc_numerical_NvMInitBlockCallback, 'VALUE').text = 'InitBlock_' + block['NAME']
        # NvMReadRamBlockFromNvCallback
        if 'NvMReadRamBlockFromNvCallback' in block.keys():
            if block['NvMReadRamBlockFromNvCallback'] == 'True' or block['NvMReadRamBlockFromNvCallback'] == '1':
                ecuc_textual_NvMReadRamBlockFromNvCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMReadRamBlockFromNvCallback, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMReadRamBlockFromNvCallback"
                value = etree.SubElement(ecuc_textual_NvMReadRamBlockFromNvCallback, 'VALUE').text = 'ReadRamFromNv_' + block['NAME']
        # NvMWriteRamBlockToNvCallback
        if 'NvMWriteRamBlockToNvCallback' in block.keys():
            if block['NvMWriteRamBlockToNvCallback'] == 'True' or block['NvMWriteRamBlockToNvCallback'] == '1':
                ecuc_textual_NvMWriteRamBlockToNvCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMWriteRamBlockToNvCallback, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMWriteRamBlockToNvCallback"
                value = etree.SubElement(ecuc_textual_NvMWriteRamBlockToNvCallback, 'VALUE').text = 'WriteRamToNv_' + block['NAME']
        # NvMBlockUseSetRamBlockStatus
        if 'NvMBlockUseSetRamBlockStatus' in block.keys():
            if block['SOURCE'] == 'Extern':
                if block['NvMBlockUseSetRamBlockStatus'] == 'True' or block['NvMBlockUseSetRamBlockStatus'] == '1':
                    ecuc_textual_NvMWriteRamBlockToNvCallback = etree.SubElement(parameter, 'ECUC-BOOLEAN-PARAM-VALUE')
                    definition = etree.SubElement(ecuc_textual_NvMWriteRamBlockToNvCallback, 'DEFINITION-REF')
                    definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockUseSetRamBlockStatus"
                    value = etree.SubElement(ecuc_textual_NvMWriteRamBlockToNvCallback, 'VALUE').text = block['NvMBlockUseSetRamBlockStatus']
        # NvMNvBlockLength
        ecuc_textual_NvMNvBlockLength = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMNvBlockLength, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMNvBlockLength"
        value = etree.SubElement(ecuc_textual_NvMNvBlockLength, 'VALUE').text = str(block['NvMNvBlockLength'])
        # NvMAdvancedRecovery
        ecuc_textual_NvMAdvancedRecovery = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMAdvancedRecovery, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMAdvancedRecovery"
        value = etree.SubElement(ecuc_textual_NvMAdvancedRecovery, 'VALUE').text = str(block['NvMAdvancedRecovery'])
        # NvMExtraBlockChecks
        ecuc_textual_NvMExtraBlockChecks = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMExtraBlockChecks, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMExtraBlockChecks"
        value = etree.SubElement(ecuc_textual_NvMExtraBlockChecks, 'VALUE').text = str(block['NvMExtraBlockChecks'])
        # NvMProvideRteAdminPort
        ecuc_textual_NvMProvideRteAdminPort = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMProvideRteAdminPort, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMProvideRteAdminPort"
        value = etree.SubElement(ecuc_textual_NvMProvideRteAdminPort, 'VALUE').text = str(block['NvMProvideRteAdminPort'])
        # NvMProvideRteInitBlockPort
        ecuc_textual_NvMProvideRteInitBlockPort = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMProvideRteInitBlockPort, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMProvideRteInitBlockPort"
        value = etree.SubElement(ecuc_textual_NvMProvideRteInitBlockPort, 'VALUE').text = str(block['NvMProvideRteInitBlockPort'])
        # NvMProvideRteJobFinishedPort
        ecuc_textual_NvMProvideRteJobFinishedPort = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMProvideRteJobFinishedPort, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMProvideRteJobFinishedPort"
        value = etree.SubElement(ecuc_textual_NvMProvideRteJobFinishedPort, 'VALUE').text = str(block['NvMProvideRteJobFinishedPort'])
        # NvMProvideRteMirrorPort
        ecuc_textual_NvMProvideRteMirrorPort = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMProvideRteMirrorPort, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMProvideRteMirrorPort"
        value = etree.SubElement(ecuc_textual_NvMProvideRteMirrorPort, 'VALUE').text = str(block['NvMProvideRteMirrorPort'])
        # NvMProvideRteServicePort
        ecuc_textual_NvMProvideRteServicePort = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMProvideRteServicePort, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMProvideRteServicePort"
        value = etree.SubElement(ecuc_textual_NvMProvideRteServicePort, 'VALUE').text = str(block['NvMProvideRteServicePort'])
        # NvMUserProvidesSpaceForBlockAndCrc
        ecuc_textual_NvMUserProvidesSpaceForBlockAndCrc = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMUserProvidesSpaceForBlockAndCrc, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMUserProvidesSpaceForBlockAndCrc"
        value = etree.SubElement(ecuc_textual_NvMUserProvidesSpaceForBlockAndCrc, 'VALUE').text = str(block['NvMUserProvidesSpaceForBlockAndCrc'])
        # NvMRPortInterfacesASRVersion
        if 'NvMRPortInterfacesASRVersion' in block.keys():
            if block['NvMRPortInterfacesASRVersion'] is not None:
                ecuc_textual_NvMRPortInterfacesASRVersion = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMRPortInterfacesASRVersion, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMRPortInterfacesASRVersion"
                value = etree.SubElement(ecuc_textual_NvMRPortInterfacesASRVersion, 'VALUE').text = block['NvMRPortInterfacesASRVersion']
        # NvMRomBlockDataAddress
        if 'NvMRomBlockDataAddress' in block.keys():
            if block['NvMRomBlockDataAddress'] is not None:
                ecuc_textual_NvMRomBlockDataAddress = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMRomBlockDataAddress, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMRomBlockDataAddress"
                value = etree.SubElement(ecuc_textual_NvMRomBlockDataAddress, 'VALUE').text = block['NvMRomBlockDataAddress']
        # NvMRamBlockDataAddress
        if 'NvMRamBlockDataAddress' in block.keys():
            if block['NvMRamBlockDataAddress'] is not None:
                ecuc_textual_NvMRamBlockDataAddress = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMRamBlockDataAddress, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-STRING-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMRamBlockDataAddress"
                value = etree.SubElement(ecuc_textual_NvMRamBlockDataAddress, 'VALUE').text = block['NvMRamBlockDataAddress']
        # NvMSingleBlockCallback
        if 'NvMSingleBlockCallback' in block.keys():
            if block['NvMSingleBlockCallback'] == 'True' or block['NvMSingleBlockCallback'] == '1':
                ecuc_textual_NvMSingleBlockCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMSingleBlockCallback, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMSingleBlockCallback"
                value = etree.SubElement(ecuc_textual_NvMSingleBlockCallback, 'VALUE').text = 'SingleBlock_' + block['NAME']
            else:
                # TRS.MEMCFG.GEN.018(0)
                ecuc_textual_NvMSingleBlockCallback = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMSingleBlockCallback, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FUNCTION-NAME-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMSingleBlockCallback"
                value = etree.SubElement(ecuc_textual_NvMSingleBlockCallback, 'VALUE').text = block['NvMSingleBlockCallback']
        # NvMBlockUseAutoValidation
        if 'NvMBlockUseAutoValidation' in block.keys():
            if block['NvMBlockUseAutoValidation'] is not None:
                ecuc_numerical_NvMBlockUseAutoValidation = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvMBlockUseAutoValidation, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockUseAutoValidation"
                value = etree.SubElement(ecuc_numerical_NvMBlockUseAutoValidation, 'VALUE').text = block['NvMBlockUseAutoValidation']
        # NvMStaticBlockIDCheck
        ecuc_numerical_NvMStaticBlockIDCheck = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMStaticBlockIDCheck, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMStaticBlockIDCheck"
        value = etree.SubElement(ecuc_numerical_NvMStaticBlockIDCheck, 'VALUE').text = block['NvMStaticBlockIDCheck']
        # NvMSelectBlockForWriteAll
        if 'NvMSelectBlockForWriteAll' in block.keys():
            if 'NvMSelectBlockForWriteAll' in block.keys():
                if block['NvMSelectBlockForWriteAll'] is not None:
                    ecuc_numerical_NvMSelectBlockForWriteAll = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                    definition = etree.SubElement(ecuc_numerical_NvMSelectBlockForWriteAll, 'DEFINITION-REF')
                    definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                    definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMSelectBlockForWriteAll"
                    value = etree.SubElement(ecuc_numerical_NvMSelectBlockForWriteAll, 'VALUE').text = block['NvMSelectBlockForWriteAll']
        # NvMSelectBlockForReadAll
        if 'NvMSelectBlockForReadAll' in block.keys():
            if block['NvMSelectBlockForReadAll'] is not None:
                ecuc_numerical_NvMSelectBlockForReadAll = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvMSelectBlockForReadAll, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMSelectBlockForReadAll"
                value = etree.SubElement(ecuc_numerical_NvMSelectBlockForReadAll, 'VALUE').text = block['NvMSelectBlockForReadAll']
        # NvMResistantToChangedSw
        ecuc_numerical_NvMResistantToChangedSw = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMResistantToChangedSw, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMResistantToChangedSw"
        value = etree.SubElement(ecuc_numerical_NvMResistantToChangedSw, 'VALUE').text = block['NvMResistantToChangedSw']
        # NvMCalcRamBlockCrc
        if 'NvMCalcRamBlockCrc' in block.keys():
            if block['NvMCalcRamBlockCrc'] is not None:
                ecuc_numerical_NvMCalcRamBlockCrc = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvMCalcRamBlockCrc, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMCalcRamBlockCrc"
                value = etree.SubElement(ecuc_numerical_NvMCalcRamBlockCrc, 'VALUE').text = block['NvMCalcRamBlockCrc']
        # NvMBlockUseCrc
        ecuc_numerical_NvMBlockUseCrc = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBlockUseCrc, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockUseCrc"
        value = etree.SubElement(ecuc_numerical_NvMBlockUseCrc, 'VALUE').text = block['NvMBlockUseCrc']
        # NvMBswMBlockStatusInformation
        ecuc_numerical_NvMBswMBlockStatusInformation = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBswMBlockStatusInformation, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBswMBlockStatusInformation"
        value = etree.SubElement(ecuc_numerical_NvMBswMBlockStatusInformation, 'VALUE').text = block['NvMBswMBlockStatusInformation']
        # NvMRomBlockNum
        ecuc_numerical_NvMRomBlockNum = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMRomBlockNum, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMRomBlockNum"
        value = etree.SubElement(ecuc_numerical_NvMRomBlockNum, 'VALUE').text = block['NvMRomBlockNum']
        # NvMNvramDeviceId
        ecuc_numerical_NvMNvramDeviceId = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMNvramDeviceId, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMNvramDeviceId"
        value = etree.SubElement(ecuc_numerical_NvMNvramDeviceId, 'VALUE').text = block['NvMNvramDeviceId']
        # NvMWriteVerification
        ecuc_numerical_NvMWriteVerification = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMWriteVerification, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMWriteVerification"
        value = etree.SubElement(ecuc_numerical_NvMWriteVerification, 'VALUE').text = block['NvMWriteVerification']
        # NvMWriteBlockOnce
        ecuc_numerical_NvMWriteBlockOnce = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMWriteBlockOnce, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMWriteBlockOnce"
        value = etree.SubElement(ecuc_numerical_NvMWriteBlockOnce, 'VALUE').text = block['NvMWriteBlockOnce']
        # NvMMaxNumOfWriteRetries
        ecuc_numerical_NvMMaxNumOfWriteRetries = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMMaxNumOfWriteRetries, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMMaxNumOfWriteRetries"
        value = etree.SubElement(ecuc_numerical_NvMMaxNumOfWriteRetries, 'VALUE').text = block['NvMMaxNumOfWriteRetries']
        # NvMMaxNumOfReadRetries
        ecuc_numerical_NvMMaxNumOfReadRetries = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMMaxNumOfReadRetries, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMMaxNumOfReadRetries"
        value = etree.SubElement(ecuc_numerical_NvMMaxNumOfReadRetries, 'VALUE').text = block['NvMMaxNumOfReadRetries']
        # NvMBlockJobPriority
        ecuc_numerical_NvMBlockJobPriority = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_numerical_NvMBlockJobPriority, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockJobPriority"
        value = etree.SubElement(ecuc_numerical_NvMBlockJobPriority, 'VALUE').text = block['NvMBlockJobPriority']
        # NvMBlockManagementType
        ecuc_textual_NvMBlockManagementType = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
        definition = etree.SubElement(ecuc_textual_NvMBlockManagementType, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockManagementType"
        value = etree.SubElement(ecuc_textual_NvMBlockManagementType, 'VALUE').text = block['NvMBlockManagementType']
        # NvMBlockCrcType
        if 'NvMBlockCrcType' in block.keys():
            if block['NvMBlockCrcType'] is not None:
                ecuc_textual_NvMBlockCrcType = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvMBlockCrcType, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMBlockCrcType"
                value = etree.SubElement(ecuc_textual_NvMBlockCrcType, 'VALUE').text = block['NvMBlockCrcType']
        # FEE or EA reference
        subcontainers = etree.SubElement(ecuc_container, 'SUB-CONTAINERS')
        container = etree.SubElement(subcontainers, 'ECUC-CONTAINER-VALUE')
        short_name = etree.SubElement(container, 'SHORT-NAME').text = "NvMTargetBlockReference"
        definition = etree.SubElement(container, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-CHOICE-CONTAINER-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMTargetBlockReference"
        subcontainer = etree.SubElement(container, 'SUB-CONTAINERS')
        container_value = etree.SubElement(subcontainer, 'ECUC-CONTAINER-VALUE')
        short_name = etree.SubElement(container_value, 'SHORT-NAME').text = "NvMTargetBlockReference"
        if block['DEVICE'] in ["FEE", "Fee", "fee"]:
            definition = etree.SubElement(container_value, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMFeeRef"
            reference_values = etree.SubElement(container_value, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-SYMBOLIC-NAME-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMFeeRef/NvMNameOfFeeBlock"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "ECUC-CONTAINER-VALUE"
            value.text = block['NvMNameOfFeeBlock']
        else:
            definition = etree.SubElement(container_value, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMEaRef"
            reference_values = etree.SubElement(container_value, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-SYMBOLIC-NAME-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvM/NvMBlockDescriptor/NvMTargetBlockReference/NvMEaRef/NvMNameOfEaBlock"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "ECUC-CONTAINER-VALUE"
            value.text = block['NvMNameOfEaBlock']
    pretty_xml = new_prettify(rootNvM)
    output = etree.ElementTree(etree.fromstring(pretty_xml))
    output.write(output_path + '/NvM.epc', encoding='UTF-8', xml_declaration=True, method="xml", doctype="<!-- XML file generated by MEM_Configurator-16 -->")

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
    definition.text = "/AUTOSAR/EcuDefs/NvDM"
    implementation = etree.SubElement(ecuc_module, 'IMPLEMENTATION-CONFIG-VARIANT').text = "VARIANT-PRE-COMPILE"
    containers = etree.SubElement(ecuc_module, 'CONTAINERS')
    for block in final_fixed_blocks:
        ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
        #short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "NvDM_" + block['NAME']
        short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = block['NAME']
        definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor"
        parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
        for profile in profiles:
            if profile['NAME'] == block['PROFILE']:
                # NvDMDurability
                ecuc_textual_NvDMDurability = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvDMDurability, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMDurability"
                value = etree.SubElement(ecuc_textual_NvDMDurability, 'VALUE').text = profile['DURABILITY']
                # NvDMSafetyBlock
                ecuc_numerical_NvDMSafetyBlock = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMSafetyBlock, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMSafetyBlock"
                value = etree.SubElement(ecuc_numerical_NvDMSafetyBlock, 'VALUE')
                if block['SDF'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMConsistency
                ecuc_numerical_NvDMConsistency = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMConsistency, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMConsistency"
                value = etree.SubElement(ecuc_numerical_NvDMConsistency, 'VALUE')
                if profile['CONSISTENCY'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMCRC
                ecuc_numerical_NvDMCRC = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMCRC, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMCRC"
                value = etree.SubElement(ecuc_numerical_NvDMCRC, 'VALUE')
                if profile['CRC'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMWriteTimeout
                ecuc_numerical_NvDMWriteTimeout = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMWriteTimeout, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FLOAT-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMWriteTimeout"
                value = etree.SubElement(ecuc_numerical_NvDMWriteTimeout, 'VALUE').text = block['TIMEOUT']
                # NvDMWritingManagement
                # ecuc_textual_NvDMWritingManagement = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                # definition = etree.SubElement(ecuc_textual_NvDMWritingManagement, 'DEFINITION-REF')
                # definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                # definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMWritingManagement"
                # value = etree.SubElement(ecuc_textual_NvDMWritingManagement, 'VALUE').text = profile['MANAGEMENT']
                # NvDMProfile
                ecuc_textual_NvDMProfile = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvDMProfile, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMProfile"
                value = etree.SubElement(ecuc_textual_NvDMProfile, 'VALUE').text = profile['NAME']
                # NvDMBlockSize
                ecuc_numerical_NvDMBlockSize = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMBlockSize, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMBlockSize"
                value = etree.SubElement(ecuc_numerical_NvDMBlockSize, 'VALUE').text = str(block['SIZE'])
                # NvDMBlockID
                ecuc_numerical_NvDMBlockID = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMBlockID, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMBlockID"
                value = etree.SubElement(ecuc_numerical_NvDMBlockID, 'VALUE').text = str(block['ID'])
        reference = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
        ecuc_container_reference = etree.SubElement(reference, 'ECUC-REFERENCE-VALUE')
        ecuc_reference = etree.SubElement(ecuc_container_reference, 'DEFINITION-REF')
        ecuc_reference.attrib['DEST'] = "ECUC-REFERENCE-DEF"
        ecuc_reference.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMNvMBlockDescriptorRef"
        value = etree.SubElement(ecuc_container_reference, 'VALUE-REF')
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
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype"
            parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
            ecuc_reference_values = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FLOAT-PARAM-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMInitValue"
            value = etree.SubElement(ecuc_reference_values, 'VALUE')
            value.text = element['INIT']
            ecuc_reference_values = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMArray"
            value = etree.SubElement(ecuc_reference_values, 'VALUE')
            if element['REAL-TYPE'] != "ARRAY":
                value.text = "false"
            else:
                value.text = "true"
            reference_values = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMBaseTypeRef"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "SW-BASE-TYPE"
            value.text = element['SW-BASE-TYPE']
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMVariableDataPrototypeRef"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "VARIABLE-DATA-PROTOTYPE"
            value.text = element['DATA']
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMTypeRef"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "IMPLEMENTATION-DATA-TYPE"
            value.text = element['TYPE']
    index = len(fixed_blocks)
    for block in final_blocks:
        ecuc_container = etree.SubElement(containers, 'ECUC-CONTAINER-VALUE')
        #short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = "NvDM_" + block['NAME']
        short_name = etree.SubElement(ecuc_container, 'SHORT-NAME').text = block['NAME']
        definition = etree.SubElement(ecuc_container, 'DEFINITION-REF')
        definition.attrib['DEST'] = "ECUC-PARAM-CONF-CONTAINER-DEF"
        definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor"
        parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
        for profile in profiles:
            if profile['NAME'] == block['PROFILE']:
                # NvDMDurability
                ecuc_textual_NvDMDurability = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvDMDurability, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMDurability"
                value = etree.SubElement(ecuc_textual_NvDMDurability, 'VALUE').text = profile['DURABILITY']
                # NvDMSafetyBlock
                ecuc_numerical_NvDMSafetyBlock = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMSafetyBlock, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMSafetyBlock"
                value = etree.SubElement(ecuc_numerical_NvDMSafetyBlock, 'VALUE')
                if block['SDF'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMConsistency
                ecuc_numerical_NvDMConsistency = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMConsistency, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMConsistency"
                value = etree.SubElement(ecuc_numerical_NvDMConsistency, 'VALUE')
                if profile['CONSISTENCY'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMCRC
                ecuc_numerical_NvDMCRC = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMCRC, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMCRC"
                value = etree.SubElement(ecuc_numerical_NvDMCRC, 'VALUE')
                if profile['CRC'] == 'true':
                    value.text = '1'
                else:
                    value.text = '0'
                # NvDMWriteTimeout
                ecuc_numerical_NvDMWriteTimeout = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMWriteTimeout, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-FLOAT-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMWriteTimeout"
                value = etree.SubElement(ecuc_numerical_NvDMWriteTimeout, 'VALUE').text = block['TIMEOUT']
                # NvDMWritingManagement
                # ecuc_textual_NvDMWritingManagement = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                # definition = etree.SubElement(ecuc_textual_NvDMWritingManagement, 'DEFINITION-REF')
                # definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                # definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMWritingManagement"
                # value = etree.SubElement(ecuc_textual_NvDMWritingManagement, 'VALUE').text = profile['MANAGEMENT']
                # NvDMProfile
                ecuc_textual_NvDMProfile = etree.SubElement(parameter, 'ECUC-TEXTUAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_textual_NvDMProfile, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-ENUMERATION-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMProfile"
                value = etree.SubElement(ecuc_textual_NvDMProfile, 'VALUE').text = profile['NAME']
                # NvDMBlockSize
                ecuc_numerical_NvDMBlockSize = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMBlockSize, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMBlockSize"
                value = etree.SubElement(ecuc_numerical_NvDMBlockSize, 'VALUE').text = str(block['SIZE'])
                # NvDMBlockID
                ecuc_numerical_NvDMBlockID = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
                definition = etree.SubElement(ecuc_numerical_NvDMBlockID, 'DEFINITION-REF')
                definition.attrib['DEST'] = "ECUC-INTEGER-PARAM-DEF"
                definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMBlockID"
                value = etree.SubElement(ecuc_numerical_NvDMBlockID, 'VALUE').text = str(block['ID'])
        reference = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
        ecuc_container_reference = etree.SubElement(reference, 'ECUC-REFERENCE-VALUE')
        ecuc_reference = etree.SubElement(ecuc_container_reference, 'DEFINITION-REF')
        ecuc_reference.attrib['DEST'] = "ECUC-REFERENCE-DEF"
        ecuc_reference.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMNvMBlockDescriptorRef"
        value = etree.SubElement(ecuc_container_reference, 'VALUE-REF')
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
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype"
            parameter = etree.SubElement(ecuc_container, 'PARAMETER-VALUES')
            ecuc_reference_values = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FLOAT-PARAM-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMInitValue"
            value = etree.SubElement(ecuc_reference_values, 'VALUE')
            value.text = element['INIT']
            ecuc_reference_values = etree.SubElement(parameter, 'ECUC-NUMERICAL-PARAM-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-BOOLEAN-PARAM-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMArray"
            value = etree.SubElement(ecuc_reference_values, 'VALUE')
            if element['REAL-TYPE'] != "ARRAY":
                value.text = "false"
            else:
                value.text = "true"
            reference_values = etree.SubElement(ecuc_container, 'REFERENCE-VALUES')
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMBaseTypeRef"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "SW-BASE-TYPE"
            value.text = element['SW-BASE-TYPE']
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMVariableDataPrototypeRef"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "VARIABLE-DATA-PROTOTYPE"
            value.text = element['DATA']
            ecuc_reference_values = etree.SubElement(reference_values, 'ECUC-REFERENCE-VALUE')
            definition = etree.SubElement(ecuc_reference_values, 'DEFINITION-REF')
            definition.attrib['DEST'] = "ECUC-FOREIGN-REFERENCE-DEF"
            definition.text = "/AUTOSAR/EcuDefs/NvDM/NvDMBlockDescriptor/NvDMVariableDataPrototype/NvDMTypeRef"
            value = etree.SubElement(ecuc_reference_values, 'VALUE-REF')
            value.attrib['DEST'] = "IMPLEMENTATION-DATA-TYPE"
            value.text = element['TYPE']
    pretty_xml = new_prettify(rootNvDM)
    output = etree.ElementTree(etree.fromstring(pretty_xml))
    output.write(output_path + '/NvDM.epc', encoding='UTF-8', xml_declaration=True, method="xml", doctype="<!-- XML file generated by MEM_Configurator-16 -->")
    ##########################################
    if error_no != 0:
        print("There is at least one blocking error! Check the generated log.")
        print("\nExecution stopped with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
        try:
            os.remove(output_path + '/NvM.epc')
            os.remove(output_path + '/NvDM.epc')
        except OSError:
            pass
        sys.exit(1)
    else:
        print("\nExecution finished with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
    # except Exception as e:
    #     print("Unexpected error: " + str(e))
    #     print("\nExecution stopped with: " + str(info_no) + " infos, " + str(warning_no) + " warnings, " + str(error_no) + " errors\n")
    #     try:
    #         os.remove(output_path + '/NvM.epc')
    #         os.remove(output_path + '/NvDM.epc')
    #     except OSError:
    #         pass
    #     sys.exit(1)


if __name__ == "__main__":                                          # pragma: no cover
    # process = psutil.Process(os.getpid())                         # pragma: no cover
    # start_time = time.clock()                                     # pragma: no cover
    # cov = Coverage()                                                # pragma: no cover
    # cov.start()                                                     # pragma: no cover
    main()                                                          # pragma: no cover
    # cov.stop()                                                      # pragma: no cover
    # cov.html_report(directory='Coverage Report')                      # pragma: no cover
    # print(str(time.clock() - start_time) + " seconds")            # pragma: no cover
    # print(str(process.memory_info()[0]/float(2**20)) + " MB")     # pragma: no cover
