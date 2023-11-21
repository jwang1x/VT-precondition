import fabric
from dtaf_core.lib.os_lib import OsCommandResult
from dtaf_core.lib.exceptions import OsCommandException, OsCommandTimeoutException
from src.virtualization.lib.tkinit import *
from src.virtualization.gnr.precondition_setup.vtsetup.ini_info import *
from src.virtualization.lib.virtualization_basic import *
from src.virtualization.gnr.precondition_setup.vtsetup.get_version_info import get_info

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

NUC_TOOLS_WINDOWS_VIRTUALIZATION = SUT_TOOLS_WINDOWS_VIRTUALIZATION = f'{SUT_TOOLS_WINDOWS_ROOT}\\' \
                                                                      f'domains\\virtualization\\'
VT_IMGS_N = VT_IMGS_W = f'{SUT_TOOLS_WINDOWS_VIRTUALIZATION}\\imgs\\'
VT_TOOLS_N = VT_TOOLS_W = f'{SUT_TOOLS_WINDOWS_VIRTUALIZATION}\\tools\\'
SUT_ISO_IMAGE_LOCATION = "C:\\Automation\\"

# Esxi
SUT_TOOLS_VMWARE_VIRTUALIZATION = "/vmfs/volumes/datastore1"
SUT_TOOLS_VMWARE_VIRTUALIZATION_APISCRIPTS = f'{SUT_TOOLS_VMWARE_VIRTUALIZATION}' \
                                             f'/BKCPkg/domains/virtualization/apiscripts/'
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
        logger.info(f'<xxxxxxxxxxxxxx> execute_host_cmd :curl -u {USERNAME}:**** {download_link} '
                    f'--output {destination}\\{rename} --ssl-no-revoke  timeout[{timeout}] cwd[None]')

        ExtensionSutFunction.ignore_log_excute_command(sut=sut, cmd=ext_cmd, powershell=False, timeout=timeout,
                                                       nuc=True)

    @classmethod
    def download_file_to_sut(cls, sut, link, destination, authentication=False, timeout=600):
        download_link = link.split(',')[0]
        rename = link.split(',')[1]

        if 'esxi' in sut.default_os_boot.lower():
            __, exist, err = sut.execute_shell_cmd(cmd=f'ls {destination} | grep {rename} ', timeout=timeout)
            if (rename in exist and connect.overwrite.lower() == 'true') or rename not in exist:
                sut.execute_shell_cmd(cmd=f'rm -rf {destination}/{rename}', timeout=timeout)
                if authentication:
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

            if authentication:
                logger.info(f'<xxxxxxxxxxxxxx> execute_shell_cmd :curl -u {USERNAME}:**** {download_link} '
                            f'--output {destination}\\{rename} --ssl-no-revoke  timeout[{timeout}] cwd[None]')
                cls.ignore_log_excute_command(sut=sut,
                                              cmd=f'curl -u {USERNAME}:{USERPASSWD} {download_link} '
                                                  f'--output {destination}\\{rename} --ssl-no-revoke',
                                              powershell=False, timeout=timeout)
            else:
                logger.info(f'<xxxxxxxxxxxxxx> execute_shell_cmd :curl  {download_link} '
                            f'--output {destination}\\{rename} --ssl-no-revoke  timeout[{timeout}] cwd[None]')
                cls.ignore_log_excute_command(sut=sut,
                                              cmd=f'curl {download_link} '
                                                  f'--output {destination}\\{rename} --ssl-no-revoke',
                                              powershell=False, timeout=timeout)

        if 'linux' in sut.default_os_boot.lower():
            __, exist, err = sut.execute_shell_cmd(cmd=f'ls {destination} | grep {rename} ', timeout=timeout)
            if (rename in exist and connect.overwrite.lower() == 'true') or rename not in exist:
                sut.execute_shell_cmd(cmd=f'rm -rf {destination}/{rename}', timeout=timeout)
                if authentication:
                    logger.info(f'<xxxxxxxxxxxxxx> execute_shell_cmd : unset http_proxy; unset https_proxy;'
                                f'curl -u {USERNAME}:**** {download_link} --output {destination}/{rename} '
                                f'--ssl-no-revoke timeout[{timeout}] cwd[None]')
                    cls.ignore_log_excute_command(sut=sut,
                                                  cmd=f'unset http_proxy; unset https_proxy;'
                                                      f'curl -u {USERNAME}:{USERPASSWD} {download_link} '
                                                      f'--output {destination}/{rename} --ssl-no-revoke',
                                                  timeout=timeout)
                else:
                    logger.info(f'<xxxxxxxxxxxxxx> execute_shell_cmd : unset http_proxy; unset https_proxy;'
                                f'curl  {download_link} --output {destination}/{rename} --ssl-no-revoke '
                                f'timeout[{timeout}] cwd[None]')
                    cls.ignore_log_excute_command(sut=sut,
                                                  cmd=f'unset http_proxy; unset https_proxy;'
                                                      f'curl  {download_link} '
                                                      f'--output {destination}/{rename} --ssl-no-revoke',
                                                  timeout=timeout)


class Nuc:
    connect = Content()

    def __init__(self, sut, args):
        self.python = None
        self.connect = Content()
        self.sut = sut
        self.args = args
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

    def deploy_version_info(self):
        if self.args.kit:
            print(self.args.kit)
            dl = True
            if self.args.dl:
                dl = False
            get_info(self.args.kit, dl)

    def deploy_python_env(self):
        ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.python_pip_modules,
                                                  destination=Windows_TOOLS, timeout=600)
        self.sut.execute_host_cmd(
            cmd=f'Expand-Archive -Path {Windows_TOOLS}\\pip_modules.zip -DestinationPath {Windows_TOOLS}\\pip_modules '
                f'-Force', powershell=True, timeout=600)

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

    def deploy_nuc_env(self):
        ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.environment_variable_bat,
                                                  destination=Windows_TOOLS, timeout=300)
        self.sut.execute_host_cmd(cmd=f'{Windows_TOOLS}\\env_setup.bat', powershell=False, timeout=600)

    def main(self):
        self.deploy_python_env()
        self.deploy_vmware_powercli()
        self.deploy_nuc_env()


class Kvm:
    def __init__(self, sut):
        self.unset_proxy = 'unset http_proxy; unset https_proxy;'
        self.sut = sut
        self.init_path()

    def init_path(self):
        Case.step("Init sut path")
        ext_cmd_list = [  # f"rm -rf {SUT_TOOLS_LINUX_VIRTUALIZATION}",
            f'mkdir -p {SUT_TOOLS_LINUX_ROOT}',
            f'mkdir -p {SUT_TOOLS_LINUX_VIRTUALIZATION}',
            f'mkdir -p {SUT_TOOLS_LINUX_VIRTUALIZATION_IMGS}',
            f'mkdir -p {VT_IMGS_L}',
            f'mkdir -p {VT_TOOLS_L}'
        ]
        for ext_cmd in ext_cmd_list:
            self.sut.execute_shell_cmd(cmd=ext_cmd, timeout=60)

    def deploy_auto_env(self):
        Case.step("Sut kernel update ")
        Maintoolkit_linux.Sut_kernel_args_set(sut=self.sut, sut_kernel_args='ibt=off')

        Case.step("Deploy SUT env yum install packages")
        for var in ['virt-manager', 'libvirt', 'python3-libvirt', 'virt-install', 'iperf', 'wget', 'tigervnc',
                    'kmod-devel', 'rust', 'bridge-utils', 'network-scripts', 'pip', 'yum-utils', 'python3-scp',
                    'iperf3', '/usr/bin/virt-customize', 'screen', 'iproute', 'protobuf']:
            self.sut.execute_shell_cmd(cmd=f'yum install -y {var}  --allowerasing --skip-broken --nobest', timeout=300)

        Case.step("Deploy auto-poc tools ")
        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.auto_poc_cent,
                                                  destination=SUT_TOOLS_LINUX_VIRTUALIZATION, timeout=600)
        self.sut.execute_shell_cmd(
            cmd=f'unzip -o {SUT_TOOLS_LINUX_VIRTUALIZATION}/auto-poc.zip -d {SUT_TOOLS_LINUX_VIRTUALIZATION}/',
            timeout=60)

        Case.step("Deploy virtualization_inband tools ")
        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.virtualization_inband_cent,
                                                  destination=SUT_TOOLS_LINUX_VIRTUALIZATION, timeout=600)

        self.sut.execute_shell_cmd(cmd=f'unzip -o {SUT_TOOLS_LINUX_VIRTUALIZATION}/virtualization_inband.zip '
                                       f'-d {SUT_TOOLS_LINUX_VIRTUALIZATION}/', timeout=600)

        self.sut.execute_shell_cmd(cmd=f'cd  {SUT_TOOLS_LINUX_VIRTUALIZATION}; chmod +x -R virtualization_inband',
                                   timeout=600)

        Case.step("Deploy python3.10 tools ")
        self.sut.execute_shell_cmd('yum groupinstall "Development Tools" -y', timeout=300)
        for var in 'openssl* openssl-devel libffi* bzip2*'.split():
            self.sut.execute_shell_cmd(cmd=f'yum install -y {var}  --allowerasing --skip-broken --nobest', timeout=300)

        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.python_linux, destination=VT_TOOLS_L,
                                                  timeout=600)

        self.sut.execute_shell_cmd(f"cd {VT_TOOLS_L}; tar -zxvf Python3.tgz", timeout=300)
        self.sut.execute_shell_cmd(f"cd {VT_TOOLS_L}/Python*/; ./configure && make && make install", timeout=300)
        cmd_list = "mv /usr/bin/python /usr/bin/python_bk; \
                ln -s /usr/local/bin/python3.10 /usr/bin/python; \
                sed -i 's/python3/python/g' /usr/bin/pip"
        self.sut.execute_shell_cmd(cmd_list, timeout=300)

        Case.step("Deploy env pip packages")
        ext_cmd = f"pip config set global.index-url https://{USERNAME}:{USERPASSWD}" \
                  f"@intelpypi.intel.com/pythonsv/production"
        ExtensionSutFunction.ignore_log_excute_command(sut=self.sut, cmd=ext_cmd)
        for var in ['xmltodict', 'wcwidth', 'pathlib2', 'artifactory', 'anybadge', 'pyqt5', 'prettytable',
                    'setuptools_rust', 'bcrypt', 'cffi', 'cryptography==3.2.1', 'prettytable', 'pynacl', 'paramiko',
                    'scp', 'requests', 'libvirt-python']:
            self.sut.execute_shell_cmd(f'pip install {var} --upgrade pip ', timeout=300)

        Case.step("Deploy vfio-pci-bind.sh test tool")
        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.vfio_pci_bind,
                                                  destination=VT_TOOLS_L, timeout=600)
        self.sut.execute_shell_cmd(cmd=f"cd {VT_TOOLS_L} && chmod +777 vfio-pci-bind.sh", timeout=300)

        Case.step("Deploy ovmf test tool")
        ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.ovmf_cent,
                                                  destination=VT_IMGS_L, timeout=600)

    def create_nat_and_bridge(self):
        Maintoolkit_linux.libvirtd_init_and_enable(sut=self.sut)
        network_xml = lambda name, bridge_name, ip_addr, range_start, range_end: \
            f"<network>\n" \
            f"  <name>{name}</name>\n" \
            f"  <bridge name='{bridge_name}'/>\n" \
            f"  <forward/>\n" \
            f"  <ip address='{ip_addr}' netmask='255.255.255.0'>\n" \
            f"      <dhcp>\n" \
            f"          <range start='{range_start}' end='{range_end}'/>\n" \
            f"      </dhcp>\n" \
            f"  </ip>\n" \
            f"</network>"

        __, result, err = self.sut.execute_shell_cmd(cmd='virsh net-list --all', timeout=60)
        if 'default' in result.lower():
            self.sut.execute_shell_cmd(cmd="virsh net-destroy default", timeout=60)
            self.sut.execute_shell_cmd(cmd="virsh net-undefine default", timeout=60)

        if 'my_network' in result.lower():
            self.sut.execute_shell_cmd(cmd="virsh net-destroy my_network", timeout=60)
            self.sut.execute_shell_cmd(cmd="virsh net-undefine my_network", timeout=60)

        my_network = network_xml(name='my_network', bridge_name='virbr0', ip_addr='192.168.123.1',
                                 range_start='192.168.123.2', range_end='192.168.123.254')
        self.sut.execute_shell_cmd(cmd=f"echo \"{my_network}\"  > {VT_TOOLS_L}/my_network.xml", timeout=60)

        self.sut.execute_shell_cmd(cmd=f'virsh net-define {VT_TOOLS_L}/my_network.xml', timeout=60)
        self.sut.execute_shell_cmd(cmd='virsh net-autostart my_network', timeout=60)
        self.sut.execute_shell_cmd(cmd='virsh net-start my_network', timeout=60)

        default = network_xml(name='default', bridge_name='virbr1', ip_addr='192.168.122.1',
                              range_start='192.168.122.2', range_end='192.168.122.254')
        self.sut.execute_shell_cmd(cmd=f"echo \"{default}\"  > {VT_TOOLS_L}/default.xml", timeout=60)

        self.sut.execute_shell_cmd(cmd=f'virsh net-define {VT_TOOLS_L}/default.xml', timeout=60)
        self.sut.execute_shell_cmd(cmd='virsh net-autostart default', timeout=60)
        self.sut.execute_shell_cmd(cmd='virsh net-start default', timeout=60)

        __, out, err = self.sut.execute_shell_cmd(
            cmd=r"ip addr show | awk '/inet.*brd.*dynamic/{print $NF; exit}'", timeout=60)

        ifcfg_file = out.split('\n')[0]
        cfg = f'"TYPE=Ethernet",\n' \
              f'"PROXY_METHOD=none",\n' \
              f'"BROWSER_ONLY=no",\n' \
              f'"BOOTPROTO=dhcp",\n' \
              f'"DEFROUTE=yes",\n' \
              f'"IPV4_FAILURE_FATAL=no",\n' \
              f'"IPV6INIT=yes",\n' \
              f'"IPV6_AUTOCONF=yes",\n' \
              f'"IPV6_DEFROUTE=yes",\n' \
              f'"IPV6_FAILURE_FATAL=no",\n' \
              f'f"NAME={ifcfg_file}",\n' \
              f'f"DEVICE={ifcfg_file}",\n' \
              f'"ONBOOT=yes"'
        self.sut.execute_shell_cmd(cmd=f'echo "{cfg}" > /etc/sysconfig/network-scripts/ifcfg-{ifcfg_file}', timeout=60)

    def deploy_stress_tools(self):
        if 'kvm_unit_tests_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy kvm-unit-tests tool")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['kvm_unit_tests_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'cmdline_config_80_workload' in connect.stress_tools_dict.keys():
            Case.step("Deploy cmdline_config_80_workload tool")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['cmdline_config_80_workload'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'mlc' in connect.stress_tools_dict.keys():
            Case.step("Deploy mlc tool")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['mlc'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'vtdchain_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy vtdchain test tool")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['vtdchain_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)
            self.sut.execute_shell_cmd(cmd=f'rm -rf /boot/efi/vtdchain;mkdir -p /boot/efi/vtdchain', timeout=120)
            self.sut.execute_shell_cmd(cmd=f'unzip -o {VT_TOOLS_L}/vtdchain_tool.zip -d /boot/efi/vtdchain',
                                       timeout=120)
        if 'sgx_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy sgx driver")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['sgx_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'sgx_functionvalidation_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy sgx functionvalidation test tool")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut,
                                                      link=connect.stress_tools_dict['sgx_functionvalidation_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'dlb_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy dlb driver")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['dlb_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'qat_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy qat driver")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['qat_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)

        if 'dsa_iaa_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy dsa/iaa driver")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['dsa_iaa_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)
        if 'accel_random_config_and_test_cent' in connect.stress_tools_dict.keys():
            Case.step("Deploy dsa/iaa test tool")
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict[
                'accel_random_config_and_test_cent'],
                                                      destination=VT_TOOLS_L, timeout=600)

    def deploy_vms(self):
        for vm_key, vm_value in connect.vm_source_file_cent.items():
            if 'regirster_vm' in vm_key:
                continue
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=vm_value, destination=VT_IMGS_L, timeout=1200)
            if '.iso' in vm_value:
                continue
            rename1 = vm_value.split(',')[1]
            self.sut.execute_shell_cmd(cmd=f'cd {VT_IMGS_L};xz -d {rename1} -T 10 -e -f ', timeout=1200)

            rename2 = rename1.replace('.xz', '')
            if '.img' in rename2:
                rename3 = rename2.replace('.img', '')
                self.sut.execute_shell_cmd(cmd=f'cd {VT_IMGS_L};qemu-img convert -O qcow2 {rename2} {rename3}.qcow2',
                                           timeout=600)

            if '.qcow2' in rename2:
                rename3 = rename1.replace('.qcow2', '')
                self.sut.execute_shell_cmd(cmd=f'cd {VT_IMGS_L};qemu-img convert -O raw {rename2} {rename3}.img',
                                           timeout=600)

        kvm = get_vmmanger(sut=self.sut)
        for vm_name, image_path in connect.vm_register_cent.items():
            if kvm.is_vm_exist(vm_name=vm_name) and connect.vm_refresh_vm.lower() == 'true':
                kvm.undefine_vm(vm_name=vm_name)

            if not kvm.is_vm_exist(vm_name=vm_name):
                os_variant = None
                if 'win' in vm_name:
                    os_variant = 'win2k19'
                elif 'rhel' in vm_name:
                    os_variant = 'rhel8.0'
                elif 'cent' in vm_name:
                    os_variant = 'centos8'
                else:
                    Case.expect('', False)

                self.sut.execute_shell_cmd(cmd=f"cp -f {image_path} {VT_IMGS_L}/{vm_name}_virt.qcow2", timeout=600)
                __, out, err = self.sut.execute_shell_cmd(cmd=f"virt-install --import --name={vm_name} "
                                                              f"--vcpu=2 --memory=4096 --cpu=host-passthrough  "
                                                              f"--disk path={VT_IMGS_L}/{vm_name}_virt.qcow2 "
                                                              f"--network network=default --os-type=linux "
                                                              f"--os-variant={os_variant} --noautoconsole ",
                                                          timeout=600)

                Case.expect(f"check register vm {vm_name} complete",
                            "Domain creation completed.".lower() in out.lower())

    def main(self):
        self.deploy_auto_env()
        self.create_nat_and_bridge()
        self.deploy_stress_tools()
        self.deploy_vms()


class Hyper_V:

    def __init__(self, sut):
        self.python = None
        self.sut = sut
        self.init_path()
        self.init_variables()

    def init_path(self):
        Case.step("Enable sshd/rdp accese and disable firewall")
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
                    cmd=f'Expand-Archive -Path {Windows_IMG}\\{rename} '
                        f'-DestinationPath {Windows_IMG}\\{dir_name} -Force',
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
        Case.step("Synchronize time with nuc")
        __, out, err = self.sut.execute_host_cmd(cmd="Get-Date -Format 'yyyy-M-d'", powershell=True)
        out = out.replace('\r\n', '')
        year, month, day = out.split('-')
        self.sut.execute_shell_cmd(cmd=f'esxcli system time set -y {year} -M {month} -d {day}')

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
                                                      authentication=True, destination=ESXI_TOOLS, timeout=600)
        Case.step("Deploy iometer")
        if 'iometer_wind' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['iometer_wind'],
                                                      destination=VT_TOOLS_N, timeout=600)
            folder_name = 'iometer_win'
            self.sut.execute_host_cmd(
                cmd=f'New-Item -Path {DTAF_IMAGEPATH}\\{folder_name} -ItemType Directory  -Force',
                powershell=True, timeout=30)
            self.sut.execute_host_cmd(
                cmd=f'Expand-Archive -Path {VT_TOOLS_N}\\iometer_win.zip '
                    f'-DestinationPath {VT_TOOLS_N}\\{folder_name} -Force',
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
                                                      authentication=True, destination=ESXI_TOOLS, timeout=600)

        Case.step("Deploy dlb tools")
        if 'dlb_esxi' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['dlb_esxi'],
                                                      authentication=True, destination=ESXI_TOOLS, timeout=600)
        if 'dlb_cent' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_nuc(sut=self.sut, link=connect.stress_tools_dict['dlb_cent'],
                                                      destination=NUC_TOOLS, timeout=600)

        Case.step("Deploy qat tools")
        if 'qat_esxi' in connect.stress_tools_dict.keys():
            ExtensionSutFunction.download_file_to_sut(sut=self.sut, link=connect.stress_tools_dict['qat_esxi'],
                                                      authentication=True, destination=ESXI_TOOLS, timeout=600)
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
