import argparse
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

class GetVersion:
    XML_PATH = r"C:\Automation\vtconfig\vt_precondition_configuration.xml"
    remote_xml = "https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/NUC/vt_precondition_configuration.xml"
    BaseUrl = "https://ubit-artifactory-ba.intel.com/artifactory/dcg-dea-srvplat-repos/Kits"
    Systemos = {"RHEL": "linux", "CENTOS": "linux", "WIN": "windows", "ESXI": "esxi"}
    esxi = {"dlb": "dlb_esxi/"}
    linux = {"dlb": "dlb/", "sgx": "SGX_PSW/", "sgx_xml": "sgx_cent","sgx_t": "SGXFVT_Tool"}
    windows = {"sgx": "SGX/","sgx_xml": "sgx_wind", "sgx_t": "SGXFVT_Tool/"}
    tools = {"esxi": esxi, "linux": linux, "windows": windows}

    def __init__(self, version, dl=True):
        if dl:
            self.get_xml_file()
        self.version = version
        self.os = self.get_os(version)

    def get_xml_file(self):
        Path(r"C:\Automation\vtconfig").mkdir(parents=True, exist_ok=True)
        xml_path = Path(self.XML_PATH)
        res = requests.get(self.remote_xml)
        xml_path.write_bytes(res.content)

    def get_os(self, version):
        for i in self.Systemos:
            if i in version:
                return self.Systemos[i]
        raise Exception("There is no system information in the parameters")

    def update_xml(self, tool, link, parent="stress_tools"):
        tree = ET.parse(self.XML_PATH)
        root = tree.getroot()
        res = root.find(f".//{parent}/{tool}")
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

    def qat(self):
        if self.os  == self.Systemos["WIN"]:
            return None
        print("Modify the qat link")
        packagelist = self.get_url(self.packageslink)
        if "QAT/" not in packagelist:
            print(f"There is no qat package in {packagelist}")
            return None
        qatlistlink = f"{self.packageslink}/QAT"
        qatlist = self.get_url(qatlistlink)
        qatversion = qatlist[0]
        qatziplink = f"{qatlistlink}/{qatversion}"
        qatzip = self.get_url(qatziplink)[-1]
        if self.os == self.Systemos["ESXI"]:
            qatlink = f"{qatziplink}{qatzip},qat-gnr.zip"
            print(qatlink)
            self.update_xml("qat_esxi", qatlink)
        else:
            qatlink = f"{qatziplink}{qatzip},qat.zip"
            print(qatlink)
            self.update_xml("qat_cent", qatlink)

    def dlb(self):
        if self.os  == self.Systemos["WIN"]:
            return None
        print("Modify the dlb link")
        packagelist = self.get_url(self.packageslink)
        dlb = self.tools[self.os]["dlb"]
        if dlb not in packagelist:
            print(f"There is no dlb package in {packagelist}")
            return None
        listlink = f"{self.packageslink}/{dlb}"
        linklist = self.get_url(listlink)
        version = linklist[0]
        ziplink = f"{listlink}{version}"
        filezip = self.get_url(ziplink)[-1]
        if self.os == self.Systemos["ESXI"]:
            link = f"{ziplink}{filezip},dlb-gnr.zip"
            print(link)
            self.update_xml("dlb_esxi", link)
        else:
            link = f"{ziplink}{filezip},dlb.zip"
            print(link)
            self.update_xml("dlb_cent", link)

    def dsa_iax(self):
        if self.os  == self.Systemos["WIN"]:
            return None
        print("Modify the dsa_iax link")
        packagelist = self.get_url(self.packageslink)
        if "iads_esxi/" not in packagelist:
            print(f"There is no dsa_iax package in {packagelist}")
            return None
        listlink = f"{self.packageslink}/iads_esxi/"
        linklist = self.get_url(listlink)
        version = linklist[0]
        ziplink = f"{listlink}{version}"
        filezip = self.get_url(ziplink)[-1]
        link = f"{ziplink}{filezip},iads-gnr.zip"
        print(link)
        self.update_xml("dsa_iaa_esxi", link)

    def vmd(self):
        if self.os  == self.Systemos["WIN"]:
            return None
        print("Modify the vmd link")
        packagelist = self.get_url(self.packageslink)
        if "VMD_ESXi/" not in packagelist:
            print(f"There is no VMD_ESXI package in {packagelist}")
            return None
        listlink = f"{self.packageslink}/VMD_ESXi/"
        linklist = self.get_url(listlink)
        version = linklist[0]
        ziplink = f"{listlink}{version}"
        filezip = self.get_url(ziplink)[-1]
        link = f"{ziplink}{filezip},intel_nvme_vmd.zip"
        print(link)
        self.update_xml("vmd_driver_esxi", link)
    
    def sgx(self):
        if self.os == self.Systemos["ESXI"]:
            return None
        print("Modify the sgx link")
        packagelist = self.get_url(self.packageslink)
        if not any(["SGX" in i for i in packagelist]):
            print(f"There is not sgx package in {packagelist}")
        sgx = self.tools[self.os]["sgx"]
        sgxlistlink = f"{self.packageslink}/{sgx}"
        sgxlistlink0 = f"{sgxlistlink}{self.get_url(sgxlistlink)[0]}"
        sgxziplink = self.get_url(sgxlistlink0)[-1]
        sgxlink = f"{sgxlistlink0}{sgxziplink},sgx.zip"
        print(sgxlink)
        sgx_xml = self.tools[self.os]["sgx_xml"]
        self.update_xml(sgx_xml, sgxlink)

    def centos_arti_img(self):
        if self.os != self.Systemos["CENTOS"]:
            return None
        print("Modify the common centos arti img")
        linuxlink = "https://ubit-artifactory-or.intel.com/artifactory/linuxbkc-or-local/linux-stack-bkc-gnr/"
        if self.os != "linux":
            print("You do not need to do this.")

        imgslist = self.get_url(self.imgslink)
        imglink = ""
        for link in imgslist:
            if link.endswith("iso"):
                imglink = link
                break
        else:
            print("There is not ISO")
            return None
        version_info = re.search(r"-\d+\.\d+-\d+\.\d+\.\d+-\d+", imglink)
        if not version_info:
            print("Get info failure")
        version = version_info.group()
        weekslist = self.get_url(linuxlink)
        for i in weekslist[::-1]:
            weeklink = f"{linuxlink}{i}"
            internal_images = self.get_url(weeklink)
            if "internal-images/" not in internal_images:
                continue
            imgslink = f"{weeklink}internal-images/"
            imgs = self.get_url(imgslink)
            imglink = ""
            for img in imgs:
                if img.endswith(".img.xz"):
                    if version in img:
                        imglink = img
                    break
            if imglink:
                self.update_xml("centos_arti_img", f"{imgslink}{imglink},cent0.img.xz",
                                parent="vm/centos")
                break
        else:
            print("There is no mirror image.")

    def tools_list(self):
        baselist = self.get_url(self.BaseUrl)
        link_parent, _ = self.version.rsplit("-", 1)
        for i in baselist:
            if i.upper() == f"{link_parent}/".upper():
                self.packageslink = f"{self.BaseUrl}/{i}{self.version}/Packages"
                self.imgslink = f"{self.BaseUrl}/{i}{self.version}/Images"
                break
        else:
            raise Exception("Error parser")
        self.qat()
        self.dlb()
        self.dsa_iax()
        self.vmd()
        self.centos_arti_img()
        self.sgx()


def get_info(system_version, dl=True):
    for i in system_version:
        getversion = GetVersion(i, dl)
        getversion.tools_list()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Automation Framework for Accelerators')
    parser.add_argument('-v', action='version', version='Automation Framework:Version: 1.0')
    parser.add_argument('--kit', type=str, nargs="+")
    parser.add_argument('--dl', action='store_true', help='Add this parameter without downloading xml file')
    args = parser.parse_args()
    if args.kit:
        print(args.kit)
        dl = True
        if args.dl:
            dl = False
        get_info(args.kit, dl)
