#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################
import os
from bson.objectid import ObjectId

from girder_client import GirderClient

__version__ = '0.0.1'
__license__ = 'Apache 2.0'

appName = 'Slicer'


class Constant:
    """
    A bunch of utilities constant, as to handle ``Error`` or set default parameters.
    """

    # Success
    EXTENSION_AREADY_UP_TO_DATE = 30
    EXTENSION_NOW_UP_TO_DATE = 31

    # Default
    CURRENT_FOLDER = os.getcwd()
    DRAFT_RELEASE_NAME = 'draft'
    DEFAULT_LIMIT = 50


class SlicerPackageClient(GirderClient):
    """
    The SlicerPackageClient allow to us the GirderClient with specific functions to use the
    slicer_package_manager plugin of Girder. This allow to manage 3 top level entity:

        * Application
        * Release
        * Extension

    To know more about the it : TODO: LINK to README
    """

    def __init__(self, host=None, port=None, apiRoot=None, scheme=None, apiUrl=None,
                 progressReporterCls=None):
        super(SlicerPackageClient, self).__init__(
            host=host, port=port, apiRoot=apiRoot, scheme=scheme, apiUrl=apiUrl,
            progressReporterCls=progressReporterCls)

    def createApp(self, name, desc=None):
        """
        Create a new application in the default collection ``Applications``.
        The application will contain a ``draft`` release (folder).
        A template of the name of each future uploaded extension will be set as a metadata of
        this new application.

        :param name: name of the new application
        :param desc: Optional description of the application
        :return:  The new application
        """
        apps = self.listApp(name=name)
        if apps:
            raise Exception('The Application "%s" already exist.' % name)
        return self.post('/app', parameters={
            'name': name,
            'app_description': desc
        })

    def listApp(self, name=None):
        """
        1. List all the applications within the default collection ``Applications``.
        2. Get the application by name.

        :param name: application mame
        :return:  A list of applications
        """
        apps = self.get('/app', parameters={
            'name': name
        })
        return apps

    def _getApp(self, app_name):
        """
        Private method to get a single application by Name.

        :param app_name: Name of the application
        :return: A single application
        """
        apps = self.listApp(app_name)
        if not apps:
            raise Exception('The Application "%s" doesn\'t exist.' % app_name)
        return apps[0]

    def deleteApp(self, name):
        """
        Delete the application by ID.

        :param name: application name
        :return: The deleted application
        """
        app = self._getApp(name)
        self.delete('/app/%s' % app['_id'])
        return app

    def createRelease(self, app_name, name, revision, desc=None):
        """
        Create a new release within the application corresponding to ``app_name``.

        :param app_name: Name of the application
        :param name: Name of the release
        :param revision: Revision of the application
        :param desc: Description of the release
        :return: The new release
        """
        app = self._getApp(app_name)
        releases = self.listRelease(app_name=app_name, name=name)
        if releases:
            raise Exception('The release "%s" already exist.' % name)
        return self.post('/app/%s/release' % app['_id'], parameters={
            'name': name,
            'app_revision': revision,
            'description': desc
        })

    def listRelease(self, app_name, name=None):
        """
        1. List all the release within an application.
        2. Get the release by name.

        :param app_name: Name of the application
        :param name: Name of the release
        :return: A list of all the release within the application
        """
        app = self._getApp(app_name)
        if name:
            releases = self.get(
                '/app/%s/release' % app['_id'],
                parameters={'release_id_or_name': name})
        else:
            releases = self.get('/app/%s/release' % app['_id'])
            draft_releases = self.get('/app/%s/release/revision' % app['_id'])
            releases += draft_releases
        return releases

    def getRevisions(self, app_name, offset=0):
        app = self._getApp(app_name)
        return self.get(
            '/app/%s/release/revision' % app['_id'],
            parameters={'offset': offset}
        )

    def deleteRelease(self, app_name, name):
        """
        Delete a release within an application.

        :param app_name: Name of the application
        :param name: Name of the release
        :return: The deleted release
        """
        app = self._getApp(app_name)
        release = self.listRelease(app_name, name)
        if not release:
            raise Exception('The release "%s" doesn\'t exist.')
        self.delete('/app/%s/release/%s' % (app['_id'], name))
        return release

    def uploadExtension(self, filepath, app_name, ext_os, arch, name, repo_type, repo_url, revision,
                        app_revision, packagetype='', codebase='', desc='', force=False):
        """
        Upload an extension by providing a path to the file. It can also be used to update an
        existing one, in this case the upload is done only if the extension has a different revision
        than the old one.

        :param filepath: The path to the file
        :param app_name: The name of the application
        :param ext_os: The target operating system of the package
        :param arch: The os chip architecture
        :param name: The baseName of the extension
        :param repo_type: Type of the repository
        :param repo_url: Url of the repository
        :param revision: The revision of the extension
        :param app_revision: The revision of the application supported by the extension
        :param packagetype: Type of the package
        :param codebase: Codebase of the extension name
        :param desc: The description of the extension
        :return: The uploaded extension
        """
        def _displayProgress(*args, **kwargs):
            pass

        app = self._getApp(app_name)
        # Get potential existing extension
        extensions = self.listExtension(
            app_name,
            name=name,
            ext_os=ext_os,
            arch=arch,
            app_revision=app_revision)
        if not extensions:
            # Create the extension into Girder hierarchy
            extension = self.post('/app/%s/extension' % app['_id'], parameters={
                'os': ext_os,
                'arch': arch,
                'baseName': name,
                'repository_type': repo_type,
                'repository_url': repo_url,
                'revision': revision,
                'app_revision': app_revision,
                'packagetype': packagetype,
                'codebase': codebase,
                'description': desc
            })

            # Upload the extension
            self.uploadFileToItem(
                extension['_id'],
                filepath,
                reference='',
                mimeType='application/octet-stream',
                progressCallback=_displayProgress)
        else:
            extension = extensions[0]
            # Revision different or force upload
            if revision != extension['meta']['revision'] or force:
                files = list(self.listFile(extension['_id']))
                if files:
                    oldFile = files[0]
                    filename = 'new_file'
                else:
                    filename = None

                # Upload the extension
                newFile = self.uploadFileToItem(
                    extension['_id'],
                    filepath,
                    reference='',
                    filename=filename,
                    mimeType='application/octet-stream',
                    progressCallback=_displayProgress)

                # Update the extension into Girder hierarchy
                extension = self.post('/app/%s/extension' % app['_id'], parameters={
                    'os': ext_os,
                    'arch': arch,
                    'baseName': name,
                    'repository_type': repo_type,
                    'repository_url': repo_url,
                    'revision': revision,
                    'app_revision': app_revision,
                    'packagetype': packagetype,
                    'codebase': codebase,
                    'description': desc
                })

                files = list(self.listFile(extension['_id']))
                if len(files) == 2:
                    # Remove the oldFIle
                    self.delete('/file/%s' % oldFile['_id'])
                    # Change the name
                    self.put('/file/%s' % newFile['_id'], parameters={
                        'name': os.path.basename(filepath)
                    })
                    return Constant.EXTENSION_NOW_UP_TO_DATE
            else:
                return Constant.EXTENSION_AREADY_UP_TO_DATE

        return extension

    def downloadExtension(self, app_name, id_or_name, dir_path=Constant.CURRENT_FOLDER):
        """
        Download an extension by ID and store it in the given option ``dir_path``.
        When we use the extension id in ``id_or_name``, the parameter ``app_name`` is ignored.

        :param app_name: Name of the application
        :param id_or_name: ID or name of the extension
        :param dir_path: Path of the directory when the extension has to be downloaded
        :return: The downloaded extension
        """
        app = self._getApp(app_name)

        if ObjectId.is_valid(id_or_name):
            ext = self.get('/resource/%s' % id_or_name, parameters={'type': 'item'})
        else:
            ext = self.get(
                '/app/%s/extension' % app['_id'],
                parameters={'extension_name': id_or_name})
            if ext:
                ext = ext[0]
        if not ext:
            raise Exception('The extension "%s" doesn\'t exist.' % id_or_name)
        files = self.get('/item/%s/files' % ext['_id'])
        if not files:
            raise Exception('The extension "%s" doesn\'t contain any file.' % id_or_name)
        file = files[0]
        self.downloadFile(
            file['_id'],
            os.path.join(dir_path, '%s.%s' % (ext['name'], file['name'].split('.')[1])))
        return ext

    def listExtension(self, app_name, name=None, ext_os=None, arch=None, app_revision=None,
                      release=Constant.DRAFT_RELEASE_NAME, limit=Constant.DEFAULT_LIMIT, all=False):
        """
        List all the extension for a specific release and filter them with some option
        (os, arch, ...). By default the extensions within ``draft`` release are listed.
        It's also possible to specify the ``--all`` option to list all the extensions from all
        the release of an application.
        To use the ``--id`` functionality you must provide a valid fullname of the extension.

        :param app_name: Name of the application
        :param name: Base name of the extension
        :param ext_os: The target operating system of the package
        :param arch: The os chip architecture
        :param app_revision: Revision of the application
        :param release: Name of the release
        :param limit: Limit of the number of extensions listed
        :param all: Boolean that allow to list extensions from all the release
        :return: A list of extensions filtered by optional parameters
        """
        app = self._getApp(app_name)

        if all:
            release_id = None
        else:
            release_folder = self.listRelease(app_name, release)
            if release_folder:
                release_id = release_folder['_id']
            else:
                raise Exception('The release "%s" doesn\'t exist.' % release)

        extensions = self.get('/app/%s/extension' % app['_id'], parameters={
            'os': ext_os,
            'arch': arch,
            'baseName': name,
            'app_revision': app_revision,
            'release_id': release_id,
            'limit': limit,
            'sort': 'created',
            'sortDir': -1
        })
        return extensions

    def deleteExtension(self, app_name, id_or_name):
        """
        Delete an extension within an application.

        :param app_name: Name of the application
        :param id_or_name: Extension ID or name
        :return: The deleted extension
        """
        app = self._getApp(app_name)

        if ObjectId.is_valid(id_or_name):
            ext = self.get(
                '/app/%s/extension' % app['_id'],
                parameters={'extension_id': id_or_name})
        else:
            ext = self.get(
                '/app/%s/extension' % app['_id'],
                parameters={'extension_name': id_or_name})
        if not ext:
            raise Exception('The extension "%s" doesn\'t exist.' % id_or_name)
        ext = ext[0]
        self.delete('/app/%s/extension/%s' % (app['_id'], ext['_id']))
        return ext