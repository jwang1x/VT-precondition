import paramiko
import re
import time
import argparse


class Client_Server():

    def __init__(self,vmip,type):
        self.hostname = vmip
        if type.lower() == 'linux':
            self.username = 'root'
            self.password = 'password'
        elif type.lower() == 'windows':
            self.username = 'windows'
            self.password = 'intel@123'

    def ssh_to_connection(self):

        try:
            if self.hostname != None  and self.username != None and self.password != None :
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(self.hostname, 22, self.username, self.password)
                return 1

            else:
                return 0


        except Exception as err:

            self.ssh_client = None
            return 0

    def close_ssh(self):
        try:
            if self.ssh_client != None:
                self.ssh_client.close()
                print("close ssh server successful")
            else:
                print("close ssh server successful")

        except Exception as err:
            ssh_client = None
            print('err', err)
            return 0

class Basic:

    def __init__(self,vmip,type,hypervisor,unattend_link,vm_name):
        self.client = self.connect_via_ssh(hostname=vmip,type=type)
        self.hypervisor = hypervisor
        self.unattend_link = unattend_link
        self.vmname = vm_name

    def connect_via_ssh(self,hostname,type):
        if type.lower() == 'linux':
            username = 'root'
            password = 'password'
        elif type.lower() == 'windows':
            username = 'windows'
            password = 'intel@123'
        else:
            assert False
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, 22, username, password)
        return client

    def download_file(self,url,path,rename,timeout=60,backstage=False):
        cmd = f'rm -rf wget-log*'
        self.excute_vm_cmd(cmd=f'{cmd}', timeout=int(timeout))

        bg = [ ' -b ' if backstage else ' '][0]
        cmd = f'wget {bg} -O {rename} -c {url} -P {path} -N'
        wget_mess,err = self.excute_vm_cmd(cmd=f'{cmd}', timeout=int(timeout))

        if backstage:
            pid = re.findall("\d+",wget_mess)[0]

            def timer(pid,url):
                cmd = f"ps -ef | grep -i {pid} " + " | awk '{print $2}' "
                out, err = self.excute_vm_cmd(cmd=f'{cmd}', timeout=int(timeout),silence=True)
                if pid == out.split('\n')[0]:
                    return True

                cmd = f"ps -ef | grep -i {url}"
                out, err = self.excute_vm_cmd(cmd=f'{cmd}', timeout=int(timeout),silence=True)
                if 'bash -c ps -ef' in out.split('\n')[0]:
                    return False
                else:
                    return True

            count = 0
            while timer(pid,url) and count < timeout:
                time.sleep(1)
                count += 1

            cmd = f"cat /root/wget-log | tail -n 30"
            self.excute_vm_cmd(cmd=f'{cmd}',timeout=int(timeout))

    def excute_cmd(self,cmd,timeout=60,silence=False):
        Transformation_decode = lambda x: x.read().decode("UTF-8")
        if not silence:
            print(f'excute cmd : {cmd}')
        _, out, err = self.client.exec_command(command=cmd, timeout=timeout, bufsize=600)
        out_trans = Transformation_decode(out)
        err_trans = Transformation_decode(err)
        if not silence:
            print(out_trans)
            print(err_trans)
        return out_trans, err_trans

    def excute_vm_cmd(self,cmd,timeout=60,silence=False):
        Transformation_decode = lambda x: x.read().decode("UTF-8")
        if self.hypervisor.lower() == 'kvm':
            cmd_cmd = f'/usr/bin/python /root/excute_vm_local.py --vm {self.vmname} --type linux --cmd "{cmd}" --timeout {timeout}'
            if not silence:
                print(f'excute cmd : {cmd_cmd}')
            _, out, err = self.client.exec_command(command=cmd_cmd,timeout=timeout,bufsize=600)
            out_trans = Transformation_decode(out)
            err_trans = Transformation_decode(err)
            if not silence:
                print(out_trans)
                print(err_trans)
            return out_trans,err_trans

        
        else:
            
            if not silence:
                print(f'excute cmd : {cmd}')
            _, out, err = self.client.exec_command(command=cmd,timeout=timeout,bufsize=600)
            out_trans = Transformation_decode(out)
            err_trans = Transformation_decode(err)
            if not silence:
                print(out_trans)
                print(err_trans)
            return out_trans,err_trans



class Unattend_L:
    def __init__(self,vmip,type,hypervisor,unattend_link,vm_name):
        self.basic = Basic(vmip,type,hypervisor,unattend_link,vm_name)
        self.hypervisor = hypervisor
        self.unattend_link = unattend_link
        self.gnr_po_unattend_iso = 'make_source_unattend.iso'

    def isolinux_cfg(self):
        if self.hypervisor.lower() == 'kvm':
            cmd = 'rm -rf /root/excute_vm_local.py'
            self.basic.excute_cmd(cmd=cmd,timeout=60)

            cmd = 'wget -c https://ubit-artifactory-sh.intel.com/artifactory/validationtools-sh-local/virtualization/linux/tools/excute_vm_local.py  -P /root/ -N'
            self.basic.excute_cmd(cmd=cmd,timeout=60)

            cmd = 'chmod +x /root/excute_vm_local.py'
            self.basic.excute_cmd(cmd=cmd,timeout=60)

        cmd = 'yum -y install createrepo mkisofs isomd5sum rsync'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = 'umount /mnt/cdrom/'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = 'rm -rf /mnt/cdrom/; mkdir -p /mnt/cdrom/'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = f'rm -rf {self.gnr_po_unattend_iso}'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)
        self.basic.download_file(url=self.unattend_link,path='/root/',rename=self.gnr_po_unattend_iso,timeout=600,backstage=True)

        cmd = f'mount -o loop {self.gnr_po_unattend_iso} /mnt/cdrom'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = f'rm -rf /root/iso'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = 'cp -ar /mnt/cdrom/ /root/iso'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)
        cmd = 'cp anaconda-ks.cfg /root/iso/ks.cfg'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)


        cmd = "sed -i 's/append initrd=initrd.img inst.stage2=hd:LABEL=CentOS-Stream-8-x86_64 quiet/append initrd=initrd.img inst.stage2=hd:LABEL=centos8 quiet/g' /root/iso/isolinux/isolinux.cfg"
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = "sed -i 's/append initrd=initrd.img inst.stage2=hd:LABEL=CentOS-Stream-8-x86_64 rd.live.check quiet/append initrd=initrd.img inst.stage2=hd:LABEL=centos8 rd.live.check inst.ks=cdrom:\/ks.cfg quiet/g' /root/iso/isolinux/isolinux.cfg"
        self.basic.excute_vm_cmd(cmd=cmd, timeout=60)

        cmd = 'cat /root/iso/isolinux/isolinux.cfg'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)




    def make_rpm(self):
        cmd = 'cp -f anaconda-ks.cfg /root/iso/ks.cfg'
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)
        cmd = "echo reboot >> /root/iso/ks.cfg"
        self.basic.excute_vm_cmd(cmd=cmd,timeout=60)

        cmd = f'mkdir -p /root/iso/{self.hypervisor}/Packages; mkdir -p /root/iso/{self.hypervisor}/repodata'
        self.basic.excute_vm_cmd(cmd=cmd, timeout=60)

        if self.hypervisor == 'vmware':
            cmd = "rpm --import http://packages.vmware.com/tools/keys/VMWARE-PACKAGING-GPG-RSA-KEY.pub"
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)
            cmd = """echo "[vmware-tools]" > /etc/yum.repos.d/vmware-tools.repo"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)
            cmd = """ echo "name=VMware Tools" >> /etc/yum.repos.d/vmware-tools.repo"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)
            cmd = """echo 'baseurl=http://packages.vmware.com/tools/esx/8.0/rhel5/$basearch' >> /etc/yum.repos.d/vmware-tools.repo"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)
            cmd = """echo "enabled=1" >> /etc/yum.repos.d/vmware-tools.repo"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)
            cmd = """echo "gpgcheck=1" >> /etc/yum.repos.d/vmware-tools.repo"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)
            cmd = """cat /etc/yum.repos.d/vmware-tools.repo"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=60)

            cmd = f'yum install -y --downloadonly --downloaddir=/root/iso/{self.hypervisor}/Packages vmware-tools* --allowerasing --skip-broken --nobest'
            self.basic.excute_vm_cmd(cmd=cmd, timeout=600)

        elif self.hypervisor == 'hyperv':
            cmd = f'yum install -y --downloadonly --downloaddir=/root/iso/{self.hypervisor}/Packages hyper* --allowerasing --skip-broken --nobest'
            self.basic.excute_vm_cmd(cmd=cmd, timeout=600)
        else:
            return 0

        cmd = f'ls /root/iso/{self.hypervisor}/Packages'
        ls_rpm, err = self.basic.excute_vm_cmd(cmd=cmd, timeout=30,silence=False)
        rpm_lib = []
        for str in ls_rpm.split('\n'):
            if str == '':
                continue
            rpm_lib.append(re.split(r'-\d+', str)[0])


        cmd = f"""echo \
"<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>
<!DOCTYPE comps
  PUBLIC '-//Red Hat, Inc.//DTD Comps info//EN'
  'comps.dtd'>
<comps>
  <group>
    <id>{self.hypervisor}</id>
    <name>{self.hypervisor}</name>
    <description>{self.hypervisor.upper()}</description>
    <default>true</default>
    <uservisible>false</uservisible>
    <packagelist>" > /root/iso/{self.hypervisor}/repodata/comp.xml"""
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600,silence=True)

        for rpm in rpm_lib:
            cmd = f"""echo "        <packagereq type=\\"default\\">{rpm}</packagereq>" >> /root/iso/{self.hypervisor}/repodata/comp.xml"""
            self.basic.excute_vm_cmd(cmd=cmd, timeout=600,silence=True)

        cmd = f"""echo "\
    </packagelist>
  </group>
</comps>">> /root/iso/{self.hypervisor}/repodata/comp.xml"""
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600,silence=True)

        cmd = f"createrepo -g /root/iso/{self.hypervisor}/repodata/comp.xml /root/iso/{self.hypervisor}/"
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600)

        cmd = f"createrepo -g /root/iso/{self.hypervisor}/repodata/comp.xml /root/iso/{self.hypervisor}/"
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600)

        cmd = f"rm -rf /root/iso/{self.hypervisor}/repodata/comp.xml"
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600)

        cmd = f"cat  /root/iso/{self.hypervisor}/repodata/*comp.xml"
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600)

        cmd = """cat -n /root/iso/ks.cfg | grep "repo --name=" | awk '{print $1}' |  tail -1"""
        num, err = self.basic.excute_vm_cmd(cmd=cmd, timeout=30)
        num = num.split('\n')[0]

        cmd = f"""sed -i '{num}a\\repo --name="{self.hypervisor}" --baseurl=file:///run/install/sources/mount-0000-cdrom/{self.hypervisor}' /root/iso/ks.cfg"""
        self.basic.excute_vm_cmd(cmd=cmd, timeout=30)


        cmd = """cat -n /root/iso/ks.cfg | grep "kexec-tools" | awk '{print $1}' |  tail -1"""
        num, err = self.basic.excute_vm_cmd(cmd=cmd, timeout=30)
        num = num.split('\n')[0]

        cmd = f"""sed -i '{num}a\\@{self.hypervisor}' /root/iso/ks.cfg"""
        self.basic.excute_vm_cmd(cmd=cmd, timeout=30)

        cmd = "cat /root/iso/ks.cfg"
        self.basic.excute_vm_cmd(cmd=cmd, timeout=30)


    def export_iso(self,vmname):
        cmd = f"cd /root/iso; mkisofs -o /root/{vmname} -V centos8 -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4  -boot-info-table -R -J -T -v ."
        self.basic.excute_vm_cmd(cmd=cmd, timeout=600)

        cmd = f'implantisomd5 /root/{vmname}'
        self.basic.excute_vm_cmd(cmd=cmd, timeout=60)


    def main(self):
        self.isolinux_cfg()
        self.make_rpm()
        self.export_iso(f'gnr_po_{self.hypervisor}_unattend.iso')




# --ip 10.89.88.135 --type linux --hypervisor hyperv --link https://ubit-artifactory-or.intel.com/artifactory/linuxbkc-or-local/linux-stack-bkc-gnr/2022ww49.1/internal-images/gnr-po-bkc-centos-stream-8-installer-minimal-1.4.2-11.iso
# --ip 10.89.92.94 --type linux --hypervisor vmware --link https://ubit-artifactory-or.intel.com/artifactory/linuxbkc-or-local/linux-stack-bkc-gnr/2022ww49.1/internal-images/gnr-po-bkc-centos-stream-8-installer-minimal-1.4.2-11.iso
# --ip 10.89.93.80 --type linux --hypervisor kvm --vm centos-stream8-4 --link https://ubit-artifactory-or.intel.com/artifactory/linuxbkc-or-local/linux-stack-bkc-gnr/2022ww49.1/internal-images/gnr-po-bkc-centos-stream-8-installer-minimal-1.4.2-11.iso

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automation Framework for Accelerators')
    parser.add_argument('-v', action='version', version='Automation Framework:Version: 1.0')

    parser.add_argument('--ip', action='store', type=str, dest='vmip', help='IP address of the virtual machine')
    parser.add_argument('--type', action='store', type=str, dest='type', help='Unattend iso type(linux/windows)')
    parser.add_argument('--hypervisor', action='store', type=str, dest='hypervisor', help='Hypervisor for sut')
    parser.add_argument('--link', action='store', type=str, dest='unattend_link', help='Unattend iso source link')
    parser.add_argument('--vm', action='store', type=str, dest='vm_name',default='centos', help='Unattend iso source link')

    args = parser.parse_args()

    unattend = Unattend_L(vmip=args.vmip,type = args.type,vm_name = args.vm_name,hypervisor=args.hypervisor,unattend_link=args.unattend_link)
    unattend.main()



























































