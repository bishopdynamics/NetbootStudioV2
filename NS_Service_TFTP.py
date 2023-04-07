#!/usr/bin/env python3
"""
Netboot Studio Service: TFTP Server and DHCP Sniffer
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

import os
import socket
import sys
import json
import logging
import tempfile
import argparse
import pathlib
import scapy.all
import shutil
import subprocess

from py3tftp.protocols import BaseTFTPServerProtocol, RRQProtocol
from py3tftp.exceptions import ProtocolException
from py3tftp import file_io
from py3tftp.netascii import Netascii
from threading import Thread

from NSClientManager import NSClientManager
from NSLogger import get_logger
from NSService import NSService
from NSCommon import print_object

# there are two different architecture values that can be found in a DHCP discover packet, and they dont always agree
#   the first is the option 93 'pxe_client_architecture', which is definied by the IANA
#   the second is within option 60 'vendor_class_id', which is a colon-delimited string with a 5-digit decimal value at position 2 (3rd value) representing architecture

# unfortunately, bios32 and bios64 systems report the same value, so we default to bios64 for those systems
#   arm32 and arm64 systems sometimes report bios32 in pxe_client_arch, but correctly report arm32 or arm64 within vendor_cladd_id
#   so we start by presuming bios64 for anything that reports bios in pxe_client_arch, but override if vci reports arm32 or arm64

# This means that, by default true bios32 platforms will fail to pxe boot, because they will be served a 64bit binary
#   you will have to manually correct which ipxe build is assigned to those clients, and then the arch will be changed to the arch of the selected build

# option 93 'pxe_client_architecture'
# https://www.iana.org/assignments/dhcpv6-parameters/processor-architecture.csv
pxe_client_arch_values = {
    '0x00 0x00': {
        'name': 'x86 BIOS',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x01': {
        'name': 'NEC/PC98 (DEPRECATED)',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x02': {
        'name': 'Itanium',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x03': {
        'name': 'DEC Alpha (DEPRECATED)',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x04': {
        'name': 'Arc x86 (DEPRECATED)',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x05': {
        'name': 'Intel Lean Client (DEPRECATED)',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x06': {
        'name': 'x86 UEFI',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x07': {
        'name': 'x64 UEFI',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x08': {
        'name': 'EFI Xscale (DEPRECATED)',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x09': {
        'name': 'EBC',
        'ref': '[RFC5970][RFC4578]',
    },
    '0x00 0x0a': {
        'name': 'ARM 32-bit UEFI',
        'ref': '[RFC5970]',
    },
    '0x00 0x0b': {
        'name': 'ARM 64-bit UEFI',
        'ref': '[RFC5970]',
    },
    '0x00 0x0c': {
        'name': 'PowerPC Open Firmware',
        'ref': '[Thomas_Huth]',
    },
    '0x00 0x0d': {
        'name': 'PowerPC ePAPR',
        'ref': '[Thomas_Huth]',
    },
    '0x00 0x0e': {
        'name': 'POWER OPAL v3',
        'ref': '[Jeremy_Kerr]',
    },
    '0x00 0x0f': {
        'name': 'x86 uefi boot from http',
        'ref': '[Samer_El-Haj-Mahmoud]',
    },
    '0x00 0x10': {
        'name': 'x64 uefi boot from http',
        'ref': '[Samer_El-Haj-Mahmoud]',
    },
    '0x00 0x11': {
        'name': 'ebc boot from http',
        'ref': '[Samer_El-Haj-Mahmoud]',
    },
    '0x00 0x12': {
        'name': 'arm uefi 32 boot from http',
        'ref': '[Samer_El-Haj-Mahmoud]',
    },
    '0x00 0x13': {
        'name': 'arm uefi 64 boot from http',
        'ref': '[Samer_El-Haj-Mahmoud]',
    },
    '0x00 0x14': {
        'name': 'pc/at bios boot from http',
        'ref': '[Samer_El-Haj-Mahmoud]',
    },
    '0x00 0x15': {
        'name': 'arm 32 uboot',
        'ref': '[Joseph_Shifflett]',
    },
    '0x00 0x16': {
        'name': 'arm 64 uboot',
        'ref': '[Joseph_Shifflett]',
    },
    '0x00 0x17': {
        'name': 'arm uboot 32 boot from http',
        'ref': '[Joseph_Shifflett]',
    },
    '0x00 0x18': {
        'name': 'arm uboot 64 boot from http',
        'ref': '[Joseph_Shifflett]',
    },
    '0x00 0x19': {
        'name': 'RISC-V 32-bit UEFI',
        'ref': '[Dong_Wei]',
    },
    '0x00 0x1a': {
        'name': 'RISC-V 32-bit UEFI boot from http',
        'ref': '[Dong_Wei]',
    },
    '0x00 0x1b': {
        'name': 'RISC-V 64-bit UEFI',
        'ref': '[Dong_Wei]',
    },
    '0x00 0x1c': {
        'name': 'RISC-V 64-bit UEFI boot from http',
        'ref': '[Dong_Wei]',
    },
    '0x00 0x1d': {
        'name': 'RISC-V 128-bit UEFI',
        'ref': '[Dong_Wei]'
    },
    '0x00 0x1e': {
        'name': 'RISC-V 128-bit UEFI boot from http',
        'ref': '[Dong_Wei]',
    },
    '0x00 0x1f': {
        'name': 's390 Basic',
        'ref': '[Viktor_Mihajlovski]',
    },
    '0x00 0x20': {
        'name': 's390 Extended',
        'ref': '[Viktor_Mihajlovski]',
    },
    '0x00 0x21': {
        'name': 'MIPS 32-bit UEFI',
        'ref': '[Jiading_Zhang]',
    },
    '0x00 0x22': {
        'name': 'MIPS 64-bit UEFI',
        'ref': '[Jiading_Zhang]',
    },
    '0x00 0x23': {
        'name': 'Sunway 32-bit UEFI',
        'ref': '[Jiading_Zhang]',
    },
    '0x00 0x24': {
        'name': 'Sunway 64-bit UEFI',
        'ref': '[Jiading_Zhang]',
    },
}

# option 60 'vendor_class_id'[2]
# https://dox.ipxe.org/group__dhcpopts.html
vendor_class_arch_values = {
    '00000': 'X86',
    '00001': 'PC98',
    '00002': 'IA64',
    '00003': 'ALPHA',
    '00004': 'ARCX86',
    '00005': 'LC',
    '00006': 'IA32',
    '00007': 'X86_64',
    '00008': 'XSCALE',
    '00009': 'EFI',
    '00010': 'ARM32',
    '00011': 'ARM64',
    '00025': 'RISCV32',
    '00027': 'RISCV64',
    '00029': 'RISCV128',
    '00033': 'MIPS32',
    '00034': 'MIPS64',
    '00035': 'SUNWAY32',
    '00036': 'SUNWAY64',
    '00037': 'LOONG32',
    '00039': 'LOONG64',
}

# map what pxe_client_arch_values gives us, to the arch codes we are using internally
pxe_client_arch_map = {
    'x86 UEFI': 'ia32',
    'x64 UEFI': 'amd64',
    'ARM 32-bit UEFI': 'arm32',
    'ARM 64-bit UEFI': 'arm64',
    'arm 32 uboot': 'arm32',  # u-boot reports its own arch values
    'arm 64 uboot': 'arm64',  # u-boot reports its own arch values
    'x86 BIOS': 'bios64',  # bios clients will only report "x00 x00", regardless of 32bit/64bit, so presume 64bit by default
}

# map what vendor_class_arch_values give us, to the arch codes we are using internally
vendor_class_arch_map = {
    'X86': 'bios64',  # unfortunately, 64bit clients usually report 00000 = X86, so presume 64bit by default
    'X86_64': 'amd64',  # EFI 64bit clients usually report this
    'IA32': 'ia32',  # the only EFI 32 bit
    'ARM32': 'arm32',
    'ARM64': 'arm64',
    'EFI': 'amd64',  # EFI 64bit sometimes report this
}


class NSTFTPService(NSService):
    """
    Netboot Studio TFTP Service. Serves files to clients based on config in client_manager, architecture, and the filename requested
    """
    def __init__(self, args):
        """
        TFTP Service
        :param args: command-line arguments
        :type args: Namespace
        """
        super().__init__(args)
        logging.info('Netboot Studio TFTP Server v%s', self.version)
        self.client_manager = NSClientManager(self.config, self.paths, 'NSTFTPService', self.loop)
        self.tftp_server = NSTFTPServer(self.config, self.paths, self.loop, self.client_manager)
        self.dhcp_sniffer = DHCPSniffer(self.config, self.paths, self.loop, self.client_manager)
        self.stopabbles['tftp_server'] = self.tftp_server
        self.stopabbles['client_manager'] = self.client_manager
        logging.info('TFTP Server is ready')
        self.start()


class DHCPSniffer(object):
    """
    Monitor DHCP broadcast packets and use them to create client stub entries. also monitor dhcp offers to warn about possibly misconfigured dhcp settings
    """

    def __init__(self, config, paths, loop, client_mgr):
        """
        DHCP Sniffer
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths object
        :type paths: dict
        :param loop: asyncio loop
        :type loop: AbstractEventLoop
        :param client_mgr: client manager
        :type client_mgr: NSClientManager
        """
        self.config = config
        self.paths = paths
        self.loop = loop
        self.client_manager = client_mgr
        logging.info('Starting DHCP Sniffer')
        self.dhcp_config = {
            'server': self.config.get('main', 'netboot_server_ip'),
            'file': '/ipxe.bin',
        }
        self.worker = Thread(target=self.do_scan)
        self.worker.setDaemon(True)
        self.worker.start()

    def do_scan(self):
        """
        Start scan of dhcp packets
        """
        try:
            scapy.all.sniff(filter="udp and (port 67 or 68)", prn=self.handle_dhcp_packet)
        except Exception:
            pass

    @staticmethod
    def get_option(dhcp_options, key, decode=True):
        """
        Get a DHCP option, decoding and formattinga as needed
        :param dhcp_options: dhcp options
        :type dhcp_options:
        :param key: key name
        :type key: str
        :return: key value
        :rtype: str
        """
        try:
            for i in dhcp_options:
                if i[0] == key:
                    if key == 'name_server' and len(i) > 2:
                        return ",".join(i[1:])
                    elif key == 'pxe_client_architecture':
                        # translate bytes into a string, formatted the way we expect in pxe_client_arch_values
                        val_array = str(i[1]).replace('b', '').replace('\\', '').replace('\'', '').split('x')
                        keystr = '0x%s 0x%s' % (val_array[1], val_array[2])
                        if keystr == '0x00 0x0':
                            keystr = '0x00 0x00'
                        return keystr
                    else:
                        try:
                            if decode:
                                decoded = i[1].decode('utf-8')
                                return decoded
                            else:
                                return i[1]
                        except Exception:
                            return str(i[1])
        except Exception:
            logging.exception('failed to decode dhcp option: %s' % key)
            return None

    def create_client_stub(self, info_dhcp):
        """
        Create a new client stub entry
        :param info_dhcp: info gathered via dhcp
        :type info_dhcp: dict
        """
        # client doesnt exist, lets create a stub entry
        if self.client_manager.new_client(info_dhcp['mac'], info_dhcp):
            logging.info('Created new client entry from dhcp discover')
        else:
            logging.error('Failed to create stub client entry')

    def handle_dhcp_packet(self, packet):
        """
        Hande a dhcp packet found by do_scan
        :param packet: packet
        :type packet: Packet
        """
        try:
            # DHCP Discover
            if scapy.all.DHCP in packet and packet[scapy.all.DHCP].options[0][1] == 1:
                arch_str = self.get_option(packet[scapy.all.DHCP].options, 'pxe_client_architecture')
                # print_object('DHCP Options', packet[scapy.all.DHCP].options)
                # examine pxe_client_architecture
                if arch_str in pxe_client_arch_values:
                    arch_iana = pxe_client_arch_values[arch_str]['name']
                else:
                    arch_iana = arch_str
                if arch_iana in pxe_client_arch_map:
                    arch = pxe_client_arch_map[arch_iana]
                else:
                    arch = 'unsupported'
                # examine vendor_class_id
                vci = str(self.get_option(packet[scapy.all.DHCP].options, 'vendor_class_id'))
                vci_split = vci.split(':')
                if str(vci_split[0]) != 'PXEClient':
                    logging.warning(f'Saw unexpected vci[0]: {str(vci_split[0])}')
                else:
                    vci_arch = str(vci_split[2])
                    if vci_arch not in vendor_class_arch_values:
                        logging.warning(f'Unknown PXEClient arch value: {vci_arch}')
                    else:
                        dhcp_arch = vendor_class_arch_values[vci_arch]
                        if dhcp_arch not in vendor_class_arch_map:
                            logging.warning(f'Unknown vendor_class_arch_map value: {dhcp_arch}')
                        else:
                            pxeclient_arch = vendor_class_arch_map[dhcp_arch]
                            logging.info(f'dhcp arch: {arch}, pxeclient_arch: {pxeclient_arch}')
                            if pxeclient_arch in ['arm32', 'arm64']:
                                arch = pxeclient_arch

                info_dhcp = {
                    'mac': str(packet[scapy.all.Ether].src),
                    'vci': vci,
                    'arch_bytes': arch_str,
                    'arch_iana': arch_iana,
                    'arch': arch,
                    'user_class': str(self.get_option(packet[scapy.all.DHCP].options, 'user_class')),
                }
                logging.debug('DHCP Sniffer: (discover): %s' % json.dumps(info_dhcp))
                if arch_iana in pxe_client_arch_map:
                    client_info = self.client_manager.get_client(info_dhcp['mac'])
                    if client_info:
                        client_ipxe_build = client_info['config']['ipxe_build']
                    else:
                        client_ipxe_build = None
                    if not client_ipxe_build:
                        logging.info(f'Found a new client via dhcp discover: {info_dhcp["mac"]} (arch: {info_dhcp["arch"]} ) {json.dumps(info_dhcp)}')
                        self.create_client_stub(info_dhcp)

            # DHCP Offer
            elif scapy.all.DHCP in packet and packet[scapy.all.DHCP].options[0][1] == 2:
                info_offer = {
                    'server': self.get_option(packet[scapy.all.DHCP].options, 'tftp_server_name'),
                    'file': packet.file.decode().strip().replace('\x00', ''),
                }
                if info_offer['server'] != self.dhcp_config['server']:
                    logging.warning('DHCP Sniffer saw an offer with server=%s, when config says server=%s' % (info_offer['server'], self.dhcp_config['server']))
                if info_offer['file'] != self.dhcp_config['file']:
                    logging.warning('DHCP Sniffer saw an offer with file=%s, when config says all architectures should have file=%s' % (info_offer['file'], self.dhcp_config['file']))
                logging.debug('DHCP Sniffer: (offer): %s' % json.dumps(info_offer))

            # DHCP request
            # elif scapy.all.DHCP in packet and packet[scapy.all.DHCP].options[0][1] == 3:
            #     requested_addr = self.get_option(packet[scapy.all.DHCP].options, 'requested_addr')
            #     hostname = self.get_option(packet[scapy.all.DHCP].options, 'hostname')
            #     logging.debug(f"DHCP Sniffer: (request) Host {hostname} ({packet[scapy.all.Ether].src}) requested {requested_addr}")

            # DHCP ack
            # elif scapy.all.DHCP in packet and packet[scapy.all.DHCP].options[0][1] == 5:
            #     subnet_mask = self.get_option(packet[scapy.all.DHCP].options, 'subnet_mask')
            #     lease_time = self.get_option(packet[scapy.all.DHCP].options, 'lease_time')
            #     router = self.get_option(packet[scapy.all.DHCP].options, 'router')
            #     name_server = self.get_option(packet[scapy.all.DHCP].options, 'name_server')
            #     logging.debug(f"DHCP Sniffer: (ack) DHCP Server {packet[scapy.all.IP].src} ({packet[scapy.all.Ether].src}) acked {packet[scapy.all.BOOTP].yiaddr}")
            #     logging.debug(f"DHCP Sniffer: (ack) DHCP Options: subnet_mask: {subnet_mask}, lease_time: {lease_time}, router: {router}, name_server: {name_server}")

            # DHCP inform
            # elif scapy.all.DHCP in packet and packet[scapy.all.DHCP].options[0][1] == 8:
            #     hostname = self.get_option(packet[scapy.all.DHCP].options, 'hostname')
            #     vendor_class_id = self.get_option(packet[scapy.all.DHCP].options, 'vendor_class_id')
            #     logging.debug(f"DHCP Sniffer: (inform) DHCP Inform from {packet[scapy.all.IP].src} ({packet[scapy.all.Ether].src}) hostname: {hostname}, vendor_class_id: {vendor_class_id}")

            # else:
            #     logging.debug('DHCP Sniffer: (other): %s' % packet.summary())
        except Exception:
            logging.exception('unexpected exception while handling dhcp packet')


class NSTFTPServer(object):
    """
    Our own TFTP server, modified to be much more opinionated about what file content is returned
    """
    http_thread = None
    transport = None
    protocol = None

    def __init__(self, config, paths, loop, client_mgr):
        """
        TFTP Server
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths object
        :type paths: dict
        :param loop: asyncio loop
        :type loop: AbstractEventLoop
        :param client_mgr: client manager
        :type client_mgr: NSClientManager
        """
        self.config = config
        self.paths = paths
        self.loop = loop
        self.client_manager = client_mgr
        self.host = '0.0.0.0'
        try:
            self.port = int(self.config.get('tftp', 'port'))
            logging.info('Starting TFTP Server on port %s', self.port)
            logging.debug('TFTP serving files from: %s' % self.paths['tftp_root'])
            logging.debug('TFTP serving ipxe_builds from: %s' % self.paths['ipxe_builds'])
            logging.debug('TFTP serving uboot scripts from: %s' % self.paths['uboot_scripts'])
            # TODO clear uboot_binaries files at shutdown or startup
            logging.debug('caching uboot binaries in: %s' % self.paths['uboot_binaries'])
            # quiet excessive info level messages from protocol
            logging.getLogger('py3tftp.tftp_parsing').setLevel(logging.INFO)
            logging.getLogger('py3tftp.protocols').setLevel(logging.WARNING)
            # TODO these options should live in the config file
            # default_opts = {b'ack_timeout': 0.5, b'timeout': 5.0, b'blksize': 512,b'windowsize': 1}
            self.extra_opts = {
                b'timeout': 120.0,
                b'ack_timeout': 30.0,
                b'conn_timeout': 120.0,
                b'blksize': 65464,
                b'windowsize': 1,
            }
            self._prepare_async_tasks()
        except Exception:
            logging.exception('Unexpected Exception while starting TFTP Server')

    def _prepare_async_tasks(self):
        """
        Prepare async tasks for TFTP Server
        """
        listen = self.loop.create_datagram_endpoint(
            lambda: NSTFTPServerProtocol(self.host, self.loop, self.extra_opts, self.config, self.paths, self.client_manager),
            local_addr=(self.host, self.port,))
        self.transport, self.protocol = self.loop.run_until_complete(listen)

    def stop(self):
        """
        Clean things up
        """
        logging.debug('Shutting down TFTP Server...')
        self.client_manager.stop()
        self.transport.close()


class NSTFTPServerProtocol(BaseTFTPServerProtocol):
    """
    Modified BaseTFTPServerProtocol to use our modified RRQProtocol
    """
    transport = None

    def __init__(self, host_interface, loop, extra_opts, config, paths, client_mgr):
        """
        TFTP Server Protocol
        :param host_interface:
        :type host_interface:
        :param loop: asyncio loop
        :type loop: AbstractEventLoop
        :param extra_opts:
        :type extra_opts:
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths object
        :type paths: dict
        :param client_mgr: client manager
        :type client_mgr: NSClientManager
        """
        super().__init__(host_interface, loop, extra_opts)
        self.config = config
        self.paths = paths
        self.client_manager = client_mgr

    def datagram_received(self, data, addr):
        """
        Opens a read or write connection to remote host by scheduling an asyncio.Protocol.
        :param data: data
        :type data: bytes
        :param addr: address
        :type addr: tuple[str, int]
        """
        first_packet = self.packet_factory.from_bytes(data)
        protocol = self.select_protocol(first_packet)
        file_handler_cls = self.select_file_handler(first_packet)

        connect = self.loop.create_datagram_endpoint(
            lambda: protocol(data, file_handler_cls, addr, self.extra_opts, self.config, self.paths, client_mgr=self.client_manager),
            local_addr=(self.host_interface,
                        0,))

        self.loop.create_task(connect)

    def select_protocol(self, packet):
        """
        Select TFTP Protocol (read or write) (write is disabled)
        :param packet: packet
        :type packet: Packet
        :return: protocol
        :rtype: class
        """
        if packet.is_rrq():
            return NSRRQProtocol
        # we dont want the write protocol to work, so we just ignore it
        # elif packet.is_wrq():
        #     return WRQProtocol
        else:
            raise ProtocolException('Received incompatible request, ignoring.')

    def select_file_handler(self, packet):
        """
        Select file handler for this packet
        :param packet: packet
        :type packet: Packet
        :return: handler
        :rtype: class
        """
        if packet.is_wrq():
            return lambda filename, opts: file_io.FileWriter(
                filename, opts, packet.mode)
        else:
            return lambda filename, opts: NSFileReader(
                filename, opts, packet.mode)

    def connection_made(self, transport):
        """
        Callback for when connection has been made
        :param transport: transport
        :type transport:
        """
        logging.info('Listening...')
        self.transport = transport

    def connection_lost(self, exc):
        """
        Callback for when connection has been lost
        :param exc:
        :type exc:
        """
        logging.info('TFTP server - connection lost')


class NSRRQProtocol(RRQProtocol):
    """
    Modified RRQProtocol to return alternate file content based on filename, client config, and client architecture
    """
    # tweak so we can modify what file is loaded on the fly
    r_opts = None
    opts = None
    uboot_script_default = """
    echo ""
    echo "#######################################################################"
    echo "               Start of Netboot Studio uboot script"
    echo ""
    echo " this script does nothing, but you can select a different uboot script per-client if desired"
    echo ""
    echo "checkout some vars:"
    echo "arch: ${arch}"
    echo "board: ${board}"
    echo "cpu: ${cpu}"
    echo "soc: ${soc}"
    echo "fdtfile: ${fdtfile}"
    echo "ethaddr: ${ethaddr}"
    echo "bootfile: ${bootfile}"
    echo ""
    echo "               End of Netboot Studio uboot script"
    echo "#######################################################################"
    
    """

    def __init__(self, rrq, file_handler_cls, addr, opts, config, paths, client_mgr=None):
        """
        Read Protocol for TFTP
        :param rrq:
        :type rrq:
        :param file_handler_cls:
        :type file_handler_cls:
        :param addr:
        :type addr:
        :param opts:
        :type opts:
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths object
        :type paths: dict
        :param client_mgr: client manager
        :type client_mgr: NSClientManager
        """
        super().__init__(rrq, file_handler_cls, addr, opts)
        self.config = config
        self.paths = paths
        self.file_root = pathlib.Path(self.paths['tftp_root'])
        self.ipxe_builds = pathlib.Path(self.paths['ipxe_builds'])
        self.uboot_scripts = pathlib.Path(self.paths['uboot_scripts'])
        self.uboot_binaries = pathlib.Path(self.paths['uboot_binaries'])
        self.client_manager = client_mgr
        self.dhcp_config = {
            'server': self.config.get('main', 'netboot_server_ip'),
            'file': '/ipxe.bin',
        }
        self.remote_ip = str(self.remote_addr[0])
        self.remote_mac_address = scapy.all.getmacbyip(self.remote_ip)
        self.hostname = self.get_hostname()
        self.requested_filename = self.packet.fname.decode('ascii').strip('/')
        self.remote_arch = None
        self.client_ipxe_build = None
        # in dhcp config, and in config.ini we should have '/ipxe.bin'
        if self.requested_filename == self.dhcp_config['file'].strip('/'):
            ipxe_file = self.choose_ipxe_file()
            if ipxe_file:
                self.filename = ipxe_file
            else:
                self.filename = self.get_tftp_file()
        elif self.requested_filename == 'boot.scr.uimg':
            self.filename = self.get_uboot_script()
        else:
            self.filename = self.get_tftp_file()

    def get_uboot_script(self):
        """
        Handler for special file: boot.scr.uimg, which u-boot fetches before anything else
        :return: file name
        :rtype: str
        """
        #   build command: mkimage -A arm -O linux -T script -C none -d boot.cmd boot.scr.uimg
        success = False
        # TODO this shouldbe named client_data
        client_info = self.client_manager.get_client(self.remote_mac_address)
        cmd = 'mkimage -A arm -O linux -T script -C none -d boot.cmd boot.scr.uimg'
        with tempfile.TemporaryDirectory() as temp:
            # with scope will make sure upload_temp is cleaned up at exit
            tempfolder = pathlib.Path(temp)
            temp_script = tempfolder.joinpath('boot.cmd')
            output_file = tempfolder.joinpath('boot.scr.uimg')
            if client_info['config']['uboot_script'] == 'default':
                self.log_info('serving default (empty) uboot_script')
                try:
                    with open(temp_script, 'w') as out:
                        out.write(self.uboot_script_default)
                    result = True
                except Exception as ex:
                    logging.error('exception while writing default uboot_script to temp file: %s' % ex)
                    result = False
                    pass
            else:
                uboot_script_path = self.uboot_scripts.joinpath(client_info['config']['uboot_script'])
                self.log_info('serving uboot_script: %s' % uboot_script_path)
                result = shutil.copyfile(uboot_script_path, temp_script)
            if result:
                binary_filepath = self.uboot_binaries.joinpath('%s.uimg' % client_info['config']['uboot_script'])
                result = subprocess.run('%s 2>&1' % cmd, shell=True, universal_newlines=True, cwd=tempfolder, capture_output=True, text=True)
                if result.returncode == 0:
                    if shutil.copyfile(output_file, binary_filepath):
                        logging.debug('successfully built boot.scr.uimg')
                        success = True
                    else:
                        logging.error('failed to copy %s to %s' % (output_file, binary_filepath))
                else:
                    logging.error('failed mkimage command')
            else:
                logging.error('failed to copy %s to %s' % (uboot_script_path, temp_script))
        if success:
            filename = binary_filepath
            self.client_manager.set_client_state(client_info['mac'], 'uboot')
        else:
            filename = self.get_tftp_file()
        return filename

    def get_tftp_file(self):
        """
        Get a regular file from the tftp root
        :return: file name
        :rtype: str
        """
        # look for the filename within tftp_root/
        #   no need to check if it exists, py3tftp.protocols will do that for us, and display its own error
        self.log_info('Serving file from tftp_root: %s' % self.requested_filename)
        filename = pathlib.Path(self.file_root).joinpath(self.requested_filename)
        return filename

    def format_log_message(self, message):
        """
        Format a message to include info about client
        :param message: message
        :type message: str
        :return: formatted message
        :rtype: str
        """
        return 'Client: %s (ip: %s, arch: %s) -> %s' % (self.remote_mac_address, self.remote_ip, self.remote_arch, message)

    def log_info(self, message):
        """
        Format an info level message
        :param message:
        :type message:
        """
        logging.info(self.format_log_message(message))

    def log_warn(self, message):
        """
        Format a warning level message
        :param message:
        :type message:
        """
        logging.warning(self.format_log_message(message))

    def log_error(self, message):
        """
        Format an error level message
        :param message:
        :type message:
        """
        logging.error(self.format_log_message(message))

    def get_hostname(self):
        """
        Get client hostname (by looking up client ip)
        :return: client hostname
        :rtype: str
        """
        try:
            hostname = socket.gethostbyaddr(self.remote_ip)[0]
        except Exception:
            hostname = 'unknown'
        return hostname

    def choose_ipxe_file(self):
        """
        Chose which ipxe binary to return to a client (from ipxe builds)
        :return: file path
        :rtype: Path
        """
        # figure out what file to serve this client
        #   by time we get here, there should always be a client entry populated by dhcp already
        #   this is where the ip is set for the first time
        settings = self.client_manager.get_settings()
        defaults = {
            'arm64': settings['ipxe_build_arm64'],
            'amd64': settings['ipxe_build_amd64'],
            'bios32': settings['ipxe_build_bios32'],
            'bios64': settings['ipxe_build_bios64'],
        }
        try:
            client_info = self.client_manager.get_client(self.remote_mac_address)
            if client_info:
                client_info['ip'] = self.remote_ip
                client_info['hostname'] = self.hostname
                self.client_manager.set_client_ip(self.remote_mac_address, self.remote_ip)
                self.client_manager.set_client_hostname(self.remote_mac_address, self.hostname)
                self.remote_arch = client_info['arch']
                self.client_ipxe_build = client_info['config']['ipxe_build']
            else:
                self.log_error('client does not have an entry in database: %s' % self.remote_mac_address)
                self.log_error('  this indicates dhcp sniffer may not be working correctly!!')
                return None
        except Exception:
            logging.exception('something went wrong while trying to look up client: %s' % self.remote_mac_address)
            return None
        else:
            if not pathlib.Path(self.ipxe_builds).joinpath(self.client_ipxe_build).joinpath('metadata.json').is_file():
                default_ipxe_build = defaults[self.remote_arch]
                self.log_warn('could not find build with id: %s, falling back to default[%s]: %s' % (self.client_ipxe_build, self.remote_arch, default_ipxe_build))
                if not pathlib.Path(self.ipxe_builds).joinpath(default_ipxe_build).joinpath('metadata.json').is_file():
                    self.log_error('default ipxe builds does not exist: %s' % default_ipxe_build)
                else:
                    self.client_ipxe_build = default_ipxe_build
            # we always serve ipxe.bin from the given build. up to build stage to make that the correct format
            filename = pathlib.Path(self.ipxe_builds).joinpath(self.client_ipxe_build).joinpath('ipxe.bin')
            if not filename.is_file():
                self.log_error('Failed to find file: %s' % filename)
            else:
                self.log_info('Serving ipxe_build file: %s' % filename)
                self.client_manager.set_client_state(client_info['mac'], 'ipxe')
            return filename

    def set_proto_attributes(self):
        """
        Sets the self.filename , self.opts, and self.r_opts.
        The caller should handle any exceptions and react accordingly
        ie. send error packet, close connection, etc.
        """
        self.r_opts = self.packet.r_opts
        self.opts = {**self.default_opts, **self.extra_opts, **self.r_opts}
        # logging.debug('Set protocol attributes as {attrs}'.format(attrs=self.opts))


class NSFileReader(object):
    """
    A wrapper around a regular file that implements:
    - read_chunk - for closing the file when bytes read is less than chunk_size.
    - finished - for easier notifications interfaces.
    When it goes out of scope, it ensures the file is closed.
    """

    def __init__(self, fname, chunk_size=0, mode=None):
        """
        TFTP File Reader
        :param fname: file path
        :type fname: Path
        :param chunk_size: chunk size
        :type chunk_size: int
        :param mode: protocol mode
        :type mode: bytes
        """
        self.fname = fname
        logging.debug('Handling request for: %s' % self.fname)
        self.chunk_size = chunk_size
        self._f = None
        self._f = self._open_file()
        self.finished = False

        if mode == b'netascii':
            self._f = Netascii(self._f)

    def _open_file(self):
        """
        Open a file
        :return: file IO handle
        :rtype: IO
        """
        return open(self.fname, 'rb')

    def file_size(self):
        """
        Get size of file
        :return: file size
        :rtype: int
        """
        return os.stat(self.fname).st_size

    def read_chunk(self, size=None):
        """
        Read a chunk of a file
        :param size: chunk size
        :type size: int
        :return: data
        :rtype: Union[int, bytes]
        """
        size = size or self.chunk_size
        if self.finished:
            return b''
        data = self._f.read(size)
        if not data or (size > 0 and len(data) < size):
            self._f.close()
            self.finished = True
        return data

    def __del__(self):
        """
        Cleanup file handle when delete is called on this object
        """
        if self._f and not self._f.closed:
            self._f.close()


if __name__ == "__main__":
    # this is the main entry point
    ARG_PARSER = argparse.ArgumentParser(description='Netboot Studio TFTP Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ARG_PARSER.add_argument('-m', dest='mode', action='store',
                            type=str, default='prod', choices=['prod', 'dev'],
                            help='which mode to run in')
    ARG_PARSER.add_argument('-c', dest='configdir', action='store',
                            type=str, default='/opt/NetbootStudio',
                            help='path to config folder')
    ARGS = ARG_PARSER.parse_args()
    if ARGS.mode == 'dev':
        # dev mode is debug level logging
        LOG_LEVEL = logging.DEBUG
    else:
        LOG_LEVEL = logging.INFO
    logger = get_logger(name=__name__, level=LOG_LEVEL)
    assert sys.version_info >= (3, 8), "Script requires Python 3.8+."
    NS = NSTFTPService(ARGS)
