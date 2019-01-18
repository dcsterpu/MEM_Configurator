import unittest
import os
import os.path
import re
import ntpath
import HtmlTestRunner
from lxml import etree

class FileCompare():
    def areSame(first_location, second_location):
        file1 = open(first_location)
        file2 = open(second_location)

        line_file1 = file1.readline()
        line_file2 = file2.readline()

        while line_file1 != "" or line_file2 != "":
            line_file1 = line_file1.rstrip()
            line_file1 = line_file1.lstrip()
            line_file2 = line_file2.rstrip()
            line_file2 = line_file2.lstrip()
            if line_file1 != line_file2:
                return False
            line_file1 = file1.readline()
            line_file2 = file2.readline()

        file1.close()
        file2.close()
        return True

    def matchLine(path, line_number, text):
        """
        path = used for defining the file to be checked
        line_number = used to identify the line that will be checked
        text = string containing the text to match
        """
        datafile = open(path)
        line_file = datafile.readline()
        line_file = line_file.rstrip()
        line_no = 1
        while line_file != "":
            if line_no == line_number:
                if line_file == text:
                    return True
                else:
                    return False
            line_no = line_no+1
            line_file = datafile.readline()
            line_file = line_file.rstrip()

    def checkLog(path, level, message):
        """
        path = used for defining the file to be checked
        level = event name or criticity level :INFO, WARNING, ERROR
        message = string to be matched
        """
        datafile = open(path)
        line_file = datafile.readline()
        while line_file != "":
            for text in message:
                if level in line_file:
                    if text in line_file:
                        # print(line_file)
                        return True
            line_file = datafile.readline()
        return False

    def checkError(path, level, message):
        """
        path = used for defining the file to be checked
        level = criticity level :INFO, WARNING, ERROR
        message = string to be matched
        """
        datafile = open(path)
        line_file = datafile.readline()
        while line_file != "":
            for text in message:
                if level in line_file:
                    if text in line_file:
                        # print(line_file)
                        return True
            line_file = datafile.readline()
        return False

    def checkParsing(path1, path2, extension, message):
        """
        path1 = used for taking the .arxml files name
        path2 = used for defining the file to be checked
        message = string to be matched
        extension = file extension
        """
        all_files = []
        for path, dirs, file in os.walk(path1):
            for f in file:
                if f.endswith(extension):
                    all_files.append(f)
        datafile = open(path2)
        line_file = datafile.readline()
        i = 0
        while line_file != "" and all_files:
            for files in all_files:
                if files + " " + message in line_file:
                    all_files.remove(files)
                    i = i + 1
            line_file = datafile.readline()
        if not all_files:
            return True
        else:
            return False

    def isOutput(path):
        """
        path = used for defining the folder to be checked
        """
        if os.path.isfile(path):
            return True
        else:
            return False

    def areSorted(path):
        """
        path = used for defining the file that contains the output data
        """
        type_list = []
        sort_order = ['uint64', 'uint32', 'uint16', 'uint8']
        tree = etree.parse(path)
        root = tree.getroot()
        values = root.findall(".//{http://autosar.org/schema/r4.0}VALUE-REF")
        for elem in values[:]:
            if elem.attrib['DEST'] == "SW-BASE-TYPE":
                type_list.append(elem.text.split('/')[-1])
        sorted_list = type_list[:]
        sorted_list.sort(key=lambda x: sort_order.index(x))
        if sorted_list == type_list:
            return True
        else:
            return False

    def checkSize(path, max_size):
        """
        path = used for defining the file that contains the output data
        max_size = the bloc-max-size defined in the profile
        """
        block_size = []
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            obj_block = {}
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation':
                    obj_block['NAME'] = block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                    temp = block.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
                    for elem in temp:
                        if elem.text.split("/")[-1] == "NvDMBlockSize":
                            obj_block['SIZE'] = elem.getnext().text
                    block_size.append(obj_block)
        for elem in block_size:
            if int(elem['SIZE']) > max_size:
                return False
        return True

    def checkSafety(path, value):
        """
        path = used for defining the file that contains the output data
        max_size = the bloc-max-size defined in the profile
        """
        tree = etree.parse(path)
        root = tree.getroot()
        references = root.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
        for reference in references:
            if reference.text.split("/")[-1] == "NvDMSafetyBlock":
                if int(reference.getnext().text) == value:
                    return True
                else:
                    return False

    def NvDMStructure(path):
        """
        path = used for defining the file that contains the output data
        """
        structure_valid = True
        attributes = ['NvDMDurability', 'NvDMSafetyBlock', 'NvDMWriteTimeout', 'NvDMProfile', 'NvDMBlockSize', 'NvDMBlockID']
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation':
                    references = block.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
                    for reference in references:
                        if reference.text.split("/")[-1] in attributes[:]:
                            attributes.remove(reference.text.split("/")[-1])
                    nvm_reference = block.find(".//{http://autosar.org/schema/r4.0}REFERENCE-VALUES")
                    if nvm_reference is None:
                        structure_valid = False
                    else:
                        for tag in nvm_reference.iter('{http://autosar.org/schema/r4.0}ECUC-REFERENCE-VALUE', '{http://autosar.org/schema/r4.0}VALUE-REF'):
                            if tag is None:
                                structure_valid = False
                    data_elements = block.find(".//{http://autosar.org/schema/r4.0}SUB-CONTAINERS")
                    if data_elements is None:
                        structure_valid = False
                    else:
                        for tag in nvm_reference.iter('{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE'):
                            if tag is None:
                                structure_valid = False
        if attributes:
            structure_valid = False
        if structure_valid:
            return True
        else:
            return False

    def checkBlockName(path, type):
        """
        path = used for defining the file that contains the output data
        """
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            obj_block = {}
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation':
                    if re.search(r'^'+type+'(.*)._\d+$', block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text) or re.search(r'^'+type+'(.*)', block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text):
                        return True
                    else:
                        return False

    def NvMStructure(path):
        """
        path = used for defining the file that contains the output data
        """
        structure_valid = True
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            obj_block = {}
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation' and block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'NvMCommon':
                    parameters = ['NvMNvramBlockIdentifier', 'NvMNvBlockNum', 'NvMRomBlockDataAddress', 'NvMBlockUseAutoValidation', 'NvMStaticBlockIDCheck',
                                  'NvMResistantToChangedSw', 'NvMBswMBlockStatusInformation', 'NvMRomBlockNum', 'NvMNvramDeviceId', 'NvMWriteVerification', 'NvMWriteBlockOnce',
                                  'NvMMaxNumOfWriteRetries', 'NvMMaxNumOfReadRetries', 'NvMBlockJobPriority', 'NvMBlockManagementType', 'NvMNvBlockLength', 'NvMBlockUseCrc']
                    references = block.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
                    for reference in references:
                        if reference.text.split("/")[-1] in parameters[:]:
                            if reference.getnext().text is not None:
                                parameters.remove(reference.text.split("/")[-1])
                    if parameters:
                        structure_valid = False
        if structure_valid:
            return True
        else:
            return False

    def checkParameter(path, parameter):
        """
        path = used for defining the file that contains the output data
        """
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation':
                    name = block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text[4:]
                    references = block.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
                    for reference in references:
                        if reference.text.split("/")[-1] == parameter:
                            if parameter == "NvMRomBlockDataAddress":
                                if reference.getnext().text != "&NvDM_RomBlock_" + name:
                                    return False
        return True

    def checkReference(path, reference_type):
        """
        path = used for defining the file that contains the output data
        """
        ref_ok = False
        tree = etree.parse(path)
        root = tree.getroot()
        references = root.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
        for reference in references:
            if reference.attrib['DEST'] == "ECUC-SYMBOLIC-NAME-REFERENCE-DEF":
                if reference_type == "EA":
                    if reference.text.split("/")[-1] == 'NvMNameOfEaBlock':
                        if reference.getnext().text is None:
                            ref_ok = True
                elif reference_type == "FEE":
                    if reference.text.split("/")[-1] == 'NvMNameOfFeeBlock':
                        if reference.getnext().text is None:
                            ref_ok = True
        return ref_ok

    def checkOrder(path):
        """
        path = used for defining the file that contains the output data
        """
        block_list = []
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation' and block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'NvMCommon':
                    obj_block = {}
                    obj_block['NAME'] = block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text
                    references = block.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
                    for reference in references:
                        if reference.text.split("/")[-1] == "NvMNvramBlockIdentifier":
                            obj_block['NvMNvramBlockIdentifier'] = reference.getnext().text
                        elif reference.text.split("/")[-1] == "NvMResistantToChangedSw":
                            obj_block['NvMResistantToChangedSw'] = reference.getnext().text
                    block_list.append(obj_block)
        ordered = True
        for block1 in block_list:
            for block2 in block_list:
                if block_list.index(block1) != block_list.index(block2):
                    if int(block1['NvMNvramBlockIdentifier']) < int(block2['NvMNvramBlockIdentifier']) and block1['NvMResistantToChangedSw'] == 'False' and block2['NvMResistantToChangedSw'] == 'True':
                        ordered = False
        return ordered

    def checkID(path):
        """
        path = used for defining the file that contains the output data
        """
        IDs = []
        tree = etree.parse(path)
        root = tree.getroot()
        blocks = root.findall(".//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE")
        for block in blocks:
            if block.getparent().tag == '{http://autosar.org/schema/r4.0}CONTAINERS':
                if block.find(".//{http://autosar.org/schema/r4.0}SHORT-NAME").text != 'CommonPublishedInformation':
                    references = block.findall(".//{http://autosar.org/schema/r4.0}DEFINITION-REF")
                    for reference in references:
                        if reference.text.split("/")[-1] == "NvMNvramBlockIdentifier":
                            IDs.append(int(reference.getnext().text))
        if IDs[0] != 2:
            return False
        if IDs == sorted(IDs):
            return True
        else:
            return False

class MEMConfigurator(unittest.TestCase):

    def test_TRS_MEMCFG_INOUT_001(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.INOUT.001\\input -out ' + head + '\\tests\\TRS.MEMCFG.INOUT.001\\output')
        self.assertTrue(FileCompare.checkParsing(head + '\\tests\\TRS.MEMCFG.INOUT.001\\input', head + '\\tests\\TRS.MEMCFG.INOUT.001\\output\\result_MEM.log', '.arxml', 'is well-formed'))

    def test_TRS_MEMCFG_INOUT_002(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.INOUT.002\\input -out ' + head + '\\tests\\TRS.MEMCFG.INOUT.002\\output')
        self.assertTrue(FileCompare.checkParsing(head + '\\tests\\TRS.MEMCFG.INOUT.002\\input', head + '\\tests\\TRS.MEMCFG.INOUT.002\\output\\result_MEM.log', '.xml', 'is well-formed'))

    def test_TRS_MEMCFG_FUNC_001_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.001_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.001_1\\output')
        self.assertTrue(FileCompare.areSorted(head + '\\tests\\TRS.MEMCFG.FUNC.001_1\\output\\NvDM.epc'))

    def test_TRS_MEMCFG_FUNC_001_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.001_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.001_2\\output')
        self.assertFalse(FileCompare.areSorted(head + '\\tests\\TRS.MEMCFG.FUNC.001_2\\output\\NvDM.epc'))

    def test_TRS_MEMCFG_FUNC_002_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.002_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.002_1\\output')
        self.assertTrue(FileCompare.checkSize(head + '\\tests\\TRS.MEMCFG.FUNC.002_1\\output\\NvDM.epc', 10))

    def test_TRS_MEMCFG_FUNC_002_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.002_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.002_2\\output')
        self.assertTrue(FileCompare.checkSize(head + '\\tests\\TRS.MEMCFG.FUNC.002_2\\output\\NvDM.epc', 10))

    def test_TRS_MEMCFG_CHECK_001_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.001_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.001_1\\output')
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.001_1\\output\\NvDM.epc'))
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.001_1\\output\\NvM.epc'))

    def test_TRS_MEMCFG_CHECK_001_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.001_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.001_2\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.001_2\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.001_2\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\TRS.MEMCFG.CHECK.001_2\\output\\result_MEM.log', "ERROR", ["Default_App_Ram_Implicit_RAR"]))

    def test_TRS_MEMCFG_CHECK_002_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\ASWC_A26.aswc.arxml ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\AUTOSAR_Datatypes.arxml ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\CompiledConfigID.xml' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\Profiles_cleaned.xml ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\SystemGenerated.arxml ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\VSM_Types.arxml ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\input\\ASWC_A26.config_mem.xml -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\output')
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\output\\NvDM.epc'))
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.002_1\\output\\NvM.epc'))

    def test_TRS_MEMCFG_CHECK_002_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in @' + head + '\\tests\\TRS.MEMCFG.CHECK.002_2\\input_list.txt -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_2\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.002_2\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.002_2\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\TRS.MEMCFG.CHECK.002_2\\output\\result_MEM.log', "ERROR", ["App_Ram_Implicit"]))

    def test_TRS_MEMCFG_CHECK_002_3(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_3\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.002_3\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.002_3\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.002_3\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\TRS.MEMCFG.CHECK.002_3\\output\\result_MEM.log', "ERROR", ["Default_App_Ram_Implicit_RAR"]))

    def test_TRS_MEMCFG_CHECK_003_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.003_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.003_1\\output')
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.003_1\\output\\NvDM.epc'))
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.003_1\\output\\NvM.epc'))

    def test_TRS_MEMCFG_CHECK_003_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.003_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.003_2\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.003_2\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.003_2\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\TRS.MEMCFG.CHECK.003_2\\output\\result_MEM.log', "ERROR", ["SR_ConsoAutonomieGM"]))

    def test_TRS_MEMCFG_CHECK_004(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.004\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.004\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.004\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.004\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\TRS.MEMCFG.CHECK.004\\output\\result_MEM.log', "ERROR", ["EEEEEE"]))

    def test_TRS_MEMCFG_CHECK_005_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_1\\output')
        self.assertTrue(FileCompare.checkSafety(head + '\\tests\\TRS.MEMCFG.CHECK.005_1\\output\\NvDM.epc', 0))

    def test_TRS_MEMCFG_CHECK_005_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_2\\output')
        self.assertTrue(FileCompare.checkSafety(head + '\\tests\\TRS.MEMCFG.CHECK.005_2\\output\\NvDM.epc', 0))

    def test_TRS_MEMCFG_CHECK_005_3(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_3\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_3\\output')
        self.assertTrue(FileCompare.checkSafety(head + '\\tests\\TRS.MEMCFG.CHECK.005_3\\output\\NvDM.epc', 0))

    def test_TRS_MEMCFG_CHECK_005_4(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_4\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.005_4\\output')
        self.assertTrue(FileCompare.checkSafety(head + '\\tests\\TRS.MEMCFG.CHECK.005_4\\output\\NvDM.epc', 1))

    def test_TRS_MEMCFG_CHECK_006_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.006_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.006_1\\output')
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.006_1\\output\\NvDM.epc'))
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.006_1\\output\\NvM.epc'))

    def test_TRS_MEMCFG_CHECK_006_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.CHECK.006_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.CHECK.006_2\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.006_2\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.CHECK.006_2\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\TRS.MEMCFG.CHECK.004\\output\\result_MEM.log', "ERROR", ["Default_App_Ram_Implicit_RAR"]))

    def test_TRS_MEMCFG_GEN_001(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.001\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.001\\output')
        self.assertTrue(FileCompare.NvDMStructure(head + '\\tests\\TRS.MEMCFG.GEN.001\\output\\NvDM.epc'))

    def test_TRS_MEMCFG_GEN_002_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.002_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.002_1\\output')
        self.assertTrue(FileCompare.checkBlockName(head + '\\tests\\TRS.MEMCFG.GEN.002_1\\output\\NvDM.epc', ''))

    def test_TRS_MEMCFG_GEN_002_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.002_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.002_2\\output')
        self.assertTrue(FileCompare.checkBlockName(head + '\\tests\\TRS.MEMCFG.GEN.002_2\\output\\NvDM.epc', ''))

    def test_TRS_MEMCFG_GEN_003(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.002bis\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.002bis\\output')
        self.assertTrue(FileCompare.NvMStructure(head + '\\tests\\TRS.MEMCFG.GEN.002bis\\output\\NvM.epc'))

    def test_TRS_MEMCFG_GEN_004_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.003_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.003_1\\output')
        self.assertTrue(FileCompare.checkBlockName(head + '\\tests\\TRS.MEMCFG.GEN.003_1\\output\\NvM.epc', 'NvM'))

    def test_TRS_MEMCFG_GEN_004_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.003_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.003_2\\output')
        self.assertTrue(FileCompare.checkBlockName(head + '\\tests\\TRS.MEMCFG.GEN.003_2\\output\\NvM.epc', 'NvM'))

    def test_TRS_MEMCFG_GEN_005(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.004\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.004\\output')
        self.assertTrue(FileCompare.checkParameter(head + '\\tests\\TRS.MEMCFG.FUNC.004\\output\\NvM.epc', 'NvMRamBlockDataAddress'))

    def test_TRS_MEMCFG_GEN_006(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.005\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.005\\output')
        self.assertTrue(FileCompare.checkParameter(head + '\\tests\\TRS.MEMCFG.FUNC.005\\output\\NvM.epc', 'NvMRomBlockDataAddress'))

    def test_TRS_MEMCFG_GEN_007_1(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.006_1\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.006_1\\output')
        self.assertTrue(FileCompare.checkReference(head + '\\tests\\TRS.MEMCFG.FUNC.006_1\\output\\NvM.epc', 'EA'))

    def test_TRS_MEMCFG_GEN_007_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.FUNC.006_2\\input -out ' + head + '\\tests\\TRS.MEMCFG.FUNC.006_2\\output')
        self.assertTrue(FileCompare.checkReference(head + '\\tests\\TRS.MEMCFG.FUNC.006_2\\output\\NvM.epc', 'FEE'))

    def test_TRS_MEMCFG_GEN_00B(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.008\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.008\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.GEN.008\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\\TRS.MEMCFG.GEN.008\\output\\result_MEM.log', "ERROR", ["Default_App_Ram_Implicit_SAV"]))

    def test_TRS_MEMCFG_GEN_00C(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.009\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.009\\output')
        self.assertTrue(FileCompare.checkOrder(head + '\\tests\\TRS.MEMCFG.GEN.009\\output\\NvM.epc'))

    def test_TRS_MEMCFG_GEN_011(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.011\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.011\\output')
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.GEN.011\\output\\NvDM.epc'))

    def test_TRS_MEMCFG_GEN_012(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TRS.MEMCFG.GEN.012\\input -out ' + head + '\\tests\\TRS.MEMCFG.GEN.012\\output')
        self.assertTrue(FileCompare.isOutput(head + '\\tests\\TRS.MEMCFG.GEN.012\\output\\NvM.epc'))

    def test_CHECK_XML(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\CHECK.XML\\input -out ' + head + '\\tests\\CHECK.XML\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\CHECK.XML\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\CHECK.XML\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\\CHECK.XML\\output\\result_MEM.log', "ERROR", [""]))

    def test_TBD(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TBD\\input -out ' + head + '\\tests\\TBD\\output')
        self.assertTrue(FileCompare.checkID(head + '\\tests\\TBD\\output\\NvM.epc'))

    def test_TBD_2(self):
        current_path = os.path.realpath(__file__)
        head, tail = ntpath.split(current_path)
        os.system('coverage run MEM_Configurator.py -in ' + head + '\\tests\\TBD_2\\input -out ' + head + '\\tests\\TBD_2\\output')
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TBD_2\\output\\NvDM.epc'))
        self.assertFalse(FileCompare.isOutput(head + '\\tests\\TBD_2\\output\\NvM.epc'))
        self.assertTrue(FileCompare.checkLog(head + '\\tests\\TBD_2\\output\\result_MEM.log', "ERROR", [""]))


suite = unittest.TestLoader().loadTestsFromTestCase(MEMConfigurator)
unittest.TextTestRunner(verbosity=2).run(suite)

# current_path = os.path.realpath(__file__)
# head, tail = ntpath.split(current_path)
# if __name__ == "__main__":
#     unittest.main(testRunner=HtmlTestRunner.HTMLTestRunner(output=head + "\\tests"))