#!/usr/bin/env python3
# Common functions for rendering web pages

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020 James Bishop (james@bishopdynamics.com)

import yattag
import pathlib
import logging


def RenderFlatFile(web_config, files):
    # given a list of VALID files, return a massive string with all their content
    # returns false in any failure, or if content returned would be empty
    path_base = web_config['libpath']
    content = ''
    try:
        for _file in files:
            _filepath = path_base.joinpath(_file)
            with open(_filepath, 'r') as fh:
                content += '\n/* -----------------  RenderFlatFile: Start of %s  --------------------- */ \n' % _file
                content += fh.read()
                content += '\n/* -----------------  RenderFlatFile: End of %s  ----------------------- */\n' % _file
    except Exception as e:
        logging.exception('failed to render flat file')
        return False
    if content:
        return content
    else:
        return False


def RenderJavascript(web_config):
    # render our standard all-in-one javascript file
    # this is also where we add any dynamically generated variables
    content = '// *****************  Content below this line auto-generated by RenderJavascript  **************************\n'
    content += 'WEBSOCKET_PORT = %s;\n' % web_config['websocket_port']
    content += 'WEBSERVER_PORT = %s;\n' % web_config['webserver_port']
    content += 'APISERVER_PORT = %s;\n' % web_config['apiserver_port']
    content += 'WEBSERVER_UPLOAD_CHUNK_SIZE = %s;\n' % web_config['upload_chunk_size']
    content += '// *****************  End auto-generated content  **************************\n\n'
    content += RenderFlatFile(web_config, web_config['scripts'])
    return content


def RenderJavascriptExternal(web_config):
    # render our standard all-in-one javascript file
    content = RenderFlatFile(web_config, web_config['scripts_external'])
    return content


def RenderStylesheet(web_config):
    # render our standard all-in-one stylesheet file
    content = RenderFlatFile(web_config, web_config['stylesheets'])
    return content


def RenderStylesheetExternal(web_config):
    # render our standard all-in-one stylesheet file
    content = RenderFlatFile(web_config, web_config['stylesheets_external'])
    return content


def RenderFullPage(web_config, _body_content):
    page_title = web_config['title']
    copyright_line = '%s - %s' % (web_config['copyright'], web_config['version'])
    style_color = web_config['style_color']
    doc, tag, text = yattag.Doc().tagtext()
    # generate our standard header for all web pages
    doc.asis('<!doctype html>')
    with tag('html', lang='en'):
        with tag('head'):
            with tag('title'):
                text(page_title)
            doc.stag('meta', name='viewport', content='width = device-width, initial-scale = 1')
            doc.stag('meta', charset='utf-8')
            doc.stag('link', href='stylesheet_external.css', rel='stylesheet')
            doc.stag('link', href='stylesheet.css', rel='stylesheet')
            with tag('script', src='javascript_external.js'):
                pass
            with tag('script', src='javascript.js'):
                pass
            with tag('div', id='static-header', style='z-index:100;'):
                with tag('nav'):
                    with tag('div', klass='nav-wrapper %s' % style_color, style='width:100vw'):
                        with tag('label', klass='brand-logo', onclick='LoadBody_Tester();'):
                            doc.asis('&nbsp &nbsp')
                            text(page_title)
        # drop in the content provided
        with tag('body'):
            with tag('div', id='page-body-content-container', klass='page-body-content-container'):
                doc.asis(_body_content)
        # generate our standard footer
        with tag('footer', klass='page-footer %s' % style_color, style='position:fixed;bottom:0;left:0;width:100vw;'):
            with tag('div', klass='footer-copyright'):
                with tag('div', klass='container'):
                    with tag('span'):
                        text(copyright_line)
                with tag('div', id='heartbeat-container', klass='heartbeat-container'):
                    text('')
    # return the whole page as a string
    content = doc.getvalue()
    return content


def RenderPage_Login(web_config):
    return RenderFullPage(web_config, RenderBody_Login(web_config))


def RenderBody_Login(web_config):
    # generate the login page and return it as a string to be served
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div', id='login-body-content'):
        with tag('main', klass='main-style container'):
            with tag('div'):
                doc.asis('&nbsp')
                doc.asis('&nbsp')
            with tag('form', klass=''):
                with tag('div', klass='row'):
                    with tag('div', klass='input-field'):
                        doc.stag('input', id='user_name', type='email', autocorrect='off', autocapitalization='none', autofocus=True)
                        with tag('label', 'for="user_name"'):
                            text('User')
                with tag('div', klass='row'):
                    with tag('div', klass='input-field'):
                        doc.stag('input', id='user_password', type='password')
                        with tag('label', 'for="user_password"'):
                            text('Password')
                with tag('div', klass='row'):
                    with tag('a', id='submit_button', klass='waves-effect waves-light btn', onclick='doLoginRequest()'):
                        text('Login')
    return doc.getvalue()


def RenderBody_Main(web_config):
    # generate /index.html, which will act as our single-page app
    # klass='nav-wrapper %s' % style_color
    style_color = web_config['style_color']
    nav_color_mod = 'lighten-2'
    content_color_mod = 'lighten-5'
    tasklist_color_mod = 'lighten-4'
    background_color_mod = 'lighten-3'
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div', id='main-body-content', klass='main-body-content'):
        with tag('div'):
            # This is the left-side nav
            with tag('div', klass='%s %s center-align main-nav' % (style_color, nav_color_mod)):
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("ipxe");'):
                        text('iPXE Management')
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("stage1");'):
                        text('iPXE Stage1 Files')
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("bootimages");'):
                        text('Boot Images')
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("unattended");'):
                        text('Unattended Configs')
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("clients");'):
                        text('Clients')
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("settings");'):
                        text('Settings')
                with tag('div', klass='row'):
                    with tag('span', klass='waves-effect waves-light btn main-nav-button %s' % style_color, onclick='main_body_nav_onclick("log");'):
                        text('Log')
            # this is the right-side content
            with tag('div', klass='main-content-wrapper %s %s' % (style_color, background_color_mod), id='main-content-wrapper'):
                with tag('div', klass='z-depth-4 main-content', id='main-content'):
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-ipxe'):
                        doc.asis(RenderMainTab_iPXE(web_config))
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-stage1'):
                        doc.asis(RenderMainTab_Stage1(web_config))
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-bootimages'):
                        doc.asis(RenderMainTab_BootImages(web_config))
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-unattended'):
                        doc.asis(RenderMainTab_Unattended(web_config))
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-clients'):
                        doc.asis(RenderMainTab_Clients(web_config))
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-settings'):
                        with tag('h2'):
                            text('Settings')
                    with tag('div', klass='main-body-content-tab %s %s' % (style_color, content_color_mod), id='main-body-content-tab-log'):
                        doc.asis(RenderMainTab_Log(web_config))
            with tag('div', klass='main-tasklist %s %s' % (style_color, tasklist_color_mod), id='main-tasklist'):
                text('tasks will go here')
    return doc.getvalue()


def RenderMainTab_iPXE(web_config):
    # generate contents of ipxe management tab
    style_color = web_config['style_color']
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div'):
        with tag('h2'):
            text('Manage iPXE Builds')
        with tag('div'):
            text('This is where a neat and insightful description of this tab would go... if I had one!')
        with tag('div', id='modal_newbuild', klass='modal big-modal modal-fixed-footer'):
            with tag('div', klass='modal-content'):
                with tag('h4'):
                    text('New iPXE build')
                with tag('p'):
                    doc.stag('input', id='createbuildjob_input_commit', type='text', placeholder='Commit ID')
                    with tag('label', ('for', 'createbuildjob_input_commit')):
                        text('Commit ID')
                    doc.stag('input', id='createbuildjob_input_stage1', type='text', placeholder='Stage1 File')
                    with tag('label', ('for', 'createbuildjob_input_stage1')):
                        text('Stage1 File')
            with tag('div', klass='modal-footer'):
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!', onclick='start_build();'):
                    text('Build')
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!'):
                    text('Cancel')
        with tag('div'):
            with tag('a', klass='waves-effect waves-light modal-trigger btn %s' % style_color, href='#modal_newbuild'):
                text('New')
        with tag('div', id='main-body-content-tab-ipxe-content-wrapper'):
            with tag('div', id='main-body-content-tab-ipxe-table-wrapper'):
                pass  # to be populated by js
    return doc.getvalue()


def RenderMainTab_Stage1(web_config):
    # generate contents of ipxe stage1 tab
    style_color = web_config['style_color']
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div'):
        with tag('h2'):
            text('Manage iPXE Stage1 Files')
        with tag('div'):
            text('Stage1 files are embedded into iPXE builds, and provide the foundation for fetching Boot Images. In most cases, the built-in default Stage1 file is all that is needed.')
        with tag('div', id='modal_newstage1', klass='modal big-modal modal-fixed-footer'):
            with tag('div', klass='modal-content'):
                with tag('h4'):
                    text('New iPXE Stage1 File')
                with tag('p'):
                    text('nothing here yet')
            with tag('div', klass='modal-footer'):
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!', onclick='create_stage1();'):
                    text('Create')
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!'):
                    text('Cancel')
        with tag('div'):
            with tag('a', klass='waves-effect waves-light modal-trigger btn %s' % style_color, href='#modal_newstage1'):
                text('New')
        with tag('div', id='main-body-content-tab-stage1-content-wrapper'):
            with tag('div', id='main-body-content-tab-stage1-table-wrapper'):
                pass  # to be populated by js
    return doc.getvalue()


def RenderMainTab_BootImages(web_config):
    # generate contents of boot images tab
    style_color = web_config['style_color']
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div'):
        with tag('h2'):
            text('Manage Boot Images')
        with tag('div'):
            text('Boot Images hold everything needed to boot a specific operating system, in most cases an installer. Boot Images can also create live environments for diskless workstations')
        with tag('div', id='modal_newbootimage', klass='modal big-modal modal-fixed-footer'):
            with tag('div', klass='modal-content'):
                with tag('h4'):
                    text('New Boot Image')
                with tag('p'):
                    text('nothing here yet')
            with tag('div', klass='modal-footer'):
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!', onclick='create_bootimage();'):
                    text('Create')
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!'):
                    text('Cancel')
        with tag('div'):
            with tag('a', klass='waves-effect waves-light modal-trigger btn %s' % style_color, href='#modal_newbootimage'):
                text('New')
        with tag('div', id='main-body-content-tab-bootimages-content-wrapper'):
            with tag('div', id='main-body-content-tab-bootimages-table-wrapper'):
                pass  # to be populated by js
    return doc.getvalue()


def RenderMainTab_Unattended(web_config):
    # generate contents of unattended configs tab
    style_color = web_config['style_color']
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div'):
        with tag('h2'):
            text('Manage Unattended Installation Configurations')
        with tag('div'):
            text('When combined with a Boot Image which supports unattended installation, an unattended config file can completely automate the installation of an operating system. '
                 'Note that for most operating systems, any needed config that is not addressed by your config file, will cause it to prompt for user input, so you really need to specify '
                 'answers to all configuration options')
        with tag('div', id='modal_newunattended', klass='modal big-modal modal-fixed-footer'):
            with tag('div', klass='modal-content'):
                with tag('h4'):
                    text('New Unattended Config File')
                with tag('p'):
                    text('nothing here yet')
            with tag('div', klass='modal-footer'):
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!', onclick='create_unattended();'):
                    text('Create')
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!'):
                    text('Cancel')
        with tag('div'):
            with tag('a', klass='waves-effect waves-light modal-trigger btn %s' % style_color, href='#modal_newunattended'):
                text('New')
        with tag('div', id='main-body-content-tab-unattended-content-wrapper'):
            with tag('div', id='main-body-content-tab-unattended-table-wrapper'):
                pass  # to be populated by js
    return doc.getvalue()


def RenderMainTab_Clients(web_config):
    # generate contents of clients tab
    style_color = web_config['style_color']
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div'):
        with tag('h2'):
            text('Manage Clients')
        with tag('div'):
            text('Manage how individual clients should behave when they boot from network')
        with tag('div', id='modal_editclient', klass='modal big-modal modal-fixed-footer'):
            with tag('div', klass='modal-content'):
                with tag('h4'):
                    text('Edit Client')
                with tag('p'):
                    text('nothing here yet')
            with tag('div', klass='modal-footer'):
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!', onclick='save_client();'):
                    text('Save')
                with tag('a', klass='modal-close waves-effect waves-light btn %s' % style_color, href='#!'):
                    text('Discard')
        with tag('div'):
            pass  # saving this for later
        with tag('div', id='main-body-content-tab-clients-content-wrapper'):
            with tag('div', id='main-body-content-tab-clients-table-wrapper'):
                pass  # to be populated by js
    return doc.getvalue()


def RenderMainTab_Log(web_config):
    # generate contents of Log tab
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div'):
        with tag('h2'):
            text('Log')
        with tag('div', id='main-body-content-tab-log-content-wrapper'):
            with tag('div', id='main-body-content-tab-log-table-wrapper'):
                pass  # populated by js
        with tag('div'):
            pass  # buffer div
    return doc.getvalue()


def RenderBody_Tester(web_config):
    # generate /tester.html
    jobcreate_types = ['longjob', 'spewjob']
    doc, tag, text = yattag.Doc().tagtext()
    with tag('div', id='tester-body-content'):
        with tag('h1'):
            text('Functionality Tester Page')
        with tag('div'):
            with tag('a', klass='waves-effect waves-light btn', onclick='tester_click_tab(1);'):
                text('Websocket Echo Chat')
            with tag('a', klass='waves-effect waves-light btn', onclick='tester_click_tab(2);'):
                text('Faux Job creation')
            with tag('a', klass='waves-effect waves-light btn', onclick='tester_click_tab(3);'):
                text('Real Job creation')
            with tag('a', klass='waves-effect waves-light btn', onclick='tester_click_tab(4);'):
                text('File upload')
        # tab: websocket chat
        with tag('div'):
            with tag('div', id='tab1'):
                with tag('h2'):
                    text('Send Websocket Message (type=echo)')
                doc.stag('input', id='message_input', type='text')
                with tag('a', klass='waves-effect waves-light btn', onclick='tester_send_ws_msg();'):
                    text('Send')
            # tab: faux job creation
            with tag('div', id='tab2'):
                with tag('h2'):
                    text('Send jobcreate messages')
                for job_type in jobcreate_types:
                    with tag('div'):
                        with tag('a', klass='waves-effect waves-light btn', onclick='tester_send_ws_createjob("%s", {});' % job_type):
                            text('Create a job of type %s' % job_type)
            # tab: real job creation
            with tag('div', id='tab3'):
                with tag('h2'):
                    text('Real Job Creation')
                with tag('div'):
                    with tag('a', klass='waves-effect waves-light btn', onclick='tester_create_buildjob();'):
                        text('Create an ipxe build job')
                    doc.stag('input', id='createbuildjob_input_commit', type='text', placeholder='Commit ID')
                    doc.stag('input', id='createbuildjob_input_stage1', type='text', placeholder='Stage1 File')
            # tab: uploader
            with tag('div', id='tab4'):
                with tag('h2'):
                    text('Upload Files')
                with tag('div'):
                    with tag('div', id='file-upload-drop'):
                        text('placeholder')
                doc.stag('div')
        # console
        with tag('div', id='console'):
            with tag('h2'):
                text('Console')
            doc.stag('textarea', id='message_log', style='width:100vw; height:60vh;')
        # thats all folks
    return doc.getvalue()
