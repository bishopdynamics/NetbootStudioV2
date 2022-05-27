#!/usr/bin/env python3
"""
Netboot Studio iPXE Client Manager
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

# ignore rules:
#   docstring
#   too-broad-exception
#   line-too-long
#   too-many-branches
#   too-many-statements
#   too-many-public-methods
#   too-many-lines
#   too-many-nested-blocks
#   toddos (annotations linter handling this)
# pylint: disable=C0111,W0703,C0301,R0912,R0915,R0904,C0302,R1702,W0511

# this is what ipxe stage1 providing as url parameters:
# mac=${mac}&buildarch=${buildarch}&platform=${platform}&manufacturer=${manufacturer}&chip=${chip}&ip=${ip}&uuid=${uuid}&serial=${serial}&product=${product}&version=${version}&unixtime=${unixtime}&asset=${asset}
import sys
import uuid
import time
import json
import logging
import pathlib
import mysql.connector
from mysql.connector import errorcode
from configparser import RawConfigParser

from NSCommon import get_timestamp, get_seconds_until_timestamp
from NSPubSub import NSMQTTClient

# Database Notes
# we store all data as text; we make zero use of the database column type system
#   this is intentional, intended to simplify the future transition to a potentially totally different database system


class NSClientManager:
    """
    Netboot Studio Client Manager. Maintains and provides access to information and config for a client, indexed by mac address
    """
    # manage clients in a sqlite database in config folder
    # TODO these defaults should be set in settings tab
    # Remember that the database stores all values as text
    default_settings = {
        'boot_image': 'standby_loop',
        'boot_image_once': False,
        'unattended_config': 'blank.cfg',
        'uboot_script': 'default',
        'do_unattended': False,
        'ipxe_build_arm64': '',
        'ipxe_build_amd64': '',
        'stage4': 'none',
        'debian_mirror': 'http://deb.debian.org/debian',
        'ubuntu_mirror': 'http://archive.ubuntu.com/ubuntu',
    }
    client_states = {
        'dhcp': {
            'state_text': 'Newly Discovered via DHCP Sniffer',
            'description': 'Client requested an IP Address from DHCP Server, we only know its MAC Address at the moment',
            'state_expiration_seconds': 60,  # note this is seconds
            'state_expiration_action': 'complete',
            'active': True,
            'error': False,
        },
        'uboot': {
            'state_text': 'U-Boot Requested boot.scr.uimg',
            'description': 'Client is using u-boot bootloader, and it fetches boot.scr.uimg before anything else',
            'state_expiration_seconds': 120,
            'state_expiration_action': 'error',
            'active': True,
            'error': False,
        },
        'ipxe': {
            'state_text': 'iPXE is initializing',
            'description': 'Client has fetched the iPXE binary and it is initializing before fetching stage2',
            'state_expiration_seconds': 600,
            'state_expiration_action': 'error',
            'active': True,
            'error': False,
        },
        'stage2': {
            'state_text': 'Stage2 boot image requested',
            'description': 'Client fetched a boot image, and will not be performing an unattended installation',
            'state_expiration_seconds': 20,  # without unattended, expire double the 10s standby loop timer
            'state_expiration_action': 'complete',
            'active': True,
            'error': False,
        },
        'unattended': {
            'state_text': 'Unattended Installation',
            'description': 'Client fetched an unattended config file and is performing the installation',
            'state_expiration_seconds': 14400,  # 4hrs for unattended
            'state_expiration_action': 'error',
            'active': True,
            'error': False,
        },
        'stage4': {
            'state_text': 'Stage4 Post-Installation',
            'description': 'Client is running a Stage4 post-installation script',
            'state_expiration_seconds': 14400,  # 4hrs for stage4
            'state_expiration_action': 'error',
            'active': True,
            'error': False,
        },
        'complete': {
            'state_text': 'Complete',
            'description': 'Client successfully completed all netboot actions',
            'state_expiration_seconds': 60,  # complete state expires into inactive
            'state_expiration_action': 'inactive',
            'active': True,
            'error': False,
        },
        'inactive': {
            'state_text': 'Inactive',
            'description': 'Client is not doing Netboot Studio things',
            'state_expiration_seconds': 0,  # inactive state does not expire
            'state_expiration_action': 'none',
            'active': False,
            'error': False,
        },
        'error': {
            'state_text': 'Client encountered an error',
            'description': 'Client encountered an unknown error',
            'state_expiration_seconds': 0,  # error state doesnt expire
            'state_expiration_action': 'none',
            'active': True,
            'error': True,
        },
    }

    def __init__(self, config, paths, name, loop):
        """
        Client Manager
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths object
        :type paths: dict
        """
        # client manager has mqtt client and will send out an update message on NetbootStudio/ClientManager to signal others to refresh their data from db
        self.config = config
        self.paths = paths
        self.name = name
        self.loop = loop
        self.conn = None
        self.uuid = uuid.uuid4()
        self.clients = []  # we store a local copy
        self.settings = {}  # internal copy of settings, in sync with file
        self.settings_file = pathlib.Path(self.paths['settings.json'])
        self.read_settings()
        self.sql_host = self.config.get('main', 'netboot_server_ip')
        self.sql_port = self.config.get('database', 'port')
        self.sql_user = self.config.get('database', 'user')
        self.sql_pass = self.config.get('database', 'password')
        self.sql_db = self.config.get('database', 'database')
        self.mqtt_client_name = 'ClientManager_%s_%s' % (self.name, self.uuid)
        self.mqtt_topic = 'NetbootStudio/ClientManager'
        self.mqtt_client = NSMQTTClient(self.mqtt_client_name, self.config, self.paths, [(self.mqtt_topic, 0)], self.mqtt_receive, self.loop)
        if self.setup_database():
            logging.info('Client Manager is ready, connected to: %s@%s:%s/%s' % (self.sql_user, self.sql_host, self.sql_port, self.sql_db))
            self.get_clients_from_db()

    def stop(self):
        """
        Clean things up
        """
        logging.info('Shutting down Client Manager')
        if self.conn:
            self.conn.close()

    def mqtt_receive(self, topic, msg):
        """
        handle a mqtt message
        :param topic: mqtt topic
        :type topic: str
        :param msg: message
        :type msg: str
        """
        try:
            if topic == self.mqtt_topic:
                msg_obj = json.loads(msg)
                if msg_obj['sender'] != self.mqtt_client_name:  # ignore our own messages
                    if msg_obj['message_type'] == 'update':
                        logging.debug('received update signal from another ClientManager instance')
                        self.get_clients_from_db()
                        self.read_settings()
        except Exception as ex:
            logging.exception('exception while mqtt_receive in client manager: %s' % ex)

    def send_update_msg(self):
        try:
            message = {
                'sender': self.mqtt_client_name,
                'message_type': 'update',
            }
            message_json = json.dumps(message)
            self.mqtt_client.publish(self.mqtt_topic, message_json)
        except Exception as ex:
            logging.exception('exception while send_update_message: %s' % ex)

    def new_settings_file(self):
        # create a fresh settings file
        logging.info('creating a fresh settings file with defaults')
        self.settings = self.default_settings
        self.save_settings()

    def read_settings(self):
        logging.debug('reading settings from file: %s' % str(self.settings_file))
        if not self.settings_file.is_file():
            self.new_settings_file()
        settings = {}
        try:
            with open(self.settings_file, 'r') as sett_f:
                settings = json.load(sett_f)
        except Exception as ex:
            logging.error('exception while read_settings: %s' % ex)
        else:
            if self.validate_settings(settings):
                self.settings = settings
            else:
                logging.error('failed to read settings from file')

    def get_settings(self):
        # fetch current state of settings
        return self.settings

    def validate_settings(self, new_settings):
        # make sure all required keys are present, and no others
        a_ok = True
        logging.debug('validating settings')
        for (key, value) in new_settings.items():
            if key not in self.default_settings:
                logging.error('invalid key: %s found in new settings' % key)
                a_ok = False
        for (key, value) in self.default_settings.items():
            if key not in new_settings:
                logging.error('new settings are missing key: %s' % key)
                a_ok = False
        if a_ok:
            logging.debug('settings validation success')
        else:
            logging.debug('settings validation failed')
        return a_ok

    def set_settings(self, new_settings):
        # update current state of settings and then save
        logging.info('saving settings')
        if self.validate_settings(new_settings):
            self.settings = new_settings
            self.save_settings()
            self.send_update_msg()
            return True
        else:
            return False

    def save_settings(self):
        # save current state of settings to file
        logging.debug('writing settings to file: %s' % str(self.settings_file))
        try:
            with open(self.settings_file, 'w') as sett_f:
                json.dump(self.settings, sett_f)
        except Exception as ex:
            logging.error('exception while writing settings file: %s' % ex)
            return False
        else:
            return True

    def db_cmd_old(self, statement, vals=None):
        """
        Perform a SQL query
        :param statement: sql statement
        :type statement: str
        :param vals: list of values if needed
        :type vals: List
        :return: result object
        :rtype: {'result': List, 'success': bool, 'error':str}
        """
        # do sql db command, committing and closing as we go
        retobj = {
            'result': [],
            'success': True,
            'error': None
        }
        retry_max = 2
        retry_count = 0
        while retry_count < retry_max:
            try:
                if not self.reconnect():
                    raise Exception('failed to reconnect to database!')
                cursor = self.conn.cursor(dictionary=True)
                if vals is not None:
                    # resolved = statement % vals
                    # logging.debug('sql cmd: %s' % resolved)
                    cursor.execute(statement, vals)
                else:
                    # logging.debug('sql cmd: %s' % statement)
                    cursor.execute(statement)
                try:
                    retobj['result'] = cursor.fetchall()
                except Exception:
                    retobj['result'] = None
                    pass
                else:
                    self.conn.commit()
                try:
                    cursor.close()
                except Exception:
                    pass
                # conn.close()
            except mysql.connector.Error as err:
                error_msg = 'unknown'
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    error_msg = 'Something is wrong with your user name or password'
                    retobj['success'] = False
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    error_msg = 'Database does not exist'
                    retobj['success'] = False
                elif err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    error_msg = 'looks like the table already exists in the database'
                    retobj['success'] = True
                    pass
                if not retobj['success']:
                    logging.exception(error_msg)
                    retobj['error'] = error_msg

            except Exception:
                error_msg = 'unexpected exception while performing sql query'
                self.conn.close()
                logging.exception(error_msg)
                retobj['success'] = False
                retobj['error'] = error_msg
            retry_count += 1
            if retobj['success']:
                break
            else:
                logging.debug('sql retry num: %s' % retry_count)
                self.conn.close()
        if not retobj['success']:
            logging.debug('sql failed after %s retries' % retry_count)
        return retobj

    def db_cmd(self, statement, vals=None):
        """
        Perform a SQL query, this version performs connect, query, commit, and close all in one pass
        :param statement: sql statement
        :type statement: str
        :param vals: list of values if needed
        :type vals: List
        :return: result object
        :rtype: {'result': List, 'success': bool, 'error':str}
        """
        # do sql db command, committing and closing as we go
        retobj = {
            'result': [],
            'success': True,
            'error': None
        }
        conn = None
        try:
            conn = mysql.connector.connect(user=self.sql_user, password=self.sql_pass, host=self.sql_host, database=self.sql_db)
            cursor = conn.cursor(dictionary=True)
            if vals is not None:
                # resolved = statement % vals
                # logging.debug('sql cmd: %s' % resolved)
                cursor.execute(statement, vals)
            else:
                # logging.debug('sql cmd: %s' % statement)
                cursor.execute(statement)
            try:
                retobj['result'] = cursor.fetchall()
            except Exception:
                retobj['result'] = None
                pass
            conn.commit()
            cursor.close()
            conn.close()
            conn = None
        except mysql.connector.Error as err:
            error_msg = 'unknown'
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                error_msg = 'Something is wrong with your user name or password'
                retobj['success'] = False
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                error_msg = 'Database does not exist'
                retobj['success'] = False
            elif err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                error_msg = 'looks like the table already exists in the database'
                retobj['success'] = True
                pass
            if not retobj['success']:
                logging.exception(error_msg)
                retobj['error'] = error_msg
        except Exception:
            error_msg = 'unexpected exception while performing sql query'
            self.conn.close()
            logging.exception(error_msg)
            retobj['success'] = False
            retobj['error'] = error_msg
        if conn is not None:
            logging.debug('trying to cleanup an orphan db connection')
            try:
                conn.close()
            except Exception:
                pass
        return retobj

    def reconnect(self):
        # try to reconnect to database, and if we fail retry on a 2 second loop forever until it works
        loop_count = 0
        while True:
            loop_count += 1
            try:
                if self.conn is not None:
                    if self.conn.is_connected():
                        # logging.debug('we are already connected')
                        break
                logging.debug('reconnecting...')
                self.conn = mysql.connector.connect(user=self.sql_user, password=self.sql_pass, host=self.sql_host, database=self.sql_db)
                if self.conn.is_connected():
                    logging.debug('we are now connected')
                    break
            except Exception as ex:
                logging.error('[Reattempt %s] failed to connect to database, trying again in 2s. exception: %s' % (loop_count, ex))
            time.sleep(2)
        return True

    def setup_database(self):
        """
        Ensure that the database exists, and has the expected table.
        """
        sql_template_clients = 'CREATE TABLE clients (mac text NOT NULL, ip text NOT NULL, arch text NOT NULL, hostname text NOT NULL, info text, config text, state text )'
        retobj = self.db_cmd(sql_template_clients)
        if not retobj['success']:
            logging.critical('failed to create clients table in the SQL database, we cannot continue')
            sys.exit(1)
        return True

    def client_exists(self, client_mac):
        """
        Check if client exists in table
        :param client_mac: mac address
        :type client_mac: str
        :return: True or False if client exists in database
        :rtype: bool
        """
        exists = False
        for client in self.clients:
            if client['mac'] == client_mac:
                exists = True
                break
        return exists

    def new_client(self, client_mac, info_dhcp):
        """
        Create a new client record in table
        :param client_mac: mac address
        :type client_mac: str
        :param info_dhcp: info from dhcp discover
        :type info_dhcp: dict
        :return: True or False if succeeded
        :rtype: bool
        """
        # this only ever comes from the dhcp server, which means it does not have the ip yet.
        # the ip will be updated when when a file is requested from tftp, and when stage1 hits stage2 endpoint
        # the important part is that we have mac and arch early as possible
        sql_template_insert = 'INSERT INTO clients (mac, ip, arch, hostname, info, config, state) VALUES (%s, %s, %s, %s, %s, %s, %s)'
        if self.client_exists(client_mac):
            logging.error('client entry with mac: %s already exists' % client_mac)
            return False
        try:
            client_ip = '0.0.0.0'
            hostname = 'unknown'
            arch = info_dhcp['arch']
            info = {
                'dhcp': info_dhcp
            }
            config = {
                'boot_image': self.settings['boot_image'],
                'unattended_config': self.settings['unattended_config'],
                'do_unattended': self.settings['do_unattended'],
                'ipxe_build': self.settings['ipxe_build_%s' % arch],
                'uboot_script': self.settings['uboot_script'],
                'stage4': self.settings['stage4'],
                'boot_image_once': self.settings['boot_image_once']
            }
            state = {
                'state': {
                    'active': self.client_states['dhcp']['active'],
                    'state': 'dhcp',
                    'state_text': self.client_states['dhcp']['state_text'],
                    'state_expiration': get_timestamp(plus_seconds=self.client_states['dhcp']['state_expiration_seconds']),
                    'state_expiration_action': self.client_states['dhcp']['state_expiration_action'],
                    'error': False,
                    'error_short': '',
                    'description': self.client_states['dhcp']['description'],
                },
                'data': {
                    'comment': 'reserved for future use',
                },
            }
            self.clients.append({
                'mac': client_mac,
                'ip': client_ip,
                'hostname': hostname,
                'arch': arch,
                'info': info,
                'config': config,
                'state': state,
            })

            info_json = json.dumps(info)
            config_json = json.dumps(config)
            state_json = json.dumps(state)
            retobj = self.db_cmd(sql_template_insert, (client_mac, client_ip, arch, hostname, info_json, config_json, state_json))
            self.get_clients_from_db()
            self.send_update_msg()
            return retobj['success']
        except Exception:
            logging.exception('unexpected exception while encoding info or config')
            return False

    def set_client_config(self, client_mac, config_dict):
        """
        Set the value of config for a client; replaces existing value, so requester must first get current state before trying to set
        :param client_mac: mac address
        :type client_mac: str
        :param config_dict: config object
        :type config_dict: dict
        :return: True or False if succeeded
        :rtype: bool
        """
        sql_template = 'UPDATE clients SET config = %s WHERE mac = %s'
        if self.client_exists(client_mac):
            try:
                config_json = json.dumps(config_dict)
                logging.debug('setting client %s config to: %s' % (client_mac, config_json))
                retobj = self.db_cmd(sql_template, (config_json, client_mac))
                self.get_clients_from_db()
                self.send_update_msg()
                return retobj['success']
            except Exception:
                logging.exception('Unexpected exception while setting config for client_mac %s', client_mac)
        else:
            logging.error('client with mac: %s does not exist!' % client_mac)
        return False

    def set_client_info(self, client_mac, info_dict):
        """
        Set the value of Info for a client; replaces existing value, so requester must first get current state before trying to set
        :param client_mac: mac address
        :type client_mac: str
        :param info_dict: info object
        :type info_dict: dict
        :return: True or False if succeeded
        :rtype: bool
        """
        sql_template = 'UPDATE clients SET info = %s WHERE mac = %s'
        if self.client_exists(client_mac):
            try:
                info_json = json.dumps(info_dict)
                logging.debug('setting client %s info to: %s' % (client_mac, info_json))
                retobj = self.db_cmd(sql_template, (info_json, client_mac))
                self.get_clients_from_db()
                self.send_update_msg()
                return retobj['success']
            except Exception:
                logging.exception('Unexpected exception while setting info for client_mac %s', client_mac)
        else:
            logging.error('client with mac: %s does not exist!' % client_mac)
        return False

    def set_client_state(self, client_mac, state, state_text=None, state_expiration_seconds=None, state_expiration_action=None, error=None, error_short=None, description=None):
        """
        Set the value of State for a client; replaces existing value, so requester must first get current state before trying to set
        :param description: detailed description of what is going on
        :type description: str
        :param error_short: short description of error
        :type error_short: str
        :param error: is this an error?
        :type error: bool
        :param state_expiration_action: what to do when expired
        :type state_expiration_action: str
        :param state_expiration_seconds: how long until it expires in seconds
        :type state_expiration_seconds: int
        :param state_text: short description of current state
        :type state_text: str
        :param state: the state we are in: dhcp, uboot, ipxe, stage2, unattended, stage4, complete, or error
        :type state: str
        :param client_mac: mac address
        :type client_mac: str
        :return: True or False if succeeded
        :rtype: bool
        """
        sql_template = 'UPDATE clients SET state = %s WHERE mac = %s'
        if state not in self.client_states:
            logging.error('invalid client state: %s' % state)
            return False
        # for the given state, we use the defaults, and can be overriden if needed
        if state_text is None:
            state_text = self.client_states[state]['state_text']
        if state_expiration_seconds is None:
            state_expiration_seconds = self.client_states[state]['state_expiration_seconds']
        if state_expiration_action is None:
            state_expiration_action = self.client_states[state]['state_expiration_action']
        if error_short is None:
            error_short = ''
        if description is None:
            description = self.client_states[state]['description']
        if error is None:
            error = self.client_states[state]['error']
        active = self.client_states[state]['active']
        if state_expiration_seconds < 1:
            state_expiration = 'none'
        else:
            state_expiration = get_timestamp(plus_seconds=state_expiration_seconds)
        state_dict = {
            'state': {
                'active': active,
                'state': state,
                'state_text': state_text,
                'state_expiration': state_expiration,
                'state_expiration_action': state_expiration_action,
                'error': error,
                'error_short': error_short,
                'description': description,
            },
            'data': {
                'comment': 'reserved for future use',
            },
        }
        if self.client_exists(client_mac):
            try:
                state_json = json.dumps(state_dict)
                logging.debug('Client %s changed state to: %s, description: %s' % (client_mac, state, description))
                retobj = self.db_cmd(sql_template, (state_json, client_mac))
                self.get_clients_from_db()
                self.send_update_msg()
                return retobj['success']
            except Exception:
                logging.exception('Unexpected exception while setting info for client_mac %s', client_mac)
        else:
            logging.error('client with mac: %s does not exist!' % client_mac)
        return False

    def delete_client(self, client_mac):
        """
        Delete a client from the clients table
        :param client_mac: mac address
        :type client_mac: str
        :return: True or False if succeeded
        :rtype: bool
        """
        sql_template = 'DELETE FROM clients WHERE mac = %s'
        if self.client_exists(client_mac):
            try:
                logging.debug('deleting client %s' % client_mac)
                retobj = self.db_cmd(sql_template, (client_mac,))
                self.get_clients_from_db()
                self.send_update_msg()
                return retobj['success']
            except Exception:
                logging.exception('Unexpected exception while deleting client with mac: %s', client_mac)
        else:
            logging.error('client with mac: %s does not exist!' % client_mac)
        return False

    def set_client_ip(self, client_mac, client_ip):
        """
        Set the ip address for a client
        :param client_mac: mac address
        :type client_mac: str
        :param client_ip: ip address
        :type client_ip: str
        :return: True or False if succeeded
        :rtype: bool
        """
        sql_template = 'UPDATE clients SET ip = %s WHERE mac = %s'
        if self.client_exists(client_mac):
            try:
                logging.debug('setting client %s ip to: %s' % (client_mac, client_ip))
                retobj = self.db_cmd(sql_template, (client_ip, client_mac))
                self.get_clients_from_db()
                self.send_update_msg()
                return retobj['success']
            except Exception:
                logging.exception('Unexpected exception while setting ip for client_mac %s', client_mac)
        else:
            logging.error('client with mac: %s does not exist!' % client_mac)
        return False

    def set_client_hostname(self, client_mac, hostname):
        """
        Set hostname for a client
        :param client_mac: mac address
        :type client_mac: str
        :param hostname: hostname
        :type hostname: str
        :return: True or False if succeeded
        :rtype: bool
        """
        # set hostname for a client
        sql_template = 'UPDATE clients SET hostname = %s WHERE mac = %s'
        if self.client_exists(client_mac):
            try:
                logging.debug('setting client %s hostname to: %s' % (client_mac, hostname))
                retobj = self.db_cmd(sql_template, (hostname, client_mac))
                self.get_clients_from_db()
                self.send_update_msg()
                return retobj['success']
            except Exception:
                logging.exception('Unexpected exception while setting hostname for client_mac %s', client_mac)
        else:
            logging.error('client with mac: %s does not exist!' % client_mac)
        return False

    def get_client(self, client_mac):
        """
        Get all values for a client
        :param client_mac: mac address
        :type client_mac: str
        :return: data
        :rtype: dict
        """
        self.get_clients_from_db()
        found_client = False
        for client in self.clients:
            if client['mac'] == client_mac:
                found_client = client
                break
        if not found_client:
            logging.info('No client entry with mac: %s' % client_mac)
        return found_client

    def get_clients(self):
        # if not self.use_cache:
        self.get_clients_from_db()
        # the clients datasource is calling this method every second, we can use it to check the expirations in client states
        for client in self.clients:
            client_state = client['state']['state']['state']
            client_state_text = client['state']['state']['state_text']
            client_state_desc = client['state']['state']['description']
            expire_timestamp = client['state']['state']['state_expiration']
            if expire_timestamp != 'none':
                expire_action = client['state']['state']['state_expiration_action']
                if expire_action != 'none':
                    seconds_left = get_seconds_until_timestamp(expire_timestamp)
                    if client_state == 'complete':
                        if client['config']['boot_image_once']:
                            # this is where we reset to standby_loop
                            logging.info('Resetting Client %s boot image to standby_loop' % client['mac'])
                            client['config']['boot_image'] = 'standby_loop'
                            client['config']['boot_image_once'] = False
                            self.set_client_config(client['mac'], client['config'])
                    # logging.info('client %s state: %s expires in %s seconds' % (client['mac'], client_state, seconds_left))
                    if seconds_left < 1:
                        if expire_action == 'complete':
                            self.set_client_state(client['mac'], 'complete')
                        elif expire_action == 'inactive':
                            self.set_client_state(client['mac'], 'inactive')
                        elif expire_action == 'error':
                            error_short = 'Timeout: %s' % client_state_text
                            error_description = 'Timeout while: %s' % client_state_desc
                            self.set_client_state(client['mac'], 'error', error_short=error_short, description=error_description)
                        else:
                            logging.warning('dont know how to handle client state expiration action: %s' % expire_action)
        return self.clients

    def get_clients_from_db(self):
        """
        Refresh our local copy of clients list from the database
        """
        # return the whole contents of the client database
        sql_template = 'SELECT * FROM clients'
        try:
            retobj = self.db_cmd(sql_template)
            clients = retobj['result']
            # TODO move conversion of unixtime to datetime object elsewhere
            # in database, we store unixtime exactly as ipxe gives it to us
            # but the user wants a human readable timestamp, so we convert it at access
            # for client in client_list:
            #     hextime = client['unixtime']
            #     try:
            #         dto = datetime.datetime.fromtimestamp(int(hextime, 0))
            #         stringtime = str(dto.strftime("%Y-%m-%d %H:%M:%S %z"))
            #         client['unixtime'] = stringtime
            #     except:
            #         client['unixtime'] = hextime
            if clients is not None:
                for client in clients:
                    client['info'] = json.loads(client['info'])
                    client['config'] = json.loads(client['config'])
                    client['state'] = json.loads(client['state'])

            self.clients = clients
        except Exception:
            logging.exception('Unexpected exception while getting all clients')
