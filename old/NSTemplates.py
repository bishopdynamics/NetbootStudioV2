#!/usr/bin/env python3
# Netboot Studio library: Templates

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

TEMPLATES = {
  'boot_images': {
    'node': {
      'name': 'template-boot_images',
      'id': 'uuid4',
      'element': None,
      'element_type': 'select',
      'element_formula': {
        'css_classes': [
          'select-template',
          'select-modal',
          'select-boot_images',
        ],
        'style': {
          'display': 'block',
        },
        'label': 'Boot Image',
        'Description': 'Select a Boot Image',
        'onclick': [],
        'onhover': [],
      },
      'display_layout': {
        'layout_type': 'primary_secondary',
        'layout_data': {
          'keys_primary': ['name'],
          'keys_secondary': ['arch', 'distribution', 'release', 'version', 'subversion'],
        },
      },
      'data_schema': {
        'name': 'string',
        'comment': 'string',
        'display': 'string',
        'created': 'dto_string',
        'image_type': 'string',
        'description': 'string',
        'release': 'string',
        'distribution': 'string',
        'version': 'string',
        'subversion': 'string',
        'arch': 'string',
        'boot_image_full_path': 'path_folder',
        'boot_image_stage_path': 'url',
      },
      'value': {
        'options': [{
          'name': 'Debian-11-arm64',
          'created': '2021-09-16_22:52:57',
          'image_type': 'debian-netboot-web',
          'description': 'Manually Generated image for debian-netboot-web',
          'release': 'bullseye',
          'distribution': 'debian',
          'version': '11',
          'subversion': '1',
          'arch': 'arm64',
          'boot_image_full_path': '/opt/NetbootStudio/boot_images/Debian-11-arm64',
          'boot_image_stage_path': 'http://192.168.1.192:8082/boot_images/Debian-11-arm64',
        }]
      },
      'children': [],
    }
  }
}

NSMAIN = {
  'scripts': [
    'variables.js',
    'lib/NSCommon.js',
    'lib/NSGUI.js',
    'lib/NSAuth.js',
    'lib/NSUploader.js',
    'lib/NSMain.js'
  ],
  'external_scripts': [
    'lib/external/materialize.min.js',
    'lib/external/jquery-3.3.1.slim.min.js',
    'lib/external/uppy.min.js',
    'lib/external/jquery.json-editor.min.js',
    'lib/external/list.min.js',
    'lib/external/mqtt.min.js'
  ],
  'page': {
    'layout': 'tabs_left',
    'layout_recipe': {
      'header': [
        {
          'type': 'title',
          'content': 'Netboot Studio',
          'onclick_url': 'main.html',
          'align': 'left'
        }
      ],
      'tabs': [
        {
          'name': 'clients',
          'label': 'Clients',
          'Description': 'Manage client configurations',
          'content': [{
            'type': 'sortable_list',
            'template': TEMPLATES['clients'],
            'data_source': 'clients'
          },
          ]
        },
        {
          'name': 'boot_images',
          'label': 'Boot Images',
          'Description': 'Manage Boot Images',
          'content': [{
            'type': 'sortable_list',
            'template': TEMPLATES['boot_images'],
            'data_source': 'boot_images'
          },
          ]
        },
        {
          'name': 'unattended_configs',
          'label': 'Unattended Configuration Files',
          'Description': 'Manage Unattended Configuration Files',
          'content': [{
            'type': 'sortable_list',
            'template': TEMPLATES['unattended_configs'],
            'data_source': 'unattended_configs'
          },
          ]
        },
        {
          'name': 'ipxe_builds',
          'label': 'iPXE Builds',
          'Description': 'Manage iPXE builds',
          'content': [{
            'type': 'sortable_list',
            'template': TEMPLATES['ipxe_builds'],
            'data_source': 'ipxe_builds'
          },
          ]
        },
        {
          'name': 'ipxe_stage1',
          'label': 'iPXE Stage1 Files',
          'Description': 'Manage iPXE Stage1 Files',
          'content': [{
            'type': 'sortable_list',
            'template': TEMPLATES['ipxe_stage1'],
            'data_source': 'ipxe_stage1'
          },
          ]
        },
        {
          'name': 'settings',
          'label': 'Settings',
          'Description': 'Manage Netboot Studio settings',
          'content': [{
            'type': 'json_editor',
            'template': TEMPLATES['settings'],
            'data_source': 'settings'
          },
          ]
        },
      ],
      'taskmanager': {
        TODO
      },
      'modal': {
        TODO
      },
      'footer': [
        {
          'type': 'copyright',
          'align': 'left'
        },
        {
          'type': 'version',
          'align': 'right'
        }
      ]
    }
  }
}
