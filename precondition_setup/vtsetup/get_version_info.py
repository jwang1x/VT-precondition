import argparse
import re
import requests
import xml.etree.ElementTree as ET
import paramiko

system_configuration = r"C:\Automation\tkconfig\system_configuration.xml"


class GetVersion:
    XML_PATH = "../vtconfig/precondition_configuration.xml"
    BaseUrl = "https://ubit-artifactory-ba.intel.com/artifactory/dcg-dea-srvplat-repos/Kits"
    Systemos = {"RHEL": "linux", "CENTOS": "linux", "WIN": "windows", "ESXI": "esxi"}
    esxi = {"dlb": "dlb_esxi/"}
    linux = {"dlb": "dlb/"}
    tools = {"esxi": esxi, "linux": linux}

    def __init__(self, version):
        self.version = version
        self.os = self.get_os(version)

    def get_os(self, version):
        for i in self.Systemos:
            if i in version:
                return self.Systemos[i]
        raise Exception("There is no system information in the parameters")

    def update_xml(self, tool, link, parent="auto/virtualization"):
        tree = ET.parse(self.XML_PATH)
        root = tree.getroot()
        res = root.find(f".//{parent}/{self.os}/{tool}")
        if res is None:
            print("It's not found in the file.")
            return
        res.text = link
        tree.write(self.XML_PATH)

    @staticmethod
    def get_url(url):
        res = requests.get(url)
        if res.status_code != 200:
            raise Exception("requests error")
        res = re.findall(r'\n<a href="(.*)?">', res.text)
        if not res:
            raise Exception("requests error")
        return res

    def qat(self, packageslink):
        print("Modify the qat link")
        packagelist = self.get_url(packageslink)
        if "QAT/" not in packagelist:
            print(f"There is no qat package in {packagelist}")
            return None
        qatlistlink = f"{packageslink}/QAT"
        qatlist = self.get_url(qatlistlink)
        qatversion = qatlist[0]
        qatziplink = f"{qatlistlink}/{qatversion}"
        qatzip = self.get_url(qatziplink)[-1]
        if self.os == self.Systemos["ESXI"]:
            qatlink = f"{qatziplink}{qatzip},qat-gnr.zip"
            print(qatlink)
            self.update_xml("qat/driver", qatlink)
        else:
            qatlink = f"{qatziplink}{qatzip},qat.zip"
            print(qatlink)
            self.update_xml("qat/driver_pwd", qatlink)

    def dlb(self, packageslink):
        print("Modify the dlb link")
        packagelist = self.get_url(packageslink)
        dlb = self.tools[self.os]["dlb"]
        if dlb not in packagelist:
            print(f"There is no dlb package in {packagelist}")
            return None
        listlink = f"{packageslink}/{dlb}"
        linklist = self.get_url(listlink)
        version = linklist[0]
        ziplink = f"{listlink}{version}"
        filezip = self.get_url(ziplink)[-1]
        if self.os == self.Systemos["ESXI"]:
            link = f"{ziplink}{filezip},dlb-gnr.zip"
            print(link)
            self.update_xml("dlb/driver", link)
        else:
            link = f"{ziplink}{filezip},dlb.zip"
            print(link)
            self.update_xml("dlb/driver_pwd", link)

    def dsa_iax(self, packageslink):
        print("Modify the dsa_iax link")
        packagelist = self.get_url(packageslink)
        if "iads_esxi/" not in packagelist:
            print(f"There is no dsa_iax package in {packagelist}")
            return None
        listlink = f"{packageslink}/iads_esxi/"
        linklist = self.get_url(listlink)
        version = linklist[0]
        ziplink = f"{listlink}{version}"
        filezip = self.get_url(ziplink)[-1]
        link = f"{ziplink}{filezip},iads-gnr.zip"
        print(link)
        self.update_xml("dsa_iax/driver", link)

    def vmd(self, packageslink):
        print("Modify the vmd link")
        packagelist = self.get_url(packageslink)
        if "VMD_ESXi/" not in packagelist:
            print(f"There is no VMD_ESXI package in {packagelist}")
            return None
        listlink = f"{packageslink}/VMD_ESXi/"
        linklist = self.get_url(listlink)
        version = linklist[0]
        ziplink = f"{listlink}{version}"
        filezip = self.get_url(ziplink)[-1]
        link = f"{ziplink}{filezip},intel_nvme_vmd.zip"
        print(link)
        self.update_xml("vmd/driver", link)

    def centos_arti_img(self):
        print("Modify the common centos arti img")
        linuxlink = "https://ubit-artifactory-or.intel.com/artifactory/linuxbkc-or-local/linux-stack-bkc-gnr/"
        if self.os != "linux":
            print("You do not need to do this.")

        def get_centosversion():
            tree = ET.parse(system_configuration)
            root = tree.getroot()
            res = root.find(r".//suts/sut")
            ip = res.attrib['ip']
            ssh = paramiko.SSHClient()
            try:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, username='root', password='intel@123')
                stdin, stdout, stderr = ssh.exec_command('uname -r')
                centosversion = stdout.read().decode()
            except Exception as _:
                return ""
            finally:
                ssh.close()
            return centosversion

        centosversion = get_centosversion()
        res = re.search(r"\d+\.\d+\.\d+\.\d+\.\d+", centosversion)
        if not res:
            print("Check version failed.")
            return
        print(f"centos version: {centosversion}")
        centosversion = res.group().replace(".", "")
        weekslist = self.get_url(linuxlink)
        for i in weekslist[::-1]:
            weeklink = f"{linuxlink}{i}"
            internal_images = self.get_url(weeklink)
            if "internal-images/" not in internal_images:
                continue
            imgslink = f"{weeklink}internal-images/"
            imgs = self.get_url(imgslink)
            print(imgs)
            res = re.search(r"\d+.\d+.\d+.\d+.\d+", imgs[0])
            if not res:
                print("Regular possible errors require modifying the code.")
                return
            res = res.group()
            res = re.sub(r"[\.-]", "", res)
            if centosversion == res:
                self.update_xml("centos_arti_img", f"{imgslink}{imgs[0]},gnr-bkc-centos-stream-9-coreserver.img.xz",
                                parent="nuc/vm")
                break
        else:
            print("There is no mirror image.")

    def tools_list(self):
        baselist = self.get_url(self.BaseUrl)
        link_parent, _ = self.version.rsplit("-", 1)
        for i in baselist:
            if i.upper() == f"{link_parent}/".upper():
                packageslink = f"{self.BaseUrl}/{i}{self.version}/Packages"
                break
        else:
            raise Exception("Error parser")
        self.qat(packageslink)
        self.dlb(packageslink)
        self.dsa_iax(packageslink)
        self.vmd(packageslink)


def main(system_version):
    for i in system_version:
        getversion = GetVersion(i)
        if getversion.os == "windows":
            print("Windows is not supported at this time")
            continue
        getversion.tools_list()
        # getversion.centos_arti_img()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Automation Framework for Accelerators')
    parser.add_argument('-v', action='version', version='Automation Framework:Version: 1.0')
    parser.add_argument('--kit', type=str, nargs="+")
    args = parser.parse_args()
    if args.kit:
        print(args.kit)
        main(args.kit)
