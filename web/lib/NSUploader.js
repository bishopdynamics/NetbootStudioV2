// file uploader functions
//      https://github.com/tus/tus-js-client/blob/master/docs/usage.md


//  will be defined by backend /variables.js
// _BROKER_PORT
// _BROKER_USER
// _BROKER_PASSWORD
// WEBSERVER_PORT
// APISERVER_PORT
// UPLOADSEVER_PORT
// WEBSERVER_UPLOAD_CHUNK_SIZE

const URL_UPLOADSERVER = 'https://' + window.location.hostname + ':' + UPLOADSERVER_PORT;


function SetupUploader(target_div_id, file_destination, status_callback) {
    // file destination must be one of: certs, ipxe_builds, iso, packages, stage4, tftp_root, uboot_scripts, unattended_configs
    const allowed_destinations = ['certs', 'ipxe_builds', 'ipxe_stage1', 'iso', 'packages', 'stage4', 'tftp_root', 'uboot_scripts', 'unattended_configs'];
    let uppy = null;
    if (allowed_destinations.includes(file_destination)) {
        try {
            uppy = Uppy.Core({
                id: 'uppy-' + file_destination,
                nsFileDestination: file_destination,
                autoProceed: true,
                allowMultipleUploads: true,
                debug: false,
                restrictions: {
                    maxFileSize: null,
                    minFileSize: null,
                    maxTotalFileSize: null,
                    maxNumberOfFiles: null,
                    minNumberOfFiles: null,
                    allowedFileTypes: null,
                },
                onBeforeFileAdded: function(currentFile, files) {
                    console.log('onBeforeFileAdded');
                    let should_continue = true;
                    try {
                        const files_datasource = getDataSourceByName(this.nsFileDestination);
                        if (files_datasource !== null) {
                            const files_array = files_datasource.get_value();
                            files_array.forEach(function(file) {
                                if (file['filename'] === currentFile.name) {
                                    console.error('file already exists');
                                    should_continue = false;
                                }
                            });
                        } else {
                            console.error('failed to get list of current files');
                        }
                    } catch (ex) {
                        console.error('exception while onBeforeFileAdded: ' + ex);
                    }
                    if (should_continue === false) {
                        // currentFile does not have an id at this point
                        status_callback('none', currentFile.name, 'Failed', 1, 'File already exists');
                        hideModal();
                    }
                    return should_continue;
                },
                onBeforeUpload: function(files) {
                    console.log('onBeforeUpload');
                },
                infoTimeout: 5000,
            });
            uppy.use(Uppy.DragDrop, {target: '#' + target_div_id});
            uppy.use(Uppy.Tus, {
                endpoint: URL_UPLOADSERVER + '/upload_' + file_destination, chunkSize: WEBSERVER_UPLOAD_CHUNK_SIZE,
                headers: {
                    'auth_token': GetAuthTokenFromSessionStorage(),
                },
                overridePatchMethod: false,
                resume: true,
                retryDelays: [0, 1000, 3000, 5000],
                removeFingerprintOnSuccess: true, // this is critical, or the next time you try to upload a file of the same name, it will get a completely unhelpful CORS error. FUCK CORS.
            });
            uppy.on('upload-error', function(file, error, response) {
                status_callback(file.id, file.name, 'Failed', 1, 'Unknown error');
            });
            uppy.on('complete', function(result) {
                status_callback(result.successful[0].id, result.successful[0].name, 'Complete', 100, '');
            });
            uppy.on('file-added', function(file) {
                status_callback(file.id, file.name, 'Running', 0, 'Preparing...');
                hideModal();
            });
            uppy.on('upload-progress', function(file, pdata) {
                const progress = (pdata.bytesUploaded / pdata.bytesTotal * 100).toFixed(2);
                status_callback(file.id, file.name, 'Running', progress, 'Uploading...');
            });
        } catch (e) {
            console.error('Exception while setting up uploader: ' + e);
        }
    } else {
        console.error('file_destination: ' + file_destination + ' is not allowed');
    }
    return uppy;
}
