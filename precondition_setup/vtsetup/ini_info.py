from configparser import ConfigParser
import xml.etree.ElementTree as ET
import os


class Ini_info():

    def __init__(self):
        # self.default_ini_name = 'sut.ini'
        self.config = ConfigParser()

    def Read_env_info(self, default_ini_name):
        sut_env_dict = {}
        self.config.read(default_ini_name)
        sut_env = self.config.sections()
        # print(sut_env)
        for section in sut_env:
            options = self.config.items(section)
            tmp_dict = {}
            for opt in options:
                tmp_dict.update({opt[0]: opt[1]})

            sut_env_dict.update({section: tmp_dict})

        return sut_env_dict

    def Read_case_info(self, default_ini_name):
        config_tmp = ConfigParser()
        sut_env_dict = {}
        config_tmp.read(default_ini_name)
        sut_env = config_tmp.sections()
        # print(sut_env)
        for section in sut_env:
            options = config_tmp.items(section)
            tmp_dict = {}
            for opt in options:
                tmp_dict.update({opt[0]: opt[1]})

            sut_env_dict.update({section: tmp_dict})

        return sut_env_dict

    def Get_sections(self, default_ini_name):
        self.config.read(default_ini_name)
        sut_env = self.config.sections()
        return sut_env

    def Get_defaults(self, default_ini_name):
        self.config.read(default_ini_name)
        sut_env = self.config.defaults()
        return sut_env

    def Read_OS_info(self, default_ini_name):
        self.config.read(default_ini_name)
        assert (self.config.has_option("DEFAULT", "os"))
        os = self.config['DEFAULT']['os']

        items = self.config.items(os) + self.config.items('args')

        info_dict = {}
        for dict_trans in items:
            info_dict.update({dict_trans[0]: dict_trans[1]})

        return info_dict


# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# system_configration = os.path.join(os.path.abspath(BASE_DIR + '/../vtconfig/'), "precondition_configuration.xml")
system_configration = "C:\\Automation\\vtconfig\\vt_precondition_configuration.xml"


class Etree:

    @classmethod
    def __init__(cls):
        pass

    @classmethod
    def get_node_value(cls, attrib):
        tree = ET.parse(system_configration)
        root = tree.getroot()
        # print(root.find(r".//{}".format(attrib)).text.strip())

        return root.find(r".//{}".format(attrib)).text.strip()

    # Traverse all nodes under the specified node
    @classmethod
    def walkData(cls, attrib):
        auto_list = []
        attrib = attrib.split('/')
        tree = ET.parse(system_configration)

        root = tree.getroot()
        for node in attrib:
            root = root.find(node)

        for node in root:
            if node.text.strip().lower() == 'true':
                auto_list.append(node.tag)

        return auto_list

    @classmethod
    def dict_walkData(cls, attrib):
        auto_list = {}
        attrib = attrib.split('/')
        tree = ET.parse(system_configration)

        root = tree.getroot()
        for node in attrib:
            root = root.find(node)

        for node in root:
            # if node.text.strip().lower() == 'true':

            auto_list.update({node.tag: node.text.strip()})

        return auto_list


class Content():

    def __init__(self):
        self.overwrite = Etree.get_node_value(attrib='overwrite')
        """
        auto tag
        """
        # xmlcli
        self.xmlcli_linux = Etree.get_node_value(attrib='auto/xmlcli/linux')
        self.xmlcli_windows = Etree.get_node_value(attrib='auto/xmlcli/windows')
        self.xmlcli_esxi = Etree.get_node_value(attrib='auto/xmlcli/esxi')
        # python
        self.python_linux = Etree.get_node_value(attrib='auto/python/python_cent')
        self.python_windows = Etree.get_node_value(attrib='auto/python/python_wind')
        self.python_pip_module_windows = Etree.get_node_value(attrib='auto/python/python_pip_module_wind')
        # auto-poc
        self.auto_poc_cent = Etree.get_node_value(attrib='auto/auto-poc/linux')
        self.virtualization_inband_cent = Etree.get_node_value(attrib='auto/auto-poc/virtualization_inband_cent')
        self.auto_poc_wind = Etree.get_node_value(attrib='auto/auto-poc/windows')
        # nuc env
        self.environment_variable_bat = Etree.get_node_value(attrib='auto/nuc/environment_variable_bat')
        self.vmware_powercli = Etree.get_node_value(attrib='auto/nuc/vmware_powercli')
        self.python_pip_modules = Etree.get_node_value(attrib='auto/nuc/python_pip_modules')
        # sut centos
        # self.iproute = Etree.get_node_value(attrib='auto/centos/iproute')
        self.vfio_pci_bind = Etree.get_node_value(attrib='auto/centos/vfio_pci_bind')
        self.ovmf_cent = Etree.get_node_value(attrib='auto/centos/ovmf_cent')
        """
        stress tools tag
        """
        self.stress_tools_dict = Etree.dict_walkData(attrib='stress_tools')

        """
        vms tag
        """
        self.vm_refresh_vm = Etree.get_node_value(attrib='vm/refresh_vm')
        # centos vm
        self.vm_source_file_cent = Etree.dict_walkData(attrib='vm/centos')
        self.vm_register_cent = Etree.dict_walkData(attrib='vm/centos/regirster_vm')
        # windows vm
        self.vm_source_file_wind = Etree.dict_walkData(attrib='vm/windows')
        self.vm_register_wind = Etree.dict_walkData(attrib='vm/windows/regirster_vm')
        # esxi vm
        self.vm_source_file_esxi = Etree.dict_walkData(attrib='vm/esxi')
        self.vm_register_esxi = Etree.dict_walkData(attrib='vm/esxi/regirster_vm')


if __name__ == "__main__":
    config = Content()
    print(config.overwrite)
    print(config.python_pip_modules)
    # config.Read_info("sut.ini")
