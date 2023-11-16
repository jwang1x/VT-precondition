from src.virtualization.lib.tkinit import *
from src.virtualization.gnr.precondition_setup.vtsetup.hypervisor import *

CASE_DESC = [
    "Configure PCIE Network pass-through devices on an ESXi host Procedures"
]

excute_vm_cmd = lambda port, cmd: f"python  {Linux_INBANDS}/vm_execute.py -p  {port} -u root -w password -c \"{cmd}\""
excute_vm_copy = lambda port, filepath,local='/root': f"python  {Linux_INBANDS}/vm_copy.py -s  {filepath} -p {port} -d {local} -u root -w password"


def pre_auto(sut, my_os):
    # type:(SUT, GenericOS) -> None
    vm_port = 2222
    Case.prepare('boot to OS')
    boot_to(sut=sut, to_state=sut.default_os)
    Case.wait_and_expect(f'OS for system back to os', 15 * 10 * 60, sut.check_system_in_os)
    Case.sleep(5,min_iterval=5)

    Case.step("Set vm template password")
    sut.execute_shell_cmd(""" kill -9 `ps -ef | egrep qemu | egrep -v grep | awk -F  ' ' '{print $2}' | xargs` """,timeout=120)
    __,out,err = sut.execute_shell_cmd(f"cd {Linux_IMG}; export LIBGUESTFS_BACKEND=direct;virt-customize -a cent0.img --root-password password:password")
    Case.expect("Check modify cent0.img password",'Finishing off'.lower() in out.lower())

    Case.step("Booting vm")
    sut.execute_shell_cmd(f"cd {Linux_IMG};nohup /usr/libexec/qemu-kvm -machine q35 -accel kvm -m 10240 -smp 10 -cpu host -monitor pty -hda ./cent0.img -nic user,hostfwd=tcp::{vm_port}-:22 -nographic > ./GuestVM2222.txt 2>&1 & ", timeout=10*60)

    Case.step("Waiting vm boot to os")
    Case.sleep(60,min_iterval=60)

    Case.step("Chheck vm are alive")
    Maintoolkit_linux.check_vms_alive_and_set_kernel(sut=sut,port_or_portlist=vm_port,guest_kernel_args=False,boot_log=False,vmtype='linux')

    Case.step("Prepare yum repo from sut")
    sut.execute_shell_cmd(excute_vm_cmd(vm_port,'mkdir -p /etc/yum.repos.d/repobak'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port,'cd /etc/yum.repos.d/; mv -f * repobak'))

    __,out,err = sut.execute_shell_cmd('ls /etc/yum.repos.d/')
    repo_files = out.split("\n")[:-1]
    for repo in repo_files:
        sut.execute_shell_cmd(excute_vm_copy(vm_port, f'/etc/yum.repos.d/{repo}','/etc/yum.repos.d/'))

    Case.step("Prepare dlb yum package")
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum -y install kernel-gnr-bkc-modules-internal'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum -y install kernel-gnr-bkc-devel'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum -y install meson'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum -y python3-pyelftools'))

    Case.step("Prepare dsa/iaa yum package")
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum groupinstall -y "Development Tools"'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum install -y autoconf automake libtool pkgconf rpm-build rpmdevtools'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum install -y asciidoc xmlto libuuid-devel json-c-devel kmod-devel libudev-devel'))

    Case.step("Prepare qat yum package")
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum -y install zlib-devel.x86_64 yasm systemd-devel boost-devel.x86_64 openssl-devel libnl3-devel gcc make gcc-c++  libgudev.x86_64 libgudev-devel.x86_64 systemd*'))
    sut.execute_shell_cmd(excute_vm_cmd(vm_port, 'yum -y install kernel-gnr-bkc-devel'))

    Case.step("Kill vm and complete vm set")
    sut.execute_shell_cmd(""" kill -9 `ps -ef | egrep qemu | egrep -v grep | awk -F  ' ' '{print $2}' | xargs` """,timeout=120)

def clean_up(sut):
    if Result.returncode != 0:
        try:
            Maintoolkit_linux.Clear_env(sut=sut,reboot=False)
        except:
            cleanup.to_s5(sut)


def test_main():
    # ParameterParser parses all the embed parameters
    # --help to see all allowed parameters
    user_parameters = ParameterParser.parse_embeded_parameters()
    # add your parameter parsers with list user_parameters

    # if you would like to hardcode to disable clearcmos
    # ParameterParser.bypass_clearcmos = True

    # if commandline provide sut description file by --sut <json file>
    #       generate sut instance from given json file
    #       if multiple files have been provided in command line, only the 1st will take effect for get_default_sut
    #       to get multiple sut, call function get_sut_list instead
    # otherwise
    #       default sut configure file will be loaded
    #       which is defined in basic.config.DEFAULT_SUT_CONFIG_FILE
    sut = get_default_sut()
    my_os = OperationSystem[OS.get_os_family(sut.default_os)]

    try:
        Case.start(sut, CASE_DESC)
        pre_auto(sut, my_os)

    except Exception as e:
        Result.get_exception(e, str(traceback.format_exc()))
    finally:
        Case.end()
        clean_up(sut)


if __name__ == '__main__':
    test_main()
    exit(Result.returncode)


