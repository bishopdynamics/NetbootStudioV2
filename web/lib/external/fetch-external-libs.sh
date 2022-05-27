#!/usr/bin/env bash
# Fetch the specific versions of libraries we are using
# this should not actually be necessary, as the libraries are included in the repository already

URL_JQUERY_V1="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"
#URL_JQUERY_V2="https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js"
#URL_JQUERY_V3="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"

URL_JQUERY_V331="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.slim.min.js"

URL_JQUERY_UI_CSS="https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/themes/smoothness/jquery-ui.css"
URL_JQUERY_UI_JS="https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js"


URL_UPPY_JS="https://releases.transloadit.com/uppy/v1.24.0/uppy.min.js"
URL_UPPY_CSS="https://releases.transloadit.com/uppy/v1.24.0/uppy.min.css"

echo "Fetching external libraries..."

echo "Fetching JQuery and JQuery UI"
wget "$URL_JQUERY_V1"
wget "$URL_JQUERY_UI_JS"
wget "$URL_JQUERY_UI_CSS"

echo "Fetching Uppy"
wget "$URL_UPPY_JS"
wget "$URL_UPPY_CSS"

echo "fetching mqtt.js"
wget https://unpkg.com/mqtt/dist/mqtt.min.js

echo "done."
