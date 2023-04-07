// auth functions

//  will be defined by backend /variables.js
// _BROKER_PORT
// _BROKER_USER
// _BROKER_PASSWORD
// WEBSERVER_PORT
// APISERVER_PORT
// WEBSERVER_UPLOAD_CHUNK_SIZE

let URL_APISERVER = 'https://' + window.location.hostname + ':' + APISERVER_PORT;

if (window.location.hostname === 'localhost') {
    URL_APISERVER = 'https://' + 'james-netboot' + ':' + APISERVER_PORT;
}

const RENEW_AUTH_CYCLE = 10000; // ms, how often to renew auth token

const POST_FETCH_TIMEOUT = 5000; // ms, how long to wait for a fetch request to return

function GetAuthTokenFromSessionStorage() {
    let auth_token = null;
    if (sessionStorage.getItem('auth_token') !== null) {
        // console.log('got token from session storage');
        auth_token = sessionStorage.getItem('auth_token');
    }
    return auth_token;
}

function PutAuthTokenInSessionStorage(_auth_token) {
    sessionStorage.setItem('auth_token', _auth_token);
}

function ClearAuthTokenInSessionStorage() {
    sessionStorage.removeItem('auth_token');
}

function onAuth(value) {
    if (value === true) {
        document.getElementById('login-body-content').classList.add('hidden');
        document.getElementById('loader-body-content').classList.add('hidden');
        document.getElementById('main-body-content').classList.remove('hidden');
        main_page_default_state();
        setTimeout(RenewAuthToken, RENEW_AUTH_CYCLE);
    } else {
        ClearAuthTokenInSessionStorage();
        try {
            if (MQTT_CLIENT != null) {
                MQTT_CLIENT.end(true);
                MQTT_CLIENT = null;
            }
        } catch (e) {
            console.debug('error while disconnecting from broker: ' + e);
        }
        document.getElementById('login-body-content').classList.remove('hidden');
        document.getElementById('loader-body-content').classList.add('hidden');
        document.getElementById('main-body-content').classList.add('hidden');
    }
}

function doLoginRequest() {
    const user = document.getElementById('user_name').value;
    const password = document.getElementById('user_password').value;
    document.getElementById('user_password').value = '';
    try {
        postData('/auth', {
            'user': user,
            'password': password,
        }).then(
            function(value) {
                if (value.status === 200) {
                    if (value.data.hasOwnProperty('auth_token')) {
                        console.log('Successfully logged in, fetching main page content');
                        PutAuthTokenInSessionStorage(value.data['auth_token']);
                        onAuth(true);
                    } else {
                        M.toast({html: 'Unauthorized'});
                        console.error('Failed to login. status: 200, but no auth_token in response');
                        onAuth(false);
                    }
                } else if (value.status === 401) {
                    M.toast({html: 'Unauthorized'});
                    console.error('Unauthorized. check user and pass');
                } else {
                    if (value.status === 408) {
                        M.toast({html: 'Login Error: timed out'});
                    } else {
                        M.toast({html: 'Login Error: ' + value.status});
                    }
                    console.error('Error logging in. status: ' + value.status);
                }
            },
            function(error) {
                console.error(error);
            },
        );
    } catch (e) {
        M.toast({html: 'Login Exception: ' + e.name});
        console.error('Exception while doing login request: ' + e);
    }
}

async function RenewAuthToken() {
    // console.debug('Renewing auth token');
    let auth_status = false;
    try {
        const auth_token = GetAuthTokenFromSessionStorage();
        await postData('/auth', {
            'auth_token': auth_token,
        }).then(
            function(value) {
                if (value.status === 200) {
                    if (value.data.hasOwnProperty('auth_token')) {
                        if (value.data['auth_token'] !== '') {
                            PutAuthTokenInSessionStorage(value.data['auth_token']);
                            auth_status = true;
                        } else {
                            M.toast({html: 'Refused'});
                            console.info('empty auth_token indicates auth refused');
                            auth_status = false;
                        }
                    } else {
                        M.toast({html: 'Unauthorized'});
                        console.error('Failed to renew auth token. status: 200, but no auth_token in response');
                        auth_status = false;
                    }
                } else {
                    M.toast({html: 'Auth Error'});
                    console.error('Failed to renew auth token. status: ' + value.status);
                    auth_status = false;
                }
                onAuth(auth_status);
            },
            function(error) {
                console.error(error);
                ClearAuthTokenInSessionStorage();
                auth_status = false;
            },
        );
    } catch (e) {
        console.error('Exception while renewing auth token: ' + e);
        ClearAuthTokenInSessionStorage();
        auth_status = false;
    }
    return auth_status;
}

async function postData(url = '', data = {}, timeout=POST_FETCH_TIMEOUT) {
    // Default options are marked with *
    const auth_token = GetAuthTokenFromSessionStorage();
    const abort_controller = new AbortController();
    const timeout_id = setTimeout(() => abort_controller.abort(), timeout);
    let response = null;
    // console.log('fetching: ' + URL_APISERVER + url);
    try {
        response = await fetch(URL_APISERVER + url, {
            method: 'POST', // *GET, POST, PUT, DELETE, etc.
            mode: 'cors', // no-cors, *cors, same-origin
            cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: 'same-origin', // include, *same-origin, omit
            headers: {
                'Content-Type': 'application/json',
                'auth_token': auth_token,
            },
            redirect: 'follow', // manual, *follow, error
            referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            body: JSON.stringify(data), // body data type must match "Content-Type" header
            signal: abort_controller.signal,
        });
        clearTimeout(timeout_id);
    } catch (error) {
        // console.info(error);
        if (error.name === 'AbortError') {
            console.warn('a postData() request timed out for: ' + url);
        }
    }
    let _res = {};
    if (response === null) {
        _res = {
            status: 408,
            data: {},
        };
    } else {
        _res = {
            status: response.status,
            data: {},
        };
        if (response.status === 200) {
            _res.data = await response.json();
        }
    }
    return _res;
}

function APICall(endpoint, payload={}, callback=null) {
    // make an api call and pass the result to the callback
    const _message = new NSMessage();
    const request_id = uuid4();
    const topic = 'api_request';
    _message.set_key('sender', 'Javascript APICall');
    _message.set_key('target', 'server');
    _message.set_key('content', {
        id: request_id,
        endpoint: endpoint,
        api_payload: payload,
    });
    // register callback first
    if (request_id in REQUEST_REGISTER) {
        console.error('somehow there is already a request with this id in the register (this should be impossible): ' + request_id);
    } else {
        REQUEST_REGISTER[request_id] = callback;
        MQTT_CLIENT.publish(topic, _message.to_json());
    }
}
