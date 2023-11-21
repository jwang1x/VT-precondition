from src.virtualization.lib.tkinit import *
from src.virtualization.gnr.precondition_setup.vtsetup.hypervisor import *

CASE_DESC = [
    "Configure PCIE Network pass-through devices on an ESXi host Procedures"
]


def get_args():
    parser = argparse.ArgumentParser(description='Automation Framework for Accelerators')
    parser.add_argument('-v', action='version', version='Automation Framework:Version: 1.0')
    parser.add_argument('--kit', type=str, nargs="+")
    parser.add_argument('--dl', action='store_true', help='Add this parameter without downloading xml file')
    return parser.parse_args()


def pre_auto(sut, my_os):
    # type:(SUT, GenericOS) -> None

    Case.prepare('boot to OS')
    boot_to(sut=sut, to_state=sut.default_os)
    Case.wait_and_expect(f'OS for system back to os', 15 * 10 * 60, sut.check_system_in_os)
    Case.sleep(60, min_iterval=60)

    nuc = Nuc(sut=sut, args=get_args())
    nuc.main()

    if 'linux' in sut.default_os.lower():
        setup = Kvm(sut=sut)
        setup.main()

    if 'windows' in sut.default_os.lower():
        setup = Hyper_V(sut=sut)
        setup.main()

    if 'esxi' in sut.default_os.lower():
        setup = Esxi(sut=sut)
        setup.main()


def clean_up(sut):
    if Result.returncode != 0:
        pass
        # cleanup.to_s5(sut)


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
