import os
import re
import fabric
import fileinput
from dtaf_core.lib.os_lib import OsCommandResult
from dtaf_core.lib.exceptions import OsCommandException, OsCommandTimeoutException
from src.virtualization.lib.tkinit import *
from src.virtualization.gnr.precondition_setup.vtsetup.ini_info import *
from src.virtualization.lib.virtualization_basic import *

# Linux
SUT_TOOLS_LINUX_ROOT = '/home/BKCPkg'
SUT_TOOLS_LINUX_VIRTUALIZATION = f'{SUT_TOOLS_LINUX_ROOT}/domains/virtualization'
SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS = f'{SUT_TOOLS_LINUX_VIRTUALIZATION}/imgs'

VT_AUTO_POC_L = f'{SUT_TOOLS_LINUX_VIRTUALIZATION}/auto-poc'
VT_IMGS_L = f'{SUT_TOOLS_LINUX_VIRTUALIZATION}/imgs'
VT_TOOLS_L = f'{SUT_TOOLS_LINUX_VIRTUALIZATION}/tools'
LINUX_DTAF_TOOLPATH = "C:\\Automation\\Tools\\GNR\\LINUX"

# NUC and Windows
NUC_TOOLS_WINDOWS_ROOT = SUT_TOOLS_WINDOWS_ROOT = 'C:\\BKCPkg'

NUC_TOOLS_WINDOWS_VIRTUALIZATION = SUT_TOOLS_WINDOWS_VIRTUALIZATION = f'{SUT_TOOLS_WINDOWS_ROOT}\\domains\\virtualization\\'
VT_IMGS_N = VT_IMGS_W = f'{SUT_TOOLS_WINDOWS_VIRTUALIZATION}\\imgs\\'
VT_TOOLS_N = VT_TOOLS_W = f'{SUT_TOOLS_WINDOWS_VIRTUALIZATION}\\tools\\'
SUT_ISO_IMAGE_LOCATION = "C:\\Automation\\"

# Esxi
SUT_TOOLS_VMWARE_VIRTUALIZATION = "/vmfs/volumes/datastore1"
SUT_TOOLS_VMWARE_VIRTUALIZATION_APISCRIPTS = f'{SUT_TOOLS_VMWARE_VIRTUALIZATION}/BKCPkg/domains/virtualization/apiscripts/'
SUT_TOOLS_VMWARE_VIRTUALIZATION_TOOLS = f'{SUT_TOOLS_VMWARE_VIRTUALIZATION}/BKCPkg/domains/virtualization/tools/'
VMWARE_DTAF_TOOLPATH = "C:\\Automation\\Tools\\GNR\\Esxi"
VMWARE_SPR_DTAF_TOOLPATH = "C:\\Automation\\Tools\\SPR\\Esxi"
DTAF_IMAGEPATH = "C:\\Automation\\BKC\\VM_DETAILS\\IMAGE"

USERNAME = os.environ.get("sys_user")
USERPASSWD = os.environ.get("sys_pwd")

connect = Content()


class ExtensionSutFunction:

    def __init__(self):

        pass

    @classmethod
    def ignore_log_excute_command(cls, sut, cmd, timeout=60, cwd=".", powershell=False, nuc=False):
        if not nuc:
            ip = sut.supported_os[sut.default_os_boot].ip
            user = sut.supported_os[sut.default_os_boot].user
            password = sut.supported_os[sut.default_os_boot].password
            port = sut.supported_os[sut.default_os_boot].port
            ex_out = None
            try:
                with fabric.Connection(ip, user, gateway=None, port=port) as target:
                    target.connect_kwargs.password = password
                    with target.cd(cwd):
                        exec_result = target.run(cmd, hide=True, warn=True, timeout=timeout,
                                                 in_stream=None)  # See comment above for details
                    target.close()
                return OsCommandResult(exec_result.exited, exec_result.stdout, exec_result.stderr)
            except OsCommandException:
                ex_out = OsCommandException("OsCommandException")
            except OsCommandTimeoutException:
                ex_out = OsCommandTimeoutException("OscommandTimeoutException")
            except Exception:
                ex_out = Exception("Other errors downloaded")
            raise ex_out
        else:
            try:
                sut._SUT__execute_host_cmd(cmd, timeout)
            except:
                raise Exception(f"Failed command")

    @classmethod
    def download_file_to_nuc(cls, sut, link, destination, timeout=600):
        download_link = link.split(',')[0]
        rename = link.split(',')[1]
        if connect.overwrite.lower() == 'true':
            ext_cmd = f'Remove-Item {destination}\\{rename} -Force -ErrorAction SilentlyContinue'
            sut.execute_host_cmd(cmd=ext_cmd, powershell=True, timeout=timeout)

        if connect.overwrite.lower() == 'false':
            if os.path.exists(f'{destination}\\{rename}'):
                return
            else:
                result, err = sut.execute_host_cmd(cmd=f"Test-Path -Path  {destination}\\{rename}", powershell=True,
                                                   timeout=timeout)
                if "true" in result.lower():
                    return
        ext_cmd = f'curl -u {USERNAME}:{USERPASSWD} {download_link} --output {destination}\\{rename} --ssl-no-revoke'
        logger.debug(f"curl {download_link}")
        ExtensionSutFunction.ignore_log_excute_command(sut=sut, cmd=ext_cmd, powershell=False, timeout=timeout,
                                                       nuc=True)

    @classmethod
    def download_file_to_sut(cls, sut, link, destination, transit=False, timeout=600):
        download_link = link.split(',')[0]
        rename = link.split(',')[1]

        if 'esxi' in sut.default_os_boot.lower():
            __, exist, err = sut.execute_shell_cmd(cmd=f'ls {destination} | grep {rename} ', timeout=timeout)
            if (rename in exist and connect.overwrite.lower() == 'true') or rename not in exist:
                sut.execute_shell_cmd(cmd=f'rm -rf {destination}/{rename}', timeout=timeout)
                if transit:
                    cls.download_file_to_nuc(sut=sut, link=link, destination=VT_TOOLS_N,
                                             timeout=timeout)
                    sut.upload_to_remote(localpath=f"{VT_TOOLS_N}\\{rename}", remotepath=f'{destination}/{rename}',
                                         timeout=timeout)
                else:

                    ext_cmd = f'esxcli network firewall unload;' \
                              f'wget --no-check-certificate {download_link} -O {destination}/{rename}; ' \
                              f'esxcli network firewall load'
                    sut.execute_shell_cmd(cmd=ext_cmd, timeout=timeout)

        if 'windows' in sut.default_os_boot.lower():
            if connect.overwrite.lower() == 'true':
                sut.execute_shell_cmd(cmd=f'Remove-Item {destination}\\{rename} -Force -ErrorAction SilentlyContinue',
                                      powershell=True, timeout=timeout)
            else:
                __, result, err = sut.execute_shell_cmd(cmd=f"Test-Path -Path  {destination}\\{rename}",
                                                        powershell=True, timeout=300)
                if "true" in result.lower():
                    return
            logger.debug(f"curl {download_link}")
            cls.ignore_log_excute_command(sut=sut,
                                          cmd=f'curl -u {USERNAME}:{USERPASSWD} {download_link} '
                                              f'--output {destination}\\{rename} --ssl-no-revoke',
                                          powershell=False, timeout=timeout)


class Nuc:
    connect = Content()

    def __init__(self, sut):
        self.python = None
        self.connect = Content()
        self.sut = sut
        self.init_variables()
        self.init_path()

    def init_variables(self):
        self.python = "c:\\python38\\python.exe"

    def init_path(self):
        init_path_cmd = [f'New-Item -Path {NUC_TOOLS_WINDOWS_ROOT} -ItemType Directory  -Force',
                         f'New-Item -Path {LINUX_DTAF_TOOLPATH} -ItemType Directory  -Force',
                         f'New-Item -Path {VMWARE_DTAF_TOOLPATH} -ItemType Directory  -Force',
                         f'New-Item -Path {NUC_TOOLS_WINDOWS_VIRTUALIZATION} -ItemType Directory  -Force',
                         f'New-Item -Path {VT_IMGS_N} -ItemType Directory  -Force',
                         f'New-Item -Path {VT_TOOLS_N} -ItemType Directory  -Force',
                         f'New-Item -Path {VMWARE_SPR_DTAF_TOOLPATH} -ItemType Directory  -Force',
                         f'New-Item -Path C:\\Automation\\BKC\\VM_DETAILS\\IMAGE\\ -ItemType Directory  -Force']

        for ext_cmd in init_path_cmd:
            self.sut.execute_host_cmd(cmd=f'{ext_cmd}', powershell=True)

    def deploy_python_env(self):
        ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.python_pip_modules,
                                                  destination=Windows_TOOLS, timeout=600)
        self.sut.execute_host_cmd(
            cmd=f'Expand-Archive -Path {Windows_TOOLS}\\pip_modules.zip -DestinationPath {Windows_TOOLS}\\pip_modules -Force',
            powershell=True, timeout=600)

        __, out, err = self.sut.execute_host_cmd(cmd=f"{self.python} -m pip list | grep pyvmomi", powershell=True,
                                                 timeout=600)
        if "pyvmomi" in out.lower():
            self.sut.execute_host_cmd(cmd=f"{self.python} -m pip uninstall -y pyvmomi", powershell=True, timeout=600)

        __, out, err = self.sut.execute_host_cmd(cmd=f"{self.python} -m pip list | grep pyvim", powershell=True,
                                                 timeout=600)
        if "pyvim" in out.lower():
            self.sut.execute_host_cmd(cmd=f"{self.python} -m pip uninstall -y pyvim", powershell=True, timeout=600)

        self.sut.execute_host_cmd(
            cmd=f"{self.python} -m pip install {Windows_TOOLS}\\pip_modules\\setuptools-58.2.0-py3-none-any.whl "
                f"--force-reinstall --no-dependencies",
            powershell=True, timeout=600)

        package_list = ['six-1.16.0-py2.py3-none-any.whl', 'pyvmomi-8.0.1.0.1', 'wcwidth-0.2.6-py2.py3-none-any.whl',
                        'pygments-2.15.1-py3-none-any.whl', 'pyflakes-3.0.1-py2.py3-none-any.whl', 'docopt-0.6.2',
                        'prompt_toolkit-3.0.39-py3-none-any.whl', 'pyvim-3.0.3-py3-none-any.whl']
        for package in package_list:
            if package in ('pyvmomi-8.0.1.0.1', 'docopt-0.6.2'):
                self.sut.execute_host_cmd(
                    cmd=f"cd {Windows_TOOLS}\\pip_modules\\{package}; {self.python} setup.py install", powershell=True,
                    timeout=600)
            else:
                self.sut.execute_host_cmd(
                    cmd=f"{self.python} -m pip install {Windows_TOOLS}\\pip_modules\\{package} --force-reinstall "
                        f"--no-dependencies",
                    powershell=True, timeout=600)

    def deploy_vmware_powercli(self):
        __, check, err = self.sut.execute_host_cmd(cmd='Get-Module -Name VMware.PowerCLI -ListAvailable',
                                                   powershell=True,
                                                   timeout=30)
        if check == '':
            out, err = self.sut.Excute_command(cmd="$env:PSModulePath", powershell=True, nuc=True, timeout=600)
            env_path = out.split(";")[0]
            env_path = env_path.replace("\r\n", '')

            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.vmware_powercli,
                                                      destination=VT_TOOLS_N,
                                                      timeout=600)
            self.sut.execute_host_cmd(cmd=f'New-Item -Path {env_path}\\VMware-PowerCLI -ItemType Directory  -Force',
                                      powershell=True, nuc=True, timeout=30)

            Case.sleep(5, min_iterval=5)
            __, get_env_path, err = self.sut.execute_host_cmd(cmd="$env:PSModulePath", powershell=True, timeout=600)
            Case.expect("verify env path", env_path.lower() in get_env_path.lower())

            self.sut.execute_host_cmd(
                cmd=f'Expand-Archive -Path {VT_TOOLS_N}\\VMware-PowerCLI.zip -DestinationPath {env_path}\\ -Force',
                powershell=True, timeout=120)

            self.sut.execute_host_cmd(cmd=f'cd {env_path}\\; Get-ChildItem * -Recurse | Unblock-File',
                                      powershell=True, timeout=120)

            __, check, err = self.sut.execute_host_cmd(cmd='Get-Module -Name VMware.PowerCLI -ListAvailable',
                                                       powershell=True, timeout=30)
            Case.expect("verify PowerCli installed", "VMware.PowerCLI".lower() in check.lower())

            try:
                self.sut.execute_host_cmd(
                    cmd='Set-PowerCLIConfiguration  -DefaultVIServerMode Multiple  -Scope User '
                        '-ParticipateInCEIP $true -InvalidCertificateAction Ignore -Confirm:$false',
                    powershell=True, timeout=120)
            except:
                pass
            finally:
                result, err = self.sut.execute_host_cmd(
                    cmd='Set-PowerCLIConfiguration  -DefaultVIServerMode Multiple  -Scope User '
                        '-ParticipateInCEIP $true -InvalidCertificateAction Ignore -Confirm:$false',
                    powershell=True, timeout=120)
                Case.expect("verify result", 'scope' in result.lower())

    def deploy_sut_env(self):
        ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.environment_variable_bat,
                                                  destination=Windows_TOOLS, timeout=300)
        self.sut.execute_host_cmd(cmd=f'{Windows_TOOLS}\\env_setup.bat', powershell=False, timeout=600)

    def main(self):
        self.deploy_python_env()
        self.deploy_vmware_powercli()
        self.deploy_sut_env()


# class Kvm:
# 
# 
#     def __init__(self,sut):
#         self.connect = Content(os_type=sut.default_os.lower())
#         self.PYTHON_PATH = "/usr/bin/python"
#         self.ADD_PROXY = f'export http_proxy=http://{self.connect.proxy}; export https_proxy=http://{self.connect.proxy};'
#         self.UNSET_PROXY = 'unset http_proxy; unset https_proxy;'
# 
#         self.sut = Basic_hypervisor(sut)
#         self.init_path()
# 
#     def init_path(self):
#         Case.step("Init sut path")
#         cmd = f"rm -rf {SUT_TOOLS_LINUX_VIRTUALIZATION}"
#         self.sut.Excute_command(cmd=cmd)
# 
#         cmd = f'mkdir -p {SUT_TOOLS_LINUX_ROOT}'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = f'mkdir -p {SUT_TOOLS_LINUX_VIRTUALIZATION}'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = f'mkdir -p {SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS}'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = f'mkdir -p {VT_IMGS_L}'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = f'mkdir -p {VT_TOOLS_L}'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#     def create_master_net_cfg(self):
#         Case.step("SUT env create master net configuration")
# 
#         MY_NETWORK_XML_FILE_NAME = "my_network.xml"
#         DEFAULT_NETWORK_XML_FILE_NAME = "default_network.xml"
# 
#         my_network = """\"<network>
#                       <name>my_network</name>
#                       <bridge name='virbr0'/>
#                       <forward/>
#                       <ip address='192.168.123.1' netmask='255.255.255.0'>
#                         <dhcp>
#                           <range start='192.168.123.2' end='192.168.123.254'/>
#                         </dhcp>
#                       </ip>
#                     </network>
#                     \""""
#         default_network = """\"<network>
#                       <name>default</name>
#                       <bridge name='virbr1'/>
#                       <forward/>
#                       <ip address='192.168.122.1' netmask='255.255.255.0'>
#                         <dhcp>
#                           <range start='192.168.122.2' end='192.168.122.254'/>
#                         </dhcp>
#                       </ip>
#                     </network>
#                     \""""
#         GET_NETWORK_INTERFACE_NAME_CMD = r"ip addr show"
#         out, err = self.sut.Excute_command(cmd=GET_NETWORK_INTERFACE_NAME_CMD, timeout=60)
#         # if "virbr0" not in out:
#         cmd = "echo {} > {}".format(my_network, MY_NETWORK_XML_FILE_NAME)
#         self.sut.Excute_command(cmd)
#         cmd = 'virsh net-list --all'
#         result, _ = self.sut.Excute_command(cmd=cmd, timeout=60)
#         if 'default' in result.lower():
#             cmd = "virsh net-destroy default"
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#             cmd = "virsh net-undefine default"
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#         if 'my_network' not in result.lower():
#             cmd = 'virsh net-define {}'.format(MY_NETWORK_XML_FILE_NAME)
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#             cmd = 'virsh net-autostart my_network'
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#             cmd = 'virsh net-start my_network'
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#         if "virbr1" not in out:
#             cmd = "echo {} > {}".format(default_network, DEFAULT_NETWORK_XML_FILE_NAME)
#             self.sut.Excute_command(cmd)
#         cmd = 'virsh net-list --all'
#         result, _ = self.sut.Excute_command(cmd=cmd, timeout=60)
#         if 'default' not in result.lower():
#             cmd = 'virsh net-define {}'.format(DEFAULT_NETWORK_XML_FILE_NAME)
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#             cmd = 'virsh net-autostart default'
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#             cmd = 'virsh net-start default'
#             self.sut.Excute_command(cmd=cmd, timeout=60)
#             cmd = "ls /etc/sysconfig/network-scripts/"
#             ifcfg_files, err = self.sut.Excute_command(cmd=cmd, timeout=60)
#             GET_NETWORK_INTERFACE_NAME_DYNAMIC_CMD = r"ip addr show | awk '/inet.*brd.*dynamic/{print $NF; exit}'"
#             ifcfg_file, err = self.sut.Excute_command(cmd=GET_NETWORK_INTERFACE_NAME_DYNAMIC_CMD, timeout=60)
#             if "ifcfg-{}".format(ifcfg_file.strip()) not in ifcfg_files:
#                 ifcfg_template = [
#                     "TYPE=Ethernet",
#                     "PROXY_METHOD=none",
#                     "BROWSER_ONLY=no",
#                     "BOOTPROTO=dhcp",
#                     "DEFROUTE=yes",
#                     "IPV4_FAILURE_FATAL=no",
#                     "IPV6INIT=yes",
#                     "IPV6_AUTOCONF=yes",
#                     "IPV6_DEFROUTE=yes",
#                     "IPV6_FAILURE_FATAL=no",
#                     f"NAME={ifcfg_file.strip()}",
#                     f"DEVICE={ifcfg_file.strip()}",
#                     "ONBOOT=yes"
#                 ]
#                 for cmd in ifcfg_template:
#                     cmd = "echo {} >> /etc/sysconfig/network-scripts/ifcfg-{}".format(cmd, ifcfg_file.strip())
#                     self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#     def maintoolkit_virbr0(self):
#         Case.step("SUT env check nat virbr0")
#         cmd = 'systemctl disable firewalld'
#         self.sut.Excute_command(cmd=cmd,timeout=60)
#         cmd = 'systemctl stop firewalld'
#         self.sut.Excute_command(cmd=cmd,timeout=60)
# 
#         #self.libvirtd()
#         cmd = 'systemctl start libvirtd'
#         self.sut.Excute_command(cmd=cmd,timeout=60)
#         cmd = 'systemctl enable libvirtd'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
#         cmd = 'systemctl restart libvirtd'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
#         cmd = ' systemctl status libvirtd | grep "active (running)"'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = 'virsh net-list --all'
#         result,_ =  self.sut.Excute_command(cmd=cmd,timeout=60)
# 
#         if 'default' not in result.lower():
#             cmd = 'ifconfig'
#             result, _ = self.sut.Excute_command(cmd=cmd, timeout=60)
#             if 'virbr0' in result.lower():
#                 cmd='ifdown virbr0'
#                 self.sut.Excute_command(cmd=cmd,timeout=60)
# 
#             cmd='virsh net-define /usr/share/libvirt/networks/default.xml'
#             self.sut.Excute_command(cmd=cmd,timeout=60)
#             cmd='virsh net-autostart default'
#             self.sut.Excute_command(cmd=cmd,timeout=60)
#             cmd='virsh net-start default'
#             self.sut.Excute_command(cmd=cmd, timeout=60)
# 
# 
#     def libvirtd(self):
#         Case.step("SUT env check libvirtd status")
#         cmd = 'mv /usr/lib64/libvirt/storage-backend/libvirt_storage_backend_rbd.so /usr/lib64/libvirt/storage-backend/libvirt_storage_backend_rbd.so-bak'
#         self.sut.Excute_command(cmd=cmd,timeout=60)
#         cmd = 'systemctl start libvirtd'
#         self.sut.Excute_command(cmd=cmd,timeout=60)
#         cmd = 'systemctl enable libvirtd'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = 'systemctl restart libvirtd'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = ' systemctl status libvirtd | grep "active (running)"'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#         cmd = 'echo "systemctl start libvirtd" >> /etc/profile'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
#         # fix the virtnetworkd issue on GNR SP 4S
#         cmd = 'systemctl enable virtnetworkd'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
#         cmd = 'systemctl restart virtnetworkd'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
# 
#     def env(self):
#         Case.step("SUT kernel update ")
#         cmd = 'grubby --update-kernel=ALL --args="ibt=off"'
#         self.sut.Excute_command(cmd=cmd, timeout=60)
#         Case.step("SUT env setup ")
#         # download auto-poc and unzip
#         if 'auto-poc' in self.connect.env_list.keys():
#             Case.step("SUT env auto-poc tools")
#             link_name = lambda link: link.split('/')[-1]
#             env_auto_poc = self.connect.env_list['auto-poc']
#             self.sut.Download_artifactory_to_Linux(link=env_auto_poc,dest=SUT_TOOLS_LINUX_VIRTUALIZATION,timeout=600)
# 
#             cmd = f'unzip -o {SUT_TOOLS_LINUX_VIRTUALIZATION}/{link_name(env_auto_poc)} -d {SUT_TOOLS_LINUX_VIRTUALIZATION}/'
#             self.sut.Excute_command(cmd=cmd,timeout=60)
# 
#         if 'repos' in self.connect.env_list.keys():
#             if self.connect.env_list['repos'].lower() == 'true':
#                 check_cmd = "ls /etc/yum.repos.d/epel-cisco-openh264.repo"
#                 out, err = self.sut.Excute_command(check_cmd)
#                 if not err:
#                     cmd = f"mv -f /etc/yum.repos.d/epel-cisco-openh264.repo /etc/yum.repos.d/epel-cisco-openh264.repo.bak"
#                     self.sut.Excute_command(cmd)
#                 # def yum_repo_deploy(self):
#                 #     proxy = 'http://' + self.connect.proxy
#                 #     cmd = f'ls /etc/yum.repos.d | grep -i .repo'
#                 #     repo, __ = Basic_hypervisor.Excute_command(cmd=cmd, timeout=60)
#                 #     for var in repo.split('\n'):
#                 #         if var == '':
#                 #             continue
#                 #         cmd = f'cat /etc/yum.repos.d/{var}'
#                 #         content, _ = Basic_hypervisor.Excute_command(cmd=cmd, timeout=60)
#                 #
#                 #         edit_repo = []
#                 #         for str in content.split('\n\n'):
#                 #             str = str.replace('\'', '')
#                 #             if str == '':
#                 #                 continue
#                 #             if '[' not in str and ']' not in str:
#                 #                 edit_repo.append(str + '\n\n')
#                 #                 continue
#                 #
#                 #             if 'linux-ftp' in str or 'artifactory' in str:
#                 #                 edit_repo.append(str + '\n\n')
#                 #                 continue
#                 #
#                 #             if 'proxy' in str:
#                 #                 tmp = []
#                 #                 for i in str.split('\n'):
#                 #                     if 'proxy' in i:
#                 #                         continue
#                 #                     tmp.append(i + '\n')
#                 #
#                 #                 edit_repo.append(f"{''.join(tmp).strip()}\nproxy={proxy}\n\n")
#                 #                 continue
#                 #
#                 #             else:
#                 #                 edit_repo.append(f"{str.strip()}\nproxy={proxy}\n\n")
#                 #
#                 #         cmd = 'echo \'{}\' > /etc/yum.repos.d/{}'.format(''.join(edit_repo), var)
#                 #         Basic_hypervisor.Excute_command(cmd=cmd,timeout=60)
#                 #
#                 #         cmd = 'cat /etc/yum.repos.d/{}'
#                 #         Basic_hypervisor.Excute_command(cmd=cmd, timeout=60)
#                 # yum_repo_deploy()
# 
#         if 'virtualization_inband' in self.connect.env_list.keys():
#             Case.step("SUT env virtualization_inband tools")
#             link_name = lambda link: link.split('/')[-1]
#             virtualization_inband = self.connect.env_list['virtualization_inband']
#             self.sut.Download_artifactory_to_Linux(link=virtualization_inband, dest=SUT_TOOLS_LINUX_VIRTUALIZATION, timeout=600)
# 
#             cmd = f'unzip -o {SUT_TOOLS_LINUX_VIRTUALIZATION}/{link_name(virtualization_inband)} -d {SUT_TOOLS_LINUX_VIRTUALIZATION}/'
#             self.sut.Excute_command(cmd=cmd, timeout=600)
# 
#             cmd = f'cd  {SUT_TOOLS_LINUX_VIRTUALIZATION}; chmod +x -R virtualization_inband'
#             self.sut.Excute_command(cmd=cmd, timeout=600)
# 
#         # #add dependent package by yum
#         # cmd = f'yum remove -y qemu-kvm'
#         # self.ssh.to_excute_shell_cmd(self.cmd_args, cmd=f'{cmd}', log=self.log, timeout=120)
# 
#         Case.step("SUT env yum install packages")
#         for var in ['virt-manager', 'libvirt', 'python3-libvirt', 'virt-install', 'iperf', 'wget', 'tigervnc',
#                     'kmod-devel', 'rust', 'bridge-utils', 'network-scripts', 'pip', 'yum-utils', 'python3-scp',
#                     'iperf3', '/usr/bin/virt-customize', 'screen'
#                     ]:
#             cmd = f'yum install -y {var}  --allowerasing --skip-broken --nobest'
#             self.sut.Excute_command(cmd=cmd, timeout=300)
# 
#         if self.connect.python310.lower() == 'true':
#             Case.step("Add yum env")
#             for var in 'openssl* openssl-devel libffi* bzip2*'.split():
#                 cmd = f'yum install -y {var}  --allowerasing --skip-broken --nobest'
#                 self.sut.Excute_command(cmd=cmd, timeout=300)
#             self.sut.Excute_command('yum groupinstall "Development Tools" -y',timeout=300)
#             py310 = 'https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/Automation_Tools/GNR/Linux/Python-3.10.10.tgz'
#             py310_file = py310.split("/")[-1]
#             cmd = f'{self.UNSET_PROXY} wget {py310} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd)
#             cmd = f"cd {VT_TOOLS_L}; tar xzvf {py310_file}"
#             self.sut.Excute_command(cmd, timeout=300)
#             py310_path = py310_file.rstrip(".tgz")
#             cmd = f"cd {VT_TOOLS_L}/{py310_path}; ./configure && make && make install"
#             self.sut.Excute_command(cmd, timeout=300)
#             cmd_list = "mv /usr/bin/python /usr/bin/python_bk; \
#                     ln -s /usr/local/bin/python3.10 /usr/bin/python; \
#                     sed -i 's/python3/python/g' /usr/bin/pip"
#             self.sut.Excute_command(cmd_list, timeout=300)
#         else:
#             Case.step("SUT env check python cmd ")
#             cmd = "test -f /usr/bin/python && echo $?"
#             result, err = self.sut.Excute_command(cmd=cmd)
#             if result == "":
#                 cmd = f'ln -s /usr/bin/python3 {self.PYTHON_PATH}'
#                 self.sut.Excute_command(cmd=cmd, timeout=300)
# 
#         # add dependent package by pip
#         cmd = f"pip config set global.index-url https://{USERNAME}:{USERPASSWD}@intelpypi.intel.com/pythonsv/production"
#         self.sut.Ignore_log_excute_command(cmd)
#         Case.step("SUT env pip install packages")
#         for var in ['xmltodict','wcwidth','pathlib2','artifactory','anybadge','pyqt5','prettytable',\
#                     'setuptools_rust','bcrypt','cffi','cryptography==3.2.1','prettytable','pynacl','paramiko','scp', 'requests', 'libvirt-python']:
# 
#             # cmd = f'{self.ADD_PROXY} {self.PYTHON_PATH}  -m pip install {var}'
#             cmd = f'pip install {var}'
#             self.sut.Excute_command(cmd, timeout=300)
#         if 'vt_tools' in self.connect.env_list.keys():
#             Case.step("SUT env download virtualization tools ")
#             vt_tools = self.connect.env_list['vt_tools']
# 
#             cmd = f'{self.UNSET_PROXY} wget {vt_tools} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd,  timeout=300)
# 
#             cmd = f'wget -i {VT_TOOLS_L}/vt_linux_tools.txt --no-check-certificate -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd,  timeout=300)
# 
#             cmd = "cd {} && wget https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/linux/tools/vfio-pci-bind.sh"
#             self.sut.Excute_command(cmd=cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION), timeout=300)
#             cmd = "cd {} && chmod +777 vfio-pci-bind.sh"
#             self.sut.Excute_command(cmd=cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION), timeout=300)
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L), timeout=300)
# 
#             cmd = "cd {} && wget https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/linux/tools/OVMF.fd"
#             self.sut.Excute_command(cmd=cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS), timeout=300)
# 
#             cmd = "cd {} && wget -q https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/Automation_Tools/GNR/Linux/fio_win.zip"
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L), timeout=300)
#             cmd = "cd {} && unzip fio_win.zip"
# 
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L), timeout=300)
#             cmd = "cd {} && wget -q https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/Automation_Tools/GNR/Linux/iperf3_win.zip"
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L), timeout=300)
#             cmd = "cd {} && unzip iperf3_win.zip"
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L), timeout=300)
# 
#         self.libvirtd()
#         self.create_master_net_cfg()
#         self.maintoolkit_virbr0()
#         #self.libvirtd()
#         Case.step("SUT env rc.local cfg")
#         GET_NETWORK_INTERFACE_NAME_DYNAMIC_CMD = r"ip addr show | awk '/inet.*brd.*dynamic/{print $NF; exit}'"
#         ifcfg_file, err = self.sut.Excute_command(cmd=GET_NETWORK_INTERFACE_NAME_DYNAMIC_CMD, timeout=60)
#         if ifcfg_file != "":
#             self.sut.Excute_command(cmd="echo ''#!/bin/bash'' > /etc/rc.d/rc.local")
#             sut_ip = self.sut.sut.supported_os[self.sut.sut.default_os].ip
#             cmd_list = ['touch /var/lock/subsys/local',
#                         'systemctl disable NetworkManager',
#                         'systemctl stop NetworkManager',
#                         'systemctl restart network',
#                         'systemctl start NetworkManager',
#                         'systemctl enable NetworkManager',
#                         "\"net=\$(ip addr show | awk '/inet.*{}.*brd.*virbr0/{}')\"".format(sut_ip,"{print \$NF; exit}"),
#                         f'\'if [ "$net" == "virbr0" ]; then sleep 60; ip a del {sut_ip} dev {ifcfg_file.strip()}; nmcli connection down {ifcfg_file.strip()};  fi\'',
#                         'virsh net-list'
#                         ]
#             for cmd in cmd_list:
#                 self.sut.Excute_command(cmd=f'echo {cmd} >> /etc/rc.d/rc.local')
#             cmd = 'chmod +777 /etc/rc.d/rc.local'
#             self.sut.Excute_command(cmd=cmd, timeout=30)
# 
#         Case.step("SUT env download xmlcli tools")
#         cmd = 'cd {} && wget {} -O xmlcli.zip'
#         self.sut.Excute_command(cmd.format(VT_TOOLS_L, self.sut.connect.xmlcli_list["link"]), timeout=600)
#         cmd = 'cd {} && unzip -o xmlcli.zip -d /opt/APP/'
#         self.sut.Excute_command(cmd.format(VT_TOOLS_L), timeout=600)
#         link = self.connect.vm_linux["centos_arti_img"].split(",")[0]
#         spr_link = self.connect.vm_linux["spr_centos_arti_img"].split(",")[0]
#         windows_link = self.connect.vm_linux["windows_arti_img"].split(",")[0]
#         self.sut.Download_artifactory_to_Linux(link, SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, timeout=60 * 60)
#         self.sut.Download_artifactory_to_Linux(spr_link, SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, timeout=60 * 60)
#         self.sut.Download_artifactory_to_Linux(windows_link, SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, timeout=60 * 60)
#         pattern = re.compile(r'(?:[^/][\d\w\.]+)+$')
#         file_name_s = pattern.findall(link)[0]
#         spr_file_name_s = pattern.findall(spr_link)[0]
#         windows_file_name_s = pattern.findall(windows_link)[0]
#         cmd = "cd {} && xz -d {}"
#         self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, file_name_s), timeout=60 * 60)
#         self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, spr_file_name_s), timeout=60 * 60)
#         self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, windows_file_name_s), timeout=60 * 60)
#         cmd = "cd {} && cp {} cent0.img"
#         self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, file_name_s[:-3]), timeout=60 * 60)
# 
#         spr_cmd = "cd {} && cp {} spr.img"
#         self.sut.Excute_command(spr_cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, spr_file_name_s[:-3]),
#                                 timeout=60 * 60)
#         win_cmd = "cd {} && cp {} windows0.img"
#         self.sut.Excute_command(win_cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, windows_file_name_s[:-3]),
#                                 timeout=60 * 60)
#         cmd = 'cd {} && virt-customize -a cent0.img --root-password password:password'
#         spr_cmd = 'cd {} && virt-customize -a spr.img --root-password password:password'
#         self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS), timeout=20 * 60)
#         self.sut.Excute_command(spr_cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS), timeout=20 * 60)
# 
#     def nuc_env(self):
#         """
#         environment settings required linux
#         """
#         tools_dest = 'C:\\Automation\\Tools\\{}\\Linux\\'.format(self.connect.nuc_env_list['platform'])
# 
#         tools = self.connect.nuc_env_list['dtaf_tools']
#         self.sut.Arti_file_to_windows(link=tools, dest=tools_dest, nuc=True, timeout=1800)
#         file_name = tools.split(',')[1]
#         with open(f'{tools_dest}{file_name}', 'r') as f:
#             links = f.read()
#             for link in links.split():
#                 pattern = re.compile(r'[^.\/]+\.[^.\/]+$')
#                 file_name = pattern.findall(link)[0]
#                 cmd = f'curl {link} --output {tools_dest}{file_name} --ssl-no-revoke'
#                 self.sut.Excute_command(cmd=cmd, powershell=False, nuc=True, timeout=1000)
# 
#     def create_vms(self):
# 
#         memory = self.connect.vm_name_list.get("memory")
#         cpu = self.connect.vm_name_list.get("cpu")
#         for vm_type, vm_name in self.connect.vm_name_list.items():
#             if "rhel" == vm_type[:-1]:
#                 Case.step(f"Create VM {vm_name}")
#                 cmd = f"virsh destroy {vm_name}"
#                 self.sut.Excute_command(cmd=cmd)
#                 cmd = f"virsh undefine {vm_name}"
#                 self.sut.Excute_command(cmd=cmd)
# 
#                 template = f"{SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS}/rhel0.qcow2"
#                 cmd = f"test -f  {template} &&  echo $?"
#                 result, err = self.sut.Excute_command(cmd=cmd)
#                 if result == "":
#                     link = self.connect.vm_linux["rhel_arti_template"].split(",")[0]
#                     file_name = self.connect.vm_linux["rhel_arti_template"].split(",")[1]
#                     self.sut.Download_artifactory_to_Linux(link, SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, timeout=60 * 30)
#                     cmd = 'cd {} && unzip {}'
#                     self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, file_name), timeout=600)
#                 qocw_path = SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS + "/" + vm_name + ".qcow2"
#                 copy_cmd = f"cp -rf {template} {qocw_path}"
#                 self.sut.Excute_command(cmd=copy_cmd, timeout=60*10)
#                 os_variant = self.connect.vm_name_list.get("rhel_os_variant")
#                 cmd = 'systemctl start libvirtd'
#                 self.sut.Excute_command(cmd=cmd,timeout=60)
#                 install_cmd = 'virt-install --import --name={} --memory={} --cpu=host-passthrough --vcpu={} ' \
#                               '--disk path={} --network network=default ' \
#                               '--os-type=linux --os-variant={} ' \
#                               '--noautoconsole '
#                 out, err = self.sut.Excute_command(cmd=install_cmd.format(vm_name, memory, cpu,
#                                                                          qocw_path, os_variant), timeout=60 * 10)
#                 Case.expect(f"Successful create VM {vm_name}", "Domain creation completed." in out)
# 
#             if "centos" == vm_type[:-1]:
#                 Case.step(f"Create VM {vm_name}")
#                 cmd = f"virsh destroy {vm_name}"
#                 self.sut.Excute_command(cmd=cmd)
#                 cmd = f"virsh undefine {vm_name}"
#                 self.sut.Excute_command(cmd=cmd)
#                 template = f"{SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS}/centos0.qcow2"
#                 cmd = f"test -f  {template} &&  echo $?"
#                 result, err = self.sut.Excute_command(cmd=cmd)
#                 if result == "":
#                     link = self.connect.vm_linux["centos_arti_template"].split(",")[0]
#                     file_name = self.connect.vm_linux["centos_arti_template"].split(",")[1]
#                     self.sut.Download_artifactory_to_Linux(link, SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, timeout=60*30)
#                     cmd = 'cd {} && unzip {}'
#                     self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, file_name), timeout=600)
#                 qocw_path = SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS + "/" + vm_name + ".qcow2"
#                 copy_cmd = f"cp -rf {template} {qocw_path}"
#                 self.sut.Excute_command(cmd=copy_cmd, timeout=60*10)
#                 os_variant = self.connect.vm_name_list.get("centos_os_variant")
#                 cmd = 'systemctl start libvirtd'
#                 self.sut.Excute_command(cmd=cmd,timeout=60)
#                 install_cmd = 'virt-install --import --name={} --memory={} --cpu=host-passthrough --vcpu={} ' \
#                               '--disk path={} --network network=default ' \
#                               '--os-type=linux --os-variant={} ' \
#                               '--noautoconsole '
#                 out, err = self.sut.Excute_command(cmd=install_cmd.format(vm_name, memory, cpu,
#                                                                          qocw_path, os_variant), timeout=60 * 15)
#                 Case.expect(f"Successful create VM {vm_name}", "Domain creation completed." in out)
#             if "windows" == vm_type[:-1]:
#                 Case.step(f"Create VM {vm_name}")
#                 cmd = f"virsh destroy {vm_name}"
#                 self.sut.Excute_command(cmd=cmd)
#                 cmd = f"virsh undefine {vm_name}"
#                 self.sut.Excute_command(cmd=cmd)
#                 template = f"{SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS}/windows0.qcow2"
#                 cmd = f"test -f  {template} &&  echo $?"
#                 result, err = self.sut.Excute_command(cmd=cmd)
#                 if result == "":
#                     link = self.connect.vm_linux["windows_arti_template"].split(",")[0]
#                     file_name = self.connect.vm_linux["windows_arti_template"].split(",")[1]
#                     self.sut.Download_artifactory_to_Linux(link, SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, timeout=60 * 30)
#                     cmd = 'cd {} && unzip {}'
#                     self.sut.Excute_command(cmd.format(SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS, file_name), timeout=600)
#                 qocw_path = SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS + "/" + vm_name + ".qcow2"
#                 copy_cmd = f"cp -rf {template} {qocw_path}"
#                 self.sut.Excute_command(cmd=copy_cmd, timeout=60*10)
#                 os_variant = self.connect.vm_name_list.get("windows_os_variant")
#                 cmd = 'systemctl start libvirtd'
#                 self.sut.Excute_command(cmd=cmd,timeout=60)
#                 install_cmd ='virt-install --import --name={} --memory={} --cpu=host-passthrough --vcpu={} ' \
#                              '--disk path={} --network network=default ' \
#                              '--os-type=windows --os-variant={} ' \
#                              '--noautoconsole '
#                 out, err = self.sut.Excute_command(cmd=install_cmd.format(vm_name, memory, cpu,
#                                                                          qocw_path, os_variant), timeout=60 * 10)
#                 Case.expect(f"Successful create VM {vm_name}", "Domain creation completed." in out)
# 
#     def rename_package(self, link):
#         if "," in link:
#             link, rename = link.split(",")
#             return link,rename
#         return link,None
# 
#     def vtdchain(self):
#         if 'vtdchain' in self.connect.vtdchain_list.keys():
#             Case.step("SUT vtdchain tools")
#             vtdchain_list = self.connect.vtdchain_list['vtdchain']
#             # download vtdchain and unzip vtdchain
#             cmd = f'{self.UNSET_PROXY} wget {vtdchain_list} -P /boot/efi --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#             cmd = f'cd /boot/efi;unzip -o /boot/efi/vtdchain_tool.zip -d /boot/efi'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#     def dlb(self):
#         if 'driver_pwd' in self.connect.dlb_list.keys():
#             Case.step("SUT dlb tools")
#             dlb_driver = self.connect.dlb_list['driver_pwd']
#             dlb_driver, rename = self.rename_package(dlb_driver)
#             Case.prepare(f"wget {dlb_driver}")
#             cmd = f'{self.UNSET_PROXY} wget --user="{USERNAME}" --password="{USERPASSWD}" -P {VT_TOOLS_L} {dlb_driver} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             try_times = 3
#             for i in range(try_times):
#                 try:
#                     self.sut.Ignore_log_excute_command(cmd=cmd, timeout=60)
#                 except Exception as _:
#                     if i == try_times-1:
#                         raise f"Download {try_times} failures"
#                 else:
#                     break
#             if rename:
#                 old_name = dlb_driver.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
#             for i in "meson kernel-gnr-bkc-modules-internal kernel-gnr-bkc-devel python3-pyelftools".split():
#                 cmd = f'yum install -y {i} --allowerasing --skip-broken --nobest'
#                 self.sut.Excute_command(cmd=cmd, timeout=300)
# 
# 
#     def qat(self):
#         if 'driver_pwd' in self.connect.qat_list.keys():
#             Case.step("SUT qat tools")
#             qat_driver = self.connect.qat_list['driver_pwd']
#             qat_driver, rename = self.rename_package(qat_driver)
#             Case.prepare(f"wget {qat_driver}")
#             cmd = f'{self.UNSET_PROXY} wget --user="{USERNAME}" --password="{USERPASSWD}" {qat_driver} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             try_times = 3
#             for i in range(try_times):
#                 try:
#                     self.sut.Ignore_log_excute_command(cmd=cmd, timeout=60)
#                 except Exception as _:
#                     if i == try_times-1:
#                         raise f"Download {try_times} failures"
#                 else:
#                     break
#             if rename:
#                 old_name = qat_driver.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
#             for i in 'zlib-devel.x86_64 yasm systemd-devel boost-devel.x86_64 openssl-devel \
#                     libnl3-devel gcc make gcc-c++  libgudev.x86_64 libgudev-devel.x86_64 \
#                     systemd* kernel-gnr-bkc-devel'.split():
#                 cmd = f'yum install -y {i} --allowerasing --skip-broken --nobest'
#                 self.sut.Excute_command(cmd=cmd, timeout=300)
# 
#     def dsa_iax(self):
#         if 'driver' in self.connect.dsa_iax_list.keys():
#             Case.step("SUT dsa_iax tools")
#             dsa_iax_driver = self.connect.dsa_iax_list['driver']
#             dsa_iax_driver, rename = self.rename_package(dsa_iax_driver)
#             cmd = f'{self.UNSET_PROXY} wget {dsa_iax_driver} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             if rename:
#                 old_name = dsa_iax_driver.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#         if 'test_tool' in self.connect.dsa_iax_list.keys():
#             dsa_iax_test_tool = self.connect.dsa_iax_list['test_tool']
#             dsa_iax_test_tool, rename = self.rename_package(dsa_iax_test_tool)
#             cmd = f'{self.UNSET_PROXY} wget {dsa_iax_test_tool} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             if rename:
#                 old_name = dsa_iax_test_tool.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#         cmd = 'yum groupinstall -y "Development Tools"'
#         self.sut.Excute_command(cmd)
#         for i in 'autoconf automake libtool pkgconf rpm-build rpmdevtools \
#                 asciidoc xmlto libuuid-devel json-c-devel kmod-devel libudev-devel'.split():
#             cmd = f'yum install -y {i} --allowerasing --skip-broken --nobest'
#             self.sut.Excute_command(cmd=cmd, timeout=300)
# 
#     def stress_tools(self):
#         Case.step("SUT stress_tools")
#         stress_tools = [i for i in self.connect.stress_tools_list.values() if i.startswith("http")]
#         for link in stress_tools:
#             link, rename = self.rename_package(link)
#             cmd = f'{self.UNSET_PROXY} wget {link} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             if rename:
#                 old_name = link.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#     def sgx(self):
#         if 'driver' in self.connect.sgx_list.keys():
#             Case.step("SUT sgx tools")
#             sgx_driver = self.connect.sgx_list['driver']
#             sgx_driver, rename = self.rename_package(sgx_driver)
#             cmd = f'{self.UNSET_PROXY} wget {sgx_driver} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             if rename:
#                 old_name = sgx_driver.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#         if 'sgx_functionvalidation' in self.connect.sgx_list.keys():
#             sgx_functionvalidation = self.connect.sgx_list['sgx_functionvalidation']
#             sgx_functionvalidation, rename = self.rename_package(sgx_functionvalidation)
#             cmd = f'{self.UNSET_PROXY} wget {sgx_functionvalidation} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             if rename:
#                 old_name = sgx_functionvalidation.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
# 
#         if 'protobuf' in self.connect.sgx_list.keys():
#             sgx_protobuf = self.connect.sgx_list['protobuf']
#             sgx_protobuf, rename = self.rename_package(sgx_protobuf)
#             cmd = f'{self.UNSET_PROXY} wget {sgx_protobuf} -P {VT_TOOLS_L} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             cmd = f'rpm -ivh {VT_TOOLS_L}/protobuf.rpm'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             if rename:
#                 old_name = sgx_protobuf.split("/")[-1]
#                 cmd = f"mv -f {VT_TOOLS_L}/{old_name} {VT_TOOLS_L}/{rename}"
#                 self.sut.Excute_command(cmd=cmd, timeout=120)
# 
# 
#     def iproute(self):
#         if 'driver' in self.connect.iproute_list.keys():
#             Case.step("SUT iproute tools")
#             iproute_driver = self.connect.iproute_list['driver']
#             pattern = re.compile(r'(?:[^/][\d\w\.]+)+$')
#             file_name_s = pattern.findall(iproute_driver)[0]
#             cmd = f'{self.UNSET_PROXY} wget {iproute_driver} -O {VT_TOOLS_L}/{file_name_s} --page-requisites --no-host-directories --cut-dirs=1000URL'
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             cmd = "yum -y install libmnl-devel"
#             self.sut.Excute_command(cmd=cmd, timeout=120)
#             cmd = "cd {} && unzip {}"
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L, file_name_s), timeout=120)
#             cmd = "cd {}/{} && ./configure"
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L, file_name_s[:-4]), timeout=120)
#             cmd = "cd {}/{} && make && make install"
#             self.sut.Excute_command(cmd=cmd.format(VT_TOOLS_L, file_name_s[:-4]), timeout=120)
# 
#     def main(self):
#         if self.connect.env_deploy.lower() == 'true':
#             self.env()
# 
#         if self.connect.nuc_env_deploy.lower() == 'true':
#             self.nuc_env()
# 
#         if self.connect.vtdchain_deploy.lower() == 'true':
#             self.vtdchain()
# 
#         if self.connect.dlb_deploy.lower() == 'true':
#             self.dlb()
# 
#         if self.connect.qat_deploy.lower() == 'true':
#             self.qat()
# 
#         if self.connect.dsa_iax_deploy.lower() == 'true':
#             self.dsa_iax()
# 
#         if self.connect.stress_tools_deploy.lower() == 'true':
#             self.stress_tools()
# 
#         if self.connect.sgx_deploy.lower() == 'true':
#             self.sgx()
# 
#         if self.connect.iproute_deploy.lower() == 'true':
#             self.iproute()
# 
#         if self.connect.vm_names_deploy.lower() == 'true':
#             self.create_vms()
#

class Hyper_V:

    def __init__(self, sut):
        self.python = None
        self.sut = sut
        self.init_path()
        self.init_variables()

    def init_path(self):
        init_sut_path_cmd = [f"New-Item -Path '{SUT_TOOLS_WINDOWS_ROOT}' -ItemType Directory  -Force",
                             f"New-Item -Path '{SUT_TOOLS_WINDOWS_VIRTUALIZATION}' -ItemType Directory  -Force",
                             f"New-Item -Path '{VT_IMGS_W}' -ItemType Directory  -Force",
                             f"New-Item -Path '{VT_TOOLS_W}' -ItemType Directory  -Force",
                             f"New-Item -Path '{SUT_ISO_IMAGE_LOCATION}' -ItemType Directory  -Force"]

        for ext_cmd in init_sut_path_cmd:
            self.sut.execute_shell_cmd(cmd=f'{ext_cmd}', powershell=True)

    def init_variables(self):
        self.python = 'c:\\python38\\python.exe'

    def deploy_auto_env(self):
        Case.step("Enable sshd/rdp accese and disable firewall")
        ext_cmd_list = [f"Start-Service sshd", f"Set-Service -Name sshd -StartupType 'Automatic'",
                        f"netsh advfirewall set allprofiles state off",
                        f"REG ADD 'HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Internet Settings' /v AutoDetect /t REG_DWORD /d 0 /f",
                        f"netsh advfirewall firewall set rule group=\"remote desktop\" new enable=Yes"]
        for ext_cmd in ext_cmd_list:
            self.sut.execute_shell_cmd(cmd=ext_cmd, powershell=True, timeout=600)

        Case.step("Set-ExecutionPolicy")
        """
        suppress progress bar in powershell commands
        """
        self.sut.execute_shell_cmd(cmd=f"Set-ExecutionPolicy -ExecutionPolicy Bypass", powershell=True, timeout=600)
        pscfg, err = self.sut.execute_shell_cmd("$PROFILE.AllUsersAllHosts", powershell=True)
        file, err = self.sut.execute_shell_cmd(f"Test-Path {pscfg.strip()}", powershell=True)
        if "True" not in file:
            self.sut.execute_shell_cmd('New-Item -Path $pscfg -ItemType "file" -Force', powershell=True)

        Case.step("Prepare install python38")
        __, result, err = self.sut.execute_shell_cmd(f"Test-Path -Path  {self.python}", powershell=True)
        if "False" in result:
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.python_windows, destination=VT_TOOLS_W)
            cmd = f"{VT_TOOLS_W}\\python38.exe /passive InstallAllUsers=1 PrependPath=1 TargetDir=C:\Python38"
            self.sut.execute_shell_cmd(cmd=cmd, powershell=False, timeout=600)

        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.python_pip_module_windows,
                                                  destination=Windows_TOOLS)
        self.sut.execute_shell_cmd(
            cmd=f'Expand-Archive -Path {Windows_TOOLS}\\pip_paramiko_w.zip -DestinationPath {Windows_TOOLS} -Force',
            powershell=True, nuc=False, timeout=600)

        for package in ['pip-23.1.2-py3-none-any.whl', 'pycparser-2.21-py2.py3-none-any.whl',
                        'cffi-1.15.1-cp38-cp38-win_amd64.whl', 'PyNaCl-1.5.0-cp36-abi3-win_amd64.whl',
                        'cryptography-40.0.2-cp36-abi3-win_amd64.whl', 'bcrypt-4.0.1-cp38-abi3-win_amd64.whl',
                        'paramiko-3.1.0-py3-none-any.whl', 'scp-0.14.5-py2.py3-none-any.whl']:
            self.sut.execute_shell_cmd(cmd=f'{self.python} -m pip install {Windows_TOOLS}\\pip_paramiko_w\\{package}',
                                       powershell=True, timeout=600)

        Case.step("Deploy auto-poc for windows")
        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.auto_poc_wind, destination=Windows_Path,
                                                  timeout=600)
        self.sut.execute_shell_cmd(cmd=f'New-Item -Path {Windows_Path}\\auto-poc -ItemType Directory  -Force',
                                   powershell=True, nuc=False, timeout=30)
        self.sut.execute_shell_cmd(
            cmd=f'Expand-Archive -Path {Windows_Path}\\auto-poc -DestinationPath {Windows_Path} -Force',
            powershell=True, timeout=600)

        __, result, err = self.sut.execute_shell_cmd(
            cmd=f"Test-Path -Path C:\\BKCPkg\\xmlcli\\xmlcli_get_verify_knobs.py",
            powershell=True)
        if "false" in result.lower():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.xmlcli_windows,
                                                      destination="C:\\BKCPkg\\",
                                                      timeout=300)
            self.sut.execute_shell_cmd(
                cmd=f'Expand-Archive -Path C:\\BKCPkg\\xmlcli_windows_linux_esxi_Python.zip '
                    f'-DestinationPath "C:\\BKCPkg\\" -Force',
                powershell=True, nuc=False, timeout=600)

    def deploy_hyperv_environment(self):
        Case.step("Install hypervisor (hyper-v) for windows")
        cmd = "powershell.exe $progressPreference = 'silentlyContinue';" \
              "Get-WindowsFeature -Name 'Hyper*'"
        __, result, err = self.sut.execute_shell_cmd(cmd=cmd, powershell=False, timeout=3 * 60)
        if "Installed" not in result:
            cmd = "powershell.exe $progressPreference = 'silentlyContinue';" \
                  "Install-WindowsFeature -Name Hyper-V -IncludeManagementTools -Restart "
            self.sut.execute_shell_cmd(cmd=cmd, powershell=False, timeout=3 * 60)
            Case.sleep(300, min_iterval=300)
            Case.wait_and_expect('wait for restoring sut ssh connection', 60 * 5, self.sut.sut.check_system_in_os)
            Case.sleep(120, min_iterval=120)

        Case.step("Create external virtual switch ")
        get_vm_switch = f"Get-VMSwitch -Name ExternalSwitch"
        __, result, err = self.sut.execute_shell_cmd(get_vm_switch, powershell=True)
        if result == "":
            GET_NETWORK_INTERFACE_NAME_CMD = "powershell.exe $progressPreference = 'silentlyContinue'" \
                                             ";  Get-NetIPAddress  ^| Select InterfaceAlias, " \
                                             "IPAddress, PrefixOrigin, SuffixOrigin"
            adapter_info, err = self.sut.execute_shell_cmd(GET_NETWORK_INTERFACE_NAME_CMD)
            regex_for_nic_name = r".+\s*10\..+\s*Dhcp.+\s*Dhcp"
            adapter_list = re.findall(regex_for_nic_name, adapter_info)
            display_name = (re.sub('\s\s+', '*', adapter_list[0])).split('*')
            adapter_name = display_name[0]
            NEW_VM_SWITCH_CMD = "powershell.exe $progressPreference = 'silentlyContinue'; " \
                                "New-VMSwitch -Name {} -NetAdapterName '{}' -AllowManagementOS $true"
            try:
                self.sut.execute_shell_cmd(cmd=NEW_VM_SWITCH_CMD.format("ExternalSwitch", adapter_name), timeout=1 * 60)
            except Exception as ex:
                pass

        __, result, err = self.sut.execute_shell_cmd(get_vm_switch, powershell=True)
        Case.expect(f"Check \"ExternalSwitch\" can be created", "ExternalSwitch".lower() in result.lower())

        Case.step("Create external virtual switch ")
        get_vm_swtich = f"Get-VMSwitch -Name \"InternalSwitch\""
        __, result, err = self.sut.execute_shell_cmd(get_vm_swtich, powershell=True)
        if result == "":
            self.sut.execute_shell_cmd(cmd=f"New-VMSwitch -Name 'InternalSwitch' -SwitchType Internal",
                                       powershell=True, timeout=1 * 60)

        __, result, err = self.sut.execute_shell_cmd(get_vm_swtich, powershell=True)
        Case.expect(f"Check InternalSwitch can be created", "InternalSwitch".lower() in result.lower())

        __, result, err = self.sut.execute_shell_cmd(cmd=f"Get-NetIPAddress", powershell=True, timeout=1 * 60)
        if 'IPAddress         : 10.0.0.3'.lower() not in result.lower():
            result, err = self.sut.execute_shell_cmd(
                cmd=f"New-NetIPAddress -IPAddress 10.0.0.3 -InterfaceAlias  'vEthernet (InternalSwitch)' "
                    f"-DefaultGateway 10.0.0.1 -AddressFamily IPv4 -PrefixLength 24",
                powershell=True, timeout=1 * 60)
            Case.expect("Set internal switch ip addr", 'IPAddress         : 10.0.0.3' in result)
        self.sut.execute_shell_cmd(
            cmd=f"Set-DnsClientServerAddress -InterfaceAlias 'vEthernet (InternalSwitch)' -ServerAddresses 10.0.0.2",
            powershell=True, timeout=1 * 60)

        __, result, err = self.sut.execute_shell_cmd(cmd=f"Install-WindowsFeature DHCP -IncludeManagementTools",
                                                     powershell=True, timeout=5 * 60)
        Case.expect(f"Enable dhcp serive result", "True".lower() in result.lower())

        __, result, err = self.sut.execute_shell_cmd(cmd=f"Get-DhcpServerv4Scope", powershell=True, timeout=5 * 60)
        if "dhcp" not in result.lower():
            self.sut.execute_shell_cmd(
                cmd=f"Add-DhcpServerv4Scope -name 'dhcp' -StartRange 10.0.0.1 -EndRange 10.0.0.254 "
                    f"-SubnetMask 255.255.254.0 -State Active",
                powershell=True, timeout=5 * 60)

        self.sut.execute_shell_cmd(
            cmd=f"Add-DhcpServerv4ExclusionRange -ScopeID 10.0.0.0 -StartRange 10.0.0.1 -EndRange 10.0.0.15",
            powershell=True, timeout=5 * 60)

    def deploy_stress_tools(self):
        Case.step("Deploy sgx tools")
        if 'sgx_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['sgx_wind'],
                                                      destination=SUT_TOOLS_WINDOWS_VIRTUALIZATION, timeout=300)

        if 'sgx_enablesgx_vm_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['sgx_enablesgx_vm_wind'],
                                                      destination=SUT_TOOLS_WINDOWS_VIRTUALIZATION, timeout=300)

        if 'ipmitool_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['ipmitool_wind'],
                                                      destination=SUT_TOOLS_WINDOWS_VIRTUALIZATION, timeout=300)

        if 'ethr_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['ethr_wind'],
                                                      destination=SUT_TOOLS_WINDOWS_VIRTUALIZATION, timeout=300)

        if 'ntttcp_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['ntttcp_wind'],
                                                      destination=SUT_TOOLS_WINDOWS_VIRTUALIZATION, timeout=300)

    def deploy_vms(self):
        for vm_key, vm_value in connect.vm_source_file_wind.items():
            if 'regirster_vm' in vm_key:
                continue
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=vm_value, destination=Windows_IMG,
                                                      timeout=1200)
            rename = vm_value.split(',')[1]
            if '.zip' in rename:
                dir_name = rename.replace(".zip", "")
                if connect.overwrite.lower() == 'true':
                    self.sut.execute_shell_cmd(
                        cmd=f'Remove-Item {Windows_IMG}\\{dir_name} -Force -Recurse -ErrorAction SilentlyContinue',
                        powershell=True, timeout=1200)

                self.sut.execute_shell_cmd(cmd=f'New-Item -Path {Windows_IMG}\\{dir_name} -ItemType Directory  -Force',
                                           powershell=True, timeout=30)
                self.sut.execute_shell_cmd(
                    cmd=f'Expand-Archive -Path {Windows_IMG}\\{rename} -DestinationPath {Windows_IMG}\\{dir_name} -Force',
                    powershell=True, timeout=600)

        mac_address = Etree.get_mac_list(os='windows')
        mac_address = list(reversed(mac_address))
        mac_order = 0

        for vm_name, vhdx_path in connect.vm_register_wind.items():
            hyperv = get_vmmanger(self.sut.sut)
            out, err = self.sut.execute_shell_cmd(cmd=f'Get-VM -Name "{vm_name}"', powershell=True, timeout=600)

            if vm_name in out and connect.vm_refresh_vm.lower() == 'true':
                hyperv.undefine_vm(vm_name=vm_name)

            if vm_name in out and connect.vm_refresh_vm.lower() == 'false':
                continue

            self.sut.execute_shell_cmd(cmd=f'Copy-Item -Path {vhdx_path} -Destination {Windows_IMG}\\{vm_name}.vhdx',
                                       powershell=True, timeout=600)

            if 'gen2' in vm_name.lower() or 'sgx' in vm_name.lower():
                out, err = self.sut.execute_shell_cmd(
                    cmd=f"New-VM -Name {vm_name} -VHDPath {Windows_IMG}\\{vm_name}.vhdx  "
                        f"-MemoryStartupBytes 4096MB -SwitchName ExternalSwitch -Generation 2",
                    powershell=True)
            else:
                out, err = self.sut.execute_shell_cmd(
                    cmd=f"New-VM -Name {vm_name} -VHDPath {Windows_IMG}\\{vm_name}.vhdx  "
                        f"-MemoryStartupBytes 4096MB -SwitchName ExternalSwitch ",
                    powershell=True)
            Case.expect("Verify vm has been created", vm_name in out)

            self.sut.execute_shell_cmd(cmd=f"Set-VMProcessor {vm_name} -Count 2", powershell=True)
            self.sut.execute_shell_cmd(cmd=f"Set-VMMemory {vm_name} -StartupBytes 4GB", powershell=True)
            Maintoolkit_windows.set_vm_mac_address(sut=self.sut.sut, hyperv=hyperv, vmname=vm_name,
                                                   mac_add=mac_address[mac_order])
            mac_order = mac_order + 1

            self.sut.execute_shell_cmd(cmd=f"Add-VMNetworkAdapter -VMName {vm_name} -SwitchName InternalSwitch",
                                       powershell=True)

    def main(self):
        self.deploy_auto_env()
        self.deploy_hyperv_environment()
        self.deploy_vms()


class Esxi:

    def __init__(self, sut):
        self.sut = sut
        self.init_path()

    def init_path(self):
        init_sut_path_cmd = [f'mkdir -p {SUT_TOOLS_VMWARE_VIRTUALIZATION}',
                             f'mkdir -p {SUT_TOOLS_VMWARE_VIRTUALIZATION_APISCRIPTS}',
                             f'mkdir -p {SUT_TOOLS_VMWARE_VIRTUALIZATION_TOOLS}',
                             f'mkdir -p {ESXI_DATASTORE1}',
                             f'mkdir -p {ESXI_Path}',
                             f'mkdir -p {ESXI_TOOLS}',
                             f'mkdir -p {ESXI_VMDK}',
                             f'mkdir -p {ESXI_INBANDS}'
                             ]
        for ext_cmd in init_sut_path_cmd:
            self.sut.execute_shell_cmd(cmd=ext_cmd, timeout=30)

    def deploy_auto_env(self):
        Case.step("Enable vmware xmlcli and verify result")
        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.xmlcli_esxi,
                                                  destination=SUT_TOOLS_VMWARE_VIRTUALIZATION, timeout=300)

        self.sut.execute_shell_cmd(
            cmd=f'cd {SUT_TOOLS_VMWARE_VIRTUALIZATION}; unzip -o xmlcli_windows_linux_esxi_Python.zip', timeout=600)
        __, result, err = self.sut.execute_shell_cmd(
            cmd=f'cd {SUT_TOOLS_VMWARE_VIRTUALIZATION}/xmlcli; python xmlcli_save_read_prog_knobs.py '
                f'esxi_certificate_injection /vmfs/volumes/datastore1/xmlcli', timeout=600)
        if "Reboot Required: true".lower() in result.lower():
            Maintoolkit_esxi.reboot_the_sut(sut=self.sut)

        verify_xmlcli_enable = 'python xmlcli_get_verify_knobs.py "read_current_knob_write" "ProcessorVmxEnable"'
        __, result, err = self.sut.execute_shell_cmd(
            cmd=f'cd {SUT_TOOLS_VMWARE_VIRTUALIZATION}/xmlcli;{verify_xmlcli_enable}',
            timeout=600)
        Case.expect('verify enable vmware xmlcli result', 'name="ProcessorVmxEnable"'.lower() in result.lower())

    def deploy_stress_tools(self):
        Case.step("Deploy vmd tools")
        if 'vmd_driver_esxi' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['vmd_driver_esxi'],
                                                      transit=True, destination=ESXI_TOOLS, timeout=600)
        Case.step("Deploy iometer")
        if 'iometer_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['iometer_wind'],
                                                      destination=VT_TOOLS_N, timeout=600)
            folder_name = 'iometer_win'
            self.sut.execute_host_cmd(
                cmd=f'New-Item -Path {DTAF_IMAGEPATH}\\{folder_name} -ItemType Directory  -Force',
                powershell=True, timeout=30)
            self.sut.execute_host_cmd(
                cmd=f'Expand-Archive -Path {VT_TOOLS_N}\\iometer_win.zip -DestinationPath {VT_TOOLS_N}\\{folder_name} -Force',
                powershell=True, timeout=600)

        Case.step("Deploy ethr tools")
        if 'ethr_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['ethr_wind'],
                                                      destination=VT_TOOLS_N, timeout=600)
            folder_name = 'ethr_windows'
            self.sut.execute_host_cmd(
                cmd=f'New-Item -Path {DTAF_IMAGEPATH}\\{folder_name} -ItemType Directory  -Force',
                powershell=True, timeout=30)
            self.sut.execute_host_cmd(
                cmd=f'Expand-Archive -Path {VT_TOOLS_N}\\ethr_windows.zip '
                    f'-DestinationPath {VT_TOOLS_N}\\{folder_name} -Force',
                powershell=True, timeout=600)

        Case.step("Deploy ntttcp tools")
        if 'ntttcp_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['ntttcp_wind'],
                                                      destination=VT_TOOLS_N, timeout=600)
            folder_name = 'ntttcp_windows'
            self.sut.execute_host_cmd(
                cmd=f'New-Item -Path {DTAF_IMAGEPATH}\\{folder_name} -ItemType Directory  -Force',
                powershell=True, timeout=30)
            self.sut.execute_host_cmd(
                cmd=f'Expand-Archive -Path {VT_TOOLS_N}\\ntttcp_windows.zip '
                    f'-DestinationPath {VT_TOOLS_N}\\{folder_name} -Force',
                powershell=True, timeout=600)

        Case.step("Deploy dsa/iaa tools")
        if 'dsa_iaa_esxi' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['dsa_iaa_esxi'],
                                                      transit=True, destination=ESXI_TOOLS, timeout=600)

        Case.step("Deploy dlb tools")
        if 'dlb_esxi' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['dlb_esxi'],
                                                      transit=True, destination=ESXI_TOOLS, timeout=600)
        if 'dlb_cent' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['dlb_cent'],
                                                      destination=NUC_TOOLS, timeout=600)

        Case.step("Deploy qat tools")
        if 'qat_esxi' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['qat_esxi'],
                                                      transit=True, destination=ESXI_TOOLS, timeout=600)
        if 'qat_cent' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['qat_cent'],
                                                      destination=NUC_TOOLS, timeout=600)

        Case.step("Deploy vsphere tools")
        if 'vsphere' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['vsphere'],
                                                      destination=NUC_TOOLS, timeout=600)

        if 'vsphere_ks_json' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut,
                                                      link=connect.stress_tools_dict['vsphere_ks_json'],
                                                      destination=NUC_TOOLS, timeout=600)
            file = f"{NUC_TOOLS}\\embedded_vCSA_on_ESXi.json"
            SearchText = '            "hostname": "xxx.xxx.xxx.xxx",\n'
            ReplaceText = f'            "hostname": "{self.sut.supported_os[self.sut.default_os].ip}",\n'
            with open(file, "r+") as f:
                for line in f.readlines():
                    if SearchText in line:
                        line = ReplaceText
                    f.write(line)

        Case.step("Deploy ballon bash")
        if 'balloon_bash_vm_cent' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut,
                                                      link=connect.stress_tools_dict['balloon_bash_vm_cent'],
                                                      destination=NUC_TOOLS, timeout=600)

    def deploy_vms(self):
        for vm_key, vm_value in connect.vm_source_file_esxi.items():
            if 'regirster_vm' in vm_key:
                continue
            if '.iso' in vm_value:
                ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=vm_value,
                                                          destination=DTAF_IMAGEPATH, timeout=1200)
                continue
            else:
                ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=vm_value, destination=DTAF_IMAGEPATH,
                                                          timeout=1200)
            rename = vm_value.split(',')[1]
            if '.zip' in rename:
                dir_name = rename.replace(".zip", "")
                if connect.overwrite.lower() == 'true':
                    self.sut.execute_host_cmd(
                        cmd=f'Remove-Item {DTAF_IMAGEPATH}\\{dir_name} -Force -Recurse -ErrorAction SilentlyContinue',
                        powershell=True, timeout=1200)

                self.sut.execute_host_cmd(
                    cmd=f'New-Item -Path {DTAF_IMAGEPATH}\\{dir_name} -ItemType Directory  -Force',
                    powershell=True, timeout=30)
                self.sut.execute_host_cmd(cmd=f'Expand-Archive -Path {DTAF_IMAGEPATH}\\{rename} '
                                              f'-DestinationPath {DTAF_IMAGEPATH}\\{dir_name} -Force',
                                          powershell=True, timeout=600)

        mac_address = Etree.get_mac_list(os='esxi')
        mac_address = list(reversed(mac_address))
        mac_order = 0
        for vm_name, vm_path in connect.vm_register_esxi.items():
            esxi = get_vmmanger(self.sut)

            __, out, err = esxi.execute_host_cmd_esxi(cmd=f'Get-VM -Name "{vm_name}"')
            if vm_name in out and connect.vm_refresh_vm.lower() == 'true':
                if esxi.is_vm_running(vm_name=vm_name):
                    esxi.shutdown_vm(vm_name=vm_name)
                esxi.execute_host_cmd_esxi(cmd=f"Remove-VM -VM '{vm_name}' -DeletePermanently -Confirm:$false",
                                           timeout=600)

            if vm_name in out and connect.vm_refresh_vm.lower() == 'false':
                continue

            self.sut.execute_shell_cmd(cmd=f'rm -rf {SUT_TOOLS_VMWARE_VIRTUALIZATION}/{vm_name}')

            import_ovf = lambda name, path: f'$vmHost = Get-VMHost ' \
                                            f'-Name {self.sut.supported_os[self.sut.default_os].ip};' \
                                            f'Import-vApp -Source "{path}" -VMHost $vmHost -Name {name} ' \
                                            f'-DiskStorageFormat Thin'

            path = f'{DTAF_IMAGEPATH}\\{vm_path}'
            __, install_result, err = esxi.execute_host_cmd_esxi(cmd=f"{import_ovf(vm_name, path)}", timeout=1800)
            Case.expect(f"verify import(ovf) vm {vm_name} result", "PowerState".lower() in install_result.lower())

            Maintoolkit_esxi.set_vm_mac_address(sut=self.sut, esxi=esxi, vmname=vm_name,
                                                mac_add=mac_address[mac_order])
            mac_order = mac_order + 1

    def main(self):
        self.deploy_auto_env()
        self.deploy_stress_tools()
        self.deploy_vms()
